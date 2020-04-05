"""
Tests time and space performance of redis data strategies for:
1) Assign role
2) Check role
3) Remove role
4) Get ids for user, role
"""
import functools
import time
import uuid

import docker
import redis

USER = "michael"
SERVICE_NAME = "dimsum_edited-recipes"
PERMISSION = "view"
TEST_SIZES = [10, 400, 1_000_000]
TEST_RUNS_PER_SIZE = 10

docker_client = docker.from_env()
for container in docker_client.containers.list(all=True):
    container.remove(force=True)

# https://www.peterbe.com/plog/understanding-redis-hash-max-ziplist-entries
docker_client.containers.run("redis:3.2.5-alpine", name="redis", ports={'6379/tcp': 6379}, detach=True)

def time_me(func):
    @functools.wraps(func)
    def timed(*args, **kwargs):
        t0 = time.time()
        func(*args, **kwargs)
        t1 = time.time()
        return t1 - t0
    return timed

def generate_ids(size):
    results = size * [None]
    for i in range(size):
        results[i] = str(uuid.uuid4())
    return results

class BaseImplementation(object):
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost')
    def flush(self):
        self.redis_client.flushall()
    def memory_info(self):
        memory_size = int(self.redis_client.info()['used_memory']) / 1024 / 1024
        print('Memory size (mb): ', memory_size)
class HashImplementation(BaseImplementation):
    def __init__(self):
        super(HashImplementation, self).__init__()
    @time_me
    def assign_role(self, resource_ids):
        for r_id in resource_ids:
            self.redis_client.hset("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id, 1)
    @time_me
    def check_role(self, resource_ids):
        for r_id in resource_ids:
            assert bool(self.redis_client.hget("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id)) == True
    @time_me
    def remove_role(self, resource_ids):
        for r_id in resource_ids:
            self.redis_client.hdel("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id)
    @time_me
    def get_ids_for_user_and_role(self, limit):
        cursor = "0"
        while cursor != 0:
            cursor, data = self.redis_client.hscan("{}:{}:{}".format(SERVICE_NAME, USER, PERMISSION),
                cursor=cursor, count=limit)
            yield [x[0].decode() for x in data.items()]

class SetImplementation(BaseImplementation):
    def __init__(self):
        super(SetImplementation, self).__init__()
    @time_me
    def assign_role(self, resource_ids):
        for r_id in resource_ids:
            self.redis_client.sadd("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id)
    @time_me
    def check_role(self, resource_ids):
        for r_id in resource_ids:
            assert bool(self.redis_client.sismember("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id)) == True
    @time_me
    def remove_role(self, resource_ids):
        for r_id in resource_ids:
            self.redis_client.srem("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id)
    @time_me
    def get_ids_for_user_and_role(self, limit):
        return self.redis_client.smembers("{}:{}:{}".format(SERVICE_NAME, USER, 'view'))

for strat in [HashImplementation, SetImplementation]:
    curr_strat = strat()
    print('\nCurrent strategy: ', curr_strat.__class__)
    for test_size in TEST_SIZES:
        assign_time = check_time = remove_time = get_ids_time = 0.0
        print('Current size: ', test_size)
        for run_number in range(0, TEST_RUNS_PER_SIZE):
            curr_strat.flush()
            resource_ids = generate_ids(test_size)
            assign_time += curr_strat.assign_role(resource_ids)
            check_time += curr_strat.check_role(resource_ids)
            remove_time += curr_strat.remove_role(resource_ids)
            get_ids_time += curr_strat.get_ids_for_user_and_role(limit=test_size)
        curr_strat.memory_info()
        print('Average assign time for size {}: {}'.format(test_size, (assign_time / TEST_RUNS_PER_SIZE)))
        print('Average check time for size {}: {}'.format(test_size, (check_time / TEST_RUNS_PER_SIZE)))
        print('Average remove time for size {}: {}'.format(test_size, (remove_time / TEST_RUNS_PER_SIZE)))
        print('Average get_ids time for size {}: {}\n'.format(test_size, (get_ids_time / TEST_RUNS_PER_SIZE)))
# view_resources = list(itertools.chain.from_iterable(get_resources(redis_client, USER, 'view')))
# scan 0 match dimsum_edited-recipes:michael:*
