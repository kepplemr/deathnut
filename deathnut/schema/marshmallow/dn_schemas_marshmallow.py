from marshmallow import Schema, fields


class DeathnutAuthSchema(Schema):
    class Meta:
        strict = True
    id = fields.String(description="Resource id", required=True)
    user = fields.String(description="User to assign role to", required=True)
    requires = fields.String(description="User role checked for grant privilege", required=True)
    grants = fields.List(fields.String(), description="The role to assign or revoke", required=True)
    revoke = fields.Boolean(description="If True, attempt to revoke the privilege", required=False)

class DeathnutErrorSchema(Schema):
    class Meta:
        strict = True
    message = fields.String(description="Description of what failed", required=True)
