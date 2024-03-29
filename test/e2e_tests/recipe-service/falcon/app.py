import uuid
from wsgiref import simple_server

import falcon
import redis
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from deathnut.interface.falcon.falcon_auth import FalconAuthorization
from deathnut.util.logger import get_deathnut_logger
from falcon_apispec import FalconPlugin
from marshmallow import Schema, fields

logger = get_deathnut_logger(__name__)
recipe_db = dict()

class Recipe(Schema):
    title = fields.String(description="Recipe title", required=True)
    ingredients = fields.List(fields.String(), description="Recipe ingredients", required=True)
class RecipeWithId(Recipe):
    id = fields.String(description="Recipe id")
class RecipePartial(Schema):
    title = fields.String(description="Recipe title")
    ingredients = fields.List(fields.String(), description="Recipe ingredients")
class RecipeList(Schema):
    fields.List(fields.Nested(RecipeWithId), description="List of recipes")

app = falcon.API()
redis_conn = redis.Redis(host="redis", port=6379)
spec = APISpec(title="Example recipe service", version="1.0.0", openapi_version="2.0",
  plugins=[FalconPlugin(app), MarshmallowPlugin()])
auth_o = FalconAuthorization(app, spec, service="example", resource_type="recipe",
    redis_connection=redis_conn, enabled=True, strict=False)
auth_endpoint = auth_o.create_auth_endpoint("/auth-recipe")
auth_endpoint.allow_grant(requires_role='own', grants_roles=['view', 'edit', 'own'])
auth_endpoint.allow_grant(requires_role='edit', grants_roles=['view'])

class RecipeBase:
    @auth_o.authentication_required(assign=['own','edit','view'])
    def on_post(self, req, resp, **kwargs):
        """
        Recipe POST endpoint
        ---
        operationId: post_recipe
        parameters:
        - in: body
          required: true
          name: payload
          schema: Recipe
        responses:
          200:
            description: the created recipe
            schema: RecipeWithId
        """
        recipe = req.media
        new_id = str(uuid.uuid4())
        new_recipe = {
            "id": new_id,
            "title": recipe["title"],
            "ingredients": recipe["ingredients"],
        }
        recipe_db[new_id] = new_recipe
        resp.media = new_recipe
        resp.status = falcon.HTTP_200

    @auth_o.fetch_accessible_for_user('view')
    def on_get(self, req, resp, limit=10, **kwargs):
        """
        Recipe GET endpoint
        ---
        operationId: get_recipe
        parameters:
        - in: path
          name: limit
          type: integer
          required: False
        responses:
          200:
            description: the created recipe
            schema: RecipeList
        """
        resp.media = [recipe_db[x] for x in kwargs.get('deathnut_ids')][0:limit]
        resp.status = falcon.HTTP_200


class RecipeSpecific:
    """Schema checking done by ESP, no need to redo. Marshmallow used only generate specs"""

    @auth_o.requires_role("edit")
    def on_patch(self, req, resp, id, *args, **kwargs):
        """
        Recipe PATCH BY ID endpoint
        ---
        operationId: patch_recipe_by_id
        parameters:
        - in: path
          name: id
          type: integer
        - in: body
          required: true
          schema: RecipePartial
        responses:
          200:
            description: the updated recipe
            schema: RecipeWithId
        """
        partial_recipe = req.media
        for key in partial_recipe:
            recipe_db[id][key] = partial_recipe[key]
        resp.media = recipe_db[id]
        resp.status = falcon.HTTP_200

    @auth_o.requires_role('view')
    def on_get(self, req, resp, id, **kwargs):
        """
        Recipe GET BY ID endpoint
        ---
        operationId: get_recipe_by_id
        parameters:
        - in: path
          name: id
          type: integer
        responses:
          200:
            description: the recipe associated with id
            schema: RecipeWithId
        """
        resp.media = recipe_db[id]
        resp.status = falcon.HTTP_200

recipe_create_and_list = RecipeBase()
recipe_resource = RecipeSpecific()
app.add_route("/recipe", recipe_create_and_list)
app.add_route("/recipe/{id}", recipe_resource)
spec.components.schema("Recipe", schema=Recipe)
spec.components.schema("RecipeWithId", schema=RecipeWithId)
spec.components.schema("RecipePartial", schema=RecipePartial)
spec.path(resource=recipe_resource)
spec.path(resource=recipe_create_and_list)
#spec.to_yaml()

if __name__ == "__main__":
    httpd = simple_server.make_server("0.0.0.0", 80, app)
    httpd.serve_forever()
