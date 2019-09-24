import os


def env_get_string(key, default=''):
    val = os.environ.get(key)

    if val is None:
        return default

    return val


def env_get_bool(key, default=False):
    val = env_get_string(key).lower().strip()

    if val == 'true':
        return True
    elif val == 'false':
        return False

    return default
