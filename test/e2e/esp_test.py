import google.auth.crypt
import google.auth.jwt
import requests
import time
import json

def generate_jwt(sa_keyfile,
                 sa_email='jwt-test@wellio-dev-michael.iam.gserviceaccount.com',
                 audience='recipe-service',
                 expiry_length=3600):
    """Generates a signed JSON Web Token using a Google API Service Account."""
    now = int(time.time())
    # build payload
    payload = {
        'iat': now,
        # expires after 'expiry_length' seconds.
        "exp": now + expiry_length,
        # iss must match 'issuer' in the security configuration in your
        # swagger spec (e.g. service account email). It can be any string.
        'iss': sa_email,
        # aud must be either your Endpoints service name, or match the value
        # specified as the 'x-google-audience' in the OpenAPI document.
        'aud':  audience,
        # sub and email should match the service account's email address
        'sub': sa_email,
        'email': sa_email
    }
    # sign with keyfile
    signer = google.auth.crypt.RSASigner.from_service_account_file(sa_keyfile)
    jwt = google.auth.jwt.encode(signer, payload)
    return jwt

def make_regular_request(method, url, data=None):
    headers = {'content-type': 'application/json'}
    response = method(url, headers=headers, data=json.dumps(data))
    print(str(response.text))
    response.raise_for_status()
    return response.text

def make_jwt_request(method, url, signed_jwt, data=None):
    headers = {'Authorization': 'Bearer {}'.format(signed_jwt.decode('utf-8')), 'content-type': 'application/json'}
    response = method(url, headers=headers, data=json.dumps(data))
    print(str(response.text))
    response.raise_for_status()
    return response.text

def test_unsecured_requests():
    print('Testing unsecured requests')
    port = 80
    new_recipe = {'title': 'Michael Cold Brew', 'ingredients': ['Soda', 'Coffee']}
    new_update = {'ingredients': ['Water', 'Coffee']}
    cold_brew_recipe = make_regular_request(requests.post, 'http://localhost:{}/recipe'.format(port), new_recipe)
    cold_brew_id = json.loads(cold_brew_recipe)['id']
    make_regular_request(requests.patch, 'http://localhost:{}/recipe/{}'.format(port,cold_brew_id), new_update)
    recipe = json.loads(make_regular_request(requests.get, 'http://localhost:{}/recipe/{}'.format(port,cold_brew_id)))
    assert(recipe['title'] == 'Michael Cold Brew')
    assert(recipe['ingredients'] == ['Water', 'Coffee'])

def test_secured_requests():
    print('Testing secured requests')
    port = 8080
    jwt = generate_jwt('keys/jwt-test.json')
    new_recipe = {'title': 'Michael spaghetti', 'ingredients': ['Pasta', 'Sour Cream']}
    new_update = {'ingredients': ['Pasta', 'Tomato Sauce']}
    spaghetti_recipe = make_jwt_request(requests.post, 'http://localhost:{}/recipe'.format(port), jwt, new_recipe)
    spaghetti_id = json.loads(spaghetti_recipe)['id']
    make_jwt_request(requests.patch, 'http://localhost:{}/recipe/{}'.format(port,spaghetti_id), jwt, new_update)
    recipe = json.loads(make_jwt_request(requests.get, 'http://localhost:{}/recipe/{}'.format(port,spaghetti_id), jwt))
    assert(recipe['title'] == 'Michael spaghetti')
    assert(recipe['ingredients'] == ['Pasta', 'Tomato Sauce'])

def main():
    test_unsecured_requests()
    test_secured_requests()

if __name__ == "__main__":
    main()
