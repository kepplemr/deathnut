"""
This module generates an OpenAPI base template from the FLask applications swagger specs. This
output is used along with the env-specific 'overrides' (see generate_configs.py) to create our GCE
OpenAPI spec files.
The intention is to allow developers to modify an endpoint's definition in one place rather than up
to nine (flask app and jwt and non-jwt OpenAPI spec for each env).
"""
import argparse
import json
import logging
import os
import sys
import flask
import fastapi
import yaml

from deathnut.util.logger import get_deathnut_logger

default_file_location = "deploy/openapi/openapi.generated.yaml"
logger = get_deathnut_logger(__name__)


def generate_openapi_template(func):
    """
    Decorator function that wraps flask application factory method to add entrypoint for CircieCI
    to '_create_template_from_app'
    """

    def wrapper(*args, **kwargs):
        flags = _handle_arg_parsing()
        app = func(*args, **kwargs)
        if flags.generate_openapi_template:
            swagger_spec_url = ''
            _create_template_from_app(
                app, flags.openapi_template_output, swagger_spec_url
            )
        return app

    return wrapper


def generate_template_from_app(app, template_output=None, force_run=False):
    """
    Just another entrypoint to template generation, for test purposes and in case it is more
    convenient for a service to pass application object directly.
    template will be generated if '--generate-openapi-template' arg is detected or force_run is set.
    force_run is mostly convenient for integration/etc testing.

    Never use force_run if you subsequently want to run the actual app (it will re-generate and run
    the test_client on stat reload caused by the spec write).
    """
    flags = _handle_arg_parsing()
    template_output = template_output or flags.openapi_template_output
    if force_run or flags.generate_openapi_template:
        swagger_spec_url = ''
        _create_template_from_app(app, template_output, swagger_spec_url)


def _handle_arg_parsing():
    """
    Handles pulling out generation-specific flags while leaving other things paased unchanged.
    Returnes recognized flags while removing them from argv so they don't cause issues in wrapped
    applcation.
    Parameters (command line args)
    ----------
    generate-template: boolean
        If 'True', will proceed creating OpenAPI template. Provided in case some services already
        consume sys.argv and would like another way to kick off.
    template_output : str
        Filename location to store generated template output.
    Returns
    -------
    flags: Namespace
        Program namespace args.
    """
    parser = argparse.ArgumentParser(description="OpenAPI template generation utility")
    parser.add_argument(
        "--openapi-template-output",
        type=str,
        help="output path for generated template",
        default=default_file_location,
    )
    parser.add_argument("--generate-openapi-template", action="store_true")
    flags, not_for_us = parser.parse_known_args()
    sys.argv = sys.argv[:1] + not_for_us
    return flags

def get_flask_specs(app):
    with app.test_client() as client:
        if app.extensions.get('restplus'):
            swagger_spec_url = next((str(x) for x in app.url_map.iter_rules() if str(x.endpoint) == "specs"), '/swagger.json')
        else:
            swagger_spec_url = app.config.get("APISPEC_SWAGGER_URL", "/swagger/")
        logger.info("Flask app swagger URL: " + swagger_spec_url)
        return json.loads(client.get(swagger_spec_url).data)

def get_fastapi_specs(app):
    return app.openapi()

def unsupported_app_type(app):
    raise NotImplementedError('Unsupported application type: ' + str(type(app)))

def get_swagger_specs(app):
    return {
        flask.app.Flask: get_flask_specs,
        fastapi.applications.FastAPI: get_fastapi_specs
    }.get(type(app), unsupported_app_type)(app)

def _create_template_from_app(app, template_output, swagger_spec_url):
    logging.info("Generating OpenAPI template from Flask swagger specs")
    template_dict = _get_dict_with_defaults()
    openapi_schema = get_swagger_specs(app)
    logger.warn("Specs -> " + str(openapi_schema))
    template_dict.update(openapi_schema)
    _handle_trailing_slashes(template_dict)
    _handle_operationIds(template_dict)
    _handle_body_arrays(template_dict)
    _remove_options_operations(template_dict)
    _write_openapi_template(template_output, template_dict)


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
                    logging.warn(
                        "Generating operationId: {} for path: {} operation: {}".format(
                            operationId, key, op
                        )
                    )
                    template_dict["paths"][key][op]["operationId"] = operationId
                curr_id = template_dict["paths"][key][op]["operationId"]
                if curr_id not in already_used:
                    already_used[curr_id] = 1
                else:
                    already_used[curr_id] += 1
                    new_id = curr_id + str(already_used[curr_id])
                    logging.warn(
                        "OperationID '{}' already exists, renaming to '{}' for path '{}', operation '{}'".format(
                            curr_id, new_id, key, op
                        )
                    )
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
                    param["schema"]["items"].update(
                        {"type": param["schema"].pop("type")}
                    )


def _get_dict_with_defaults():
    default_dict = {}
    default_path = "/".join(
        [os.path.dirname(os.path.realpath(__file__)), "defaults.yaml"]
    )
    with open(default_path, "r") as cfg_f:
        default_dict = dict(**yaml.safe_load(cfg_f))
    return default_dict


def _write_openapi_template(filename, swagger_dict):
    yaml.emitter.Emitter.process_tag = lambda *args: None
    with open(filename, "w") as outfile:
        yaml.dump(dict(sorted(swagger_dict.items())), outfile, default_flow_style=False)
