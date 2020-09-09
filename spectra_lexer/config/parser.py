import ast
from typing import Any

from .io import ConfigStrDict
from .spec import ConfigDict, ConfigSpec


def eval_str(s:str) -> Any:
    """ Try to evaluate a string as a Python literal. This fixes crap like bool('False') = True.
        Strings that are not valid Python literals are returned as-is. """
    try:
        return ast.literal_eval(s)
    except (SyntaxError, ValueError):
        return s


def nested_copy(d:dict) -> dict:
    """ Copy a two-level nested dictionary. """
    return {k: {**v} for k, v in d.items()}


def parse_opts(spec:ConfigSpec, d:ConfigStrDict=None) -> ConfigDict:
    """ Parse strings from a raw config dictionary into the types required by <spec>.
        Options in <d> but not in <spec> are left alone.
        Options in <spec> but not in <d> are set to default values. """
    options = nested_copy(d) if d is not None else {}
    for sect in spec:
        sect_name = sect.name
        if sect_name not in options:
            options[sect_name] = {}
        page = options[sect_name]
        for opt in sect.options:
            opt_name = opt.name
            if opt_name not in page:
                v = opt.default
            else:
                v = eval_str(page[opt_name])
            page[opt_name] = v
    return options


def unparse_opts(spec:ConfigSpec, options:ConfigDict) -> ConfigStrDict:
    """ Parse values from a normal config dictionary back into string form using <spec>. """
    d = nested_copy(options)
    for sect in spec:
        page = d[sect.name]
        for opt in sect.options:
            opt_name = opt.name
            obj = page[opt_name]
            page[opt_name] = str(obj)
    return d
