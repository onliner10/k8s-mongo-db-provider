import kopf
import kubernetes
import base64
from pymongo import MongoClient

CLUSTER_DOMAIN = 'cluster.local'
APP_NAME='mongodb-replicaset'
SSL=False

kubernetes.config.load_kube_config()
ns_mongo = dict()

def has_label_and_ends_with(item, ends, labels_key='_labels'):
    labels = vars(item.metadata).get(labels_key)
    if not labels:
        return False

    app_label = labels.get('app')
    name = item.metadata.name

    return \
        app_label == APP_NAME \
        and name.endswith(ends)

def parse_credentials(secret):
    user = base64.b64decode(secret.data['user']).decode("utf-8")
    pwd = base64.b64decode(secret.data['password']).decode("utf-8")

    return user, pwd

def construct_connection_string(db_name, user, pwd, mongo_svc_name, ns):
    return f'mongodb+srv://{user}:{pwd}@{mongo_svc_name}.{ns}.svc.{CLUSTER_DOMAIN}/{db_name}?tls={SSL}'

def seek_mongo_svc(api, ns):
    svcs = api.list_namespaced_service(ns).items

    mongo_svc = next(x for x in svcs if has_label_and_ends_with(x, '-client'))
    return mongo_svc.metadata.name

def get_mongo_connection_string(ns, mongo_svc_name):
    api = kubernetes.client.CoreV1Api()
    if ns not in ns_mongo:
        secrets = api.list_namespaced_secret(ns).items
        admin_secret = next(x for x in secrets if has_label_and_ends_with(x, 'admin'))
        user,pwd = parse_credentials(admin_secret)

        ns_mongo[ns] = construct_connection_string('admin', user, pwd, mongo_svc_name, ns)

    return ns_mongo[ns]

def to_b64(data):
    return str(base64.b64encode(data.encode('utf-8')), "utf-8")

def create_secret(api, ns, secret_name, connection_string, db_name):
    secret_body = kubernetes.client.V1Secret(
                        data={
                            'ConnectionString': to_b64(connection_string),
                            'DbName': to_b64(db_name)
                        },
                        metadata=kubernetes.client.V1ObjectMeta(name=secret_name))
    api.create_namespaced_secret(ns, secret_body)

@kopf.on.create('urbanonsoftware.com', 'v1alpha1', 'mongodatabases')
def create_fn(body, **kwargs):
    ns = body['metadata']['namespace']
    resource_name = body['metadata']['name']
    db_name = body['spec']['dbName']

    reader_db_name = f'{db_name}_reader'
    reader_db_pwd = 'test123'
    writer_db_name = f'{db_name}_writer'
    writer_db_pwd = 'test123'

    api = kubernetes.client.CoreV1Api()
    mongo_svc = seek_mongo_svc(api, ns)
    admin_connection_string = get_mongo_connection_string(ns, mongo_svc)

    client = MongoClient(admin_connection_string, ssl=SSL)
    client[db_name]['__init'].insert_one({'init': 'ok'})
    client[db_name].add_user(writer_db_name, writer_db_pwd, roles=[{'role':'readWrite','db':db_name}])
    client[db_name].add_user(reader_db_name, reader_db_pwd, roles=[{'role': 'read', 'db': db_name}])

    reader_secret_name = f'{resource_name}-reader'
    writer_secret_name = f'{resource_name}-writer'

    writer_connection_string = construct_connection_string(db_name, writer_db_name, writer_db_pwd, mongo_svc, ns)
    reader_connection_string = construct_connection_string(db_name, reader_db_name, reader_db_pwd, mongo_svc, ns)

    create_secret(api, ns, reader_secret_name, reader_connection_string, db_name)
    create_secret(api, ns, writer_secret_name, writer_connection_string, db_name)

    # print(f'Abut to create {db_name} in {ns}')
