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

from django.conf import settings
from arches.management.commands import utils
from django.utils.translation import ugettext as _

entities = []
errors = []
curr_status = ""

def check_required_fields(resource, ew_status):
    # Checks if there are populated all required fields for given status
    print resource.entitytypeid
    error_description = _('Value must be populated.')
    warning_description = _('Value should be populated.')
    required_fields = []
    construction_type = get_current_construction_type(resource)
    if (resource.entitytypeid == 'HERITAGE_RESOURCE.E18' or resource.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27'):
        if (ew_status == 'Draft' or ew_status == 'Pending approval' or ew_status == 'Published'):
            required_entities = [{'entitytypeid': 'NAME.E41', 'data_group': _('Names'), 'type': 'error' },
                                 {'entitytypeid': 'NAME_TYPE.E55', 'data_group': _('Name Type'), 'type': 'error'}]
            if (resource.entitytypeid == 'HERITAGE_RESOURCE.E18'):
                required_entities.append({'entitytypeid': 'EXTERNAL_XREF_TYPE.E55', 'data_group': _('Identificator type'), 'type': 'error' })
                required_entities.append({'entitytypeid': 'EXTERNAL_XREF.E42', 'data_group': _('Value of identificator'), 'type': 'error' })
                required_entities.append({'entitytypeid': 'RESOURCE_TYPE_CLASSIFICATION.E55', 'data_group': _('Watercraft Type'), 'type': 'error'})
            required_fields.append({'form_id': 'summary', 
                                    'sort'   : '1',
                                    'field'  : required_entities})
    if (resource.entitytypeid == 'HERITAGE_RESOURCE.E18'):
        if (ew_status == 'Draft' or ew_status == 'Pending approval' or ew_status == 'Published'):
            required_fields.append({'form_id': 'component', 
                                    'sort'   : '2',
                                    'field'  : [{'entitytypeid': 'COMPONENT_TYPE.E55', 'data_group': _('Elements'), 'type': 'error'}]})
    if (resource.entitytypeid == 'HERITAGE_RESOURCE.E18' or resource.entitytypeid == 'HERITAGE_RESOURCE_GROUP.E27'):
        if (ew_status == 'Draft' or ew_status == 'Pending approval' or ew_status == 'Valid'):
            required_fields.append({'form_id': 'description', 
                                    'sort'   : '3',
                                    'field'  : [{'entitytypeid': 'DESCRIPTION.E62', 'data_group': _('Description'), 'type': 'warning'}]})
            required_entities = [{'entitytypeid': 'REGION.E55', 'data_group': _('Region'), 'type': 'error'},
                                 {'entitytypeid': 'STATE.E55', 'data_group': _('State'), 'type': 'error'},
                                 {'entitytypeid': 'SPATIAL_COORDINATES_GEOMETRY.E47', 'data_group': _('Mapped location'), 'type': 'error'}]
            if (resource.entitytypeid == 'HERITAGE_RESOURCE.E18'):
                required_entities.append({'entitytypeid': 'CONTEXT.E55', 'data_group': _('Context'), 'type': 'error'})
                if (construction_type == 'Original'):
                    required_entities.append({'entitytypeid': 'SETTLEMENT_TYPE.E55', 'data_group': _('Settlement Type'), 'type': 'error'})
            required_fields.append({'form_id': 'location', 
                                    'sort'   : '5',
                                    'field'  : required_entities})
   #if (resource.entitytypeid == 'HERITAGE_RESOURCE.E18'):
     #   if (ew_status == 'Draft' or ew_status == 'Required validation' or ew_status == 'Valid'):
     #       required_fields.append({'form_id': 'dating', 
     #                               'sort'   : '5',
     #                               'field'  : [{'entitytypeid': 'MEASUREMENT_TYPE.E62', 'data_group': _('Period'), 'type': 'warning'}]})
     #       required_fields.append({'form_id': 'related-files', 
     #                               'sort'   : '8',
     #                               'field'  : [{'entitytypeid': 'THUMBNAIL.E62', 'data_group': _('Image and files'), 'type': 'warning'}]})

    for form in required_fields:
        #print form["form_id"]
        #print form["field"]
        for field in form["field"]:
            #print field["entitytypeid"]
            #print field["data_group"]
            found = False;
            for entity in entities:
                #print entity.entitytypeid
                #print entity.value
                #print entity.label
                if (entity.entitytypeid == field["entitytypeid"] and entity.value != ''):
                    found = True;
                    break;
            if (not found):
                description = error_description
                if field['type'] == 'warning':
                    description = warning_description
                error = {'type': field['type'], 'form_id': form['form_id'], 'sort': form['sort'], 'data_group': field['data_group'], 'description': description}
                errors.append(error)

def check_unique_fields(resource, ew_status):
    # Checks if there are populated all required fields for given status
    error_description = _('There are more than one instance of that value.')
    if (ew_status == 'Draft' or ew_status == 'Pending approval' or ew_status == 'Published'):
        unique_fields = [{'form_id': 'summary', 
                          'sort'   : '1',
                          'field'  : [{'entitytypeid': 'NAME_TYPE.E55', 'data_group': _('Name Type'), 'type': 'error'},
                                      {'entitytypeid': 'RESOURCE_TYPE_CLASSIFICATION.E55', 'data_group': _('Watercraft Type'), 'type': 'error'}]},                       
                         {'form_id': 'description', 
                          'sort'   : '3',
                          'field'  : [{'entitytypeid': 'DESCRIPTION.E62', 'data_group': _('Description'), 'type': 'error'}]},
                         {'form_id': 'location', 
                          'sort'   : '4',
                          'field'  : [{'entitytypeid': 'SETTLEMENT_TYPE.E55', 'data_group': _('Settlement Type'), 'type': 'error'},
                                      {'entitytypeid': 'ADDRESS_TYPE.E55', 'data_group': _('Address Type'), 'type': 'error'}]},
                         {'form_id': 'dating', 
                          'sort'   : '5',
                          'field'  : [{'entitytypeid': 'MEASUREMENT_TYPE.E62', 'data_group': _('Period'), 'type': 'error'}]}]
   
    for form in unique_fields:
        #print form["form_id"]
        #print form["field"]
        for field in form["field"]:
            #print field["entitytypeid"]
            #print field["data_group"]
            foundDuplicate = False;
            value = ''
            for entity in entities:
                #print entity.entitytypeid
                #print entity.value
                #print entity.label
                if (entity.entitytypeid == field["entitytypeid"] and value != '' and entity.value != '' and value == entity.value):
                    foundDuplicate = True
                    print "Found duplicate!"
                    print entity.value
                    break
                if (entity.entitytypeid == field["entitytypeid"] and entity.value != ''):
                    value = entity.value
                
            if (foundDuplicate):
                error = {'type': field['type'], 'form_id': form['form_id'], 'sort': form['sort'], 'data_group': field['data_group'], 'description': error_description}
                errors.append(error)


def fill_all_entities(child_entities):
    for entity in child_entities:
        entities.append(entity)
        if entity.child_entities:
            fill_all_entities(entity.child_entities)

def get_current_construction_type(resource):
    for entity in entities:
        if entity.entitytypeid == 'CONSTRUCTION_TYPE.E55':
            return entity.label
    return 'Original'

def get_current_status(resource):
    del entities[:]
    fill_all_entities(resource.child_entities)
    for entity in entities:
        if entity.entitytypeid == 'EW_STATUS.E55':
            return entity.label
    return 'Draft'

def get_current_group(resource):
    del entities[:]
    fill_all_entities(resource.child_entities)
    for entity in entities:
        if entity.entitytypeid == 'EW_GROUP.E62':
            return entity.label
    return ''

def get_resource_icon(resource):
    del entities[:]
    fill_all_entities(resource.child_entities)
    ew_status = ''
    ew_type = ''
    element = ''
    material = ''
    construction_type = ''
    icon = '\uf060'
    
    for entity in entities:
        if entity.entitytypeid == 'EW_STATUS.E55':
            ew_status = entity.label
        if entity.entitytypeid == 'RESOURCE_TYPE_CLASSIFICATION.E55':
            ew_type = entity.label
        if entity.entitytypeid == 'COMPONENT_TYPE.E55':
            element = element + '<' + entity.label + '>'
        if entity.entitytypeid == 'MATERIAL.E57':
            material = material + '<' + entity.label + '>'
        if entity.entitytypeid == 'CONSTRUCTION_TYPE.E55':
            construction_type = construction_type + '<' + entity.label + '>'
    if (element == ''):
       element = '<Watercraft>'
       construction_type = '<Original>'
    # Ikone za ladje
    if ('<Watercraft>' in element):
        if (ew_type == 'Boat'):
            icon = u'\ue00d'
        else:
            if (ew_type == 'Coracle'):
                icon = u'\ue00c'
            else:
                if (ew_type == 'Raft'):
                    icon = u'\ue001'
                else:
                    if (ew_type == 'Canoe'):
                        icon = u'\ue00f'
                    else:
                        if (ew_type == 'Kayak'):
                            icon = u'\ue00e'
                        else:
                            if (ew_type == 'Board'):
                                icon = u'\ue00b'
    else:
        # Ikona za veslo
        if ('<Paddle>' in element):
            icon = u'\ue002'
        # Ikona za jadro
        if ('<Sail>' in element):
            icon = u'\ue00a'
        # Ikona za okvir
        if ('<Frame>' in element):
            icon = u'\ue007'
    
    # Za ostale tipe zaenkrat ne damo nobene posebne ikone
    if (resource.entitytypeid != 'HERITAGE_RESOURCE.E18' and resource.entitytypeid != 'HERITAGE_RESOURCE_GROUP.E27'):
        icon = u''
    
    # Ikone glede na status
    icon_status = ''
    if (ew_status == 'Draft'):
        icon_status = u'\uf011'
    else:
        if (ew_status == 'Pending approval'):
            icon_status = u'\uf02c'
        else:
            if ew_status == 'Approval rejected':
                icon_status = u'\uf081'
    # Barva glede na material 
    color = '#C4171D'
    if ('<Log>' in material):
        # Rjava
        color = '#8A4B08'
    if ('<Bark>' in material):
        # Siva
        color = '#585858'
    if ('<Bamboo>' in material):
        # Zelena
        color = '#088A08'
    if ('<Reed>' in material):
        # Oranzna
        color = '#B18904'
    if ('<Skin>' in material):
        # Roza
        color = '#F781BE'
    # Crke glede na tip konstrukcije
    con_type = ''
    if ('<Original>' in construction_type):
        con_type = ''
    else:
        if ('<Replica>' in construction_type):
            con_type = 'REP'
        else:
            if ('<Reconstruction>' in construction_type):
                con_type = 'REC'
            else:
                if ('<Virtual reconstruction>' in construction_type):
                    con_type = 'VRC'    
                else:
                    if ('<Model>' in construction_type):
                        con_type = 'MOD'
    icon_type = {'icon_type': icon, 'status': icon_status, 'color': color, 'con_type': con_type}
    
    return icon_type

def validate_resource(resource, ew_status):
    del entities[:]
    del errors[:]
    fill_all_entities(resource.child_entities)
    check_required_fields(resource, ew_status)
    # Unique se preverja ze v JS (sem dopolnil, da dela)
    #check_unique_fields(resource, ew_status)
    #print errors
    #check_duplicates(resource)
    #check_paired_attributes(resource)
    return sorted(errors, key=lambda x: x["sort"], reverse=False)


