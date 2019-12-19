import argparse
import logging
import sys

from flask import Blueprint, Flask
from flask_apispec import MethodResource, doc, marshal_with, use_kwargs
from flask_apispec.extension import FlaskApiSpec
from marshmallow import Schema, fields

from generate_template import generate_template_from_app

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)

class RecipeSchema(Schema):
    class Meta:
        strict = True
    id = fields.Integer(description='Recipe id', required=False)
    title = fields.String(description='Recipe title', required=True)
    ingredients = fields.List(fields.String(), description='Recipe ingredients', required=True)


recipe_db = [
    {"id": 0, "title": "Michael's famous peanut butter and jelly", "ingredients": ["pb", "j"]},
    {"id": 1, "title": "Grilled fish", "ingredients": ["fish"]}
]

app = Flask(__name__)

@app.route('/recipe/<int:id>', methods=('GET',))
@marshal_with(RecipeSchema)
def get(id):
    return recipe_db[id], 200

@app.route('/recipe', methods=('POST',))
@use_kwargs(RecipeSchema, locations=('json',))
@marshal_with(RecipeSchema)
def post(title, ingredients, **kwargs):
    if 'id' in kwargs:
        new_id = int(kwargs['id'])
    else:
        new_id = recipe_db[-1]["id"] + 1 if len(recipe_db) > 0 else 0
    new_recipe = {"id": new_id, "title": title, "ingredients": ingredients}
    recipe_db.append(new_recipe)
    return new_recipe, 200

@app.route('/recipe/<int:id>', methods=('PATCH',))
@use_kwargs(RecipeSchema(partial=True), locations=('json',))
@marshal_with(RecipeSchema)
def patch(id, **kwargs):
    for kw in kwargs:
        recipe_db[id][kw] = kwargs[kw]
    return recipe_db[id], 200

def create_app():
    FlaskApiSpec(app).register_existing_resources()
    #generate_template_from_app(app, force_run=True)
    app.run(debug=True, port=80, host='0.0.0.0')

if __name__ == "__main__":
    create_app()