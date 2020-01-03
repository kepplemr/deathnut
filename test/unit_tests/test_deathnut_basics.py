import birdisle
import unittest

from deathnut.client import DeathnutClient

server = birdisle.Server()
redis = birdisle.redis.StrictRedis(server=server)

dn_client = DeathnutClient(service='test', resource='recipes', redis_connection=redis)

class TestEquivalenceHash(unittest.TestCase):
    def test_duplicate_recipes_hashes_are_equal(self):
        pass