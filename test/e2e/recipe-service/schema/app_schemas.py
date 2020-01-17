from marshmallow import Schema, fields

class RecipeSchema(Schema):
    class Meta:
        strict = True
    id = fields.String(description='Recipe id', required=False)
    title = fields.String(description='Recipe title', required=True)
    ingredients = fields.List(fields.String(), description='Recipe ingredients', required=True)