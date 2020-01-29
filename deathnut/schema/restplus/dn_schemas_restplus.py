from flask_restplus import Resource, fields, Api

def register_restplus_schemas(api):
    deathnut_auth_schema = api.model("DeathnutAuthSchema", {
        "id": fields.String(description="Resource id", required=True),
        "user": fields.String(description="User to assign role to", required=True),
        "role": fields.String(description="The role to assign or revoke", required=True),
        "revoke": fields.Boolean(description="If true, revokes the privilege")})
    deathnut_error_schema = api.model("DeathnutErrorSchema", {
        "message": fields.String(description="Description of what failed")})
    return deathnut_auth_schema, deathnut_error_schema