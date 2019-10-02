from pymongo import MongoClient


class MongoAdapter:
    def __init__(self, mongo_seeker, cluster_domain, tls):
        self.tls = tls
        self.seeker = mongo_seeker
        self.cluster_domain = cluster_domain
        self.mongo_svc = mongo_seeker.seek_mongo_svc()

        admin_usr, admin_pwd = mongo_seeker.seek_mongo_credentials()
        admin_connection_string = self.connection_string('admin', admin_usr, admin_pwd)
        self.client = MongoClient(admin_connection_string, ssl = self.tls)

    def connection_string(self, db_name, user, pwd):
        return f'mongodb+srv://{user}:{pwd}@{self.mongo_svc}.{self.seeker.ns}.svc.{self.cluster_domain}/{db_name}?tls={self.tls}'

    def init_database(self, db_name):
        self.client[db_name]['__init'].insert_one({'init': 'ok'})

    def add_user(self, name, password, db_name, role = 'read'):
        self.client[db_name].add_user(name, password, roles=[{'role': role, 'db': db_name}])

    def drop_database(self, db_name):
        all_dbs = self.client.list_database_names()

        if db_name in all_dbs:
            self.client.drop_database(db_name)
        else:
            print("Database '%s' already deleted" % db_name)