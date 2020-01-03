import fakeredis
import unittest

from deathnut.client.deathnut_client import DeathnutClient

fake_redis_conn = fakeredis.FakeStrictRedis()

dn_client = DeathnutClient(service='test', resource='recipes', redis_connection=fake_redis_conn)

class TestEquivalenceHash(unittest.TestCase):
    def test_duplicate_recipes_hashes_are_equal(self):
        pass