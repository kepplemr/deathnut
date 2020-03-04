"""
This module generates an OpenAPI base template from an application instance. Current supports Flask
and fastapi.
"""
import argparse
import json
import logging
import sys

from util import clean_dict, write_yaml_file, get_dict_with_defaults, dict_merge

DEFAULT_FILE_LOCATION = "deploy/openapi/openapi.generated.yaml"


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

    Parameters
    ----------
    template_output: str
        if present, overrides the default template output location
    force_run: boolean
        primarily for tests  to run without passing '--generate-openapi-template' arg.
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
    generate-openapi-template: boolean
        If 'True', will proceed creating OpenAPI template. Provided in case some services already
        consume sys.argv and would like another way to kick off.
    openapi-template_output : str
        Filename location to store generated template output.

    Returns
    -------
    flags: Namespace
        Program namespace args.
    """
    parser = argparse.ArgumentParser(description="OpenAPI template generation utility")
    parser.add_argument("--openapi-template-output", type=str,
                        help="output path for generated template", default=DEFAULT_FILE_LOCATION)
    parser.add_argument("--generate-openapi-template", action="store_true")
    flags, not_for_us = parser.parse_known_args()
    sys.argv = sys.argv[:1] + not_for_us
    return flags


def _get_flask_specs(app):
    """
    Function to return swagger doc dict for flask apps (apispec and restplus). Determines swagger 
    location, starts a test app, and returns the pulled docs.

    Parameters
    ----------
    app : flask.app.Flask
    
    Returns
    -------
    dict : swagger dict
    """
    with app.test_client() as client:
        if app.extensions.get('restplus'):
            swagger_spec_url = next((str(x) for x in app.url_map.iter_rules() if
                                    str(x.endpoint).endswith("specs")), '/swagger.json')
        else:
            swagger_spec_url = app.config.get("APISPEC_SWAGGER_URL", "/swagger/")
        logging.info("Flask app swagger URL: %s", swagger_spec_url)
        return json.loads(client.get(swagger_spec_url).data)


def _get_fastapi_specs(app):
    """
    Function to return oas3 specs from fastapi app. Hopefully in the future it will be possible
    to 1) perform the OAS3 -> swagger2 conversion ourselves or 2) GCP will accept OAS specs and we
    won't have to modify this.

    Parameters
    ----------
    app : fastapi.applications.FastAPI
        FastAPI application
    
    Returns
    -------
    dict
        OpenAPI3-formatted Schema dict that we'll have to convert to swagger2
    """
    return app.openapi()


def _unsupported_app_type(app):
    raise NotImplementedError('Unsupported application type: ' + str(type(app)))


def _get_swagger_specs(app):
    """
    Convenient switch for all supported app types, presently just flask and fastapi

    We need to support python2 which can't use fastapi, so use names instead of type.
    """
    return {
        'Flask': _get_flask_specs,
        'FastAPI': _get_fastapi_specs
    }.get(app.__class__.__name__, _unsupported_app_type)(app)


def _create_template_from_app(app, template_output):
    logging.info("Generating OpenAPI template from Flask swagger specs")
    configs = get_dict_with_defaults()
    dict_merge(configs, _get_swagger_specs(app))
    clean_dict(configs)
    write_yaml_file(template_output, configs)
