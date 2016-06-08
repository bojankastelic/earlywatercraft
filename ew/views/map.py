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

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.conf import settings
from django.contrib.auth.models import User
from arches.app.utils.betterJSONSerializer import JSONSerializer

def get_page(request):
    resource_id = request.GET.get('resourceid', '')
    # Pravice preverjamo zaenkrat le preko grup
    # Uporabnik mora imeti dodeljeno grupo z nazivom tipa resourca
    if (request.user.is_authenticated()):
        user = User.objects.get(username=request.user.username)
        if (user.is_staff or user.is_superuser):
           # Grupe vzamemo kar iz nastavitev
           user_groups = []
           all_groups = settings.RESOURCE_TYPE_CONFIGS()
           for group in all_groups:
               user_groups.append('EDIT_' + group)
               user_groups.append('PUBLISH_' + group)
        else:
           user_groups = user.groups.values_list('name', flat=True)
    else:
		user_groups = []
    json_user_groups = JSONSerializer().serialize(user_groups)
    return render_to_response('map.htm', {
            'main_script': 'map',
            'active_page': 'Map',
            'resource_id': resource_id,
            'user_groups': json_user_groups,
            'help' : settings.HELP['map']
        },
        context_instance=RequestContext(request))

