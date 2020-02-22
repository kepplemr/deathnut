#!/bin/bash
PORT=82
id=$(curl -X POST "http://localhost:$PORT/recipe" -H "content-type: application/json" -d '{"title": "Michael Cold Brew", "ingredients": ["Water", "Coffee"]}' 2> /dev/null | jq -r '.id')
echo "Created recipe id: $id"
curl -X GET "http://localhost:$PORT/recipe/$id" -H "content-type: application/json"
echo
curl -X PATCH "http://localhost:$PORT/recipe/$id" -H "content-type: application/json" -d '{"ingredients": ["Water", "Coffee", "Spices"]}'
