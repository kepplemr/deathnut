# deathnut overview

Deathnut is an extremely simple, easy-to-use, and blazing fast authorization library. It supports
several python REST tools (Flask, Falcon, Fastapi) and uses redis for data storage.

Endpoint decorators are provided for each REST tool so that services need not add heaps of
authorization logic themselves. Instead, introducing a one-line decorator around endpoints can
handle all common use cases and make AuthZ requirements clear at a glance. Additionally, a "lower
level" deathnut client is available for unique cases or easy investigation of authorization status.

# contents
1. [deathnut overview](#deathnut-overview)
2. [main concepts](#main-concepts)
3. [example service](#example-service)
    - [e2e example - fastapi](test/e2e_tests/recipe-service/fastapi/app.py)
    - [e2e example - flask-apispec](test/e2e_tests/recipe-service/flask/app-apispec.py)
    - [e2e example - flask-restplus](test/e2e_tests/recipe-service/flask/app-restplus.py)
    - [e2e example - falcon](test/e2e_tests/recipe-service/falcon/app.py)
4. [interface magic](#interface-magic)
5. [strict and enabled](#strict-and-enabled)
6. [lower-level client](#lower-level-client)
7. [redis overview](#redis-overview)
    - [detailed redis walkthrough](docs/redis.md)
8. [authentication overview](#authentication-overview)
9. [deathnut deployment](#deathnut-deployment)
10. [pre-commit setup](#pre-commit-setup)

# main concepts

Deathnut is not a service. Deathnut is a library/tool that services can use to handle their own
authorization logic.

It encapsulates logic to talk to redis and assign/retrieve stored user authorization information.
For a given user and resource_id, a service with deathnut can: assign a role, check a role, and
revoke a role. There are no restrictions on the number or naming of roles that a service can use;
that is entirely up to the service. In most examples we'll use ['view', 'edit', 'own'] for
privileges but these could just as easily be ['serf', 'peasant', 'knight', 'king'].

Deathnut does not handle authentication of users. It relies on the pod ESP sidecar(s) to verify the
signage of JWT tokens received from cloud endpoints. When ESP does this successfully, it attaches a
'X-Endpoint-Api-Userinfo' header with user information deathnut trusts entirely for AuthZ. Other
headers/auth support could be added, but this header is currently all that is supported.

In addition to the one-line decorators to surround endpoints with authorization requirements/etc,
deathnut interfaces also provide the ability to add **auth endpoints**. Auth endpoints are easy ways
to define which user privileges can grant/revoke from others, and provides an endpoint to entirely
handle this. Again, ensuring services do not get bogged down implementing their own authorization
solutions.

Performance is a central concern. Intra-datacenter calls to redis are extremely fast: for the most
common 'check role' operation the round-trip response time is about 5ms. For operations that create
or update resources, the expected performance hit for adding deathnut will be around this. **For
the most common operations (GETs), deathnut is even faster.** We achieve additional speed on GETs by
not waiting for authorization OK before executing the called endpoint. In another thread (start time
 < 1 millisecond) we then check the user's authorization for the resource. If authorized,
we'll return the result we get back from the endpoint. If not, we'll return the normal 401. *Deathnut
will not, by any remotely perceptible measure, slow your service.*

# example service

Below is an example of a recipe serving service. Users can:
1) Create personal recipes by POST to /recipe
2) Retrieve personal recipes by GET to /recipe/{id}
3) Update personal recipes by PATCH to /recipe/{id}

Pretty simple. Where deathnut comes into play:
1) When users POST a recipe, they are assigned ['own', 'edit', 'view'] privileges to that recipe.
2) To view the created recipe, users must have 'view' access to it, meaning initially that only the
creator can view.
3) To patch the created recipe, users must have 'edit' access to it, meaning initially that only the
creator can update.
4) By calling GET on /recipe, users will receive a list of all recipes they have 'view' access to.

Towards the top, we also create an **auth endpoint** which allows for easy handling of user-initiated
sharing and revocation of access. The endpoint is added to the service (and OpenAPI specs) at
/auth-recipe. Any number of auth endpoints can be defined, but one per service should handle most
use cases.

Once we have an auth endpoint defined, we specify the roles available for granting.
Here a role of 'own' can grant 'view', 'edit', and 'own'. A role of 'edit' can grant 'view'.

As the initial creator is assigned all privileges (own, edit, view), they are capable of granting
a friend whatever access the friend would want.

If the initial user 'user1' wants to grant their friend 'user2' access to view and edit the recipe,
they would initiate a call to /auth-recipe containing:

```json
{"id": "${recipe_id}", "requires": "own", "grants": ["view", "edit"], "user": "${user2_id}"}
```
The data payload indicates user1 (determined via JWT token) wants to use their 'own' privilege to
grant ['edit', 'view'] to user2.

Deathnut will:
1) verify that the authenticated user (user1) has the 'own' privilege.
2) the 'own' privilege has been granted the ability to assign both 'edit' and 'view'

Further, any privilege that can grant a role can also revoke one.

Should user1 and user2 have a falling out, user1 can revoke user2's 'edit' and 'view' access with
a very similar call to /auth-recipe:

```json
{"id": "${recipe_id}", "requires": "own", "grants": ["view", "edit"], "user": "${user2_id}", "revoke": true}
```

An obvious byproduct of this ability is that should user1 have granted user2 **all** privileges
('view', 'edit' and 'own'), user2 is capable of revoking all of user1's access, locking them out of
their own created recipe!

To avoid such situations, services should likely follow the pattern below of granting the initial
creator an extra privilege ('own') that they need not share to grant others full access to view/edit
their created recipe.

```python
app = FastAPI()
redis_conn = redis.Redis(host="redis", port=6379)
auth_o = FastapiAuthorization(app, service="example", resource_type="recipe",
    redis_connection=redis_conn, enabled=True, strict=False)
auth_endpoint = auth_o.create_auth_endpoint('/auth-recipe')
auth_endpoint.allow_grant(requires_role='own', grants_roles=['view', 'edit', 'own'])
auth_endpoint.allow_grant(requires_role='edit', grants_roles=['view'])
recipe_db = dict()

@app.get("/recipe/{id}", response_model=RecipeWithId)
@auth_o.requires_role('view')
async def get_recipe(id: str, request: Request):
    return recipe_db[id]

@app.post("/recipe", response_model=RecipeWithId)
@auth_o.authentication_required(assign=["own", "edit", "view"])
async def create_recipe(recipe: Recipe, request: Request):
    new_id = str(uuid.uuid4())
    new_recipe = {"id": new_id, "title": recipe.title, "ingredients": recipe.ingredients}
    recipe_db[new_id] = new_recipe
    return new_recipe

@app.get("/recipe", response_model=List[RecipeWithId])
@auth_o.fetch_accessible_for_user('view')
async def get_recipes(request: Request, limit: int = 10):
    return [recipe_db[x] for x in request.deathnut_ids][0:limit]

@app.patch("/recipe/{id}", response_model=RecipeWithId)
@auth_o.requires_role('edit')
async def patch_recipe(id: str, recipe: PartialRecipe, request: Request):
    for update in [x for x in recipe.dict().keys() if recipe.dict()[x]]:
        recipe_db[id][update] = getattr(recipe, update)
    return recipe_db[id]
```

For a full E2E example of the deathnut Fastapi interface, see the example app [here](test/e2e_tests/recipe-service/fastapi/app.py).

For full examples of the other interface:\
[flask-apispec](test/e2e_tests/recipe-service/flask/app-apispec.py)\
[flask-restplus](test/e2e_tests/recipe-service/flask/app-restplus.py)\
[falcon](test/e2e_tests/recipe-service/falcon/app.py)

# interface magic

In the above example, the deathnut decorator adds some attributes to the provided starlette request
object. The calling user (extracted from the JWT) can be found at request.deathnut_user.

For the fetch_accessible_for_user(role) decorator an additional request.deathnut_ids list is
provided, populated with all the resource ids the calling user is able to access for the role
indicated.

For interfaces other than fastapi, deathnut_user and deathnut_ids are supplied as kwargs to the
endpoint functions.

# strict and enabled

In the above example, the FastApiAuthorization interface constructor is passed 'enabled=True' and
'strict=False'. What these settings mean:

- enabled = if false, deathnut does nothing but wrap the endpoints and product some log info to test
that it is working. A nice way to test that everything is imported properly and ready to go.

- strict = if false, deathnut will allow unauthenticated users to call the app as well. Since ESP
will not allow external users in without a JWT token, this will mostly be internal traffic. In the
above example, recipes should be created and fetched but no access grants would be honored. If
strict is true, *only* JWT-authenticated users will be able to access the endpoint.

# lower level client

The lower-level client is used by the various REST interfaces to perform the core deathnut
operations (assign, check, remove). Additionally, there are some methods that are useful for
debugging.

The following test script shows how to interact with the client:

```python
import fakeredis
from deathnut.client.deathnut_client import DeathnutClient

fake_redis_conn = fakeredis.FakeStrictRedis()
dn_client = DeathnutClient(service="test", resource_type="recipes", redis_connection=fake_redis_conn)

# assign privileges
for privilege in ['own', 'view']:
    for i in range(3):
        dn_client.assign_role('michael', privilege, str(i))

# check privilege
assert dn_client.check_role('michael', 'view', '1') == True

# revoke privilege
dn_client.revoke_role('michael', 'view', '1')
assert dn_client.check_role('michael', 'view', '1') == False

# return all 3
assert sorted(dn_client.get_resources('michael', 'own')) == ['0', '1', '2']

# return only 2
assert len(dn_client.get_resources('michael', 'own', limit=2)) == 2

# assign some more
for i in range(10):
    dn_client.assign_role('michael', 'own', str(i + 3))

# three pages of results [5, 5, 3]
assert len(list(dn_client.get_resources_page('michael', 'own', page_size=5))) == 3

# page through results
for i, page in enumerate(dn_client.get_resources_page('michael', 'own', page_size=5)):
    assert len(page) == [5, 5, 3][i]

# show all roles and ids
all_roles = dn_client.get_roles('michael')
assert sorted(all_roles['own']) == ['0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9']
assert sorted(all_roles['view']) == ['0', '2']
```

**Note: get_roles(user) is for debugging and should not be used in prod endpoints.**

# redis overview

redis is used as the backend data store for user roles -> resource_ids. redis was chosen because it
is extremely fast, we're already using it, and GCP provides a managed, HA instance (Memorystore).

Memorystore does now support [exporting db data](https://cloud.google.com/blog/products/databases/cloud-memorystore-adds-import-export-and-redis-4-0). Thus Deathnut backend redis data can be
periodically backed up to GCS in RDB format. This process should likely be managed by
composer/Airflow once or twice monthly.

Should redis fill up, we want to return outage notifications to the user and log all access
grants/etc to stackdriver. Logging to stackdriver would let us replay operations missed while redis
was down, basically acting as a redis edit log.

[For a detailed breakdown of deathnut's data model.](docs/redis.md)

# authentication overview

The low-level deathnut client's job is to encapsulate our communicaiton with redis; it accepts
any string value for a username.

As for the REST interfaces, currently only auth information passed from ESP via the
'X-Endpoint-Api-Userinfo' header is supported.

If you're running ESP locally, you can generate these tokens with an appropriate service account
similar to the approach [here](test/e2e_tests/test_e2e.py) (see generate_jwt_token).

If you're interested in generating these tokens to hit cloud endpoints, the below script should be
helpful. First you'll need a service account authorized to create custom tokens that we'll exchange
with idtk for id tokens. You'll also need an API key to talk to idtk.

The 'SERVICE_ACCOUNT_KEY' can be obtained by:
1) Ask Ops to grant you access to the desired firebase project (feinschmecker-integration,
mealhero-app-integration, etc.).
2) Log into the firebase console and select that project.
3) Click on the screw widget in the upper left and select 'Project settings'
4) Select 'Service accounts' tab
5) Click 'Generate new private key'.

