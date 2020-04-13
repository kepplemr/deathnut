import firebase_admin
import json
import requests
from firebase_admin import credentials
from firebase_admin import auth

def create_token_with_claims():
    cred = credentials.Certificate('./keys/gcloud-integration.json')
    default_app = firebase_admin.initialize_app(cred)
    # [START create_token_with_claims]
    uid = 'some-uid'
    email = 'michael@aol.com'
    additional_claims = {
        'premiumAccount': True
    }

    custom_token = auth.create_custom_token(uid, additional_claims)
    # [END create_token_with_claims]
    firebase_admin.delete_app(default_app)
    return custom_token

def make_jwt_request(method, url, signed_jwt, data=None, extra_header=None):
    headers = {"Authorization": "Bearer {}".format(signed_jwt.decode("utf-8")),
        "content-type": "application/json"}
    if extra_header:
        headers.update(extra_header)
    response = method(url, headers=headers, data=json.dumps(data))
    print(str(response.text))
    return response

token = create_token_with_claims()
# TODO replace url with CE

recipe = json.loads(make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, spaghetti_id), jwt).text)

print(str(token))