import base64


def parse_credentials(secret):
    user = base64.b64decode(secret.data['user']).decode("utf-8")
    pwd = base64.b64decode(secret.data['password']).decode("utf-8")

    return user, pwd


class Seeker:
    def __init__(self, api, label_value, ns):
        self.api = api
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

    def parse_credentials(secret):
        user = base64.b64decode(secret.data['user']).decode("utf-8")
        pwd = base64.b64decode(secret.data['password']).decode("utf-8")

        return user, pwd

    def seek_mongo_svc(self):
        svcs = self.api.list_namespaced_service(self.ns).items

        mongo_svc = next(x for x in svcs if self.__has_label_and_ends_with(x, '-client'))
        return mongo_svc.metadata.name

    def seek_mongo_credentials(self):
        secrets = self.api.list_namespaced_secret(self.ns).items
        admin_secret = next(x for x in secrets if self.__has_label_and_ends_with(x, 'admin'))
        return parse_credentials(admin_secret)
