import time
import unittest
import uuid
from timeit import default_timer as timer

import fakeredis
from deathnut.client.rest_client import DeathnutRestClient
from deathnut.util.logger import get_deathnut_logger

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


logger = get_deathnut_logger(__name__)
fake_redis_conn = fakeredis.FakeStrictRedis()


def execute_me_on_success(*args, **kwargs):
    return True


def execute_me_on_failure(*args, **kwargs):
    return False


def slow_auth(*args, **kwargs):
    time.sleep(3)
    return True


def slow_getter(*args, **kwargs):
    time.sleep(3)
    return True


dnr_client = DeathnutRestClient(
    service="test",
    failure_callback=execute_me_on_failure,
    redis_connection=fake_redis_conn,
)


class TestRestDeathnutClient(unittest.TestCase):
    def setUp(self):
        fake_redis_conn.flushall()

    def test_execute_if_authorized(self):
        random_resource_id = str(uuid.uuid4())
        self.assertFalse(
            dnr_client.execute_if_authorized(
                "test_user",
                "own",
                random_resource_id,
                True,
                True,
                False,
                execute_me_on_success,
            )
        )
        dnr_client.assign_role("test_user", "own", random_resource_id)
        self.assertTrue(
            dnr_client.execute_if_authorized(
                "test_user",
                "own",
                random_resource_id,
                True,
                True,
                False,
                execute_me_on_success,
            )
        )

    @patch.object(dnr_client, "_is_authorized", new=slow_auth)
    def test_dont_wait_speeds_up(self):
        random_resource_id = str(uuid.uuid4())
        start = timer()
        self.assertTrue(
            dnr_client.execute_if_authorized(
                "test_user", "own", random_resource_id, True, True, False, slow_getter
            )
        )
        end = timer()
        wait_time = int(end - start)
        start = timer()
        self.assertTrue(
            dnr_client.execute_if_authorized(
                "test_user", "own", random_resource_id, True, True, True, slow_getter
            )
        )
        end = timer()
        dont_wait_time = int(end - start)
        self.assertGreater(wait_time, dont_wait_time)
