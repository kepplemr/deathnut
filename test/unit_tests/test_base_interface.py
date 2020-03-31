import time
import unittest
import uuid
from timeit import default_timer as timer

import fakeredis
from deathnut.interface.base_interface import BaseAuthorizationInterface
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

logger = get_deathnut_logger(__name__)
fake_redis_conn = fakeredis.FakeStrictRedis()

def execute_me_on_success(*args, **kwargs):
    return True

def slow_auth(*args, **kwargs):
    time.sleep(3)
    return True

def slow_getter(*args, **kwargs):
    time.sleep(3)
    return True

class TestInterface(BaseAuthorizationInterface):
    @staticmethod
    def get_auth_header(*args, **kwargs):
        pass
    @staticmethod
    def get_resource_id(id_identifier, *args, **kwargs):
        pass
    @staticmethod
    def get_dont_wait(*args, **kwargs):
        pass
    def create_auth_endpoint(self, name, requires_role, grants_role):
        pass

# we can't instantiate the BaseInterface class but we're only testing Base methods here
auth_o = TestInterface(service="test", resource_type="resource", strict=True, enabled=True,
    redis_connection=fake_redis_conn)

class TestRestDeathnutClient(unittest.TestCase):
    def setUp(self):
        fake_redis_conn.flushall()

    def test_execute_if_authorized(self):
        random_resource_id = str(uuid.uuid4())
        self.assertRaises(DeathnutException, auth_o._execute_if_authorized, "test_user", "own",
            random_resource_id, True, True, False, execute_me_on_success)
        auth_o.assign_roles(random_resource_id, ["own"], deathnut_calling_user="test_user", deathnut_user="test_user")
        self.assertTrue(auth_o._execute_if_authorized("test_user", "own", random_resource_id, True,
            True, False, execute_me_on_success))

    @patch.object(auth_o, "is_authorized", new=slow_auth)
    def test_dont_wait_speeds_up(self):
        random_resource_id = str(uuid.uuid4())
        start = timer()
        self.assertTrue(auth_o._execute_if_authorized("test_user", "own", random_resource_id,
            True, True, False, slow_getter))
        end = timer()
        wait_time = int(end - start)
        start = timer()
        self.assertTrue(auth_o._execute_if_authorized("test_user", "own", random_resource_id, True,
            True, True, slow_getter))
        end = timer()
        dont_wait_time = int(end - start)
        self.assertGreater(wait_time, dont_wait_time)
