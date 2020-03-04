#!/bin/bash
set -e

#docker-compose build --no-cache
# docker-compose up -d recipe-service-fastapi
# docker-compose up -d recipe-service-apispec
# docker-compose up -d recipe-service-restplus

nosetests --nocapture --no-byte-compile
#python test_e2e.py