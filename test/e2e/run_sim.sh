#!/bin/bash

docker-compose build --no-cache 
docker-compose up -d

sleep 10

# TODO wait until service is up

# docker exec recipe-service-apispec python /recipe-service/generate_openapi/generate_configs.py \
#   -b /recipe-service/deploy/openapi/openapi.generated.yaml \
#   -o /recipe-service/deploy/openapi/openapi.overrides.yaml -p /recipe-service/deploy/openapi

docker exec recipe-service-restplus python /recipe-service/generate_openapi/generate_configs.py \
  -b /recipe-service/deploy/openapi/openapi.generated.yaml \
  -o /recipe-service/deploy/openapi/openapi.overrides-restplus.yaml -p /recipe-service/deploy/openapi

# endpoints != esp
# gcloud endpoints services deploy openapi.recipe-service-deploy.yaml 
# gcloud endpoints services describe recipe-service.endpoints.wellio-dev-michael.cloud.goog
# gcloud endpoints operations describe operations/rollouts.recipe-service.endpoints.wellio-dev-michael.cloud.goog:9936baa8-3251-4263-8533-d43e7fa17d3d
python esp_test.py
