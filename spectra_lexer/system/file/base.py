""" Module for encoding/decoding Python objects from various file formats. """

from typing import Any

from . import codec, path
from .path import Path


def load(filename:str, **kwargs) -> Any:
    """ Attempt to load and decode a single resource given by name. """
    return _read(path.from_string(filename), **kwargs)


def load_all(pattern:str, **kwargs) -> list:
    """ Attempt to expand a pattern and decode all files, returning a list. """
    return [_read(rs, **kwargs) for rs in path.from_string(pattern).search()]


def save(filename:str, obj:Any, **kwargs) -> None:
    """ Attempt to encode and save a resource to a file given by name. """
    _write(path.from_string(filename), obj, **kwargs)


def _read(rs:Path, *, ignore_missing:bool=False, **kwargs) -> Any:
    """ Read and decode a file resource. Missing files may return a default object instead of raising. """
    try:
        data = rs.read()
    except OSError:
        if not ignore_missing:
            raise
        data = None
    return codec.decode(data, rs, **kwargs)


def _write(rs:Path, obj:Any, **kwargs) -> None:
    """ Encode and save a file resource. """
    data = codec.encode(obj, rs, **kwargs)
    rs.write(data)
