import google.auth.crypt
import google.auth.jwt
import requests
import time
import json

def generate_jwt(user, sa_keyfile='keys/jwt-test.json', 
        sa_email='jwt-test@wellio-dev-michael.iam.gserviceaccount.com', audience='recipe-service', 
        expiry_length=3600):
    """Generates a signed JSON Web Token using a Google API Service Account."""
    now = int(time.time())

    payload = {
        'iat': now,
        "exp": now + expiry_length,
        # iss must match x-google-issuer in openapi spec (who signed me)
        'iss': sa_email,
        # aud must match x-google-audience or full service name (who this is intended for)
        'aud':  audience,
        # sub must be sa_email or JWT validation fails (it becomes id?)
        'sub': sa_email,
        'email': user
    }
    # firebase handles signing our real clients
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
    #print('Headers -> ' + str(headers))
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
    jwt = generate_jwt('michael')
    new_recipe = {'title': 'Michael spaghetti', 'ingredients': ['Pasta', 'Sour Cream']}
    new_update = {'ingredients': ['Pasta', 'Tomato Sauce']}
    spaghetti_recipe = make_jwt_request(requests.post, 'http://localhost:{}/recipe'.format(port), jwt, new_recipe)
    spaghetti_id = json.loads(spaghetti_recipe)['id']
    make_jwt_request(requests.patch, 'http://localhost:{}/recipe/{}'.format(port,spaghetti_id), jwt, new_update)
    recipe = json.loads(make_jwt_request(requests.get, 'http://localhost:{}/recipe/{}'.format(port,spaghetti_id), jwt))
    assert(recipe['title'] == 'Michael spaghetti')
    assert(recipe['ingredients'] == ['Pasta', 'Tomato Sauce'])

def test_deathnut():
    print('Testing deathnut')
    port = 8080
    user_1 = generate_jwt('michael')
    user_2 = generate_jwt('jennifer')
    # user1 creates, edits, and gets a new recipe
    new_recipe = {'title': 'Pierogis', 'ingredients': ['potatoes', 'cream or whatever']}
    new_update = {'ingredients': ['potatoes', 'cream']}
    pierogi_recipe = make_jwt_request(requests.post, 'http://localhost:{}/recipe'.format(port), user_1, new_recipe)
    pierogi_id = json.loads(pierogi_recipe)['id']
    make_jwt_request(requests.patch, 'http://localhost:{}/recipe/{}'.format(port,pierogi_id), user_1, new_update)
    recipe = json.loads(make_jwt_request(requests.get, 'http://localhost:{}/recipe/{}'.format(port,pierogi_id), user_1))
    assert(recipe['title'] == 'Pierogis')
    assert(recipe['ingredients'] == ['potatoes', 'cream'])
    # user2 attempts to get and update the newly created recipe
    another_update = {'ingredients': ['potatoes', 'cream', 'cheddar']}
    recipe = json.loads(make_jwt_request(requests.get, 'http://localhost:{}/recipe/{}'.format(port,pierogi_id), user_2))
    make_jwt_request(requests.patch, 'http://localhost:{}/recipe/{}'.format(port,pierogi_id), user_2, new_update)
    print('Testing deathnut')

def main():
    test_unsecured_requests()
    test_secured_requests()
    test_deathnut()

if __name__ == "__main__":
    main()
