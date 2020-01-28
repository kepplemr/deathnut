from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
import falcon
from falcon_apispec import FalconPlugin
from marshmallow import Schema, fields
from wsgiref import simple_server
import uuid
import yaml

#from deathnut.util.logger import get_deathnut_logger

#logger = get_deathnut_logger(__name__)
recipe_db = dict()

class Recipe(Schema):
    title = fields.String(description='Recipe title', required=True)
    ingredients = fields.List(fields.String(), description='Recipe ingredients', required=True)

class RecipeWithId(Recipe):
    id = fields.String(description='Recipe id')

class RecipePartial(Schema):
    title = fields.String(description='Recipe title')
    ingredients = fields.List(fields.String(), description='Recipe ingredients')

app = falcon.API()

class RecipeBase:
    #TODO list

    #@auth_o.authentication_required()
    def on_post(self, req, resp):
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
        new_recipe = {"id": new_id, "title": recipe['title'], "ingredients": recipe['ingredients']}
        recipe_db[new_id] = new_recipe
        #auth_o.assign_roles(new_id, ['own','edit','view'], **kwargs)
        resp.media = new_recipe
        resp.status = falcon.HTTP_200

class RecipeSpecific:
    """Schema checking done by ESP, no need to redo. Marshmallow used only generate specs"""

    #@auth_o.requires_role('edit')
    def on_patch(self, req, resp, id):
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
        partial_recipe = req.media
        for key in partial_recipe:
            recipe_db[id][key] = partial_recipe[key]
        resp.media = recipe_db[id]
        resp.status = falcon.HTTP_200

    #@auth_o.requires_role('view')
    def on_get(self,req, resp, id):
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

spec = APISpec(title='Example recipe service', version='1.0.0', openapi_version='2.0',
    plugins=[FalconPlugin(app),MarshmallowPlugin()])

spec.components.schema('Recipe', schema=Recipe)
spec.components.schema('RecipeWithId', schema=RecipeWithId)
spec.components.schema('RecipePartial', schema=RecipePartial)
spec.path(resource=recipe_resource)
spec.path(resource=recipe_create_and_list)
print('Spec -> \n' + str(spec.to_yaml()))

def output_conf(filename, output_dict, path_prefix):
    yaml.emitter.Emitter.process_tag = lambda *args: None
    with open('/'.join([path_prefix, filename]), 'w') as outfile:
        yaml.dump(output_dict, outfile, default_style=None, default_flow_style=False)

output_conf('test.yaml', spec.to_dict(), './deploy')

if __name__ == '__main__':
    httpd = simple_server.make_server('0.0.0.0', 80, app)
    httpd.serve_forever()