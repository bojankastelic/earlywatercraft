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
import uuid
from datetime import datetime
from django.conf import settings
from django.contrib.gis.geos import fromstr
import arches.app.models.models as archesmodels
from ew.models.edit_history import EditHistory
from arches.app.models.resource import Resource as ArchesResource
from ew.models.concept import Concept
from ew.models.entity import Entity
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from ew.models import forms
from ew.models import ew_utils
from ew.models.forms import DeleteResourceForm
from django.utils.translation import ugettext as _
from django.contrib.gis.geos import GEOSGeometry

class Resource(ArchesResource):
    def __init__(self, *args, **kwargs):
        super(Resource, self).__init__(*args, **kwargs)
        resource_name = _('Resource Description')
        if self.entitytypeid:
            resource_name = settings.RESOURCE_TYPE_CONFIGS()[self.entitytypeid]['name']
        description_group = {
            'id': 'resource-description',
            'icon':'fa-folder',
            'name': resource_name,
            'forms': [
                forms.RelatedResourcesForm.get_info(),
                #forms.ExternalReferenceForm.get_info()
            ]   
        }

        self.form_groups.append(description_group)

        if self.entitytypeid == 'HERITAGE_RESOURCE.E18':
            description_group['forms'][:0] = [
                forms.SummaryForm.get_info(), 
                forms.ComponentForm.get_info(),
                forms.DescriptionForm.get_info(),
                forms.LocationForm.get_info(),
                forms.DatingForm.get_info(),
                forms.MeasurementForm.get_info(),
                forms.ConditionForm.get_info(),
                forms.RelatedFilesForm.get_info(),
            ]

            self.form_groups.append({
                'id': 'others-resource',
                'icon':'fa-dashboard',
                'name': _('Other (unused) data'),
                'forms': [
                    forms.ClassificationForm.get_info(),
                    forms.DesignationForm.get_info(),
                    forms.EvaluationForm.get_info(),
                ]   
            })

        elif self.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27':
            description_group['forms'][:0] = [
                forms.SummaryForm.get_info(),
                forms.DescriptionForm.get_info(),
                forms.LocationForm.get_info(),
                forms.MeasurementForm.get_info(),
                forms.ConditionForm.get_info(),
                forms.ExternalReferenceForm.get_info()
            ]
            
            self.form_groups.append({
                'id': 'others-resource',
                'icon':'fa-dashboard',
                'name': _('Other (unused) data'),
                'forms': [
                    forms.DistrictClassificationForm.get_info(),
                    forms.EvaluationForm.get_info(),
                    forms.DesignationForm.get_info(),
                ]   
            })


        elif self.entitytypeid == 'ACTIVITY.E7':
            description_group['forms'][:0] = [
                forms.ActivitySummaryForm.get_info(),
                forms.DescriptionForm.get_info(),
                forms.LocationForm.get_info(),
                forms.ActivityActionsForm.get_info(),
                forms.ExternalReferenceForm.get_info()
            ]
     

        elif self.entitytypeid == 'ACTOR.E39':
            description_group['forms'][:0] = [
                forms.ActorSummaryForm.get_info(), 
                forms.DescriptionForm.get_info(),
                forms.LocationForm.get_info(),
                forms.RoleForm.get_info(),
                forms.ExternalReferenceForm.get_info()
            ]


        elif self.entitytypeid == 'HISTORICAL_EVENT.E5':
            description_group['forms'][:0] = [
                forms.HistoricalEventSummaryForm.get_info(),
                forms.DescriptionForm.get_info(),
                forms.LocationForm.get_info(), 
                forms.PhaseForm.get_info(),
                forms.ExternalReferenceForm.get_info()
            ]


        elif self.entitytypeid == 'INFORMATION_RESOURCE.E73':
            description_group['forms'][:0] = [
                forms.InformationResourceSummaryForm.get_info(), 
                forms.PublicationForm.get_info(),
                forms.CoverageForm.get_info(),
                forms.DescriptionForm.get_info(),
                forms.ExternalReferenceForm.get_info()
            ]
            description_group['forms'].append(forms.FileUploadForm.get_info())

            

        if self.entityid != '':
            self.form_groups.append({
                'id': 'manage-resource',
                'icon': 'fa-wrench',
                'name': _('Manage') + ' ' + settings.RESOURCE_TYPE_CONFIGS()[self.entitytypeid]['name'].replace(settings.REMOVE_EW_STRING, ''),
                'forms': [
                    forms.ValidateResourceForm.get_info(settings.RESOURCE_TYPE_CONFIGS()[self.entitytypeid]['name'].replace(settings.REMOVE_EW_STRING, '')),
                    EditHistory.get_info(),
                    DeleteResourceForm.get_info(settings.RESOURCE_TYPE_CONFIGS()[self.entitytypeid]['name'].replace(settings.REMOVE_EW_STRING, ''))
                ]
            })

    def get_form(self, form_id):
        selected_form = None
        forms = [form for group in self.form_groups for form in group['forms']]
        for form in forms:
            if form['id'] == form_id:
                selected_form = form
        if selected_form != None:
            return selected_form['class'](self, selected_form['id'], selected_form['name'].replace('Delete','').replace('Validate',''))

    def get_primary_name(self):
        displayname = super(Resource, self).get_primary_name()
        names = self.get_names()
        if len(names) > 0:
            displayname = names[0].value
        return displayname


    def get_names(self):
        """
        Gets the human readable name to display for entity instances

        """

        names = []
        name_nodes = self.find_entities_by_type_id(settings.RESOURCE_TYPE_CONFIGS()[self.entitytypeid]['primary_name_lookup']['entity_type'])
        if len(name_nodes) > 0:
            for name in name_nodes:
                names.append(name)

        return names

    def index(self):
        """
        Indexes all the nessesary documents related to resources to support the map, search, and reports

        """

        se = SearchEngineFactory().create()

        search_documents = self.prepare_documents_for_search_index()
        for document in search_documents:
            se.index_data('entity', self.entitytypeid, document, id=self.entityid)

            report_documents = self.prepare_documents_for_report_index(geom_entities=document['geometries'])
            for report_document in report_documents:
                se.index_data('resource', self.entitytypeid, report_document, id=self.entityid)

            geojson_documents = self.prepare_documents_for_map_index(geom_entities=document['geometries'])
            for geojson in geojson_documents:
                se.index_data('maplayers', self.entitytypeid, geojson, idfield='id')

        for term in self.prepare_terms_for_search_index():
           se.index_term(term['term'], term['entityid'], term['context'], term['ewstatus'], term['options'])

    def prepare_search_index(self, resource_type_id, create=False):
        """
        Creates the settings and mappings in Elasticsearch to support resource search

        """

        index_settings = super(Resource, self).prepare_search_index(resource_type_id, create=False)

        index_settings['mappings'][resource_type_id]['properties']['date_groups'] = { 
            'properties' : {
                'conceptid': {'type' : 'string', 'index' : 'not_analyzed'}
            }
        }

        if create:
            se = SearchEngineFactory().create()
            try:
                se.create_index(index='entity', body=index_settings)
            except:
                index_settings = index_settings['mappings']
                se.create_mapping(index='entity', doc_type=resource_type_id, body=index_settings)

    def prepare_documents_for_search_index(self):
        """
        Generates a list of specialized resource based documents to support resource search

        """
        # Arches
        document = Entity()
        document.property = self.property
        document.entitytypeid = self.entitytypeid
        document.entityid = self.entityid
        document.value = self.value
        document.label = self.label
        document.businesstablename = self.businesstablename
        document.primaryname = self.get_primary_name()
        document.child_entities = []
        document.dates = []
        document.domains = []
        document.geometries = []
        document.numbers = []
        # EW dopolnitev
        document.ewstatus = self.get_current_status()

        for entity in self.flatten():
            if entity.entityid != self.entityid:
                if entity.businesstablename == 'domains':
                    value = archesmodels.Values.objects.get(pk=entity.value)
                    entity_copy = entity.copy()
                    entity_copy.conceptid = value.conceptid_id
                    document.domains.append(entity_copy)
                elif entity.businesstablename == 'dates':
                    document.dates.append(entity)
                elif entity.businesstablename == 'numbers':
                    document.numbers.append(entity)
                elif entity.businesstablename == 'geometries':
                    entity.value = JSONDeserializer().deserialize(fromstr(entity.value).json)
                    document.geometries.append(entity)
                else:
                    document.child_entities.append(entity)

        documents = [JSONSerializer().serializeToPython(document)]

        # Arches_hip        
        for document in documents:
            document['date_groups'] = []
            for nodes in self.get_nodes('BEGINNING_OF_EXISTENCE.E63', keys=['value']):
                document['date_groups'].append({
                    'conceptid': nodes['BEGINNING_OF_EXISTENCE_TYPE_E55__value'],
                    'value': nodes['START_DATE_OF_EXISTENCE_E49__value']
                })

            for nodes in self.get_nodes('END_OF_EXISTENCE.E64', keys=['value']):
                document['date_groups'].append({
                    'conceptid': nodes['END_OF_EXISTENCE_TYPE_E55__value'],
                    'value': nodes['END_DATE_OF_EXISTENCE_E49__value']
                })

        return documents


    def prepare_documents_for_map_index(self, geom_entities=[]):
        """
        Generates a list of geojson documents to support the display of resources on a map

        """
        
        # Arches

        document1 = []
        if len(geom_entities) > 0:
            geojson_geom = {
                'type': 'GeometryCollection',
                'geometries': [geom_entity['value'] for geom_entity in geom_entities]
            }
            geom = GEOSGeometry(JSONSerializer().serialize(geojson_geom), srid=4326)
             
            document1 = [{
                'type': 'Feature',
                'id': self.entityid,
                'geometry':  geojson_geom,
                'properties': {
                    'entitytypeid': self.entitytypeid,
                    'primaryname': self.get_primary_name(),
                    'centroid': JSONDeserializer().deserialize(geom.centroid.json),
                    'extent': geom.extent,
                    # EW dopolnitev
                    'ewstatus': self.get_current_status(),
                    'ewicon': self.get_resource_icon(),
                }
            }]
        
        documents = document1

        
        # Arches_hip
        def get_entity_data(entitytypeid, get_label=False):
            entity_data = _('None specified')
            entity_nodes = self.find_entities_by_type_id(entitytypeid)
            if len(entity_nodes) > 0:
                entity_data = []
                for node in entity_nodes:
                    if get_label:
                        entity_data.append(node.label)
                    else:
                        entity_data.append(node.value)
                entity_data = ', '.join(entity_data)
            return entity_data

        def get_entity_data2(entitytypeid1, entitytypeid2, get_label=False):
            entity_data = _('None specified')
            entity_nodes1 = self.find_entities_by_type_id(entitytypeid1)
            entity_nodes2 = self.find_entities_by_type_id(entitytypeid2)
            if len(entity_nodes1) > 0:
                entity_data1 = []
                for node in entity_nodes1:
                    if get_label:
                        entity_data1.append(node.label)
                    else:
                        entity_data1.append(node.value)
            if len(entity_nodes2) > 0:
                entity_data2 = []
                for node in entity_nodes2:
                    if get_label:
                        entity_data2.append(node.label)
                    else:
                        entity_data2.append(node.value)

            entity_data = [] 
            for i in range(len(entity_nodes1)):
                niz = ' ('.join([entity_nodes1[i].label, entity_nodes2[i].label])
                niz = ''.join([niz, ')'])
                entity_data.append(niz) 
            entity_data = ', '.join(entity_data)
               
            return entity_data

        document_data = {}
        if self.entitytypeid == 'HERITAGE_RESOURCE.E18':
            document_data['resource_type'] = get_entity_data('RESOURCE_TYPE_CLASSIFICATION.E55', get_label=True)

            document_data['address'] = _('None specified')
            address_nodes = self.find_entities_by_type_id('PLACE_ADDRESS.E45')
            for node in address_nodes:
                if node.find_entities_by_type_id('ADDRESS_TYPE.E55')[0].label == 'Primary':
                    document_data['address'] = node.value

        if self.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27':
            document_data['resource_type'] = get_entity_data('HERITAGE_RESOURCE_GROUP_TYPE.E55', get_label=True)

        if self.entitytypeid == 'ACTIVITY.E7':
            document_data['resource_type'] = get_entity_data('ACTIVITY_TYPE.E55', get_label=True)

        if self.entitytypeid == 'HISTORICAL_EVENT.E5':
            document_data['resource_type'] = get_entity_data('HISTORICAL_EVENT_TYPE.E55', get_label=True)

        if self.entitytypeid == 'ACTOR.E39':
            document_data['resource_type'] = get_entity_data('ACTOR_TYPE.E55', get_label=True)

        if self.entitytypeid == 'INFORMATION_RESOURCE.E73':
            document_data['resource_type'] = get_entity_data('RESOURCE_TYPE_CLASSIFICATION.E55', get_label=True)
            # Zaenkrat samo zakomentiramo (teh podatkov ne potrebujemo)
            #document_data['creation_date'] = get_entity_data('DATE_OF_CREATION.E50')
            #document_data['publication_date'] = get_entity_data('DATE_OF_PUBLICATION.E50')

        if self.entitytypeid == 'HISTORICAL_EVENT.E5' or self.entitytypeid == 'ACTIVITY.E7' or self.entitytypeid == 'ACTOR.E39':
            document_data['start_date'] = get_entity_data('BEGINNING_OF_EXISTENCE.E63')
            document_data['end_date'] = get_entity_data('END_OF_EXISTENCE.E64')

        if self.entitytypeid == 'HERITAGE_RESOURCE.E18' or self.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27':
            document_data['designations'] = get_entity_data2('MATERIAL.E57', 'MATERIAL_TYPE.E57', get_label=True)

        if self.entitytypeid == 'HERITAGE_RESOURCE.E18' or self.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27':
            document_data['elements'] = get_entity_data2('COMPONENT_TYPE.E55', 'CONSTRUCTION_TYPE.E55', get_label=True)

        if self.entitytypeid == 'HERITAGE_RESOURCE.E18' or self.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27':
            document_data['constructions'] = get_entity_data2('CONSTRUCTION_SKILL.E55', 'CONSTRUCTION_TECHNIQUE.E55', get_label=True)

        # if self.entitytypeid == 'HERITAGE_RESOURCE.E18' or self.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27':
        #    document_data['ew_status'] = get_entity_data('EW_STATUS.E55', get_label=True)
        for document in documents:
            for key in document_data:
                document['properties'][key] = document_data[key]

        return documents

    def prepare_terms_for_search_index(self):
        """
        Generates a list of term objects with composed of any string less then the length of settings.WORDS_PER_SEARCH_TERM  
        long and any concept associated with a resource to support term search  

        """
        terms = []

        def gather_entities(entity):
            if entity.businesstablename == '':
                pass
            elif entity.businesstablename == 'strings':
                if settings.WORDS_PER_SEARCH_TERM == None or (len(entity.value.split(' ')) < settings.WORDS_PER_SEARCH_TERM):
                    entitytype = archesmodels.EntityTypes.objects.get(pk=entity.entitytypeid)
                    terms.append({'term': entity.value, 'entityid': entity.entityid, 'context': entitytype.conceptid_id, 'ewstatus': self.get_current_status(), 'options': {}})
            elif entity.businesstablename == 'domains':
                pass
            elif entity.businesstablename == 'geometries':
                pass
            elif entity.businesstablename == 'dates':
                pass
            elif entity.businesstablename == 'numbers':
                pass
            elif entity.businesstablename == 'files':
                pass

        self.traverse(gather_entities)
        return terms
              
    def get_primary_name(self):
        displayname = super(Resource, self).get_primary_name()
        #if self.entityid == '':
        #    displayname = _('New Early Watercraft')
        #else:
        #    displayname = _('Unnamed Early Watercraft1')
        names = self.get_names()
        if len(names) > 0:
            displayname = names[0].value
        return displayname
  
    @staticmethod
    def get_report(resourceid):
        # get resource data for resource_id from ES, return data
        # with correct id for the given resource type
        return {
            'id': 'heritage-resource',
            'data': {
                'hello_world': 'Hello World!'
            }
        }
    
    def get_current_status(self):
        return ew_utils.get_current_status(self)    

    def get_current_group(self):
        return ew_utils.get_current_group(self)    

    def validate_resource(self):
        return ew_utils.validate_resource(self, 'Draft')

    def find_status(self, child_entities):
        for entity in child_entities:
            if entity.entitytypeid == 'EW_STATUS.E55':
                print 'Value: ' + entity.value
                print 'Label: ' + entity.label
            if entity.child_entities:
                self.find_status(entity.child_entities)

    def set_resource_status(self, status, user):
        print self.entitytypeid
        current_status = self.get_current_status()
        #print 'Current status: ' + self.get_current_status()
        #self.find_status(self.child_entities)
        statusi = Concept().get_e55_domain('EW_STATUS.E55')
        for ew_status in statusi:
            if ew_status['text'] == status:
                #print ew_status['text']
                #print ew_status['value']
                self.set_entity_value("EW_STATUS.E55", ew_status['id'], False)

        print 'Povezani IS:'
        for relatedentity in self.get_related_resources(entitytypeid='INFORMATION_RESOURCE.E73'):
            related_resource = relatedentity['related_entity']
            print 'Current status IS: ' + related_resource.get_current_status()
            if related_resource.get_current_status() == current_status:
                for ew_status in statusi:
                    if ew_status['text'] == status:
                        related_resource.set_entity_value("EW_STATUS.E55", ew_status['id'], False)
                related_resource.delete_index()
                related_resource.save(user)
                related_resource.index()
        self.save(user)
        print "Status " + status + " postavljen."
        #self.find_status(self.child_entities)

    def get_resource_icon(self):
        return ew_utils.get_resource_icon(self)    

        
    def add_child_entity(self, entitytypeid, property, value, entityid):
        """
        Add a child entity to this entity instance

        """     
        node = Entity()
        node.property = property
        node.entitytypeid = entitytypeid
        node.value = value
        node.entityid = entityid
        self.append_child(node)
        return node
    
