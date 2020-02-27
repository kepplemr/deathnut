import logging

import yaml


def load_yaml_file(filename):
    with open(filename, "r") as my_file:
        return dict(**yaml.safe_load(my_file))


def write_yaml_file(filename, swagger_dict):
    yaml.emitter.Emitter.process_tag = lambda *args: None
    with open(filename, "w") as outfile:
        yaml.dump(dict(sorted(swagger_dict.items())), outfile, default_flow_style=False)

# def output_conf(filename, output_dict, path_prefix):
#     yaml.emitter.Emitter.process_tag = lambda *args: None
#     with open("/".join([path_prefix, filename]), "w") as outfile:
#         yaml.dump(output_dict, outfile, default_flow_style=False)


def clean_dict(template_dict):
    _handle_trailing_slashes(template_dict)
    _handle_operationIds(template_dict)
    _handle_body_arrays(template_dict)
    _remove_options_operations(template_dict)


def _handle_trailing_slashes(template_dict):
    """
    Google does not support paths ending with a trailing slash character
    (see https://cloud.google.com/endpoints/docs/frameworks/known-issues).
    We previously would scan for these instances and remove the offending character, which would
    result in a redirect to the '/' endpoint when CE came calling. This redirect no longer appears
    to work, returning '{"isTrusted": "true"}. Plus it seemed pretty hacky to begin with.
    Now we will drop all paths ending with a slash. If we need to expose one in the future, we can
    either go through to work to rename the endpoint everywhere or provide a 'un-slashed' route that
    just duplicates the 'slashed' one.
    Parameters
    ----------
    template_dict: dict
        Template dictionary, possibly containing bad paths such as '/api/ingredients/' which will
        now be dropped from GCE specs.
    """
    for path in list(template_dict.get('paths', [])):
        if path.endswith("/"):
            del template_dict["paths"][path]


def _remove_options_operations(template_dict):
    """
    Remove 'options' operations from endpoint spec
    """
    for path in list(template_dict.get('paths', [])):
        for operation in list(template_dict["paths"][path]):
            if operation == "options":
                del template_dict["paths"][path][operation]


def _handle_operationIds(template_dict):
    """
    flask-apispec does not generate default operationIds which are required by the OpenAPI spec.
    In case we do not set defaults in the apps, add operationIds where necessary.
    Additionally, sometimes duplicate operationIds can be generated, which will be rejected by
    OpenAPI spec standards.
    template_dict is modified in place.
    """
    already_used = {}
    for key, _ in template_dict.get("paths", {}).items():
        for op, _ in template_dict["paths"][key].items():
            current = template_dict["paths"][key][op]
            if isinstance(current, dict):
                if "operationId" not in current:
                    operationId = "{}_{}".format(op, key.split("/")[-1])
                    logging.warn("Generating operationId: {} for path: {} operation: {}".format(
                        operationId, key, op))
                    template_dict["paths"][key][op]["operationId"] = operationId
                curr_id = template_dict["paths"][key][op]["operationId"]
                if curr_id not in already_used:
                    already_used[curr_id] = 1
                else:
                    already_used[curr_id] += 1
                    new_id = curr_id + str(already_used[curr_id])
                    logging.warn("Operation '{}' exists, renaming to '{}' for '{}', op '{}'".format(
                            curr_id, new_id, key, op))
                    template_dict["paths"][key][op]["operationId"] = new_id


def _handle_body_arrays(template_dict):
    """
    Though valid by OpenAPI specs, google's spec validoator does not allow top-level arrays in
    request bodies. To get around this, we can camouflage that array and it works just fine.
    """
    for key, _ in template_dict.get("paths", {}).items():
        for op, _ in template_dict["paths"][key].items():
            if op not in ["get", "post", "put", "patch", "delete"]:
                continue
            for param in template_dict["paths"][key][op].get("parameters", []):
                schema = param.get("schema", None)
                if schema and schema.get("type", None) == "array":
                    param["schema"]["items"].update({"type": param["schema"].pop("type")})
