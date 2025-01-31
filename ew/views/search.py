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

from datetime import datetime
from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.db.models import Max, Min
from arches.app.models import models
from arches.app.views.search import get_paginator
from arches.app.views.search import _get_child_concepts
from arches.app.views.concept import get_preflabel_from_conceptid
from ew.models.concept import Concept
from arches.app.utils.JSONResponse import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Bool, Match, Query, Nested, Terms, GeoShape, Range
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from arches.app.utils.betterJSONSerializer import JSONSerializer
from ew.views.search_utils import get_auto_filter, get_search_contexts
from ew.utils.data_management.resources.exporter import ResourceExporter

def home_page(request):
    lang = request.GET.get('lang', settings.LANGUAGE_CODE)
    min_max_dates = models.Dates.objects.aggregate(Min('val'), Max('val'))

    if (request.user.username != 'anonymous'):
        user = User.objects.get(username=request.user.username)
        if (user.is_staff or user.is_superuser):
           # Grupe vzamemo kar iz nastavitev
           user_groups = []
           all_groups = settings.RESOURCE_TYPE_CONFIGS()
           for group in all_groups:
               print group
               user_groups.append(group)
        else:
           user_groups = user.groups.values_list('name', flat=True)
    else:
        user_groups = []
    
    search_context =  get_search_contexts(request)
    
    return render_to_response('search.htm', {
            'main_script': 'search',
            'active_page': 'Search',
            'min_date': min_max_dates['val__min'].year if min_max_dates['val__min'] != None else 0,
            'max_date': min_max_dates['val__max'].year if min_max_dates['val__min'] != None else 1,
            'timefilterdata': JSONSerializer().serialize(Concept.get_time_filter_data()),
            'user_groups': user_groups,
            'search_context': search_context,
            'help' :  settings.HELP['search']
        }, 
        context_instance=RequestContext(request))

def search_results(request):
    query = build_search_results_dsl(request)
    #print query
    results = query.search(index='entity', doc_type='') 
    total = results['hits']['total']
    page = 1 if request.GET.get('page') == '' else int(request.GET.get('page', 1))
    all_entity_ids = ['_all']
    if request.GET.get('include_ids', 'false') == 'false':
        all_entity_ids = ['_none']
    elif request.GET.get('no_filters', '') == '':
        full_results = query.search(index='entity', doc_type='', start=0, limit=1000000, fields=[])
        all_entity_ids = [hit['_id'] for hit in full_results['hits']['hits']]

    return get_paginator(results, total, page, settings.SEARCH_ITEMS_PER_PAGE, all_entity_ids)

def build_base_search_results_dsl(request):
    term_filter = request.GET.get('termFilter', '')
    spatial_filter = JSONDeserializer().deserialize(request.GET.get('spatialFilter', None)) 
    export = request.GET.get('export', None)
    page = 1 if request.GET.get('page') == '' else int(request.GET.get('page', 1))
    temporal_filter = JSONDeserializer().deserialize(request.GET.get('temporalFilter', None))

    se = SearchEngineFactory().create()

    if export != None:
        limit = settings.SEARCH_EXPORT_ITEMS_PER_PAGE  
    else:
        limit = settings.SEARCH_ITEMS_PER_PAGE
    
    query = Query(se, start=limit*int(page-1), limit=limit)
    boolquery = Bool()
    boolfilter = Bool()
    
    if term_filter != '':
        # Ce uporabnik ni avtenticiran, prikazemo le veljavne (to je verjetno potrebno se dodelati (mogoce da vidijo le svoje???)!!!)
        if (request.user.username == 'anonymous'):
            auto_filter = []
            for item in JSONDeserializer().deserialize(term_filter):
               auto_filter.append(item) 
            
            # Poiscimo concept id in context za Published status
            AUTO_TERM_FILTER = get_auto_filter(request)
            
            auto_filter.append(AUTO_TERM_FILTER)
            term_filter = JSONSerializer().serialize(auto_filter)
            
    print 'term_filter'
    if term_filter != '':
        for term in JSONDeserializer().deserialize(term_filter):
            print term
            if term['type'] == 'term':
                entitytype = models.EntityTypes.objects.get(conceptid_id=term['context'])
                boolfilter_nested = Bool()
                boolfilter_nested.must(Terms(field='child_entities.entitytypeid', terms=[entitytype.pk]))
                boolfilter_nested.must(Match(field='child_entities.value', query=term['value'], type='phrase'))
                nested = Nested(path='child_entities', query=boolfilter_nested)
                if term['inverted']:
                    boolfilter.must_not(nested)
                else:    
                    boolfilter.must(nested)
            elif term['type'] == 'concept':
                concept_ids = _get_child_concepts(term['value'])
                terms = Terms(field='domains.conceptid', terms=concept_ids)
                nested = Nested(path='domains', query=terms)
                if term['inverted']:
                    boolfilter.must_not(nested)
                else:
                    boolfilter.must(nested)
            elif term['type'] == 'string':
                boolfilter_folded = Bool()
                boolfilter_folded.should(Match(field='child_entities.value', query=term['value'], type='phrase_prefix'))
                boolfilter_folded.should(Match(field='child_entities.value.folded', query=term['value'], type='phrase_prefix'))
                nested = Nested(path='child_entities', query=boolfilter_folded)
                if term['inverted']:
                    boolquery.must_not(nested)
                else:    
                    boolquery.must(nested)
    if 'geometry' in spatial_filter and 'type' in spatial_filter['geometry'] and spatial_filter['geometry']['type'] != '':
        geojson = spatial_filter['geometry']
        if geojson['type'] == 'bbox':
            coordinates = [[geojson['coordinates'][0],geojson['coordinates'][3]], [geojson['coordinates'][2],geojson['coordinates'][1]]]
            geoshape = GeoShape(field='geometries.value', type='envelope', coordinates=coordinates )
            nested = Nested(path='geometries', query=geoshape)
        else:
            buffer = spatial_filter['buffer']
            geojson = JSONDeserializer().deserialize(_buffer(geojson,buffer['width'],buffer['unit']).json)
            geoshape = GeoShape(field='geometries.value', type=geojson['type'], coordinates=geojson['coordinates'] )
            nested = Nested(path='geometries', query=geoshape)

        if 'inverted' not in spatial_filter:
            spatial_filter['inverted'] = False

        if spatial_filter['inverted']:
            boolfilter.must_not(nested)
        else:
            boolfilter.must(nested)

    if 'year_min_max' in temporal_filter and len(temporal_filter['year_min_max']) == 2:
        start_date = date(temporal_filter['year_min_max'][0], 1, 1)
        end_date = date(temporal_filter['year_min_max'][1], 12, 31)
        if start_date:
            start_date = start_date.isoformat()
        if end_date:
            end_date = end_date.isoformat()
        range = Range(field='dates.value', gte=start_date, lte=end_date)
        nested = Nested(path='dates', query=range)
        
        if 'inverted' not in temporal_filter:
            temporal_filter['inverted'] = False

        if temporal_filter['inverted']:
            boolfilter.must_not(nested)
        else:
            boolfilter.must(nested)
        
    if not boolquery.empty:
        query.add_query(boolquery)

    if not boolfilter.empty:
        query.add_filter(boolfilter)

    return query

