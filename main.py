import kopf

import mongo_adapter
import kubernetes_adapter
from provider_core import *
from env_helpers import *

API_GROUP = 'mongo-db-provider.urbanonsoftware.com'
CLUSTER_DOMAIN = env_get_string('CLUSTER_DOMAIN', 'cluster.local')
MONGO_APP_NAME = env_get_string('MONGO_APP_NAME', 'mongodb-replicaset')
TLS = str(env_get_bool('TLS', False)).lower()
HARD_DELETE = env_get_bool('HARD_DELETE', False)


# uncomment for debug
# kubernetes.config.load_kube_config()

def create_mongo_adapter(kubernetes, domain, tls):
    return mongo_adapter.MongoAdapter(kubernetes, domain, tls)


def create_kubernetes_adapter(app_name, ns):
    return kubernetes_adapter.KubernetesAdapter(app_name, ns)


@kopf.on.create(API_GROUP, 'v1alpha1', 'mongodatabases')
def create_fn(body, **kwargs):
    print(f'Create {body}')

    ns = body['metadata']['namespace']
    resource_name = body['metadata']['name']
    db_name = resource_name

    kubernetes = create_kubernetes_adapter(MONGO_APP_NAME, ns)

    reader_user, reader_pwd = get_reader_credentials(db_name)
    writer_user, writer_pwd = get_writer_credentials(db_name)

    mongo = create_mongo_adapter(kubernetes, CLUSTER_DOMAIN, TLS)
    mongo.init_database(db_name)
    mongo.add_user(reader_user, reader_pwd, db_name, 'read')
    mongo.add_user(writer_user, writer_pwd, db_name, 'readWrite')

    reader_secret_name = get_reader_secret_name(resource_name)
    writer_secret_name = get_writer_secret_name(resource_name)

    writer_connection_string = mongo.connection_string(db_name, writer_user, writer_pwd)
    reader_connection_string = mongo.connection_string(db_name, reader_user, reader_pwd)

    kubernetes.create_secret(reader_secret_name, reader_connection_string, db_name)
    kubernetes.create_secret(writer_secret_name, writer_connection_string, db_name)


@kopf.on.delete(API_GROUP, 'v1alpha1', 'mongodatabases')
def delete_fn(body, **kwargs):
    print(f'Delete {body}')

    ns = body['metadata']['namespace']
    resource_name = body['metadata']['name']

    reader_secret_name = get_reader_secret_name(resource_name)
    writer_secret_name = get_writer_secret_name(resource_name)

    kubernetes = create_kubernetes_adapter(MONGO_APP_NAME, ns)
    kubernetes.delete_secret(reader_secret_name)
    kubernetes.delete_secret(writer_secret_name)

    if HARD_DELETE:
        mongo = create_mongo_adapter(kubernetes, CLUSTER_DOMAIN, TLS)
        mongo.drop_database(resource_name)
