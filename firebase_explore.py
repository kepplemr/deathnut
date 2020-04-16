"""Dimsum CE e2e auth/deathnut test script"""
import json
import firebase_admin
import requests
from firebase_admin import credentials
from firebase_admin import auth

# make sure service account has 'firebaseauth.users.[create,get]'
SERVICE_ACCOUNT_KEY_LOCATION = './keys/gcloud-integration.json'
# make sure the key used has 'Identity Toolkit API' access. Or sign in with email/pw.
FIREBASE_WEB_API_KEY = 'AIzaSyDjGqnElsoDTV6BjMdmRGjIk8f04aUQMXU'

def get_id_token_for_user_email(email):
    user_id = auth.get_user_by_email(email).uid
    user_custom_token = auth.create_custom_token(user_id).decode()
    idtk_url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key='
    payload = {"token": user_custom_token, "returnSecureToken": True}
    return requests.post(''.join([idtk_url, FIREBASE_WEB_API_KEY]), data=payload).json().get('idToken')

def make_jwt_request(method, url, signed_jwt, data=None, extra_header=None):
    headers = {"Authorization": "Bearer {}".format(signed_jwt),
        "content-type": "application/json"}
    if extra_header:
        headers.update(extra_header)
    response = method(url, headers=headers, data=json.dumps(data))
    print(str(response.text))
    return response

def main():
    firebase_admin.initialize_app(credentials.Certificate(SERVICE_ACCOUNT_KEY_LOCATION))
    # if user does not yet exist, first run auth.create_user(email=<>, password=<>)
    michael_jwt = get_id_token_for_user_email('michael@test.com')
    jennifer_jwt = get_id_token_for_user_email('jennifer@test.com')

#url = 'https://dimsum-jwt.endpoints.wellio-integration.cloud.goog/api/edited_recipes'

if __name__ == "__main__":
    main()
