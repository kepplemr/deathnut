# deathnut overview

Deathnut is an extremely simple, easy-to-use, and blazing fast authorization library. It supports
several pyton REST tools (Flask, Falcon, Fastapi) and uses redis for data storage.

Endpoint decorators are provided for each REST tool so that services need not add heaps of 
authorization logic themselves. Instead, introducing a one-line decorator around endpoints can 
handle all common use cases while basic authz requirements can be understood at a glance. 
Additionally, a "lower level" deathnut client is available for unique cases or easy investigation of
authorization status. 


Services can add authorization support by defining a list of privileges -- e.g., ['view', 'edit',
'own'] and denoting endpoints that assign or require said privileges.


# contents
[TOC]
- [Deathnut overview](#deathnut-overview)
- [Redis overview](docs/redis.md)
- [Pre-commit setup](#pre-commit-setup)

# design points of emphasis

- be fast
- be simple to add and simple to understand
- do not slow the majority of traffic (GETs) at all
- support enabling authorization checks in phases

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

Towards the top, we also create an auth endpoint which allows for easy handling of user-initiated
sharing and revocation of access. The endpoint is added to the service (and OpenAPI specs) at 
/auth-recipe. Any number of auth endpoints can be defined, but one per service should handle most 
use cases.

Once we have an auth endpoint defined, we specify the roles available for granting.
Here a role of 'own' can grant 'view', 'edit', and 'own'. A role of 'edit' can grant 'view'. 

As the initial creator is assigned all privileges (own, edit, view), they are capable of granting
a friend whatever access the friend would want. 


```python
app = FastAPI()
redis_conn = redis.Redis(host="redis", port=6379)
auth_o = FastapiAuthorization(app, service="example", resource_type="recipe", redis_connection=redis_conn, enabled=True, strict=False)
auth_endpoint = auth_o.create_auth_endpoint('/auth-recipe')
auth_endpoint.allow_grant(requires_role='own', grants_roles=['view', 'edit', 'own'])
auth_endpoint.allow_grant(requires_role='edit', grants_roles=['view'])
logger = get_deathnut_logger(__name__)
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

# pre-commit setup
1) brew install pre-commit
