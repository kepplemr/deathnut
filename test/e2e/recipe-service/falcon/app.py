import uuid
from wsgiref import simple_server

import falcon
import redis
import yaml
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
    ingredients = fields.List(
        fields.String(), description="Recipe ingredients", required=True
    )


class RecipeWithId(Recipe):
    id = fields.String(description="Recipe id")


class RecipePartial(Schema):
    title = fields.String(description="Recipe title")
    ingredients = fields.List(fields.String(), description="Recipe ingredients")


app = falcon.API()
redis_conn = redis.Redis(host="redis", port=6379)
auth_o = FalconAuthorization(
    app,
    service="example",
    resource_type="recipe",
    redis_connection=redis_conn,
    enabled=True,
    strict=False,
)
auth_o.create_auth_endpoint("/auth-recipe", requires_role="own", grants_role="view")


class RecipeBase:
    # TODO list
    @auth_o.authentication_required()
    # @jsonschema.validate(req_schema=Recipe, resp_schema=RecipeWithId)
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
        print("Req media -> " + str(req.media))
        recipe = req.media
        new_id = str(uuid.uuid4())
        new_recipe = {
            "id": new_id,
            "title": recipe["title"],
            "ingredients": recipe["ingredients"],
        }
        recipe_db[new_id] = new_recipe
        # auth_o.assign_roles(new_id, ['own','edit','view'], **kwargs)
        resp.media = new_recipe
        resp.status = falcon.HTTP_200


class RecipeSpecific:
    """Schema checking done by ESP, no need to redo. Marshmallow used only generate specs"""

    @auth_o.requires_role("edit")
    def on_patch(self, req, resp, id, *args, **kwargs):
        """
        Recipe PATCH endpoint
        ---
        operationId: patch_recipe
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
        # logger.info('Req media -> ' + str(req.media))
        # print('Recipe schema dict -> ' + str(dict(RecipeWithId)))
        print("Test -> " + str(locals()))
        print("Args -> " + str(args))
        print("Kwargs -> " + str(kwargs))
        print("Req media -> " + str(req.media))
        print("Req dir -> " + str(dir(req)))
        print("Req params -> " + str(req.params))
        print("Req context -> " + str(req.context))
        print("Req path -> " + str(req.path))
        print("Req dict -> " + str(req.__dict__))
        print("Req query string -> " + str(req.query_string))
        print("Req uri -> " + str(req.uri))
        print("Req rel uri -> " + str(req.relative_uri))
        partial_recipe = req.media
        for key in partial_recipe:
            recipe_db[id][key] = partial_recipe[key]
        resp.media = recipe_db[id]
        resp.status = falcon.HTTP_200

    # @auth_o.requires_role('view')
    def on_get(self, req, resp, id, **kwargs):
        """
        Recipe POST endpoint
        ---
        operationId: get_recipe
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

spec = APISpec(
    title="Example recipe service",
    version="1.0.0",
    openapi_version="2.0",
    plugins=[FalconPlugin(app), MarshmallowPlugin()],
)

spec.components.schema("Recipe", schema=Recipe)
spec.components.schema("RecipeWithId", schema=RecipeWithId)
spec.components.schema("RecipePartial", schema=RecipePartial)
spec.path(resource=recipe_resource)
spec.path(resource=recipe_create_and_list)
print("Spec -> \n" + str(spec.to_yaml()))


def output_conf(filename, output_dict, path_prefix):
    yaml.emitter.Emitter.process_tag = lambda *args: None
    with open("/".join([path_prefix, filename]), "w") as outfile:
        yaml.dump(output_dict, outfile, default_style=None, default_flow_style=False)


output_conf("test.yaml", spec.to_dict(), "./deploy")

if __name__ == "__main__":
    httpd = simple_server.make_server("0.0.0.0", 80, app)
    httpd.serve_forever()
