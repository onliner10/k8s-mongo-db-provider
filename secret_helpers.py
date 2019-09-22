import kubernetes, base64


def __to_b64(data):
    return str(base64.b64encode(data.encode('utf-8')), "utf-8")


def create_secret(api, ns, secret_name, connection_string, db_name):
    secret_body = kubernetes.client.V1Secret(
                        data={
                            'ConnectionString': __to_b64(connection_string),
                            'DbName': __to_b64(db_name)
                        },
                        metadata=kubernetes.client.V1ObjectMeta(name=secret_name))
    api.create_namespaced_secret(ns, secret_body)
