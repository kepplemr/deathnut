import argparse

from flask import Blueprint, Flask
from flask_apispec import MethodResource, doc, marshal_with, use_kwargs
from flask_apispec.extension import FlaskApiSpec
from marshmallow import Schema, fields

class RecipeSchema(Schema):
    id = fields.Integer(description='Recipe id', required=True)
    title = fields.String(description='Recipe title', required=True)


recipe_db = [
    {"id": 0, "title": "Michael's famous peanut butter and jelly"},
    {"id": 1, "title": "Grilled fish"}
]

app = Flask(__name__)

@app.route('/recipe', methods=('GET',))
@marshal_with(RecipeSchema(many=True))
def get():
    return recipe_db

@app.route('/recipe', methods=('POST',))
@use_kwargs(RecipeSchema, locations=('json',))
@marshal_with(RecipeSchema)
def post(id, title):
    new_id = recipe_db[-1]["id"] + 1 if len(recipe_db) > 0 else 0
    new_recipe = {"id": new_id, "title": title}
    recipe_db.append(new_recipe)
    return new_recipe

def create_app():
    FlaskApiSpec(app).register_existing_resources()
    app.run(debug=True)

if __name__ == "__main__":
    create_app()