The 'FIREBASE_WEB_API_KEY' can be obtained by:
1) Follow steps 1-3 above
2) The 'Web API Key' should be displayed in the 'General' tab.

```python
import json
import os
import firebase_admin
import requests
from firebase_admin import auth, credentials

# make sure service account has 'firebaseauth.users.[create,get]'
SERVICE_ACCOUNT_KEY_LOCATION = 'devops/keys/fenschmecker-int.json'
# make sure the key used has 'Identity Toolkit API' access. Or sign in with email/pw.
FIREBASE_WEB_API_KEY = os.environ.get('FS_INT_APIKEY')
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

firebase_admin.initialize_app(credentials.Certificate(SERVICE_ACCOUNT_KEY_LOCATION))
# if user did not yet exist, first run auth.create_user(email=<>, password=<>)
m_id, m_jwt = get_id_token_for_user_email('michael@test.com')
get_response = make_jwt_request(requests.get, edited_recipe_url, m_jwt)
```

Each tool has a different way of pulling these headers, all must implement the abstract
get_auth_header() method defined in the base interface.

The actual extraction of user information from these headers is done [here](deathnut/util/jwt.py).

For an example of how we test dimsum cloud endpoints E2E, see [here](https://github.com/cephalo-ai/dimsum/blob/master/tests/auth/ce_auth.py).


# deathnut deployment

On successful build of master, the deathnut 'pip zip' is deployed to GCS @
https://console.cloud.google.com/storage/browser/dist.getwellio.com/projects/deathnut/master

When making changes to deathnut, bump the version [here](setup.py#L5)

# pre-commit setup

brew install pre-commit
