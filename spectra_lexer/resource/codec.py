import json


def json_decode(data:bytes, **kwargs) -> dict:
    """ Decode a byte string to a dict (even if empty).
        JSON standard library functions are among the fastest ways to load structured data in Python. """
    return json.loads(data or b"{}", **kwargs)


def json_encode(d:dict, *, encoding:str='utf-8', **kwargs) -> bytes:
    """ Key sorting helps some parsing and search algorithms run faster.
        An explicit flag is required to preserve Unicode symbols. """
    kwargs = {"sort_keys": True, "ensure_ascii": False, **kwargs}
    return json.dumps(d, **kwargs).encode(encoding)


def cson_decode(data:bytes, comment_prefixes=frozenset(b"#/"), **kwargs) -> dict:
    """ Decode a JSON byte string with full-line standalone comments. """
    # JSON doesn't care about leading or trailing whitespace, so strip every line.
    stripped_line_iter = map(bytes.strip, data.splitlines())
    # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
    data_lines = [line for line in stripped_line_iter if line and line[0] not in comment_prefixes]
    return json.loads(b"\n".join(data_lines) or b"{}", **kwargs)


def cfg_decode(data:bytes, encoding:str='utf-8') -> dict:
    """ Decode CFG file contents into a nested dict.
        Parse lines of sectioned configuration data. Each section in a configuration file contains a header,
        indicated by a name in square brackets (`[]`), plus key/value options, indicated by `name = value`.
        Configuration files may include comments, prefixed by `#' or `;' in an otherwise empty line. """
    cfg = {}
    line_iter = data.decode(encoding).splitlines()
    cursect = None
    for line in line_iter:
        # strip full line comments
        line = line.strip()
        if line and line[0] not in '#;':
            # Parse as a section header: [ + header + ]
            if line[0] == "[" and line[-1] == "]":
                sectname = line[1:-1]
                cursect = cfg.setdefault(sectname, {})
            elif cursect is None:
                raise ValueError('No initial header in file.')
            # Parse as an option line: name + spaces/tabs + `=` delimiter + spaces/tabs + value
            elif "=" not in line:
                raise ValueError(f'Missing `=` for option in line: {line}.')
            else:
                optname, optval = line.split("=", 1)
                cursect[optname.rstrip()] = optval.lstrip()
    return cfg


def cfg_encode(cfg:dict, *, encoding:str='utf-8') -> bytes:
    """ Encode this dict into a config/INI formatted representation of the configuration state."""
    s_list = []
    for section in cfg:
        s_list += "\n[", section, "]\n"
        for key, value in cfg[section].items():
            if '\n' in key or '\n' in value:
                raise ValueError(f'Newline in option {key}: {value}')
            s_list += key, " = ", value, "\n"
    return "".join(s_list)[1:].encode(encoding)
