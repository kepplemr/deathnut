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

Fine. Scaling up memory is easy enough, what really matters is which one is faster. 
