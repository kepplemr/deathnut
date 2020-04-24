import uuid

import redis
from deathnut.interface.flask.flask_apispec import FlaskAPISpecAuthorization
from deathnut.util.logger import get_deathnut_logger
from flask import Flask
from flask_apispec import doc, marshal_with, use_kwargs
from flask_apispec.extension import FlaskApiSpec
from generate_openapi.generate_template import generate_openapi_template
from schema.app_schemas import RecipeSchema

logger = get_deathnut_logger(__name__)
recipe_db = dict()

app = Flask(__name__)
redis_conn = redis.Redis(host="redis", port=6379)
auth_o = FlaskAPISpecAuthorization(app, service="example", resource_type="recipe",
    redis_connection=redis_conn, enabled=True, strict=False)
auth_endpoint = auth_o.create_auth_endpoint('/auth-recipe')
auth_endpoint.allow_grant(requires_role='own', grants_roles=['view', 'edit', 'own'])
auth_endpoint.allow_grant(requires_role='edit', grants_roles=['view'])

@app.route("/recipe/<string:id>", methods=("GET",))
@marshal_with(RecipeSchema)
@auth_o.requires_role("view")
def get(id, **kwargs):
    return recipe_db[id], 200

@app.route("/recipe", methods=("POST",))
@use_kwargs(RecipeSchema, required=True, locations=("json",))
@marshal_with(RecipeSchema)
@auth_o.authentication_required()
def post(title, ingredients, **kwargs):
    new_id = str(uuid.uuid4())
    new_recipe = {"id": new_id, "title": title, "ingredients": ingredients}
    recipe_db[new_id] = new_recipe
    auth_o.assign_roles(new_id, ["own", "edit", "view"], **kwargs)
    return new_recipe, 200

@app.route("/recipe", methods=("GET",))
@doc(params={'limit': {'description': 'optional limit', 'in': 'query', 'type': 'integer', 'required': False}})
@marshal_with(RecipeSchema(many=True))
@auth_o.fetch_accessible_for_user('view')
def get_recipe_list(limit=10, **kwargs):
    return [recipe_db[x] for x in kwargs.get('deathnut_ids')][0:limit], 200

@app.route("/recipe/<string:id>", methods=("PATCH",))
@use_kwargs(RecipeSchema(partial=True), required=True, locations=("json",))
@marshal_with(RecipeSchema)
@auth_o.requires_role("edit")
def patch(id, **kwargs):
    for kw in kwargs:
        recipe_db[id][kw] = kwargs[kw]
    return recipe_db[id], 200

@generate_openapi_template
def create_app():
    #app.config['APISPEC_SWAGGER_URL'] = '/wtf.json'
    FlaskApiSpec(app).register_existing_resources()
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=80, host="0.0.0.0")
