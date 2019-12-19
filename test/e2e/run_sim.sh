#!/bin/bash

docker build --no-cache -t recipe_service -f Dockerfile .

docker run -dp 80:80 recipe_service

docker run --detach -v $(pwd)/keys:/keys gcr.io/endpoints-release/endpoints-runtime:1 \
  --service=recipe_service --rollout_strategy=managed --backend=127.0.0.1:80 \
  --service_account_key=/keys/gcloud-test-key.json
