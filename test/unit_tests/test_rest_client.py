import fakeredis
import unittest
import uuid

from deathnut.util.logger import get_deathnut_logger
from deathnut.client.rest_client import DeathnutRestClient

logger = get_deathnut_logger(__name__)
fake_redis_conn = fakeredis.FakeStrictRedis()
dn_client = DeathnutRestClient(service='test', redis_connection=fake_redis_conn)

class TestRestDeathnutClient(unittest.TestCase):
    def setUp(self):
        fake_redis_conn.flushall()
    
    def test_execute_if_authorized(self):
        pass