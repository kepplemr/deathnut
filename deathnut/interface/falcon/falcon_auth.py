import falcon
from deathnut.client.deathnut_client import DeathnutClient
from deathnut.interface.base_interface import BaseAuthorizationInterface
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.redis import get_redis_connection

logger = get_deathnut_logger(__name__)

class ErrorHandler:
    @staticmethod
    def deathnut_exception(ex, req, resp, params):
        resp.media = {"message": ex.args[0]}
        resp.status = falcon.HTTP_401

class FalconAuthorization(BaseAuthorizationInterface):
    def __init__(self, app, service, resource_type=None, strict=True, enabled=True, **kwargs):
        super(FalconAuthorization, self).__init__(service, resource_type, strict, enabled, **kwargs)
        self._app = app
        self._app.add_error_handler(DeathnutException, ErrorHandler.deathnut_exception)

    @staticmethod
    def get_auth_header(*args, **kwargs):
        req = args[1]
        return req.get_header("X-Endpoint-Api-Userinfo", default="")

    @staticmethod
    def get_resource_id(id_identifier, *args, **kwargs):
        req = args[1]
        dn_args = req.media or {}
        dn_args.update(kwargs)
        return dn_args[id_identifier]

    @staticmethod
    def get_dont_wait(*args, **kwargs):
        req = args[1]
        return kwargs.get("dont_wait", req.method == "GET")

    def create_auth_endpoint(self, name, requires_role, grants_role):
        auth_interface = self
        class DeathnutAuth:
            @self.requires_role(requires_role, strict=True)
            def on_post(self, req, resp, **kwargs):
                dn_auth = req.media
                id = dn_auth["id"]
                user = dn_auth["user"]
                revoke = dn_auth.get("revoke", False)
                kwargs.update(deathnut_user=user)
                if revoke:
                    auth_interface.revoke_roles(id, [grants_role], **kwargs)
                else:
                    auth_interface.assign_roles(id, [grants_role], **kwargs)
                resp.media = {"id": id, "user": user, "role": grants_role, "revoke": revoke}
                resp.status = falcon.HTTP_200
        curr_auth_endpoint = DeathnutAuth()
        self._app.add_route(name, curr_auth_endpoint)
