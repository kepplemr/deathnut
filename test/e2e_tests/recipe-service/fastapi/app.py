import uuid
from typing import List

import redis
import uvicorn
from deathnut.interface.fastapi.fastapi_auth import FastapiAuthorization
from deathnut.util.logger import get_deathnut_logger
from fastapi import FastAPI
from generate_openapi.generate_template import generate_openapi_template
from schema.app_schemas import PartialRecipe, Recipe, RecipeWithId
from starlette.requests import Request

app = FastAPI()
redis_conn = redis.Redis(host="redis", port=6379)
auth_o = FastapiAuthorization(app, service="example", resource_type="recipe",
    redis_connection=redis_conn, enabled=True, strict=False)
auth_endpoint = auth_o.create_auth_endpoint('/auth-recipe')
auth_endpoint.allow_grant(requires_role='own', grants_roles=['view', 'edit', 'own'])
auth_endpoint.allow_grant(requires_role='edit', grants_roles=['view'])
logger = get_deathnut_logger(__name__)
recipe_db = dict()

@app.get("/recipe/{id}", response_model=RecipeWithId)
@auth_o.requires_role('view')
async def get_recipe(id: str, request: Request):
    return recipe_db[id]

@app.post("/recipe", response_model=RecipeWithId)
@auth_o.authentication_required(assign=["own", "edit", "view"])
async def create_recipe(recipe: Recipe, request: Request):
    new_id = str(uuid.uuid4())
    new_recipe = {"id": new_id, "title": recipe.title, "ingredients": recipe.ingredients}
    recipe_db[new_id] = new_recipe
    return new_recipe

@app.get("/recipe", response_model=List[RecipeWithId])
@auth_o.fetch_accessible_for_user('view')
async def get_recipes(request: Request, limit: int = 10):
    return [recipe_db[x] for x in request.deathnut_ids][0:limit]

@app.patch("/recipe/{id}", response_model=RecipeWithId)
@auth_o.requires_role('edit')
async def patch_recipe(id: str, recipe: PartialRecipe, request: Request):
    for update in [x for x in recipe.dict().keys() if recipe.dict()[x]]:
        recipe_db[id][update] = getattr(recipe, update)
    return recipe_db[id]

@generate_openapi_template
def get_app():
    return app

if __name__ == "__main__":
    app = get_app()
    uvicorn.run("recipe-service.fastapi.app:app", debug=True, port=80, host="0.0.0.0")
