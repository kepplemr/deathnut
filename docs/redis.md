# redis overview

redis is used as the backend data store for our user -> resource_ids. redis was chosen because it is
extremely fast, we're already using it, and GCP provides a managed, HA instance (Memorystore). 

# data model

When designing deathnut, two approaches for redis id storage were considered: using redis sets and
using redis hashes. 

## sets

blah blah

## hashes
...