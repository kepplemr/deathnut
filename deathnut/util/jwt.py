import base64
import json

def get_user_from_jwt_header(request):
    user = 'Unauthenticated'
    jwt_header = request.headers.get('X-Endpoint-Api-Userinfo', '')
    if jwt_header:
        user = json.loads(base64.b64decode(jwt_header))['email']
    return user