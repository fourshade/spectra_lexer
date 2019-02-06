""" Contains decorators for component engine command flow. """

from functools import partial
from typing import Any, Hashable, Mapping


def control_decorator(dispatch_fn:callable, **dec_kwargs) -> callable:
    """ Create a new control decorator, with additional arguments for the dispatcher in dec_kwargs. """
    def command_decorator(cmd_key:Hashable, *cmd_args, **cmd_kwargs) -> callable:
        def base_decorator(func:callable) -> callable:
            func.cmd = (cmd_key, partial(dispatch_fn, *cmd_args, **dec_kwargs, **cmd_kwargs) if dispatch_fn else None)
            return func
        return base_decorator
    return command_decorator


def dispatch(next_key:Hashable, value:Any, unpack:bool=False, **cmd_kwargs) -> tuple:
    """ If a command is marked to pipe its output <value> to another command (and it isn't None), add the new
        command to the <stack>. If <unpack>ed, the correct form of unpacking is applied based on its type. """
    if not unpack:
        value = (value,)
    elif isinstance(value, Mapping):
        cmd_kwargs.update(value)
        value = ()
    return next_key, value, cmd_kwargs
