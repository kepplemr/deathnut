# redis overview

redis is used as the backend data store for our user -> resource_ids. redis was chosen because it is
extremely fast, we're already using it, and GCP provides a managed, HA instance (Memorystore).

# data model

When designing deathnut, two approaches for redis id storage were considered: using redis sets and
using redis hashes.

## sets

redis sets are unordered collections of strings. The core deathnut operations (assign a role, check
a role, revoke a role) could be performed as:

```bash
127.0.0.1:6379> SADD dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 1
127.0.0.1:6379> SISMEMBER dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 1
127.0.0.1:6379> SREM dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 1
127.0.0.1:6379> SISMEMBER dimsum_edited-recipes:jennifer:view 85a9082e-e5c8-454c-b020-ac168ce91669
(integer) 0
```


## hashes

redis hashes are hashes that map string names to string values.
