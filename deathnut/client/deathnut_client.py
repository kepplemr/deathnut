from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.redis import get_redis_connection

logger = get_deathnut_logger(__name__)


class DeathnutClient(object):
    def __init__(self, service, resource_type=None, **kwargs):
        """
        Parameters
        ----------
        service: str
            Name of calling service.
        resource_type: str
            Optional name of specific resource being protected, used in the event services have
            multiple resource types.
        kwargs: dict
            Expected in kwargs are either a redis.Redis connection (redis_connection, allowing
            deathnut client to inject their own) OR the specification or redis_host, redis_port,
            redis_pw, redis_db in which case we will attempt to establish a redis connection for
            the client.
        """
        self._client = get_redis_connection(**kwargs)
        if resource_type:
            self._name = "{}_{}".format(service, resource_type)
        else:
            self._name = service

    def _check_authenticated(self, user):
        if user == "Unauthenticated":
            raise DeathnutException(
                "Unauthenticated user cannot be granted/removed from roles"
            )

    def assign_role(self, user, role, resource_id):
        self._check_authenticated(user)
        logger.warn(
            "Assigning role <{}> to user <{}> for resource <{}>, id <{}>".format(
                role, user, self._name, resource_id
            )
        )
        self._client.hset("{}:{}:{}".format(self._name, user, role), resource_id, "T")

    def check_role(self, user, role, resource_id):
        return bool(
            self._client.hget("{}:{}:{}".format(self._name, user, role), resource_id)
        )

    def revoke_role(self, user, role, resource_id):
        self._check_authenticated(user)
        logger.warn(
            "Revoking role <{}> from user <{}> for resource <{}>, id <{}>".format(
                role, user, self._name, resource_id
            )
        )
        self._client.hdel("{}:{}:{}".format(self._name, user, role), resource_id)

    def get_resources(self, user, role, page_size=10):
        """redis default is a count of 10"""
        cursor = "0"
        while cursor != 0:
            cursor, data = self._client.hscan(
                "{}:{}:{}".format(self._name, user, role),
                cursor=cursor,
                count=page_size,
            )
            yield [x[0].decode() for x in data.items()]

    def get_roles(self, user, resource_type):
        # TODO
        pass
