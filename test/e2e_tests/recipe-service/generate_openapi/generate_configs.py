"""
This module assists in the generation of env-specific OpenAPI formatted Swagger docs.
"""
import argparse
import copy
import os
import subprocess

import yaml
from util import clean_dict, dict_merge, load_yaml_file, write_yaml_file


def convert_oas3_to_swagger2(filename):
    """
    Function to convert OpenAPI3-formatted spec files to swagger2.

    Parameters
    ----------
    filename : str
        path to OAS3-formatted file

    Returns
    -------
    dict
        dictionary containing converted OAS3 -> swagger2 specs
    """
    template_loc = os.path.split('/'.join([os.getcwd(), filename]))
    run_converter_cmd = ['/usr/bin/docker', 'run', '-v', '{}:/tmp'.format(template_loc[0]),'--name',
        'converter', 'ioggstream/api-spec-converter', '--from', 'openapi_3', '--to', 'swagger_2',
        '-d', '--syntax', 'yaml', '--order', 'alpha', '/tmp/{}'.format(template_loc[1])]
    subprocess.check_call(run_converter_cmd)
    replace_oas3_cmd = ['docker', 'logs', 'converter']
    subprocess.check_call(replace_oas3_cmd, stdout=open(filename, 'w'))
    return load_yaml_file(filename)


def generate_yaml_confs(base_template_filename, overrides_filename, path_prefix=".",
                        merge_lists=False):
    """
    This function recursively merges two dictionaries.

    Parameters
    ----------
    base_template_filename: str
        Base OpenAPI template file we'll apply env-specific overrides to.
    overrides_filename : str
        Overrides file containing just the env-specific differences from the base.
    path_prefix : str
        If provided, the directory where we'll output the env-specific yaml files designed in the
        overrides file. If nothing is provided, they will be output in the current directory. Paths
        can be relative, ex: 'tmp_output' or absolute, ex: '/tmp/tmp_output'.
    merge_lists : bool
        If True, keys with list values will be combined together, If False (default), the override
        list will completely replace the original.

    Notes
    -----
    OAS3 -> swagger2 strips unrecognized root elements, notably GCP securityDefinitions. We could
    add all these keys back, but we risk including new things that were renamed as expected in the
    conversions (i.e. components -> definitions).
    So instead the approach here is to add back only certain keys. If in the future there are other
    root elements that go missing, add them to the put_back list (or switch to the other approach).
    These elements should be only stuff found in the override files.
    """
    configs = load_yaml_file(base_template_filename)
    # if configs are OpenAPI3 format, convert them
    if 'openapi' in configs:
        put_back = {}
        put_back_keys = ['securityDefinitions']
        for key in put_back_keys:
            put_back[key] = configs.get(key)
        configs = convert_oas3_to_swagger2(base_template_filename)
        configs.update(put_back)
        clean_dict(configs)
    with open(overrides_filename, "r") as cfg_f:
        for yaml_dict in list(yaml.safe_load_all(cfg_f)):
            temp = copy.deepcopy(configs)
            dict_merge(temp, yaml_dict, merge_lists)
            write_yaml_file('/'.join([path_prefix, temp.pop("filename")]), dict(temp.items()))


def main():
    parser = argparse.ArgumentParser(description="YAML file generation utility")
    parser.add_argument("-b", "--base", type=str, required=True,
                        help="base YAML filename to inherit from")
    parser.add_argument("-o", "--overrides", type=str, required=True,
                        help="template overrides file")
    parser.add_argument("-p", "--path", type=str,
                        help="output path for generated confs (default is pwd)", default=".")
    parser.add_argument("-m", "--merge-lists", action="store_true")
    args = parser.parse_args()
    generate_yaml_confs(args.base, args.overrides, args.path, args.merge_lists)


if __name__ == "__main__":
    main()
