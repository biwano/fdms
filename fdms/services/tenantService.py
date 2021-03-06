""" Contains the class managing tenants """
from . import SchemaService
from .esService import EsService
from .documentService import DocumentService
from .constants import (SCHEMA_SCHEMA_DEFINITION, 
ROOT_SCHEMA_DEFINITION, 
FOLDER_SCHEMA_DEFINITION, 
USER_SCHEMA_DEFINITION, 
GROUP_SCHEMA_DEFINITION,
TENANT_SCHEMA_DEFINITION,
TENANT_MASTER)

class TenantService(object):
    """ Class managing tenants """
    def __init__(self, tenant_id, context):
        self.tenant_id = tenant_id
        self.es_service = EsService()
        self.context = context
        

    def create(self, drop=False):
        """ Creates a tenant """
        # create data index
        self.es_service.create_data_index(self.tenant_id, drop)

        SchemaService(self.tenant_id, "root", self.context, refresh="wait_for").register(SCHEMA_SCHEMA_DEFINITION, drop, persist=False)
        
        document_service = DocumentService(self.tenant_id, self.context, refresh="wait_for")
        # create root document
        root = document_service.create("root", {
            "id": "root",
            }, parent=None)

        # create base search indexes
        SchemaService(self.tenant_id, "schema", self.context).register(SCHEMA_SCHEMA_DEFINITION, drop)
        SchemaService(self.tenant_id, "root", self.context).register(SCHEMA_SCHEMA_DEFINITION, drop=False)
        SchemaService(self.tenant_id, "folder", self.context).register(FOLDER_SCHEMA_DEFINITION, drop)
        SchemaService(self.tenant_id, "user", self.context).register(USER_SCHEMA_DEFINITION, drop)
        SchemaService(self.tenant_id, "group", self.context).register(GROUP_SCHEMA_DEFINITION, drop)
        if self.tenant_id == TENANT_MASTER:
            SchemaService(self.tenant_id, "tenant", self.context).register(TENANT_SCHEMA_DEFINITION, drop)

        
        # create base users
        document_service.create("user", {
            "id": "admin",
            "is_tenant_admin": True
            }, parent = root["document_uuid"])
        # create base groups
        document_service.create("group", {
            "id": "admin",
            "users": ["admin"]
            }, parent = root["document_uuid"])
        # Register tenant in tenant master
        fdms_document_service = DocumentService(TENANT_MASTER, self.context, refresh="wait_for")
        fdms_document_service.create("tenant", {
                "id": self.tenant_id,
                }, parent=fdms_document_service.get_root())

    def delete(self, drop=False):
        """ Delete tenant """
        
        # Find all schemas
        document_service = DocumentService(self.tenant_id, self.context)
        schemas = document_service.search("schema")
        
        # Delete all schemas
        for schema in schemas:
            SchemaService(self.tenant_id, schema["id"], self.context).delete()

        self.es_service.delete_data_index(self.tenant_id)

        # Unregister tenant in tenant master
        
        document_service = DocumentService(TENANT_MASTER, self.context, refresh="wait_for")
        document_service.delete_child_by_id("/", self.tenant_id)            
