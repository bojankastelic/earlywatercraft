import os
import sys
from django.conf import settings
from django.core import management
import arches_hip.setup as setup
from management.commands.package_utils import authority_files
from arches.db.install import install_db
from ew.models.resource import Resource
import os.path

def install(path_to_source_data_dir=None):
    setup.install()
    install_ew_db()

def load_resource_graphs():
    setup.resource_graphs.load_graphs(break_on_error=True)

def load_authority_files(path_to_files=None):
    setup.authority_files.load_authority_files(path_to_files, break_on_error=True)

def load_resources(external_file=None):
    setup.load_resources(external_file)

    
def load_authority_files(path_to_files=None):
    authority_files.load_authority_files(path_to_files, break_on_error=True)
    
def create_indexes():
    Resource().prepare_resource_relations_index(create=True)
    Resource().prepare_search_index('HERITAGE_RESOURCE_GROUP.E27', create=True)
    Resource().prepare_search_index('HERITAGE_RESOURCE.E18', create=True)
    Resource().prepare_search_index('INFORMATION_RESOURCE.E73', create=True)
    Resource().prepare_search_index('ACTIVITY.E7', create=True)
    Resource().prepare_search_index('ACTOR.E39', create=True)
    Resource().prepare_search_index('HISTORICAL_EVENT.E5', create=True)
    
def install_ew_db():
    ew_db_settings = settings.DATABASES['default']
    install_ew_path = os.path.join(os.path.dirname(settings.PACKAGE_ROOT), 'db', 'install', 'install_ew_db.sql')  
    print install_ew_path
    ew_db_settings['install_path'] = install_ew_path   
        
    os.system('psql -h %(HOST)s -p %(PORT)s -U %(USER)s -d %(NAME)s -f "%(install_path)s"' % ew_db_settings)
