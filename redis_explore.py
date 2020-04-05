import docker
import itertools
import redis
import time
import uuid

USER = "michael"
SERVICE_NAME = "dimsum_edited-recipes"
#NUM_ENTRIES = 1_000_000
NUM_ENTRIES=300
SAMPLE_EVERY = 100

docker_client = docker.from_env()
# stop and remove all containers before test
for container in docker_client.containers.list(all=True):
    container.remove(force=True)

# https://www.peterbe.com/plog/understanding-redis-hash-max-ziplist-entries
docker_client.containers.run("redis:3.2.5-alpine", name="redis", ports={'6379/tcp': 6379}, detach=True)
# CONFIG GET *

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

time.sleep(10)
redis_client = redis.Redis(host='localhost')

sample_ids = []
t0 = time.time()
for i in range(0, NUM_ENTRIES):
    resource_id = str(uuid.uuid4())
    redis_client.hset("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), resource_id, 1)
    redis_client.hset("{}:{}:{}".format(SERVICE_NAME, USER, 'own'), resource_id, 1)
    if i and not i % (NUM_ENTRIES // SAMPLE_EVERY):
        sample_ids.append(resource_id)
t1 = time.time()
for r_id in sample_ids:
    res = redis_client.hget("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), r_id)
    assert bool(res) == True
t2 = time.time()
view_resources = list(itertools.chain.from_iterable(get_resources(redis_client, USER, 'view')))
print('View resources -> ' + str(view_resources))
print('View resource length -> ' + str(len(view_resources)))
t3 = time.time()
# scan 0 match dimsum_edited-recipes:michael:*

# Hashname is dimsum_edited-recipe_michael_view
# Property/field is recipe_id
# Value is 'T' if set
print('Testing hash implementation:')
size = int(redis_client.info()['used_memory']) / 1024 / 1024
print('Creation took: ', t1-t0, " seconds")
print('Getting took: ', t2-t1, ' seconds')
print('Get resources for role took: ', t3-t2, ' seconds')
print('Memory size: ', size)
print('DB size: ', redis_client.dbsize())

#redis_client.flushall()

import sys
sys.exit(0)

# For sets:
# Set name is dimsum_edited-recipe_michael_view
# SISMEMBER is 1 if member
# get_resources() works. 
t0 = time.time()
for i in range(0, NUM_ENTRIES):
    resource_id = str(uuid.uuid4())
    redis_client.sadd("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), resource_id)
    redis_client.sadd("{}:{}:{}".format(SERVICE_NAME, USER, 'own'), resource_id)
    if i and not i % (NUM_ENTRIES // SAMPLE_EVERY):
        sample_ids.append(resource_id)
t1 = time.time()
for r_id in sample_ids:
    res = redis_client.sismember("{}:{}:{}".format(SERVICE_NAME, USER, 'view'), resource_id)
    assert bool(res) == True
t2 = time.time()

print('Testing set implementation:')
size = int(redis_client.info()['used_memory']) / 1024 / 1024
print('Creation took: ', t1-t0, " seconds")
print('Getting took: ', t2-t1, ' seconds')
print('Memory size: ', size)
print('DB size: ', redis_client.dbsize())

# 1_000_000, 500
# Operation took:  263.28804636001587  seconds
# Memory size:  107.96537780761719
# DB size:  1
# Operation took:  262.70152616500854  seconds
# Memory size:  85.0772933959961
# DB size:  1
# $ python redis_explore.py 
# Operation took:  0.2247629165649414  seconds
# Memory size:  0.8065948486328125
# DB size:  1
# Operation took:  0.22451448440551758  seconds
# Memory size:  0.8253021240234375
# DB size:  1
