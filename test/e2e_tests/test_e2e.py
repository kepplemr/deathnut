import atexit
import filecmp
import glob
import json
import os
import subprocess
import sys
import time

import google.auth.crypt
import google.auth.jwt
import requests

E2E_DIR = os.path.dirname(os.path.realpath(__file__))
RECIPE_CONTAINERS = ['recipe-service-apispec', 'recipe-service-restplus', 'recipe-service-fastapi',
                     'recipe-service-falcon']
ESP_CONTAINERS = ['esp-apispec', 'esp-restplus', 'esp-fastapi', 'esp-falcon']
OTHER_CONTAINERS = ['converter']
SERVICE_CONTAINERS = RECIPE_CONTAINERS + ESP_CONTAINERS + ['redis']
ALL_CONTAINERS = SERVICE_CONTAINERS + OTHER_CONTAINERS
COMPOSE_CONF = '/'.join([E2E_DIR, 'docker-compose.yml'])


def generate_jwt(user, sa_keyfile="{}/recipe-service/keys/jwt-test.json".format(E2E_DIR),
                 sa_email="jwt-test@wellio-dev-michael.iam.gserviceaccount.com",
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
    print(str(response.text))
    response.raise_for_status()
    return response


def make_jwt_request(method, url, signed_jwt, data=None, extra_header=None):
    headers = {"Authorization": "Bearer {}".format(signed_jwt.decode("utf-8")),
        "content-type": "application/json"}
    if extra_header:
        headers.update(extra_header)
    response = method(url, headers=headers, data=json.dumps(data))
    print(str(response.text))
    return response


def unsecured_requests(port):
    new_recipe = {"title": "Michael Cold Brew", "ingredients": ["Soda", "Coffee"]}
    new_update = {"ingredients": ["Water", "Coffee"]}
    cold_brew_recipe = make_regular_request(requests.post, "http://localhost:{}/recipe".format(port), new_recipe)
    cold_brew_id = json.loads(cold_brew_recipe.text)["id"]
    make_regular_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, cold_brew_id), new_update)
    recipe = json.loads(make_regular_request(requests.get, "http://localhost:{}/recipe/{}".format(port, cold_brew_id)).text)
    assert recipe["title"] == "Michael Cold Brew"
    assert recipe["ingredients"] == ["Water", "Coffee"]


def secured_requests(port):
    jwt = generate_jwt("michael")
    new_recipe = {"title": "Michael spaghetti", "ingredients": ["Pasta", "Sour Cream"]}
    new_update = {"ingredients": ["Pasta", "Tomato Sauce"]}
    spaghetti_recipe = make_jwt_request(requests.post, "http://localhost:{}/recipe".format(port), jwt, new_recipe)
    spaghetti_id = json.loads(spaghetti_recipe.text)["id"]
    make_jwt_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, spaghetti_id), jwt, new_update)
    recipe = json.loads(make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, spaghetti_id), jwt).text)
    assert recipe["title"] == "Michael spaghetti"
    assert recipe["ingredients"] == ["Pasta", "Tomato Sauce"]


