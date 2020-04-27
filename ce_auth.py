"""Dimsum CE e2e auth/deathnut test script"""
import json
import os

import firebase_admin
import requests
from firebase_admin import auth, credentials
from google.cloud import datastore

# make sure service account has 'firebaseauth.users.[create,get]'
SERVICE_ACCOUNT_KEY_LOCATION = 'devops/keys/fenschmecker-int.json'
# make sure the key used has 'Identity Toolkit API' access. Or sign in with email/pw.
<<<<<<< HEAD
FIREBASE_WEB_API_KEY = 'AIzaSyAVmCbuZC6xmsYIOuVPlbrocWEsBbh4cx4'
=======
FIREBASE_WEB_API_KEY = os.environ.get('FS_INT_APIKEY')
>>>>>>> 0aebf186bcead3d52950f51fe5fb995507a0ea72
PROJECT_ID = 'wellio-integration'
DIMSUM_CE_URL = 'https://dimsum-jwt.endpoints.wellio-integration.cloud.goog'
EDITED_RECIPES_PATH = 'api/edited_recipes'
AUTH_ENDPOINT_PATH = 'auth-recipe'

def get_id_token_for_user_email(email):
    user_id = auth.get_user_by_email(email).uid
    user_custom_token = auth.create_custom_token(user_id).decode()
    idtk_url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key='
    payload = {"token": user_custom_token, "returnSecureToken": True}
    return user_id, requests.post(''.join([idtk_url, FIREBASE_WEB_API_KEY]), data=payload).json().get('idToken')

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
    _, m_jwt = get_id_token_for_user_email('michael@test.com')
    j_id, j_jwt = get_id_token_for_user_email('jennifer@test.com')
    k_id, k_jwt = get_id_token_for_user_email('kim@test.com')
    edited_recipes_base_url = '/'.join([DIMSUM_CE_URL, EDITED_RECIPES_PATH])
    # create and get recipe as michael (no patch for update)
    edited_recipe_id = _create_edited_recipe(ds_client, edited_recipes_base_url, m_jwt,
        'Michaels smokin Cannelloni')
    edited_recipe_url = '/'.join([edited_recipes_base_url, edited_recipe_id])
    get_response = make_jwt_request(requests.get, edited_recipe_url, m_jwt)
    assert get_response.status_code == 200
    # try to get recipe as jennifer
    get_response = make_jwt_request(requests.get, edited_recipe_url, j_jwt)
    assert get_response.status_code == 401
    # assign view to jennifer (as michael)
    auth_grant = {"id": edited_recipe_id, "requires": "own", "grants": ["view"], "user": j_id}
    auth_path = '/'.join([DIMSUM_CE_URL, AUTH_ENDPOINT_PATH])
    dn_response = make_jwt_request(requests.post, auth_path, m_jwt, data=auth_grant)
    assert dn_response.status_code == 200
    # jennifer should now be able to fetch the recipe
    get_response = make_jwt_request(requests.get, edited_recipe_url, j_jwt)
    assert get_response.status_code == 200
    # jennifer lacks 'own', cannot assign privileges
    auth_grant = {"id": edited_recipe_id, "requires": "own", "grants": ["view"],
        "user": j_id}
    dn_response = make_jwt_request(requests.post, auth_path, j_jwt, data=auth_grant)
    assert dn_response.status_code == 401
    # michael can revoke privilege
    auth_grant = {"id": edited_recipe_id, "requires": "own", "grants": ["view"],
        "user": j_id,  "revoke": True}
    dn_response = make_jwt_request(requests.post, auth_path, m_jwt, data=auth_grant)
    assert dn_response.status_code == 200
    # jennifer can no longer access the recipe
    get_response = make_jwt_request(requests.get, edited_recipe_url, j_jwt)
    assert get_response.status_code == 401
    # michael grants kim view and edit
    auth_grant = {"id": edited_recipe_id, "requires": "own", "grants": ["view", "edit"],
        "user": k_id}
    dn_response = make_jwt_request(requests.post, auth_path, m_jwt, data=auth_grant)
    assert dn_response.status_code == 200
    # kim cannot grant jennifer edit (edit cannot grant edit)
    auth_grant = {"id": edited_recipe_id, "requires": "edit", "grants": ["view", "edit"],
        "user": j_id}
    dn_response = make_jwt_request(requests.post, auth_path, k_jwt, data=auth_grant)
    assert dn_response.status_code == 401
    # jennifer still cannot view the recipe
    get_response = make_jwt_request(requests.get, edited_recipe_url, j_jwt)
    assert get_response.status_code == 401
    # kim can grant jennifer view
    auth_grant = {"id": edited_recipe_id, "requires": "edit", "grants": ["view"],
        "user": j_id}
    dn_response = make_jwt_request(requests.post, auth_path, k_jwt, data=auth_grant)
    assert dn_response.status_code == 200
    # jennifer should now be able to fetch the recipe (again)
    get_response = make_jwt_request(requests.get, edited_recipe_url, j_jwt)
    assert get_response.status_code == 200


def test_list_endpoint(ds_client):
    _, m_jwt = get_id_token_for_user_email('michael@test.com')
    edited_recipes_base_url = '/'.join([DIMSUM_CE_URL, EDITED_RECIPES_PATH])
    get_response = make_jwt_request(requests.get, edited_recipes_base_url, m_jwt)
    assert get_response.status_code == 200
    original_recipes_length = len(get_response.json())
    # add a new recipe Michael will have 'view' access to
    _create_edited_recipe(ds_client, edited_recipes_base_url, m_jwt, 'Another Michael recipe')
    get_response = make_jwt_request(requests.get, edited_recipes_base_url, m_jwt)
    assert get_response.status_code == 200
    # michael should now have 'view' access to one more recipe
    assert len(get_response.json()) == (original_recipes_length + 1)


# clean up redis/datastore
def test_revoke_all(ds_client):
    m_id, m_jwt = get_id_token_for_user_email('michael@test.com')
    j_id, j_jwt = get_id_token_for_user_email('jennifer@test.com')
    k_id, k_jwt = get_id_token_for_user_email('kim@test.com')
    auth_path = '/'.join([DIMSUM_CE_URL, AUTH_ENDPOINT_PATH])
    edited_recipes_base_url = '/'.join([DIMSUM_CE_URL, EDITED_RECIPES_PATH])
    get_response = make_jwt_request(requests.get, edited_recipes_base_url, m_jwt)
    assert get_response.status_code == 200
    for remove_id in [dict(x)['id'] for x in get_response.json()]:
        ds_client.delete(ds_client.key('edited_recipe', remove_id))
        for user in [k_id, j_id, m_id]:
            auth_grant = {"id": remove_id, "requires": "own", "grants": ["view", "edit", "own"], "user": user, "revoke": True}
            make_jwt_request(requests.post, auth_path, m_jwt, auth_grant)
    # double check that no roles remain
    for user_jwt in [k_jwt, j_jwt, m_jwt]:
        recipes_response = make_jwt_request(requests.get, edited_recipes_base_url, user_jwt)
        assert len(recipes_response.json()) == 0


def main():
    firebase_admin.initialize_app(credentials.Certificate(SERVICE_ACCOUNT_KEY_LOCATION))
    ds_client = datastore.Client(PROJECT_ID)
    test_basic_auth(ds_client)
    test_list_endpoint(ds_client)
    test_revoke_all(ds_client)

if __name__ == "__main__":
    main()
