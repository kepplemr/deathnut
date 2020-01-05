
from marshmallow import Schema, fields

class RecipeSchema(Schema):
    class Meta:
        strict = True
    id = fields.Integer(description='Recipe id', required=False)
    title = fields.String(description='Recipe title', required=True)
    ingredients = fields.List(fields.String(), description='Recipe ingredients', required=True)

class ShareSchema(Schema):
    class Meta:
        strict = True
    id = fields.Integer(description='Recipe id', required=True)
    user = fields.String(description='Recipe title', required=True)