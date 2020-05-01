import unittest
import uuid

import fakeredis
from deathnut.client.deathnut_client import DeathnutClient
from deathnut.util.logger import get_deathnut_logger

logger = get_deathnut_logger(__name__)
fake_redis_conn = fakeredis.FakeStrictRedis()
dn_client = DeathnutClient(service="test", resource_type="recipes", redis_connection=fake_redis_conn)

class TestBaseDeathnutClient(unittest.TestCase):
    def setUp(self):
        fake_redis_conn.flushall()

    def test_assign_role(self):
        random_resource_id = str(uuid.uuid4())
        dn_client.assign_role("test_user", "own", random_resource_id)
        self.assertTrue(fake_redis_conn.sismember("test_recipes:test_user:own", random_resource_id))
        self.assertFalse(fake_redis_conn.sismember("test_recipes:test_user:own", "42"))
        #self.assertTrue(fake_redis_conn.hget("test_recipes:test_user:own", random_resource_id))
        #self.assertFalse(fake_redis_conn.hget("test_recipes:test_user:own", "42"))

    def test_check_role(self):
        random_resource_id = str(uuid.uuid4())
        self.assertFalse(dn_client.check_role("test_user", "own", random_resource_id))
        dn_client.assign_role("test_user", "own", random_resource_id)
        self.assertTrue(fake_redis_conn.sismember("test_recipes:test_user:own", random_resource_id))
        #self.assertTrue(fake_redis_conn.hget("test_recipes:test_user:own", random_resource_id))
        self.assertTrue(dn_client.check_role("test_user", "own", random_resource_id))

    def test_revoke_role(self):
        random_resource_id = str(uuid.uuid4())
        self.assertFalse(dn_client.check_role("test_user", "own", random_resource_id))
        dn_client.assign_role("test_user", "own", random_resource_id)
        self.assertTrue(fake_redis_conn.sismember("test_recipes:test_user:own", random_resource_id))
        #self.assertTrue(fake_redis_conn.hget("test_recipes:test_user:own", random_resource_id))
        self.assertTrue(dn_client.check_role("test_user", "own", random_resource_id))
        dn_client.revoke_role("test_user", "own", random_resource_id)
        self.assertFalse(fake_redis_conn.sismember("test_recipes:test_user:own", random_resource_id))
        #self.assertFalse(fake_redis_conn.hget("test_recipes:test_user:own", random_resource_id))
        self.assertFalse(dn_client.check_role("test_user", "own", random_resource_id))

    def test_get_resources(self):
        for _ in range(90):
            random_resource_id = str(uuid.uuid4())
            dn_client.assign_role("test_user", "view", random_resource_id)
        self.assertEqual(90, len(dn_client.get_resources("test_user", "view")))
        self.assertEqual(42, len(dn_client.get_resources("test_user", "view", limit=42)))
        self.assertEqual(5, len(list(dn_client.get_resources_page("test_user", "view", page_size=20))))
        self.assertEqual(9, len(list(dn_client.get_resources_page("test_user", "view", page_size=10))))
        self.assertEqual(1, len(list(dn_client.get_resources_page("test_user", "view", page_size=90))))
        for page in dn_client.get_resources_page("test_user", "view", page_size=10):
            self.assertEqual(10, len(page))
