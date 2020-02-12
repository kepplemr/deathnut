import json
import time

import google.auth.crypt
import google.auth.jwt
import requests


def generate_jwt(user, sa_keyfile="keys/jwt-test.json", sa_email="jwt-test@wellio-dev-michael.iam.gserviceaccount.com",
    audience="recipe-service", expiry_length=3600):
    """Generates a signed JSON Web Token using a Google API Service Account."""
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + expiry_length,
        # iss must match x-google-issuer in openapi spec (who signed me)
        "iss": sa_email,
        # aud must match x-google-audience or full service name (who this is intended for)
        "aud": audience,
        # sub must be sa_email or JWT validation fails (it becomes id?)
        "sub": sa_email,
        "email": user,
    }
    # firebase handles signing our real clients
    signer = google.auth.crypt.RSASigner.from_service_account_file(sa_keyfile)
    jwt = google.auth.jwt.encode(signer, payload)
    return jwt


def make_regular_request(method, url, data=None):
    headers = {"content-type": "application/json"}
    response = method(url, headers=headers, data=json.dumps(data))
    #print(str(response.text))
    response.raise_for_status()
    return response


def make_jwt_request(method, url, signed_jwt, data=None):
    headers = {"Authorization": "Bearer {}".format(signed_jwt.decode("utf-8")),
        "content-type": "application/json"}
    response = method(url, headers=headers, data=json.dumps(data))
    print(str(response.text))
    return response


def test_unsecured_requests(port):
    new_recipe = {"title": "Michael Cold Brew", "ingredients": ["Soda", "Coffee"]}
    new_update = {"ingredients": ["Water", "Coffee"]}
    cold_brew_recipe = make_regular_request(requests.post, "http://localhost:{}/recipe".format(port), new_recipe)
    cold_brew_id = json.loads(cold_brew_recipe.text)["id"]
    make_regular_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, cold_brew_id), new_update)
    recipe = json.loads(make_regular_request(requests.get, "http://localhost:{}/recipe/{}".format(port, cold_brew_id)).text)
    assert recipe["title"] == "Michael Cold Brew"
    assert recipe["ingredients"] == ["Water", "Coffee"]


def test_secured_requests(port):
    jwt = generate_jwt("michael")
    new_recipe = {"title": "Michael spaghetti", "ingredients": ["Pasta", "Sour Cream"]}
    new_update = {"ingredients": ["Pasta", "Tomato Sauce"]}
    spaghetti_recipe = make_jwt_request(
        requests.post, "http://localhost:{}/recipe".format(port), jwt, new_recipe
    )
    spaghetti_id = json.loads(spaghetti_recipe.text)["id"]
    make_jwt_request(
        requests.patch,
        "http://localhost:{}/recipe/{}".format(port, spaghetti_id),
        jwt,
        new_update,
    )
    recipe = json.loads(
        make_jwt_request(
            requests.get,
            "http://localhost:{}/recipe/{}".format(port, spaghetti_id),
            jwt,
        ).text
    )
    assert recipe["title"] == "Michael spaghetti"
    assert recipe["ingredients"] == ["Pasta", "Tomato Sauce"]


def test_deathnut_basics(port):
    michael_jwt = generate_jwt("michael")
    jennifer_jwt = generate_jwt("jennifer")
    # michael creates, edits, and gets a new recipe
    recipe = {"title": "Pierogis", "ingredients": ["potatoes", "cream or whatever"]}
    update = {"ingredients": ["potatoes", "cream"]}
    pierogi_id = json.loads(make_jwt_request(requests.post,"http://localhost:{}/recipe".format(port), michael_jwt, recipe).text)["id"]
    make_jwt_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, pierogi_id),vmichael_jwt, update)
    recipe = json.loads(
        make_jwt_request(
            requests.get,
            "http://localhost:{}/recipe/{}".format(port, pierogi_id),
            michael_jwt,
        ).text
    )
    assert recipe["title"] == "Pierogis"
    assert recipe["ingredients"] == ["potatoes", "cream"]
    assert recipe["id"] == pierogi_id
    # jennifer attempts to get and update the newly created recipe (she fails)
    another_update = {"ingredients": ["potatoes", "cream", "cheddar"]}
    response = make_jwt_request(
        requests.get,
        "http://localhost:{}/recipe/{}".format(port, pierogi_id),
        jennifer_jwt,
    )
    assert response.status_code == 401
    response = make_jwt_request(
        requests.patch,
        "http://localhost:{}/recipe/{}".format(port, pierogi_id),
        jennifer_jwt,
        another_update,
    )
    assert response.status_code == 401
    # michael grants jennifer 'view' privilege
    auth_grant = {"id": pierogi_id, "role": "view", "user": "jennifer"}
    response = make_jwt_request(
        requests.post,
        "http://localhost:{}/auth-recipe".format(port),
        michael_jwt,
        auth_grant,
    )
    assert response.status_code == 200
    # jennifer still cannot patch, but can view, the recipe
    response = make_jwt_request(
        requests.patch,
        "http://localhost:{}/recipe/{}".format(port, pierogi_id),
        jennifer_jwt,
        another_update,
    )
    assert response.status_code == 401
    response = make_jwt_request(
        requests.get,
        "http://localhost:{}/recipe/{}".format(port, pierogi_id),
        jennifer_jwt,
    )
    assert response.status_code == 200
    assert json.loads(response.text) == recipe
    # jennifer gets greedy and tries to give herself edit rights to the recipe
    auth_grant = {"id": pierogi_id, "role": "edit", "user": "jennifer"}
    response = make_jwt_request(
        requests.post,
        "http://localhost:{}/auth-recipe".format(port),
        jennifer_jwt,
        auth_grant,
    )
    assert response.status_code == 401
    # michael finds out and decides to revoke jennifer's view access
    auth_grant = {"id": pierogi_id, "role": "view", "user": "jennifer", "revoke": True}
    response = make_jwt_request(
        requests.post,
        "http://localhost:{}/auth-recipe".format(port),
        michael_jwt,
        auth_grant,
    )
    assert response.status_code == 200
    # jennifer can no longer view the recipe, and still cannot patch it (sucks to be jennifer)
    response = make_jwt_request(
        requests.get,
        "http://localhost:{}/recipe/{}".format(port, pierogi_id),
        jennifer_jwt,
    )
    assert response.status_code == 401
    response = make_jwt_request(
        requests.patch,
        "http://localhost:{}/recipe/{}".format(port, pierogi_id),
        jennifer_jwt,
        another_update,
    )
    assert response.status_code == 401


def generate_and_deploy_openapi_spec():
    pass


def main():
    # wait for docker-compose
    # generate_and_deploy_openapi_spec()
    for port in [80, 81, 82]:
        print('Testing unsecured requests on port: ' + str(port))
        test_unsecured_requests(port)
    for port in [8080, 8081, 8082]:
        print('Testing secured requests on port: ' + str(port))
        test_secured_requests(port)
        test_deathnut_basics(port)


if __name__ == "__main__":
    main()
