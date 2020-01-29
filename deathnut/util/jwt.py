import base64
import json

from deathnut.util.logger import get_deathnut_logger

logger = get_deathnut_logger(__name__)


def get_user_from_jwt_header(jwt_header):
    user = "Unauthenticated"
    if jwt_header:
        user = json.loads(base64.b64decode(jwt_header))["email"]
    return user
