#!/bin/bash

curl -X POST "http://localhost:80/recipe" -H "accept: application/json"  --data-binary \
  '{"title": "Michael Cold Brew", "ingredients": ["Water", "Coffee"]}'
curl -X GET "http://localhost:80/recipe/2" -H "accept: application/json"
curl -X PATCH "http://localhost:80/recipe/2" -H "accept: application/json" --data-binary \
  '{"ingredients": ["Water", "Coffee", "Spices"]}'
curl -X GET "http://localhost:80/recipe/2" -H "accept: application/json"
