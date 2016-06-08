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

from arches_hip import urls as arches_hip_urls
from django.conf.urls import patterns, url, include

uuid_regex = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

urlpatterns = patterns('',
    url(r'^$', 'ew.views.main.index'),
    url(r'^rdm/(?P<conceptid>%s|())$' % uuid_regex , 'ew.views.concept.rdm', name='rdm'),
    url(r'^index.htm', 'ew.views.main.index', name='home'),
    url(r'^auth/', 'ew.views.main.auth', name='auth'),
    url(r'^map', 'ew.views.map.get_page', name="map"),
    url(r'^search$', 'ew.views.search.home_page', name="search_home"),
    url(r'^search/terms$', 'ew.views.search.search_terms', name="search_terms"),
    url(r'^search/resources$', 'ew.views.search.search_results', name="search_results"),
    url(r'^search/export$', 'ew.views.search.export_results', name="search_results_export"),
    url(r'^resources/(?P<resourcetypeid>[0-9a-zA-Z_.]*)/(?P<form_id>[a-zA-Z_-]*)/(?P<resourceid>%s|())$' % uuid_regex, 'ew.views.resources.resource_manager', name="resource_manager"),
    url(r'^reports/(?P<resourceid>%s)$' % uuid_regex , 'ew.views.resources.report', name='report'),
    url(r'^resources/layers/(?P<entitytypeid>.*)$', 'ew.views.resources.map_layers', name="map_layers"),
    url(r'^resources/markers/(?P<entitytypeid>.*)$', 'ew.views.resources.map_layers', {'get_centroids':True}, name="map_markers"),    
    url(r'', include(arches_hip_urls)),
    # Change Password URLs:
    url(r'^accounts/password_change/$', 
        'django.contrib.auth.views.password_change', 
        {'post_change_redirect' : '/accounts/password_change/done/'}, 
        name="password_change"), 
    (r'^accounts/password_change/done/$', 
        'django.contrib.auth.views.password_change_done')
)