def deathnut_basics(port):
    michael_jwt = generate_jwt("michael")
    jennifer_jwt = generate_jwt("jennifer")
    kim_jwt = generate_jwt("kim")
    # michael creates, edits, and gets a new recipe
    recipe = {"title": "Pierogis", "ingredients": ["potatoes", "cream or whatever"]}
    update = {"ingredients": ["potatoes", "cream"]}
    pierogi_id = json.loads(make_jwt_request(requests.post,"http://localhost:{}/recipe".format(port), michael_jwt, recipe).text)["id"]
    make_jwt_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, pierogi_id), michael_jwt, update)
    recipe = json.loads(make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, pierogi_id), michael_jwt).text)
    assert recipe["title"] == "Pierogis"
    assert recipe["ingredients"] == ["potatoes", "cream"]
    assert recipe["id"] == pierogi_id
    # jennifer attempts to get and update the newly created recipe (she fails)
    another_update = {"ingredients": ["potatoes", "cream", "cheddar"]}
    response = make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, pierogi_id), jennifer_jwt)
    assert response.status_code == 401
    response = make_jwt_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, pierogi_id), jennifer_jwt, another_update)
    assert response.status_code == 401
    # michael grants jennifer 'view' privilege
    auth_grant = {"id": pierogi_id, "requires": "own", "grants": ["view"], "user": "jennifer"}
    response = make_jwt_request(requests.post, "http://localhost:{}/auth-recipe".format(port), michael_jwt, auth_grant)
    assert response.status_code == 200
    # jennifer still cannot patch, but can view, the recipe
    response = make_jwt_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, pierogi_id), jennifer_jwt, another_update)
    assert response.status_code == 401
    response = make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, pierogi_id), jennifer_jwt)
    assert response.status_code == 200
    assert json.loads(response.text) == recipe
    # jennifer gets greedy and tries to give herself edit rights to the recipe
    auth_grant = {"id": pierogi_id, "requires": "own", "grants": ["edit"], "user": "jennifer"}
    response = make_jwt_request(requests.post, "http://localhost:{}/auth-recipe".format(port), jennifer_jwt, auth_grant)
    assert response.status_code == 401
    # michael finds out and decides to revoke jennifer's view access
    auth_grant = {"id": pierogi_id, "requires": "own", "grants": ["view"], "user": "jennifer", "revoke": True}
    response = make_jwt_request(requests.post, "http://localhost:{}/auth-recipe".format(port), michael_jwt, auth_grant)
    assert response.status_code == 200
    # jennifer can no longer view the recipe, and still cannot patch it (sucks to be jennifer)
    for jwt in [jennifer_jwt, kim_jwt]:
        response = make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, pierogi_id), jwt)
        assert response.status_code == 401
        response = make_jwt_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, pierogi_id), jwt, another_update)
        assert response.status_code == 401
    # michael grants kim 'view' and 'edit' privilege
    auth_grant = {"id": pierogi_id, "requires": "own", "grants": ["edit", "view"], "user": "kim"}
    response = make_jwt_request(requests.post, "http://localhost:{}/auth-recipe".format(port), michael_jwt, auth_grant)
    assert response.status_code == 200
    # kim can now view and edit the recipe
    another_update = {"ingredients": ["potatoes", "cream", "cheddar", "salt"]}
    response = make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, pierogi_id), kim_jwt)
    assert response.status_code == 200
    response = make_jwt_request(requests.patch, "http://localhost:{}/recipe/{}".format(port, pierogi_id), kim_jwt, another_update)
    assert response.status_code == 200
    # update the recipe
    recipe = response.json()
    # kim (edit) can grant view to jennifer
    auth_grant = {"id": pierogi_id, "requires": "edit", "grants": ["view"], "user": "jennifer"}
    response = make_jwt_request(requests.post, "http://localhost:{}/auth-recipe".format(port), kim_jwt, auth_grant)
    assert response.status_code == 200
    # jennifer can now view the recipe again
    response = make_jwt_request(requests.get, "http://localhost:{}/recipe/{}".format(port, pierogi_id), jennifer_jwt)
    assert response.status_code == 200
    assert json.loads(response.text) == recipe


def list_endpoint(port):
    michael_jwt = generate_jwt("michael")
    recipes_response = make_jwt_request(requests.get, "http://localhost:{}/recipe".format(port), michael_jwt)
    orig_recipes_length = len(recipes_response.json())
    recipe = {"title": "Enchiladas", "ingredients": ["tortilla", "cheese"]}
    make_jwt_request(requests.post,"http://localhost:{}/recipe".format(port), michael_jwt, recipe)
    recipes_response = make_jwt_request(requests.get, "http://localhost:{}/recipe".format(port), michael_jwt)
    new_recipes_length = len(recipes_response.json())
    assert new_recipes_length == (orig_recipes_length + 1)


