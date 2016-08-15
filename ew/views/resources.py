'''
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import re 
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect, resolve_url
from django.conf import settings
from arches.app.models import models
from ew.models.concept import Concept
from ew.models.resource import Resource
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.JSONResponse import JSONResponse
from arches.app.views.search import _get_child_concepts
from arches.app.views.concept import get_preflabel_from_valueid
from arches.app.views.concept import get_preflabel_from_conceptid
from arches.app.views.resources import get_related_resources
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Query, Terms, Bool, Match, Nested
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Max, Min
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from ew.views.search_utils import get_auto_filter
from django.core.mail import EmailMultiAlternatives
from django.core import mail
from ew.utils import html2text

class UserNotAuthorized(Exception):
    """Base class for exceptions in this module."""
    pass

errors = []

def empty_errors_cache():
    cache.delete('resourceid')
    cache.delete('errors')

def get_possible_actions(current_status, errorsExists, user):
    actions = []
    if (current_status == 'Draft' and not errorsExists): 
        actions.append('ready-for-approval')
    if (current_status == 'Pending approval' and not errorsExists): 
        actions.append('reject-approval')
        actions.append('publish')
    if ((current_status == 'Approval rejected' or current_status == 'Published') and not errorsExists): 
        actions.append('return-to-draft')
    return actions

def get_user_can_edit_document(current_status, current_group, user, resourcetypeid, user_groups, group_ownership):
    if (current_status == 'Draft' and current_group == group_ownership): 
        return True
    else:
        # Posebnim uporabnikom dovolimo vse
        if (user.is_staff and current_group == group_ownership): 
            print "Posebni uporabnik (staff)"
            return True
     	if (user.is_superuser): 
            print "Posebni uporabnik (superuser)"
            return True
     	# Ce uporabnik nima iste skupine kot dokument, nima pravice urejanja
     	if (current_group != group_ownership):
     	    return False
     	# Pri vseh statusih, ki niso draft, zahtevamo tudi pravico PUBLISH
 	    user_can_edit_document = false
        if 'PUBLISH_' + resourcetypeid in user_groups:
            return True
        else:
            return False

@permission_required('edit')
@csrf_exempt
def resource_manager(request, resourcetypeid='', form_id='default', resourceid=''):

    if resourceid != '':
        resource = Resource(resourceid)
    elif resourcetypeid != '':
        resource = Resource({'entitytypeid': resourcetypeid})

    if form_id == 'default':
        form_id = resource.form_groups[0]['forms'][0]['id']
    form = resource.get_form(form_id)

    # Pravice preverjamo zaenkrat le preko grup
    # Uporabnik mora imeti dodeljeno grupo z nazivom tipa resourca
    if (request.user.username != 'anonymous'):
        user = User.objects.get(username=request.user.username)
        user_groups = user.groups.values_list('name', flat=True)
    else:
        user_groups = []

    if (not 'EDIT_' + resourcetypeid in user_groups and not 'PUBLISH_' + resourcetypeid in user_groups and not request.user.is_staff and not request.user.is_superuser):
		raise UserNotAuthorized('User does have permission for this resource!')

    group_ownerships = 0
    group_ownership = ''
    for group in user_groups:
        if group.startswith('OWNERSHIP_'):
            group_ownership = group[10:]
            group_ownerships = group_ownerships + 1
    
    if (group_ownerships == 0 and (resourceid == '' or (resourceid != '' and not request.user.is_staff and not request.user.is_superuser))):
		raise UserNotAuthorized('User does have a ownership group! Please contact Early Watercraft administrator to resolve this issue.')
    
    if (group_ownerships > 1 and (resourceid == '' or (resourceid != '' and not request.user.is_staff and not request.user.is_superuser))):
		raise UserNotAuthorized('User have more than one ownership group! Please contact Early Watercraft administrator to resolve this issue.')

    if request.method == 'DELETE':
        resource.delete_index()
        se = SearchEngineFactory().create()
        realtionships = resource.get_related_resources(return_entities=False)
        for realtionship in realtionships:
            se.delete(index='resource_relations', doc_type='all', id=realtionship.resourcexid)
            realtionship.delete()
        resource.delete()
        return JSONResponse({ 'success': True })

    if request.method == 'POST':
        data = JSONDeserializer().deserialize(request.POST.get('formdata', {}))
        current_status = resource.get_current_status()
        if (resourceid != ''):
            current_group = resource.get_current_group()
        else:
            current_group = group_ownership
        user_can_edit_document = get_user_can_edit_document(current_status, current_group, user, resourcetypeid, user_groups, group_ownership)
        if (not user_can_edit_document):
            return HttpResponseNotFound('<h1>User can not edit this document!</h1>')
        if 'action' in request.POST:
            action = request.POST.get('action')
            
            if action == 'ready-for-approval':
                current_status = 'Pending approval'
                resource.set_resource_status(current_status, user)
                empty_errors_cache()
                errors = []
                actions = get_possible_actions(current_status, False, user)
                if settings.EMAIL_ENABLED:
                    resource_url = request.build_absolute_uri(resolve_url('resource_manager', resourcetypeid=resourcetypeid, form_id='summary', resourceid=resourceid))
                    # Dobimo seznam vseh publisherjev v trenutni skupini uporabnika
                    if group_ownership <> '':
                        search_group = 'OWNERSHIP_' + group_ownership
                        current_group = Group.objects.get(name=search_group)
                        current_users = current_group.user_set.all()
                        search_group = 'PUBLISH_' + resourcetypeid
                        publisher_group = Group.objects.get(name=search_group)
                        publisher_users = publisher_group.user_set.all()
                        recipients = []
                        for user1 in current_users:
                            if user1 in publisher_users:
                                if user1.username <> user.username: 
                                    recipients.append(user1.first_name + ' ' + user1.last_name + '<' + user1.email + '>')
                        # Pripravmo seznam mailov
                        if len(recipients)>0:
                            resource_type_name= settings.RESOURCE_TYPE_CONFIGS()[resourcetypeid]['name']
                            status = 'Pending approval'
                            resource_name = resource.get_primary_name()
                            subject = resource_name + ' (' + resource_type_name + ') - ' + status
                            from_email = settings.EMAIL_FROM
                            text_content = 'User ' + user.first_name + ' ' + user.last_name + ' (' + user.username + ') has submitted a document ' + resource_name + ' (' + resource_type_name + ') for approval.'
                            html_content = 'User <strong>' + user.first_name + ' ' + user.last_name + ' (' + user.username + ')</strong> has submitted a document <a href="' + resource_url + '">' + resource_name + ' (' + resource_type_name + ')</a> for approval.<br>'
                            #print html_content
                            
                            msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
                            msg.attach_alternative(html_content, "text/html")            
                            msg.content_subtype = "html"  # Main content is now text/html
                            
                            # Posljemo mail
                            connection = mail.get_connection()
                            
                            # Manually open the connection
                            connection.open()

                            # Construct an email message that uses the connection
                            msg.send()
                            
                            connection.close()   
            else:
                if action == 'reject-approval':
                    current_status = 'Approval rejected'
                    resource.set_resource_status(current_status, user)
                    empty_errors_cache()
                    errors = []
                    actions = get_possible_actions(current_status, False, user)
                    if settings.EMAIL_ENABLED:
                        # Dobimo razlog zavrnitve
                        rejectedDescription = request.POST.get('description')
                        resource_url = request.build_absolute_uri(resolve_url('resource_manager', resourcetypeid=resourcetypeid, form_id='summary', resourceid=resourceid))
                        
                        # Dobimo uporabnika, ki je dokument dal v pregled
                        ret = []
                        current = None
                        index = -1
                        start = 0
                        limit = 3
                        recipients = []
                        if resourceid != '':
                            dates = models.EditLog.objects.filter(resourceid = resourceid).values_list('timestamp', flat=True).order_by('-timestamp').distinct('timestamp')[start:limit]
                            for log in models.EditLog.objects.filter(resourceid = resourceid, timestamp__in = dates).values().order_by('-timestamp', 'attributeentitytypeid'):
                                if log['attributeentitytypeid'] == 'EW_STATUS.E55' and log['oldvalue'] == 'Draft' and log['newvalue'] == 'Pending approval':
                                    if int(log['userid'])<>user.id:
                                        print 'Sending mail...'
                                        print log['userid']<>user.id
                                        print log['userid']
                                        print user.id
                                        recipients.append(log['user_firstname'] + ' ' + log['user_lastname'] + '<' + log['user_email'] + '>')
                            if len(recipients)>0:
                                resource_type_name= settings.RESOURCE_TYPE_CONFIGS()[resourcetypeid]['name']
                                status = 'Approval rejected'
                                resource_name = resource.get_primary_name()
                                subject = resource_name + ' (' + resource_type_name + ') - ' + status
                                from_email = settings.EMAIL_FROM
                                text_content = 'User ' + user.first_name + ' ' + user.last_name + ' (' + user.username + ') has rejected a document ' + resource_name + ' (' + resource_type_name + '). For explanation go open document in Early Watercraft (section Validate Watercraft)'
                                html_content = 'User <strong>' + user.first_name + ' ' + user.last_name + ' (' + user.username + ')</strong> has rejected a document <a href="' + resource_url + '">' + resource_name + ' (' + resource_type_name + ')</a> with following explanation:<br>' + rejectedDescription
                                print html_content
                                msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
                                msg.attach_alternative(html_content, "text/html")            
                                msg.content_subtype = "html"  # Main content is now text/html
                                
                                # Posljemo mail
                                connection = mail.get_connection()
                                
                                # Manually open the connection
                                connection.open()

                                # Construct an email message that uses the connection
                                msg.send()
                                
                                connection.close()  
                else:
                    if action == 'return-to-draft':
                        current_status = 'Draft'
                        resource.set_resource_status(current_status, user)
                        empty_errors_cache()
                        errors = []
                        actions = get_possible_actions(current_status, False, user)
                    else:
                        if action == 'publish':
                            current_status = 'Published'
                            resource.set_resource_status(current_status, user)
                            empty_errors_cache()
                            errors = []
                            actions = get_possible_actions(current_status, False, user)
        form.update(data, request.FILES)

        with transaction.atomic():
            if resourceid != '':
                resource.delete_index()
            resource.save(user=request.user)
            resource.index()
            resourceid = resource.entityid
            print "Redirect_resource_manager"
            return redirect('resource_manager', resourcetypeid=resourcetypeid, form_id=form_id, resourceid=resourceid)

    min_max_dates = models.Dates.objects.aggregate(Min('val'), Max('val'))
    
    if request.method == 'GET':
        if form != None:
            lang = request.GET.get('lang', settings.LANGUAGE_CODE)
            current_status = resource.get_current_status()
            if (resourceid != ''):
                current_group = resource.get_current_group()
            else:
                current_group = group_ownership
            print "Current status: "
            print current_status
            print "Current group: "
            print current_group
            actions = []
            user_can_edit_document = get_user_can_edit_document(current_status, current_group, user, resourcetypeid, user_groups, group_ownership)
            form.load(lang, current_group)
                     
            # If user can not edit resource, there will be no validate and delete resource options
            if (not user_can_edit_document):
                for form_group in resource.form_groups:
                    for form1 in form_group["forms"]:
                        if (form1["id"] == 'delete-resource' or form1["id"] == 'validate-resource'):
                            form_group["forms"].remove(form1)
            # If status is not Draft and user is not superuser, delete is disabled
            if (current_status<> 'Draft' and not user.is_superuser):
                for form_group in resource.form_groups:
                    for form1 in form_group["forms"]:
                        if (form1["id"] == 'delete-resource'):
                            form_group["forms"].remove(form1)
            if form_id == 'validate-resource':
                errors = resource.validate_resource()
                cache.set('errors', errors, 1000)
                cache.set('resourceid', resourceid, 1000)
                errorsExists = False
                for error in errors:
                    print error
                    if error['type'] == 'error':
                        errorsExists = True
                        break
                actions = get_possible_actions(current_status, errorsExists, user)
            else:
                saved_resourceid = cache.get('resourceid')
                if (resourceid == saved_resourceid):
                    errors = cache.get('errors')
                else:
                    empty_errors_cache()
                    errors = []
                    
            return render_to_response('resource-manager.htm', {
                    'form': form,
                    'formdata': JSONSerializer().serialize(form.data),
                    'form_template': 'views/forms/' + form_id + '.htm',
                    'form_id': form_id,
                    'resourcetypeid': resourcetypeid,
                    'resourceid': resourceid,
                    'main_script': 'resource-manager',
                    'active_page': 'ResourceManger',
                    'resource': resource,
                    'resource_name': resource.get_primary_name(),
                    'resource_type_name': resource.get_type_name(),
                    'resource_icon': settings.RESOURCE_TYPE_CONFIGS()[resourcetypeid]["icon_class"],
                    'form_groups': resource.form_groups,
                    'min_date': min_max_dates['val__min'].year if min_max_dates['val__min'] != None else 0,
                    'max_date': min_max_dates['val__max'].year if min_max_dates['val__min'] != None else 1,
                    'timefilterdata': JSONSerializer().serialize(Concept.get_time_filter_data()),
                    'current_status': current_status,
                    'user_groups': user_groups,
					'errors': errors,
					'actions': actions,
					'user_can_edit_document': user_can_edit_document,
					'region_coordinates': JSONSerializer().serialize(settings.REGION_COORDINATES),
                    'help' :  settings.HELP['resource_manager']
                },
                context_instance=RequestContext(request))
        else:
            return HttpResponseNotFound('<h1>Arches form not found.</h1>')

def report(request, resourceid):
    lang = request.GET.get('lang', settings.LANGUAGE_CODE)
    se = SearchEngineFactory().create()
    report_info = se.search(index='resource', id=resourceid)
    report_info['source'] = report_info['_source']
    report_info['type'] = report_info['_type']
    report_info['source']['graph'] = report_info['source']['graph']
    del report_info['_source']
    del report_info['_type']

    def get_evaluation_path(valueid):
        value = models.Values.objects.get(pk=valueid)
        concept_graph = Concept().get(id=value.conceptid_id, include_subconcepts=False, 
            include_parentconcepts=True, include_relatedconcepts=False, up_depth_limit=None, lang=lang)
        
        paths = []
        for path in concept_graph.get_paths(lang=lang)[0]:
            if path['label'] != 'Arches' and path['label'] != 'Evaluation Criteria Type':
                paths.append(path['label'])
        return '; '.join(paths)

    current_status = 'None'
    user_can_edit_document = False
    resourcetypeid = report_info['type']
        
    # Pravice preverjamo zaenkrat le preko grup
    # Uporabnik mora imeti dodeljeno grupo z nazivom tipa resourca
    print request.user.username
    if (request.user.username != 'anonymous'):
        user = User.objects.get(username=request.user.username)
        user_groups = user.groups.values_list('name', flat=True)
    
        for entity in report_info['source']['graph']:
            if entity == 'EW_STATUS_E55':
                print report_info['source']['graph']["EW_STATUS_E55"]
                for value in report_info['source']['graph']["EW_STATUS_E55"]:
                    current_status = value["EW_STATUS_E55__label"]
        print "Current status for report: "
        print current_status
        user_can_edit_document = get_user_can_edit_document(current_status, 'same_group', user, resourcetypeid, user_groups, 'same_group')
        
    else:
        user_groups = []
        for entity in report_info['source']['graph']:
            if entity == 'EW_STATUS_E55':
                print report_info['source']['graph']["EW_STATUS_E55"]
                for value in report_info['source']['graph']["EW_STATUS_E55"]:
                    current_status = value["EW_STATUS_E55__label"]
        if current_status != settings.PUBLISHED_LABEL:
    		raise UserNotAuthorized('Unauthenticated users can view only published resources!')
    
    concept_label_ids = set()
    uuid_regex = re.compile('[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
    # gather together all uuid's referenced in the resource graph
    def crawl(items):
        for item in items:
            for key in item:
                if isinstance(item[key], list):
                    crawl(item[key])
                else:
                    if uuid_regex.match(item[key]):
                        if key == 'EVALUATION_CRITERIA_TYPE_E55__value':
                            item[key] = get_evaluation_path(item[key])
                        concept_label_ids.add(item[key])

    crawl([report_info['source']['graph']])

    # get all the concept labels from the uuid's
    concept_labels = se.search(index='concept_labels', id=list(concept_label_ids))

    # convert all labels to their localized prefLabel
    temp = {}
    if concept_labels != None:
        for concept_label in concept_labels['docs']:
            #temp[concept_label['_id']] = concept_label
            if concept_label['found']:
                # the resource graph already referenced the preferred label in the desired language
                if concept_label['_source']['type'] == 'prefLabel' and concept_label['_source']['language'] == lang:
                    temp[concept_label['_id']] = concept_label['_source']
                else: 
                    # the resource graph referenced a non-preferred label or a label not in our target language, so we need to get the right label
                    temp[concept_label['_id']] = get_preflabel_from_conceptid(concept_label['_source']['conceptid'], lang)

    # replace the uuid's in the resource graph with their preferred and localized label                    
    def crawl_again(items):
        for item in items:
            for key in item:
                if isinstance(item[key], list):
                    crawl_again(item[key])
                else:
                    if uuid_regex.match(item[key]):
                        try:
                            item[key] = temp[item[key]]['value']
                        except:
                            pass

    crawl_again([report_info['source']['graph']])
    # Podatke na visjih nivojih, ki zdruzujejo vec razlicnih nivojev, prestavimo na prvi nivo
    # To je potrebno zato, ker sicer ne moremo skrivati posameznih sklopov iz skupinske veje
    keys = ['REGION_E55','SETTLEMENT_TYPE_E55', 'CONTEXT_E55',
            'PLACE_ADDRESS_E45','PLACE_CADASTRAL_REFERENCE_E53',
            'ADMINISTRATIVE_SUBDIVISION_E48']
    old_key = 'PLACE_E53'
    for key in keys:
        if old_key in report_info['source']['graph']: 
            for data in report_info['source']['graph'][old_key]:
                if key in data:
                    if key not in report_info['source']['graph']:
                       report_info['source']['graph'][key] = []
                    report_info['source']['graph'][key].append(data.pop(key)[0])
    keys = ['SETTING_TYPE_E55','DESCRIPTION_OF_LOCATION_E62']
    old_key = 'PLACE_SITE_LOCATION_E53'
    old_key1 = 'PLACE_E53'
    for key in keys:
        if old_key1 in report_info['source']['graph']: 
            for data in report_info['source']['graph'][old_key1]:
                if old_key in data:
                    if key in data[old_key][0]:
                        if key not in report_info['source']['graph']:
                            report_info['source']['graph'][key] = []
                        report_info['source']['graph'][key].append(data[old_key][0].pop(key)[0])
    keys = ['DESCRIPTION_OF_LOCATION_E62']
    old_key = 'SPATIAL_COVERAGE_E53'
    old_key1 = 'PLACE_E53'
    for key in keys:
        if old_key1 in report_info['source']['graph']: 
            for data in report_info['source']['graph'][old_key1]:
                if old_key in data:
                    if key in data[old_key][0]:
                        if key not in report_info['source']['graph']:
                            report_info['source']['graph'][key] = []
                        report_info['source']['graph'][key].append(data[old_key][0].pop(key)[0])
    
    # PLY koncnico spremenimo za potrebe reporta v NXS
    if 'FILE_PATH_E62' in report_info['source']['graph']:
        report_info['source']['graph']['FILE_PATH_E62'][0]['FILE_PATH_E62__value'] = report_info['source']['graph']['FILE_PATH_E62'][0]['FILE_PATH_E62__label'].replace(".ply", ".nxs")
        report_info['source']['graph']['FILE_PATH_E62'][0]['FILE_PATH_E62__value'] = report_info['source']['graph']['FILE_PATH_E62'][0]['FILE_PATH_E62__value'].replace(".PLY", ".nxs")
        print 'Koncni path: ' + report_info['source']['graph']['FILE_PATH_E62'][0]['FILE_PATH_E62__value']

    #print report_info['source']['graph']
    
    #return JSONResponse(report_info, indent=4)

    related_resource_dict = {
        'HERITAGE_RESOURCE': [],
        'HERITAGE_RESOURCE_GROUP': [],
        'ACTIVITY': [],
        'ACTOR': [],
        'HISTORICAL_EVENT': [],
        'INFORMATION_RESOURCE_IMAGE': [],
        'INFORMATION_RESOURCE_DOCUMENT': [],
        'INFORMATION_RESOURCE_JSC3D': [],
        'INFORMATION_RESOURCE_3DHOP': []
    }

    related_resource_info = get_related_resources(resourceid, lang)

    # parse the related entities into a dictionary by resource type
    for related_resource in related_resource_info['related_resources']:
        information_resource_type = 'DOCUMENT'
        related_resource['relationship'] = []
        if related_resource['entitytypeid'] == 'HERITAGE_RESOURCE.E18':
            for entity in related_resource['domains']:
                if entity['entitytypeid'] == 'RESOURCE_TYPE_CLASSIFICATION.E55':
                    related_resource['relationship'].append(get_preflabel_from_valueid(entity['value'], lang)['value'])
        elif related_resource['entitytypeid'] == 'HERITAGE_RESOURCE_GROUP.E27':
            for entity in related_resource['domains']:
                if entity['entitytypeid'] == 'RESOURCE_TYPE_CLASSIFICATION.E55':
                    related_resource['relationship'].append(get_preflabel_from_valueid(entity['value'], lang)['value'])
        elif related_resource['entitytypeid'] == 'ACTIVITY.E7':
            for entity in related_resource['domains']:
                if entity['entitytypeid'] == 'ACTIVITY_TYPE.E55':
                    related_resource['relationship'].append(get_preflabel_from_valueid(entity['value'], lang)['value'])
        elif related_resource['entitytypeid'] == 'ACTOR.E39':
            for entity in related_resource['domains']:
                if entity['entitytypeid'] == 'ACTOR_TYPE.E55':
                    related_resource['relationship'].append(get_preflabel_from_conceptid(entity['conceptid'], lang)['value'])
                    related_resource['actor_relationshiptype'] = ''
        elif related_resource['entitytypeid'] == 'HISTORICAL_EVENT.E5':
            for entity in related_resource['domains']:
                if entity['entitytypeid'] == 'HISTORICAL_EVENT_TYPE.E55':
                    related_resource['relationship'].append(get_preflabel_from_conceptid(entity['conceptid'], lang)['value'])
        elif related_resource['entitytypeid'] == 'INFORMATION_RESOURCE.E73':
            for entity in related_resource['domains']:
                if entity['entitytypeid'] == 'INFORMATION_RESOURCE_TYPE.E55':
                    related_resource['relationship'].append(get_preflabel_from_valueid(entity['value'], lang)['value'])
            for entity in related_resource['child_entities']:
                if entity['entitytypeid'] == 'FILE_PATH.E62':
                    related_resource['file_path'] = settings.MEDIA_URL + entity['label']
                    
                    related_resource['file_path'] = settings.MEDIA_URL + entity['label']
                    # PLY koncnico spremenimo za potrebe reporta v NXS
                    if related_resource['file_path'][-3:].lower() == 'ply':
                        related_resource['file_path'] = related_resource['file_path'].replace(".ply", ".nxs")
                        related_resource['file_path'] = related_resource['file_path'].replace(".PLY", ".nxs")
                        information_resource_type = '3DHOP'
                    if related_resource['file_path'][-3:].lower() == 'stl' or related_resource['file_path'][-3:].lower() == 'obj':
                        information_resource_type = 'JSC3D'
                        
                if entity['entitytypeid'] == 'THUMBNAIL.E62':
                    related_resource['thumbnail'] = settings.MEDIA_URL + entity['label']
                    information_resource_type = 'IMAGE'
            
        # get the relationship between the two entities
        for relationship in related_resource_info['resource_relationships']:
            if relationship['entityid1'] == related_resource['entityid'] or relationship['entityid2'] == related_resource['entityid']: 
                related_resource['relationship'].append(get_preflabel_from_valueid(relationship['relationshiptype'], lang)['value'])
                if relationship['notes'] != '':
                    related_resource['relationship'].append(html2text.html2text(relationship['notes']))

        if len(related_resource['relationship']) > 0:
            related_resource['relationship'] = '(%s)' % (', '.join(related_resource['relationship']))
        else:
            related_resource['relationship'] = ''

        entitytypeidkey = related_resource['entitytypeid'].split('.')[0]
        if entitytypeidkey == 'INFORMATION_RESOURCE':
            entitytypeidkey = '%s_%s' % (entitytypeidkey, information_resource_type)
        related_resource_dict[entitytypeidkey].append(related_resource)

    resource_type_config = settings.RESOURCE_TYPE_CONFIGS()[resourcetypeid]
    return render_to_response('resource-report.htm', {
            'geometry': JSONSerializer().serialize(report_info['source']['geometry']),
            'resourceid': resourceid,
            'report_template': 'views/reports/' + report_info['type'] + '.htm',
            'report_info': report_info,
            'related_resource_dict': related_resource_dict,
            'main_script': 'resource-report',
            'active_page': 'ResourceReport',
            'RESOURCE_TYPE_CONFIGS': resource_type_config,
            'user_groups': user_groups,
            'current_status': current_status,
            'user_can_edit_document': user_can_edit_document,
            'help' : settings.HELP['report']
        },
        context_instance=RequestContext(request))   
        
def map_layers(request, entitytypeid='all', get_centroids=False):
    data = []
    geom_param = request.GET.get('geom', None)

    bbox = request.GET.get('bbox', '')
    limit = request.GET.get('limit', settings.MAP_LAYER_FEATURE_LIMIT)
    entityids = request.GET.get('entityid', '')
    geojson_collection = {
      "type": "FeatureCollection",
      "features": []
    }
    
    se = SearchEngineFactory().create()
    query = Query(se, limit=limit)

    args = { 'index': 'maplayers' }
    if entitytypeid != 'all':
        args['doc_type'] = entitytypeid
    if entityids != '':
        for entityid in entityids.split(','):
            geojson_collection['features'].append(se.search(index='maplayers', id=entityid)['_source'])
        return JSONResponse(geojson_collection)

    data = query.search(**args)
    if not data:
        return JSONResponse({})
    for item in data['hits']['hits']:
        # Ce uporabnik ni avtenticiran, prikazemo le veljavne (to je verjetno potrebno se dodelati (mogoce da vidijo le svoje???)!!!)
        if (not request.user.username != 'anonymous'):
            if (item['_source']['properties']['ewstatus'] != settings.PUBLISHED_LABEL):
                continue
        if get_centroids:
            item['_source']['geometry'] = item['_source']['properties']['centroid']
            #item['_source'].pop('properties', None)
            item['_source']['properties'].pop('extent', None)
            item['_source']['properties'].pop('elements', None)
            item['_source']['properties'].pop('entitytypeid', None)
            item['_source']['properties'].pop('constructions', None)
            item['_source']['properties'].pop('centroid', None)
            item['_source']['properties'].pop('ewstatus', None)
            item['_source']['properties'].pop('address', None)
            item['_source']['properties'].pop('designations', None)
            item['_source']['properties'].pop('primaryname', None)
            item['_source']['properties'].pop('resource_type', None)
        elif geom_param != None:
            item['_source']['geometry'] = item['_source']['properties'][geom_param]
            item['_source']['properties'].pop('extent', None)
            item['_source']['properties'].pop(geom_param, None)
        else:
            item['_source']['properties'].pop('extent', None)
            item['_source']['properties'].pop('centroid', None)
        geojson_collection['features'].append(item['_source'])
    return JSONResponse(geojson_collection)  

