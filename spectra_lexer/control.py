""" Contains decorators for component engine command flow. """
from typing import Any, Hashable, Mapping

from spectra_lexer.utils import nop


def control_decorator(dispatch_fn:callable, **dec_kwargs) -> callable:
    """ Create a new control decorator, with additional arguments for the dispatcher in dec_kwargs. """
    def command_decorator(cmd_key:Hashable, *cmd_args, **cmd_kwargs) -> callable:
        def base_decorator(func:callable) -> callable:
            func.cmd = (cmd_key, lambda s, v: dispatch_fn(s, v, *cmd_args, **dec_kwargs, **cmd_kwargs))
            return func
        return base_decorator
    return command_decorator


on = control_decorator(nop)                      # Most basic decorator: do nothing after the command is called.
respond_to = control_decorator(lambda *args, **kwargs: True)  # Call the command and return its value to caller.


def _dispatch(stack:list, value:Any, *next_keys:Hashable, ret:bool=False, unpack:bool=False, **cmd_kwargs) -> bool:
    """ If a command is marked to pipe its output to another command (and it isn't None), add that command
        to the stack. Return True if that last command must (also) return the output to its caller.
        If the return value is unpacked, the correct star unpacking operator is chosen based on its type. """
    if value is not None:
        if unpack:
            if isinstance(value, Mapping):
                arg_tuple = ((), {**value, **cmd_kwargs})
            else:
                arg_tuple = (value, cmd_kwargs)
        else:
            arg_tuple = ((value,), cmd_kwargs)
        stack += [(cmd, *arg_tuple) for cmd in next_keys]
    return ret


pipe = control_decorator(_dispatch)             # Call the command and pipe its return value to another command.
fork = control_decorator(_dispatch, ret=True)   # Combination of @pipe and @respond_to.
