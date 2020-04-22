"""Dimsum CE e2e auth/deathnut test script"""
import json

import firebase_admin
import requests
from firebase_admin import auth, credentials
from google.cloud import datastore

# make sure service account has 'firebaseauth.users.[create,get]'
SERVICE_ACCOUNT_KEY_LOCATION = 'devops/keys/fenschmecker-int.json'
# make sure the key used has 'Identity Toolkit API' access. Or sign in with email/pw.
FIREBASE_WEB_API_KEY = ''
PROJECT_ID = 'wellio-integration'
DIMSUM_CE_URL = 'https://dimsum-jwt.endpoints.wellio-integration.cloud.goog'
EDITED_RECIPES_PATH = 'api/edited_recipes'
AUTH_ENDPOINT_PATH = 'auth-recipe'

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
    if method == requests.get:
        response = method(url, headers=headers)
    else:
        response = method(url, headers=headers, data=json.dumps(data))
    print(str(response.text))
    return response

def _create_edited_recipe(ds_client, base_url, jwt, title):
    # Cannelloni With Silver Beet and Mediterranean Vegetables Sauce
    basis_recipe_id = '5209b969-6d0c-45f2-ae60-561c18dc0ce2'
    basis_recipe = dict(ds_client.get(ds_client.key('recipe', basis_recipe_id)))
    edited_recipe = {'is_edited': True, 'basis_recipe_id': basis_recipe_id,
        'source': 'edited_recipe', 'title': title, 'thumbnail_data_uri': None}
    full_edited_recipe = dict(basis_recipe, **edited_recipe)
    # create and get recipe as michael
    response = make_jwt_request(requests.post, base_url, jwt, data=full_edited_recipe)
    assert response.status_code == 200
    return response.json().get('id')

def test_basic_auth(ds_client):
    # if user did not yet exist, first run auth.create_user(email=<>, password=<>)
    michael_jwt = get_id_token_for_user_email('michael@test.com')
    jennifer_jwt = get_id_token_for_user_email('jennifer@test.com')
    edited_recipes_base_url = '/'.join([DIMSUM_CE_URL, EDITED_RECIPES_PATH])
    # create and get recipe as michael
    edited_recipe_id = _create_edited_recipe(ds_client, edited_recipes_base_url, michael_jwt,
        'Michaels smokin Cannelloni')
    edited_recipe_url = '/'.join([edited_recipes_base_url, edited_recipe_id])
    get_response = make_jwt_request(requests.get, edited_recipe_url, michael_jwt)
    assert get_response.status_code == 200
    # # try to get recipe as jennifer
    get_response = make_jwt_request(requests.get, edited_recipe_url, jennifer_jwt)
    assert get_response.status_code == 401
    # assign view to jennifer (as michael)
    auth_grant = {"id": edited_recipe_id, "requires": "own", "grants": ["view"],
        "user": "jennifer@test.com"}
    auth_path = '/'.join([DIMSUM_CE_URL, AUTH_ENDPOINT_PATH])
    dn_response = make_jwt_request(requests.post, auth_path, michael_jwt, data=auth_grant)
    assert dn_response.status_code == 200
    # # jennifer should now be able to fetch the recipe
    get_response = make_jwt_request(requests.get, edited_recipe_url, jennifer_jwt)
    assert get_response.status_code == 200
    # # jennifer lacks 'own', cannot assign privileges
    auth_grant = {"id": edited_recipe_id, "requires": "own", "grants": ["view"],
        "user": "jennifer@test.com"}
    dn_response = make_jwt_request(requests.post, auth_path, jennifer_jwt, data=auth_grant)
    assert dn_response.status_code == 401
    # # michael can revoke privilege
    auth_grant = {"id": edited_recipe_id, "requires": "own", "grants": ["view"],
        "user": "jennifer@test.com",  "revoke": True}
    dn_response = make_jwt_request(requests.post, auth_path, michael_jwt, data=auth_grant)
    assert dn_response.status_code == 200
    # # jennifer can no longer access the recipe
    get_response = make_jwt_request(requests.get, edited_recipe_url, jennifer_jwt)
    assert get_response.status_code == 401
    ds_client.delete(ds_client.key('recipe', edited_recipe_id))

def test_list_endpoint(ds_client):
    michael_jwt = get_id_token_for_user_email('michael@test.com')
    edited_recipes_base_url = '/'.join([DIMSUM_CE_URL, EDITED_RECIPES_PATH])
    get_response = make_jwt_request(requests.get, edited_recipes_base_url, michael_jwt)
    assert get_response.status_code == 200
    original_recipes_length = len(get_response.json())
    # add a new recipe Michael will have 'view' access to
    new_edited_recipe_id = _create_edited_recipe(ds_client, edited_recipes_base_url, michael_jwt,
        'Another Michael recipe')
    get_response = make_jwt_request(requests.get, edited_recipes_base_url, michael_jwt)
    assert get_response.status_code == 200
    # michael should now have 'view' access to one more recipe
    assert len(get_response.json()) == (original_recipes_length + 1)
    ds_client.delete(ds_client.key('recipe', new_edited_recipe_id))

def main():
    firebase_admin.initialize_app(credentials.Certificate(SERVICE_ACCOUNT_KEY_LOCATION))
    ds_client = datastore.Client(PROJECT_ID)
    test_basic_auth(ds_client)
    test_list_endpoint(ds_client)

if __name__ == "__main__":
    main()
