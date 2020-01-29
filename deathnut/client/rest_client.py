from deathnut.client.deathnut_client import DeathnutClient
from deathnut.util.logger import get_deathnut_logger

logger = get_deathnut_logger(__name__)


class DeathnutRestClient(DeathnutClient):
    # TODO clients should not trrack enabled, strict; interfaces should?
    # TODO should this all be moved to the global interface?
    def __init__(
        self, service, resource_type=None, strict=True, enabled=True, **kwargs
    ):
        """
        Parameters
        ----------
        strict: bool
            If False, user 'Unauthenticated'
            Note: this value is a default and can be overiden when calling client methods.
        enabled: bool
            If True, authorization checks will run. If False, all users will have access to
            everything.
            Note: this value is a default and can be overiden when calling client methods.
        *Other params defined in superclass.
        """
        self._strict = strict
        self._enabled = enabled
        super(DeathnutRestClient, self).__init__(service, resource_type, **kwargs)
