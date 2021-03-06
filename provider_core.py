import random, string


def __random_string(stringLength=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def __get_credentials(db_name, suffix):
    user_name = f'{db_name}-{suffix}'
    pwd = __random_string()

    return user_name, pwd


def get_reader_credentials(db_name):
    """Return reader username, password for given database"""
    return __get_credentials(db_name, 'reader')


def get_writer_credentials(db_name):
    """Return writer username, password for given database"""
    return __get_credentials(db_name, 'writer')


def get_reader_secret_name(db_name):
    return f'{db_name}-reader'


def get_writer_secret_name(db_name):
    return f'{db_name}-writer'
