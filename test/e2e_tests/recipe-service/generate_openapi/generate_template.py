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
import yaml

import fastapi
from deathnut.util.logger import get_deathnut_logger
from .util import load_yaml_file, write_yaml_file, clean_dict

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
            _create_template_from_app(app, flags.openapi_template_output)
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
        _create_template_from_app(app, template_output)


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
    parser.add_argument("--openapi-template-output", type=str,
                        help="output path for generated template", default=default_file_location)
    parser.add_argument("--generate-openapi-template", action="store_true")
    flags, not_for_us = parser.parse_known_args()
    sys.argv = sys.argv[:1] + not_for_us
    return flags


def get_flask_specs(app):
    with app.test_client() as client:
        if app.extensions.get('restplus'):
            swagger_spec_url = next((str(x) for x in app.url_map.iter_rules() if
                                    str(x.endpoint) == "specs"), '/swagger.json')
        else:
            swagger_spec_url = app.config.get("APISPEC_SWAGGER_URL", "/swagger/")
        logger.info("Flask app swagger URL: " + swagger_spec_url)
        return json.loads(client.get(swagger_spec_url).data)


def get_fastapi_specs(app):
    # TODO convert openapi3 -> swagger2
    # this being run inside the app image so product the oas3 specs as-is.
    # Let CI take care of mounting & converting them.
    # docker run -v "$PWD:/tmp" -it ioggstream/api-spec-converter --from openapi_3 --to swagger_2
    #  -d --syntax yaml --order alpha --check /tmp/fastapi.yaml
    return app.openapi()


def unsupported_app_type(app):
    raise NotImplementedError('Unsupported application type: ' + str(type(app)))


def get_swagger_specs(app):
    return {
        flask.app.Flask: get_flask_specs,
        fastapi.applications.FastAPI: get_fastapi_specs
    }.get(type(app), unsupported_app_type)(app)


def _create_template_from_app(app, template_output):
    logging.info("Generating OpenAPI template from Flask swagger specs")
    template_dict = _get_dict_with_defaults()
    openapi_schema = get_swagger_specs(app)
    template_dict.update(openapi_schema)
    clean_dict(template_dict)
    write_yaml_file(template_output, template_dict)


def _get_dict_with_defaults():
    default_path = "/".join([os.path.dirname(os.path.realpath(__file__)), "defaults.yaml"])
    return load_yaml_file(default_path)
