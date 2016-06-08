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

"""This module contains commands for building Arches."""
#!/usr/bin/env python
import os
import sys
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ew.settings")

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from ew import settings
import arches.app.models.models as archesmodels
from ew.models.concept import Concept
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.search.search_engine_factory import SearchEngineFactory

if __name__ == "__main__":
    """A general command used index Arches data into Elasticsearch."""

    def index_concepts_labels():
        # see http://sqlblog.com/blogs/adam_machanic/archive/2006/07/12/swinging-from-tree-to-tree-using-ctes-part-1-adjacency-to-nested-sets.aspx          
        # Value of Lft for the root node is 1
        # Value of Rgt for the root node is 2 * (Number of nodes)
        # Value of Lft for any node is ((Number of nodes visited) * 2) - (Level of current node)
        # Value of Rgt for any node is (Lft value) + ((Number of subnodes) * 2) + 1 
     

        sys.setrecursionlimit(3000)
        se = SearchEngineFactory().create()
        se.create_mapping('concept', 'all', 'conceptid', 'string', 'not_analyzed')
        se.create_mapping('concept', 'all', 'labelid', 'string', 'not_analyzed')
        
        se.create_mapping('concept_labels', '00000000-0000-0000-0000-000000000005', fieldname='conceptid', fieldtype='string', fieldindex='not_analyzed')

        def _findNarrowerConcept(conceptid, context='', ret=None, limit=200000, level=1):
            returnobj = {'subnodes': 0}
            if ret == None: # the root node
                labels = archesmodels.Values.objects.filter(conceptid = conceptid)
                ret = {}
                nodesvisited = len(ret) + 1
                ret[conceptid] = {'context': conceptid, 'labels': [], 'left': (nodesvisited*2)-level, 'right': 0}               
                for label in labels:
                    ret[conceptid]['labels'].append({'labelid': label.pk, 'label': label.value})
                level = level + 1

            conceptrealations = archesmodels.ConceptRelations.objects.filter(conceptidfrom = conceptid)
            for relation in conceptrealations:
                nodesvisited = len(ret) + 1
                labels = archesmodels.Values.objects.filter(conceptid = relation.conceptidto)
                context1 = context
                if context1 == '' or context1 == '00000000-0000-0000-0000-000000000001' or context1 == '00000000-0000-0000-0000-000000000003' or context1 == '00000000-0000-0000-0000-000000000004':
                    context1 = conceptid
                ret[relation.conceptidto_id] = {'context': context1, 'labels': [], 'left': (nodesvisited*2)-level, 'right': 0}
                for label in labels:
                    ret[relation.conceptidto_id]['labels'].append({'labelid': label.pk, 'label': label.value})
                returnobj = _findNarrowerConcept(relation.conceptidto_id, context1, ret=ret, level=level+1)      
            
            subnodes = returnobj['subnodes']
            if subnodes == 0: # meaning we're at a leaf node
                ret[conceptid]['right'] = ret[conceptid]['left'] + 1
            else:
                ret[conceptid]['right'] = subnodes + 1
            return {'all_concepts': ret, 'subnodes': ret[conceptid]['right']}

        concepts = _findNarrowerConcept('00000000-0000-0000-0000-000000000001')
        
        all_concepts = []
        for key, concept in concepts['all_concepts'].iteritems():
            all_concepts.append({'conceptid': key, 'context': concept['context'], 'labels': concept['labels'], 'left': concept['left'], 'right': concept['right']})
        print 'Klic self.index'
        index(all_concepts, 'concept', 'all', 'conceptid')

    def index(documents, index, type, idfield, processdoc=None, getid=None, bulk=False):
        print 'index_concepts.index'
        detail = ''
        bulkitems = []
        errorlist = []
        se = SearchEngineFactory().create()
        if not isinstance(documents, list):
            documents = [documents]
        for document in documents:
            sys.stdout.write('.')
            if processdoc == None:
                data = document
            else:
                data = processdoc(document)
            id = None
            if getid != None:
                id = getid(document, data)            
            try:
                if bulk:
                    bulkitem = se.create_bulk_item(index, type, id, data)
                    bulkitems.append(bulkitem[0])
                    bulkitems.append(bulkitem[1])        
                else:
                    se.index_data(index, type, data, idfield=idfield, id=id)
                    #se.index_data('concept_labels', '00000000-0000-0000-0000-000000000005', data, 'id')
                    for concept in data['labels']:
                        #se.index_term(concept['label'], concept['labelid'], '00000000-0000-0000-0000-000000000005', settings.PUBLISHED_LABEL, {'conceptid': data['conceptid']})
                        if concept['label'].strip(' \t\n\r') != '':
                            already_indexed = False
                            count = 1
                            ids = [id]
                        try:
                            _id = uuid.uuid3(uuid.NAMESPACE_DNS, '%s%s' % (hash(concept['label']), hash(data['conceptid'])))
                            result = se.es.get(index='term', doc_type='value', id=_id, ignore=404)

                            #print 'result: %s' % result
                            if result['found'] == True:
                                ids = result['_source']['ids']
                                if id not in ids:
                                    ids.append(id)
                            else:
                                ids = [id]                             
                            if data['context'] != '00000000-0000-0000-0000-000000000003' and data['context'] != '00000000-0000-0000-0000-000000000004':
                                se.index_data('term', 'value', {'term': concept['label'], 'context': data['context'], 'ewstatus': settings.PUBLISHED_LABEL, 'options': {'conceptid': data['conceptid']}, 'count': len(ids), 'ids': ids}, id=_id)
                            
                        except Exception as detail:
                            raise detail   
            except Exception as detail:
                print detail
                errorlist.append(id)
        if bulk:
            try:
                se.bulk_index(index, type, bulkitems)
            except Exception as detail:
                errorlist = bulkitems
                print 'bulk inset failed'

        if detail != '':
            print "\n\nException detail: %s " % (detail)
            print "There was a problem indexing the following items:"
            print errorlist

    def index_concepts_by_entitytypeid(entitytypeid):
        entitytype = archesmodels.EntityTypes.objects.get(pk = entitytypeid)
        conceptid = entitytype.conceptid_id
        concept_graph = Concept().get(id=conceptid, include_subconcepts=True, exclude=['note'])
        if len(concept_graph.subconcepts) > 0:
            data = JSONSerializer().serializeToPython(concept_graph, ensure_ascii=True, indent=4)
            index(data, 'concept', entitytypeid, 'id', processdoc=None, getid=None, bulk=False) 

    def delete_index(self, index):
        se = SearchEngineFactory().create()
        se.delete_index(index=index)
        
    print 'Index: concepts_labels'
    index_concepts_labels()
    #sql = """
    #    SELECT a.entitytypeid
    #    FROM data.entity_types a;
    #    """
    #cursor.execute(sql)
    #entitytypeids = cursor.fetchall()
    #for entitytypeid in entitytypeids:
    #    index_concepts_by_entitytypeid(entitytypeid[0])

