import functools
import logging
import sys

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

class Authorization:
    def __init__(self, resource, privileges, enabled=True):
        pass
    
    def assigns_roles(self, roles=[]):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, userid='', **kwargs):
                logger.info('in wrapper')
                #user_id = 'testing'
                val = func(*args, user_id='testing', roles=roles, **kwargs)
                return val
            return wrapped
        return decorator
    
    def assign(self, resource_id, **kwargs):
        logger.info('Locals -> ' + str(locals()))
        pass