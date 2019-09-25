import unittest
from unittest.mock import MagicMock, patch, ANY
from main import create_fn, delete_fn, MONGO_APP_NAME, CLUSTER_DOMAIN, TLS
import main


@patch('main.create_kubernetes_adapter')
@patch('main.create_mongo_adapter')
class HandlersTestCase(unittest.TestCase):
    TEST_NS = 'TEST-NAMESPACE'
    TEST_RESOURCE_NAME = 'TEST-MONGO'
    TEST_BODY = {
        "metadata": {
            "namespace": TEST_NS,
            "name": TEST_RESOURCE_NAME
        }
    }

    def test_create_handler_creates_adapters(self, mongo_mock, kubernetes_mock):
        create_fn(self.TEST_BODY)

        kubernetes_mock.assert_called_with(MONGO_APP_NAME, self.TEST_NS)
        mongo_mock.assert_called_with(kubernetes_mock.return_value, CLUSTER_DOMAIN, TLS)

    def test_create_handler_inits_database(self, mongo_mock, kubernetes_mock):
        create_fn(self.TEST_BODY)

        init_database = mongo_mock.return_value.init_database

        init_database.assert_called_with(self.TEST_RESOURCE_NAME)
        assert init_database.call_count == 1

    def test_create_handler_creates_users_in_mongo(self, mongo_mock, kubernetes_mock):
        create_fn(self.TEST_BODY)

        add_user = mongo_mock.return_value.add_user
        add_user.assert_any_call(f'{self.TEST_RESOURCE_NAME}-reader', ANY, self.TEST_RESOURCE_NAME, 'read')
        add_user.assert_any_call(f'{self.TEST_RESOURCE_NAME}-writer', ANY, self.TEST_RESOURCE_NAME, 'readWrite')

        assert add_user.call_count == 2

    def test_create_handler_creates_secrets(self, mongo_mock, kubernetes_mock):
        get_connection_string = mongo_mock.return_value.connection_string
        get_connection_string.side_effect = lambda db, user, pwd: user

        create_fn(self.TEST_BODY)

        reader_name = f'{self.TEST_RESOURCE_NAME}-reader'
        writer_name = f'{self.TEST_RESOURCE_NAME}-writer'

        get_connection_string.assert_any_call(self.TEST_RESOURCE_NAME, reader_name, ANY)
        get_connection_string.assert_any_call(self.TEST_RESOURCE_NAME, writer_name, ANY)
        assert get_connection_string.call_count == 2

        create_secret = kubernetes_mock.return_value.create_secret
        create_secret.assert_any_call(reader_name, reader_name, self.TEST_RESOURCE_NAME)
        create_secret.assert_any_call(writer_name, writer_name, self.TEST_RESOURCE_NAME)
        assert create_secret.call_count == 2

    def test_delete_handler_and_default_hard_delete_doesnt_delete_database(self, mongo_mock, kubernetes_mock):
        delete_fn(self.TEST_BODY)
        drop_database = mongo_mock.return_value.drop_database

        assert drop_database.call_count == 0

    def test_delete_handler_and_hard_delete_true_drops_db(self, mongo_mock, kubernetes_mock):
        main.HARD_DELETE = True

        delete_fn(self.TEST_BODY)
        drop_database = mongo_mock.return_value.drop_database

        drop_database.assert_called_with(self.TEST_RESOURCE_NAME)
        assert drop_database.call_count == 1

    def test_delete_handler_drops_secrets(self, mongo_mock, kubernetes_mock):
        delete_fn(self.TEST_BODY)

        delete_secret = kubernetes_mock.return_value.delete_secret
        reader_name = f'{self.TEST_RESOURCE_NAME}-reader'
        writer_name = f'{self.TEST_RESOURCE_NAME}-writer'

        delete_secret.assert_any_call(reader_name)
        delete_secret.assert_any_call(writer_name)

        assert delete_secret.call_count == 2


if __name__ == '__main__':
    unittest.main()
