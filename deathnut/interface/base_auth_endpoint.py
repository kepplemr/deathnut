from abc import abstractmethod

from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.abstract_classes import ABC

logger = get_deathnut_logger(__name__)

class BaseAuthEndpoint(ABC):
    def __init__(self, auth_o, name):
        self._name = name
        self._auth_o = auth_o
        self._allowed = {}
        self.generate_auth_endpoint()

    def _check_grant_enabled(self, requires, grants):
        logger.warn("Required: {} grants: {}".format(requires, grants))
        if grants not in self._allowed[requires]:
            raise DeathnutException('Role {} is not authorized to grant role {}'.format(requires, grants))

    def allow_grant(self, requires_role, grants_roles):
        """
        For a given role, allow users with that role to assign roles to others

        Parameters
        ----------
        requires_role: str
            name of the role required of the calling user in order to grant privileges
        grants_role: str
            name of the role granted to the id if the calling user has the authority to do so.
        """
        if self._allowed.get(requires_role):
            self._allowed[requires_role].extend(grants_roles)
        else:
            self._allowed[requires_role] = grants_roles

    @abstractmethod
    def generate_auth_endpoint(self):
        pass
    
