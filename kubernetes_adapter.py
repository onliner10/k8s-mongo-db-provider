import base64
import kubernetes
from kubernetes.client.rest import ApiException


class KubernetesAdapter:
    def __init__(self, label_value, ns):
        self.api = kubernetes.client.CoreV1Api()
        self.label_value = label_value
        self.ns = ns

    def __has_label_and_ends_with(self, item, ends):
        labels = vars(item.metadata).get('_labels')
        if not labels:
            return False

        app_label = labels.get('app')
        name = item.metadata.name

        return \
            app_label == self.label_value \
            and name.endswith(ends)

    def seek_mongo_svc(self):
        svcs = self.api.list_namespaced_service(self.ns).items

        mongo_svc = next(x for x in svcs if self.__has_label_and_ends_with(x, '-client'))
        return mongo_svc.metadata.name

    def seek_mongo_credentials(self):
        secrets = self.api.list_namespaced_secret(self.ns).items
        admin_secret = next(x for x in secrets if self.__has_label_and_ends_with(x, 'admin'))

        b64_user = admin_secret.data['user']
        b64_pwd = admin_secret.data['password']

        user = base64.b64decode(b64_user).decode("utf-8")
        pwd = base64.b64decode(b64_pwd).decode("utf-8")

        return user, pwd

    @staticmethod
    def __to_b64(data):
        return str(base64.b64encode(data.encode('utf-8')), "utf-8")

    def create_secret(self, secret_name, connection_string, db_name):
        secret_body = kubernetes.client.V1Secret(
            data={
                'ConnectionString': self.__to_b64(connection_string),
                'DbName': self.__to_b64(db_name)
            },
            metadata=kubernetes.client.V1ObjectMeta(name=secret_name))
        self.api.create_namespaced_secret(self.ns, secret_body)

    def delete_secret(self, secret_name):
        try:
            self.api.delete_namespaced_secret(secret_name, self.ns)
        except ApiException as e:
            if e.status == 404:
                print("Secret '%s' already deleted, continuing" % secret_name)
                return
            raise
