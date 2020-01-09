from marshmallow import Schema, fields

class RecipeSchema(Schema):
    class Meta:
        strict = True
    id = fields.Integer(description='Recipe id', required=False)
    title = fields.String(description='Recipe title', required=True)
    ingredients = fields.List(fields.String(), description='Recipe ingredients', required=True)

class DeathnutAuthSchema(Schema):
    class Meta:
        strict = True
    id = fields.Integer(description='Resource id', required=True)
    user = fields.String(description='User to assign role to', required=True)
    role = fields.String(description='The role being assigned', required=True)