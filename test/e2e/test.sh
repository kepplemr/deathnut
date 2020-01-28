#!/bin/bash
curl -X POST "http://localhost:80/recipe" -H "content-type: application/json" -d '{"title": "Michael Cold Brew", "ingredients": ["Water", "Coffee"]}'


curl -X POST "http://localhost:80/recipe" -H "accept: application/json"  --data-binary \
  '{"title": "Michael Cold Brew", "ingredients": ["Water", "Coffee"]}'
curl -X GET "http://localhost:80/recipe/2" -H "accept: application/json"
curl -X PATCH "http://localhost:80/recipe/2" -H "accept: application/json" --data-binary \
  '{"ingredients": ["Water", "Coffee", "Spices"]}'
curl -X GET "http://localhost:8080/recipe/2" -H {"accept: application/json"}


# michael (gets past esp, fails at deathnut)
curl -X GET "http://localhost:8080/recipe/2" -H "accept: application/json" -H "Authorization: Bearer eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCIsICJraWQiOiAiYjkwZmY0Y2FjMWI2ODI4Nzc3ZDQ4NzRjZGVhYWUwMTYxMGFiMDk2NyJ9.eyJhdWQiOiAicmVjaXBlLXNlcnZpY2UiLCAiaXNzIjogImp3dC10ZXN0QHdlbGxpby1kZXYtbWljaGFlbC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsICJleHAiOiAxNTc4NTM5NjE3LCAiaWF0IjogMTU3ODUzNjAxNywgImVtYWlsIjogIm1pY2hhZWwiLCAic3ViIjogImp3dC10ZXN0QHdlbGxpby1kZXYtbWljaGFlbC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSJ9.Tm3SSBR5Gk82DFpYFfRvlTbHUTLPoVOWTP9LPaOY9qfCh_zKyYTGI0df8DezRXlmyXRNd7eDuihWmBsZ9GTXw79ZQoJXB6D1SBiNLBS-ruwJZlDoynY6L6bvi0gq2O31JzsoUkbBHcfxxzjSzMXhvcJAIuWexVYM4bo8Di1XY6YCAHfBQ5lZetEbGXWbiYrBhc8fmgHtuD7EiliKFQ8KsYwe7f4fYDZCdk2vc45V5ORO0DNUUyAlKzTBAP4zROs5GjxbX1OmXktcQjbWSvPobTIvh2c_beLByHFBwn6FA7g0icb90dZwlvs9h2CigX0LqncmeCBprOcxGMiRSPlh6A"

# jennifer (fails at deathnut)
curl -X GET "http://localhost:8080/recipe/2" -H "accept: application/json" -H "Authorization: Bearer eyJhbGciOiAiUlMyNTYiLCAidHlwIjogIkpXVCIsICJraWQiOiAiYjkwZmY0Y2FjMWI2ODI4Nzc3ZDQ4NzRjZGVhYWUwMTYxMGFiMDk2NyJ9.eyJhdWQiOiAicmVjaXBlLXNlcnZpY2UiLCAiaXNzIjogImp3dC10ZXN0QHdlbGxpby1kZXYtbWljaGFlbC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsICJleHAiOiAxNTc4NTQxMTY2LCAiaWF0IjogMTU3ODUzNzU2NiwgImVtYWlsIjogImplbm5pZmVyIiwgInN1YiI6ICJqd3QtdGVzdEB3ZWxsaW8tZGV2LW1pY2hhZWwuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20ifQ.oAqDO5M4dlQhdR5tZvcqj-5he1iZqULg3a0wKE07ti0rT02jLL4NTRgqmGMEKCWV1QwkXziiNsEaLvzFh9GmWRilY7duXAPvVxGRb1jmTEMV4B7LNQwWy6MuRkQL3xfPVYpPmAuLMB_CcTCNesqdv2V8BSiZaGjokH8XCMulVcYZdMmFNQPP5TB2JHxG6bWyKKrVpaHL0z0A762g9GDNKYdDW1YfD5gdxr8MAjoG90Nx3Zr-rkPcJKvlNLFgFahTZlhOhj6HJV9dD6U6EZo1H2Kf0JGS8xfYhWZSlwSiA2-0YQJyf2c8sBVDG0fqDOV5MAupMFUPcL8Z7ZtHLZGfIg"
