import fakeredis
import unittest

from deathnut.client.deathnut_client import DeathnutClient

fake_redis_conn = fakeredis.FakeStrictRedis()

dn_client = DeathnutClient(service='test', resource='recipes', redis_connection=fake_redis_conn)

class TestBaseDeathnutClient(unittest.TestCase):
    def test_assign_role(self):
        pass

    def test_check_role(self):
        pass

    def test_revoke_role(self):
        pass

    def test_get_resources(self):
        pass

    def test_basic_flow(self):
        pass