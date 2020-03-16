import logging
import os

import yaml

# support python2 & 3
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping


def dict_merge(dct, merge_dct, merge_lists=False):
    """
    This function recursively merges two dictionaries.
    It handles nested dicts, updating and adding anything merge_dct contains without wiping what was
    in dct.
    The point to watch for is list merging, particularly when merging lists of dictionaries. Since
    these dict elements are not hashable the way a string key is, we have to handle them
    differently. The default behavior is to replace the dct list with the list in merge_dct, but
    passing the merge_lists flag will result in the lists under a shared key to be combined instead.
    Note: even if we made a hashable dict class (easy enought), obviously updating one key/value
    would result in a new hash. This would make the behavior of this function more complicated; I
    think it's better not to try to be too smart here.

    Parameters
    ----------
    dct: dict
        The dict that will be modified after merging in merge_dct
    merge_dct : dict
        This dict will be merged into dct.
    merge_lists : boolean
        If true, keys with type(list) values will be merged together. This behavior is disabled by
        default.
    """
    for key, val in merge_dct.items():
        if (key in dct and isinstance(dct[key], dict) and isinstance(merge_dct[key], Mapping)):
            dict_merge(dct[key], merge_dct[key])
        elif isinstance(val, list) and merge_lists:
            dct[key] = dct.get(key, []) + val
        else:
            dct[key] = merge_dct[key]


def load_yaml_file(filename):
    """
    Parameters
    ----------
    filename : str

    Returns
    -------
    dict
        dict created from loading 'filename' file.
    """
    with open(filename, "r") as my_file:
        return dict(**yaml.safe_load(my_file))


def write_yaml_file(filename, swagger_dict):
    """
    Writes swagger_dict dictionary to file specified by filename parameter

    Parameters
    ----------
    filename : str
        filename to write dict values to
    swagger_dict : dict
        dictionaty to be serialized.
    """
    yaml.emitter.Emitter.process_tag = lambda *args: None
    with open(filename, "w") as outfile:
        yaml.dump(dict(sorted(swagger_dict.items())), outfile, default_flow_style=False)
    os.chmod(filename, 0o766)


def get_dict_with_defaults():
    """
    Returns
    -------
    dict
        dictionary of values pulled from defaults.yaml
    """
    default_path = "/".join([os.path.dirname(os.path.realpath(__file__)), "defaults.yaml"])
    return load_yaml_file(default_path)


def clean_dict(template_dict):
    """
    Driver function to 'clean' the template dictionary and make it compatible with GCP's required
    format.

    Parameters
    ----------
    template_dict : dict
        Generated template dictionaty. All steps will modify it in place.
    """
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
    Some tooling may not generate default operationIds which are required by the OpenAPI spec.
    In case we do not set defaults in the apps, add operationIds where necessary.
    Additionally, sometimes duplicate operationIds can be generated, which will be rejected by
    OpenAPI spec standards.
    """
    already_used = {}
    for key, _ in template_dict.get("paths", {}).items():
        for op, _ in template_dict["paths"][key].items():
            current = template_dict["paths"][key][op]
            if isinstance(current, dict):
                if "operationId" not in current:
                    operationId = "{}_{}".format(op, key.split("/")[-1])
                    logging.warning("Generating operationId: {} for path: {} operation: {}".format(
                        operationId, key, op))
                    template_dict["paths"][key][op]["operationId"] = operationId
                curr_id = template_dict["paths"][key][op]["operationId"]
                if curr_id not in already_used:
                    already_used[curr_id] = 1
                else:
                    already_used[curr_id] += 1
                    new_id = curr_id + str(already_used[curr_id])
                    logging.warning("Operation '{}' exists, renaming to '{}' for '{}', op '{}'".format(
                            curr_id, new_id, key, op))
                    template_dict["paths"][key][op]["operationId"] = new_id


def _handle_body_arrays(template_dict):
    """
    Though valid by OpenAPI specs, google's spec validoator does not allow top-level arrays in
    request bodies. To get around this, we can camouflage that array and it works just fine.

    Notes
    -----
    this is hacky and probably won't work forever.
    """
    for key, _ in template_dict.get("paths", {}).items():
        for op, _ in template_dict["paths"][key].items():
            if op not in ["get", "post", "put", "patch", "delete"]:
                continue
            for param in template_dict["paths"][key][op].get("parameters", []):
                schema = param.get("schema", None)
                if schema and schema.get("type", None) == "array":
                    param["schema"]["items"].update({"type": param["schema"].pop("type")})
