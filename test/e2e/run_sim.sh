#!/bin/bash
set -e

docker-compose build --no-cache 
docker-compose up -d

sleep 10

docker exec recipe-service-apispec python /recipe-service/generate_openapi/generate_configs.py \
  -b /recipe-service/deploy/openapi/openapi.generated.yaml \
  -o /recipe-service/deploy/openapi/openapi.overrides-apispec.yaml -p /recipe-service/deploy/openapi
gcloud endpoints services deploy deploy/openapi/openapi.recipe-service-deploy-apispec.yaml

docker exec recipe-service-restplus python /recipe-service/generate_openapi/generate_configs.py \
  -b /recipe-service/deploy/openapi/openapi.generated.yaml \
  -o /recipe-service/deploy/openapi/openapi.overrides-restplus.yaml -p /recipe-service/deploy/openapi
gcloud endpoints services deploy deploy/openapi/openapi.recipe-service-deploy-restplus.yaml

python esp_test.py
