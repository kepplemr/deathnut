import uuid

import redis
from deathnut.interface.flask.flask_restplus import FlaskRestplusAuthorization
from deathnut.util.logger import get_deathnut_logger
from flask import Flask, request
from flask_restplus import Api, Resource, fields
from generate_openapi.generate_template import generate_openapi_template

logger = get_deathnut_logger(__name__)
recipe_db = dict()

app = Flask(__name__)
api = Api()
ns = api.namespace("recipe", description="recipe operations")

recipe_schema = api.model("RecipeSchema", {
    "title": fields.String(description="Recipe title", required=True),
    "ingredients": fields.List(fields.String(), description="Recipe ingredients", required=True)})
recipe_with_id = api.inherit("RecipeWithId", recipe_schema, {
    "id": fields.String(description="Recipe id")})
recipe_partial = api.model("PartialRecipeSchema", {
    "title": fields.String(description="Recipe title"),
    "ingredients": fields.List(fields.String(), description="Recipe ingredients")})
recipe_list = api.model("RecipeList", fields.List(fields.Nested(recipe_with_id)))

redis_conn = redis.Redis(host="redis", port=6379)
auth_o = FlaskRestplusAuthorization(api, service="example", resource_type="recipe",
    redis_connection=redis_conn, enabled=True, strict=False)
auth_endpoint = auth_o.create_auth_endpoint('/auth-recipe')
auth_endpoint.allow_grant(requires_role='own', grants_roles=['view', 'edit'])
auth_endpoint.allow_grant(requires_role='edit', grants_roles=['view'])

@ns.route("")
class RecipeCreate(Resource):
    @ns.expect(recipe_schema, validate=True)
    @ns.marshal_with(recipe_with_id)
    @auth_o.authentication_required()
    def post(self, **kwargs):
        recipe = request.json
        new_id = str(uuid.uuid4())
        new_recipe = {
            "id": new_id,
            "title": recipe["title"],
            "ingredients": recipe["ingredients"],
        }
        recipe_db[new_id] = new_recipe
        auth_o.assign_roles(new_id, ["own", "edit", "view"], **kwargs)
        return new_recipe, 200
    
    @api.doc(params={'limit': {'description': 'optional limit', 'in': 'query', 'type': 'integer', 'required': False}})
    @ns.marshal_with(recipe_list)
    @auth_o.fetch_accessible_for_user('view')
    def get(self, **kwargs):
        limit = request.args.get('limit', 10)
        return [recipe_db[x] for x in kwargs.get('deathnut_ids')][0:limit]


@ns.route("/<string:id>")
class Recipe(Resource):
    @ns.marshal_with(recipe_with_id)
    @auth_o.requires_role("view")
    def get(self, id, **kwargs):
        return recipe_db[id], 200

    @ns.expect(recipe_partial)
    @ns.marshal_with(recipe_with_id)
    @auth_o.requires_role("edit")
    def patch(self, id, **kwargs):
        partial_recipe = request.json
        for key in partial_recipe:
            recipe_db[id][key] = partial_recipe[key]
        return recipe_db[id], 200

@generate_openapi_template
def create_app():
    api.init_app(app)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=80, host="0.0.0.0")