def build_search_results_dsl(request):
    temporal_filters = JSONDeserializer().deserialize(request.GET.get('temporalFilter', None))

    query = build_base_search_results_dsl(request)  
    boolfilter = Bool()
    
    if 'filters' in temporal_filters:
        for temporal_filter in temporal_filters['filters']:
            terms = Terms(field='date_groups.conceptid', terms=temporal_filter['date_types__value'])
            boolfilter.must(terms)

            date_value = datetime.strptime(temporal_filter['date'], '%d/%m/%Y').isoformat()

            if temporal_filter['date_operators__value'] == '1': # equals query
                range = Range(field='date_groups.value', gte=date_value, lte=date_value)
            elif temporal_filter['date_operators__value'] == '0': # greater than query 
                range = Range(field='date_groups.value', lt=date_value)
            elif temporal_filter['date_operators__value'] == '2': # less than query
                range = Range(field='date_groups.value', gt=date_value)

            if 'inverted' not in temporal_filters:
                temporal_filters['inverted'] = False

            if temporal_filters['inverted']:
                boolfilter.must_not(range)
            else:
                boolfilter.must(range)

            query.add_filter(boolfilter)

    return query

def search_terms(request):
    lang = request.GET.get('lang', settings.LANGUAGE_CODE)
    
    query = build_search_terms_dsl(request)
    results = query.search(index='term', doc_type='value')
    
    return_results = []
    for result in results['hits']['hits']:
        # Ce uporabnik ni avtenticiran, prikazemo le veljavne (to je verjetno potrebno se dodelati (mogoce da vidijo le svoje???)!!!)
        if (request.user.username == 'anonymous'):
            if ('ewstatus' in result['_source']):
                if (result['_source']['ewstatus'] != settings.PUBLISHED_LABEL):
                    continue
        prefLabel = get_preflabel_from_conceptid(result['_source']['context'], lang)
        result['_source']['options']['context_label'] = prefLabel['value']
        return_results.append(result)
    results['hits']['hits'] = return_results
    return JSONResponse(results)   

def build_search_terms_dsl(request):
    se = SearchEngineFactory().create()
    searchString = request.GET.get('q', '')
    query = Query(se, start=0, limit=settings.SEARCH_DROPDOWN_LENGTH)
    boolquery = Bool()
    boolquery.should(Match(field='term', query=searchString.lower(), type='phrase_prefix', fuzziness='AUTO'))
    boolquery.should(Match(field='term.folded', query=searchString.lower(), type='phrase_prefix', fuzziness='AUTO'))
    boolquery.should(Match(field='term.folded', query=searchString.lower(), fuzziness='AUTO'))
    query.add_query(boolquery)

    return query
    
def export_results(request):
    dsl = build_search_results_dsl(request)
    search_results = dsl.search(index='entity', doc_type='') 
    response = None
    format = request.GET.get('export', 'csv')
    exporter = ResourceExporter(format)
    results = exporter.export(search_results['hits']['hits'])
    zipped_results = exporter.zip_response(results, '{0}_{1}_export.zip'.format(settings.PACKAGE_NAME, format))
    return zipped_results
