import redis

from flask import Flask, jsonify, request
from flask_apispec import marshal_with, use_kwargs
from flask_apispec.extension import FlaskApiSpec

from deathnut.interface.flask_interface import RestAuthorization
from deathnut.util.logger import get_deathnut_logger
from generate_template import generate_template_from_app
from schema.app_schemas import RecipeSchema, ShareSchema

logger = get_deathnut_logger(__name__)
redis_conn = redis.Redis(host='redis', port=6379)
auth_o = RestAuthorization(service='example', resource_type='recipe', redis_connection=redis_conn, 
    enabled=True, strict=False)

recipe_db = [
    {"id": 0, "title": "Michael's famous peanut butter and jelly", "ingredients": ["pb", "j"]},
    {"id": 1, "title": "Grilled fish", "ingredients": ["fish"]}
]

app = Flask(__name__)

@app.route('/recipe/<int:id>', methods=('GET',))
@marshal_with(RecipeSchema)
@auth_o.requires_role('view')
def get(id, **kwargs):
    return recipe_db[id], 200

@app.route('/recipe', methods=('POST',))
@use_kwargs(RecipeSchema, locations=('json',))
@marshal_with(RecipeSchema)
@auth_o.authentication_required()
def post(title, ingredients, **kwargs):
    if 'id' in kwargs:
        new_id = int(kwargs['id'])
    else:
        new_id = recipe_db[-1]["id"] + 1 if len(recipe_db) > 0 else 0
    new_recipe = {"id": new_id, "title": title, "ingredients": ingredients}
    recipe_db.append(new_recipe)
    auth_o.assign_roles(new_id, ['own','edit','view'], **kwargs)
    return new_recipe, 200

@app.route('/recipe/<int:id>', methods=('PATCH',))
@use_kwargs(RecipeSchema(partial=True), locations=('json',))
@marshal_with(RecipeSchema)
@auth_o.requires_role('edit')
def patch(id, **kwargs):
    for kw in kwargs:
        recipe_db[id][kw] = kwargs[kw]
    return recipe_db[id], 200

@app.route('/share', methods=('POST',))
@use_kwargs(ShareSchema)
@marshal_with(ShareSchema)
@auth_o.requires_role('own')
def share_post(id, user, **kwargs):
    auth_o.assign_roles(id, ['view'], deathnut_user=user)
    return {"id": id, "user": user}, 200

@app.errorhandler(422)
@app.errorhandler(400)
def handle_error(err):
    headers = err.data.get("headers", None)
    messages = err.data.get("messages", ["Invalid request."])
    if headers:
        return jsonify({"errors": messages}), err.code, headers
    else:
        return jsonify({"errors": messages}), err.code

def create_app():
    FlaskApiSpec(app).register_existing_resources()
    #generate_template_from_app(app, force_run=True)
    app.run(debug=True, port=80, host='0.0.0.0')

if __name__ == "__main__":
    create_app()