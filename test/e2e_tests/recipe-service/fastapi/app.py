import uuid
import uvicorn
from fastapi import FastAPI

from deathnut.util.logger import get_deathnut_logger
from schema.app_schemas import Recipe, RecipeWithId, PartialRecipe
from generate_openapi.generate_template import generate_openapi_template

app = FastAPI()
logger = get_deathnut_logger(__name__)
recipe_db = dict()

@app.get("/recipe/{id}", response_model=RecipeWithId)
async def root(id: str):
    return recipe_db[id]

@app.post("/recipe", response_model=RecipeWithId)
async def create_recipe(recipe: Recipe):
    new_id = str(uuid.uuid4())
    new_recipe = {"id": new_id, "title": recipe.title, "ingredients": recipe.ingredients}
    recipe_db[new_id] = new_recipe
    #auth_o.assign_roles(new_id, ["own", "edit", "view"], **kwargs)
    return new_recipe

@app.patch("/recipe/{id}", response_model=RecipeWithId)
async def patch_recipe(id: str, recipe: PartialRecipe):
    for update in [x for x in recipe.dict().keys() if recipe.dict()[x]]:
        recipe_db[id][update] = getattr(recipe, update)
    return recipe_db[id]

@generate_openapi_template
def get_app():
    return app

if __name__ == "__main__":
    app = get_app()
    uvicorn.run("recipe-service.fastapi.app:app", debug=True, port=80, host="0.0.0.0")

#generate_template_from_app(app, template_output="deploy/openapi/generated/fastapi.yaml", force_run=True)

