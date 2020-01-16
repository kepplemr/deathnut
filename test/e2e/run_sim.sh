#!/bin/bash

docker build --no-cache -t recipe-service -f Dockerfile .

docker run -dp 6379:6379 --name redis redis

docker run -dp 80:80 -v $(pwd)/keys:/keys -v $(pwd)/../../deathnut:/deathnut \
  -v $(pwd)/deploy:/recipe-service/deploy --link redis:redis --name recipe-service recipe-service

docker run --detach -v $(pwd)/keys:/keys -p 8080:8080 \
  --link recipe-service:recipe-service --name esp gcr.io/endpoints-release/endpoints-runtime:1 \
  --service=recipe-service.endpoints.wellio-dev-michael.cloud.goog --rollout_strategy=managed \
  --backend=recipe-service:80 --http_port 8080 --service_account_key=/keys/jwt-test.json

sleep 20

docker exec recipe-service python /recipe-service/generate_openapi/generate_configs.py \
  -b /recipe-service/deploy/openapi/openapi.generated.yaml \
  -o /recipe-service/deploy/openapi/openapi.overrides.yaml -p /recipe-service/deploy/openapi

python esp_test.py
