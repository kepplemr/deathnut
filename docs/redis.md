# redis overview

redis is used as the backend data store for user roles -> resource_ids. redis was chosen because it
is extremely fast, we're already using it, and GCP provides a managed, HA instance (Memorystore).

# data model

When designing deathnut, two approaches for redis id storage were considered: using redis sets and
using redis hashes.

## sets

redis sets are unordered collections of strings. The core deathnut operations (assign a role, check
a role, revoke a role) could be performed as:

```bash
# assign a role
redis:6379> SADD dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 1
# check a role
redis:6379> SISMEMBER dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 1
# revoke a role
redis:6379> SREM dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 1
redis:6379> SISMEMBER dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 0
```

## hashes

redis hashes are hashes that map string names to string values. This is the datastruture actually
utilized by the "low level" deathnut client (and the various interfaces built on top).

The hash approach equivalent of the above set commands:

```bash
# assign a role
redis:6379> HSET dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669 T
(integer) 1
# check a role
redis:6379> HGET dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
"T"
# revoke a role
redis:6379> HDEL dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 1
# re-check
redis:6379> HGET dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(nil)
```

## so why hashes over sets

In [redis docs on memory optimization](https://redis.io/topics/memory-optimization) they encourage
using hashes "when possible." The documentation there is excellent for a full overview of what's
going on, but suffice to say using hashes allows redis to store the hash values more efficiently in
memory (as a ziplist up to a certain threshold) as well as take advantage of cache locality
benefits.

The drawbacks of using a hash approach over sets are that we cannot assign TTLs to hash fields and
the keys and values can only be strings. Lack of TTL is not a concern for us because we *never*
want these keys to expire. That the keys and values must be strings is also not a limiting concern
as for the user object, keys should always be uuids (strings) and all we care about is whether they
are set or not, which we can represent perfectly well with a "T".

## who cares about memory usage, which approach is faster?

Fine. Scaling up memory is easy enough, what really matters is which one is faster. While the
ziplist approach may increase cache locality, it is also not a truly O(1) lookup when the



```python
"""
Tests time and space performance of redis data strategies for:
1) Assign role
2) Check role
3) Remove role
4) Get ids for user, role
"""
import functools
import itertools
import time
import uuid

import docker
import redis

USER = "michael"
SERVICE_NAME = "dimsum_edited-recipes"
PERMISSION = "view"
#TEST_SIZES = [10, 400, 10_000, 1_000_000]
TEST_SIZES = [10_000]
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

def get_resources(redis_conn, user, role, page_size=10):
    """
    Note
    ----
    In real redis, page_size is just a suggestion. If a value less than hash-max-ziplist-entries
    is provided, it will be ignored. See https://redis.io/commands/scan.
    """
    cursor = "0"
    while cursor != 0:
        cursor, data = redis_conn.hscan("{}:{}:{}".format(SERVICE_NAME, user, role),
            cursor=cursor, count=page_size)
        yield [x[0].decode() for x in data.items()]

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
            self.redis_client.hset("{}:{}:{}".format(SERVICE_NAME, USER, PERMISSION), r_id, 1)
    @time_me
    def check_role(self, resource_ids):
        for r_id in resource_ids:
            self.redis_client.hget("{}:{}:{}".format(SERVICE_NAME, USER, PERMISSION), r_id)
    @time_me
    def remove_role(self, resource_ids):
        for r_id in resource_ids:
            self.redis_client.hdel("{}:{}:{}".format(SERVICE_NAME, USER, PERMISSION), r_id)
    @time_me
    def get_ids_for_user_and_role(self, limit):
        return list(itertools.chain.from_iterable(self.get_ids(limit)))
    def get_ids(self, page_size=10):
        cursor = "0"
        while cursor != 0:
            cursor, data = self.redis_client.hscan("{}:{}:{}".format(SERVICE_NAME, USER, PERMISSION),
                cursor=cursor, count=page_size)
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
            self.redis_client.sismember("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id)
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
            if run_number == 0:
                curr_strat.memory_info()
            get_ids_time += curr_strat.get_ids_for_user_and_role(limit=test_size)
            remove_time += curr_strat.remove_role(resource_ids)
        print('Average assign time for size {}: {}'.format(test_size, (assign_time / TEST_RUNS_PER_SIZE)))
        print('Average check time for size {}: {}'.format(test_size, (check_time / TEST_RUNS_PER_SIZE)))
        print('Average get_ids time for size {}: {}'.format(test_size, (get_ids_time / TEST_RUNS_PER_SIZE)))
        print('Average remove time for size {}: {}\n'.format(test_size, (remove_time / TEST_RUNS_PER_SIZE)))
```

```bash
Current strategy:  <class '__main__.HashImplementation'>
Current size:  10
Memory size (mb):  0.7845611572265625
Average assign time for size 10: 0.004366040229797363
Average check time for size 10: 0.003734135627746582
Average get_ids time for size 10: 0.0005964994430541992
Average remove time for size 10: 0.0031267404556274414

Current size:  400
Memory size (mb):  0.7987823486328125
Average assign time for size 400: 0.13514745235443115
Average check time for size 400: 0.13190145492553712
Average get_ids time for size 400: 0.007589221000671387
Average remove time for size 400: 0.12719266414642333

Current size:  10000
Memory size (mb):  1.6711883544921875
Average assign time for size 10000: 3.000464415550232
Average check time for size 10000: 2.9063908576965334
Average get_ids time for size 10000: 0.15026919841766356
Average remove time for size 10000: 3.0094299793243406

Current size:  1000000
Memory size (mb):  85.07996368408203
Average assign time for size 1000000: 297.41595299243926
Average check time for size 1000000: 287.0515630245209
Average get_ids time for size 1000000: 11.717451572418213
Average remove time for size 1000000: 284.6934894800186


Current strategy:  <class '__main__.SetImplementation'>
Current size:  10
Memory size (mb):  0.7897720336914062
Average assign time for size 10: 0.004841279983520508
Average check time for size 10: 0.003919005393981934
Average get_ids time for size 10: 0.0005879640579223633
Average remove time for size 10: 0.0033682107925415037

Current size:  400
Memory size (mb):  0.8233108520507812
Average assign time for size 400: 0.1207657814025879
Average check time for size 400: 0.10877158641815185
Average get_ids time for size 400: 0.003831219673156738
Average remove time for size 400: 0.11320104598999023

Current size:  10000
Memory size (mb):  1.6768264770507812
Average assign time for size 10000: 2.849530482292175
Average check time for size 10000: 2.8491246700286865
Average get_ids time for size 10000: 0.08144667148590087
Average remove time for size 10000: 2.8955405950546265

Current size:  1000000
Memory size (mb):  85.08293151855469
Average assign time for size 1000000: 249.72130484580993
Average check time for size 1000000: 245.1982428073883
Average get_ids time for size 1000000: 5.724928784370422
Average remove time for size 1000000: 243.08973100185395
```
