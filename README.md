# deathnut overview
Deathnut is an extremely simple, easy-to-use, and blazing fast authorization library. It supports
several pyton REST tools (Flask, Falcon, Fastapi) and uses redis as the data store. 

Services can add authorization support by defining a list of privileges -- e.g., ['view', 'edit', 
'own'] and denoting endpoints that assign or require said privileges. 

Decorators are provided so that your service doesn't have to handle authorization logic itself - and
privileges required are easily understood by glancing at the endpoint signature. 

# contents
[TOC]
- [Deathnut overview](#deathnut-overview)
- [Redis overview](docs/redis.md)
- [Pre-commit setup](#pre-commit-setup)

# pre-commit setup
1) brew install pre-commit
