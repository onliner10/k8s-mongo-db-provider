import kopf
import kubernetes
from pymongo import MongoClient
from provider_core import *
from secret_helpers import create_secret
from seeker import Seeker

API_GROUP = 'mongo-db-provider.urbanonsoftware.com'
CLUSTER_DOMAIN = 'cluster.local'
APP_NAME='mongodb-replicaset'
TLS=False
HARD_DELETE=True

# uncomment for debug
# kubernetes.config.load_kube_config()

def construct_connection_string(ns, db_name, user, pwd, mongo_svc_name):
    return f'mongodb+srv://{user}:{pwd}@{mongo_svc_name}.{ns}.svc.{CLUSTER_DOMAIN}/{db_name}?tls={TLS}'

def create_mongo_admin_client(seeker):
    mongo_svc = seeker.seek_mongo_svc()
    admin_usr, admin_pwd = seeker.seek_mongo_credentials()
    admin_connection_string = construct_connection_string(seeker.ns, 'admin', admin_usr, admin_pwd, mongo_svc)

    return MongoClient(admin_connection_string, ssl=TLS)

@kopf.on.create(API_GROUP, 'v1alpha1', 'mongodatabases')
def create_fn(body, **kwargs):
    print(f'Create {body}')

    ns = body['metadata']['namespace']
    resource_name = body['metadata']['name']
    db_name = resource_name

    api = kubernetes.client.CoreV1Api()
    seeker = Seeker(api, APP_NAME, ns)
    mongo_svc = seeker.seek_mongo_svc()

    client = create_mongo_admin_client(seeker)
    client[db_name]['__init'].insert_one({'init': 'ok'})

    reader_user, reader_pwd = get_reader_credentials(db_name)
    writer_user, writer_pwd = get_writer_credentials(db_name)
    client[db_name].add_user(writer_user, writer_pwd, roles=[{'role':'readWrite','db':db_name}])
    client[db_name].add_user(reader_user, reader_pwd, roles=[{'role': 'read', 'db': db_name}])

    reader_secret_name = get_reader_secret_name(resource_name)
    writer_secret_name = get_writer_secret_name(resource_name)

    writer_connection_string = construct_connection_string(ns, db_name, writer_user, writer_pwd, mongo_svc)
    reader_connection_string = construct_connection_string(ns, db_name, reader_user, reader_pwd, mongo_svc)

    create_secret(api, ns, reader_secret_name, reader_connection_string, db_name)
    create_secret(api, ns, writer_secret_name, writer_connection_string, db_name)

@kopf.on.delete(API_GROUP, 'v1alpha1', 'mongodatabases')
def delete_fn(body, **kwargs):
    print(f'Delete {body}')

    ns = body['metadata']['namespace']
    resource_name = body['metadata']['name']

    reader_secret_name = get_reader_secret_name(resource_name)
    writer_secret_name = get_writer_secret_name(resource_name)

    api = kubernetes.client.CoreV1Api()
    api.delete_namespaced_secret(reader_secret_name, ns)
    api.delete_namespaced_secret(writer_secret_name, ns)

    if HARD_DELETE:
        seeker = Seeker(api, APP_NAME, ns)
        client = create_mongo_admin_client(seeker)
        client.drop_database(resource_name)