def revoke_all(port):
    michael_jwt = generate_jwt("michael")
    recipes_response = make_jwt_request(requests.get, "http://localhost:{}/recipe".format(port), michael_jwt).json()
    ids = [dict(x)['id'] for x in recipes_response]
    for revoke_id in ids:
        for user in ['kim', 'jennifer', 'michael']:
            auth_grant = {"id": revoke_id, "requires": "own", "grants": ["view", "edit", "own"], "user": user, "revoke": True}
            make_jwt_request(requests.post, "http://localhost:{}/auth-recipe".format(port), michael_jwt, auth_grant)
    for user in ['kim', 'jennifer', 'michael']:
        recipes_response = make_jwt_request(requests.get, "http://localhost:{}/recipe".format(port), michael_jwt)
        assert len(recipes_response.json()) == 0


def remove_output():
    nuke_me = glob.glob('recipe-service/deploy/openapi/generated/*') + glob.glob('recipe-service/deploy/openapi/output/*')
    for to_nuke in nuke_me:
        os.remove(to_nuke)


def generate_and_deploy_openapi_spec(tag, deploy=False):
    if tag == 'fastapi' and sys.version_info < (3, 0):
        print('fastapi requires python 3')
        return
    if tag == 'falcon':
        print("Falcon openapi generation not supported")
        return
    os.chdir('/'.join([E2E_DIR, 'recipe-service']))
    generate_cmd = ['python',
        'generate_openapi/generate_configs.py', '-b',
        'deploy/openapi/generated/{}.yaml'.format(tag), '-o',
        'deploy/openapi/overrides/{}.yaml'.format(tag), '-p',
        'deploy/openapi/output']
    if deploy:
        deploy_cmd = ['gcloud', 'endpoints', 'services', 'deploy',
            'deploy/openapi/output/{}.yaml'.format(tag)]
        # esp containers must be restared to pick up latest spec
        esp_container = 'esp-{}'.format(tag)
        stop_and_remove_container(esp_container)
        run_container(esp_container)
    else:
        deploy_cmd = ['gcloud', 'endpoints', 'services', 'deploy',
            'deploy/openapi/output/{}.yaml'.format(tag), '--validate-only']
    subprocess.check_call(generate_cmd)
    subprocess.check_call(deploy_cmd)
    try:
        assert filecmp.cmp('deploy/openapi/output/{}.yaml'.format(tag),
            'deploy/openapi/expected/{}.yaml'.format(tag))
    except AssertionError as ae:
        print('Output -> ' + open('deploy/openapi/output/{}.yaml'.format(tag), 'r').read())
        print('Expected -> ' + open('deploy/openapi/expected/{}.yaml'.format(tag), 'r').read())
        raise ae


def build_container(*containers):
    for container in containers:
        compose_build_cmd = ['docker-compose', '-f', COMPOSE_CONF, 'build', '--no-cache', container]
        subprocess.check_output(compose_build_cmd)


def run_container(*containers):
    for container in containers:
        compose_up_cmd = ['docker-compose', '-f', COMPOSE_CONF, 'up', '-d', container]
        subprocess.check_output(compose_up_cmd)


def stop_and_remove_container(*containers):
    for container in containers:
        stop_cmd = ['docker', 'stop', container]
        rm_cmd = ['docker', 'rm', container]
        subprocess.call(stop_cmd, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        subprocess.call(rm_cmd, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)


def test_apispec_e2e():
    run_e2e_suite('recipe-service-apispec', 80, 8080)


def test_restplus_e2e():
    run_e2e_suite('recipe-service-restplus', 81, 8081)


def test_fastapi_e2e():
    run_e2e_suite('recipe-service-fastapi', 82, 8082)


def test_falcon_e2e():
    run_e2e_suite('recipe-service-falcon', 83, 8083)


def run_e2e_suite(container, unsecured_port, secured_port):
    print('Testing: ' + container)
    tag = container.split('-')[-1]
    build_container(container)
    run_container(container, 'esp-{}'.format(tag))
    generate_and_deploy_openapi_spec(tag)
    time.sleep(8)
    unsecured_requests(unsecured_port)
    secured_requests(secured_port)
    deathnut_basics(secured_port)
    list_endpoint(secured_port)
    revoke_all(secured_port)
    stop_and_remove_container(container, 'esp-{}'.format(tag))


atexit.register(stop_and_remove_container, *ALL_CONTAINERS)
if __name__ == "__main__":
    test_apispec_e2e()
    test_restplus_e2e()
    test_fastapi_e2e()
    test_falcon_e2e()
