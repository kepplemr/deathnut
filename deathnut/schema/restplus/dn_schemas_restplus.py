from flask_restplus import fields

def register_restplus_schemas(api):
    deathnut_auth_schema = api.model("DeathnutAuthSchema", {
        "id": fields.String(description="Resource id", required=True),
        "user": fields.String(description="User to assign role to", required=True),
        "requires": fields.String(description="role required of calling user", required=True),
        "grants": fields.List(fields.String(), description="roles to grant", required=True),
        "revoke": fields.Boolean(description="If true, revokes the privilege")})
    deathnut_error_schema = api.model("DeathnutErrorSchema", {
        "message": fields.String(description="Description of what failed")})
    return deathnut_auth_schema, deathnut_error_schema
