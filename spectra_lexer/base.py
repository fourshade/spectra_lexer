from __future__ import annotations

from typing import ClassVar, Dict, Hashable, List, NamedTuple

from spectra_lexer.utils import nop


class SpectraCommand(NamedTuple):
    func: callable  # Function or bound method to call.
    kwargs: dict    # Keyword arguments for either command or function.


def control_decorator(*dec_fields:str, **dec_kwargs) -> function:
    """ Create a new control decorator, with positional field names specified in dec_args
        and additional keyword arguments for the dispatcher in dec_kwargs. """
    def command_decorator(cmd_key:Hashable, *cmd_args, **cmd_kwargs) -> function:
        def base_decorator(func:function) -> function:
            args = list(cmd_args)
            kwargs = dict(cmd_kwargs)
            # Every listed field is a positional argument that must be in the command.
            assert len(args) == len(dec_fields), "Wrong number of positional arguments for this decorator."
            for field in dec_fields:
                kwargs[field] = args.pop()
            kwargs.update(dec_kwargs)
            # The final command has the key and the combined kwargs with NO leftover positionals.
            func.cmd = (cmd_key, kwargs)
            return func
        return base_decorator
    return command_decorator


class SpectraComponent:
    """
    Base class for any component that sends and receives commands from the Spectra engine.
    It is the root class of the Spectra lexer object hierarchy, being subclassed directly
    or indirectly by nearly every important (externally-visible) piece of the program.
    As such, it cannot depend on anything inside the package itself except pure utility functions.
    """

    _cmd_attr_list: ClassVar[List[tuple]] = []  # Default class command parameter list; meant to be copied.
    engine_call: callable = nop  # Default engine callback is a no-op (useful for testing individual components).
    engine_send: callable = nop  # Send an engine command with no expected response (may be async).

    def __init_subclass__(cls) -> None:
        """ Make a list of commands this component class handles with methods that handle each one.
            Each engine-callable method (callable class attribute) has its command info saved on attributes.
            Save each of these to a list, using the parent's command list as a starting point.
            Combine the lists to cover the full inheritance tree. Child class commands override parents. """
        cmd_list = cls._cmd_attr_list[:]
        cmd_list += [(attr, *func.cmd) for attr, func in cls.__dict__.items()
                     if callable(func) and hasattr(func, "cmd")]
        cls._cmd_attr_list = cmd_list

    def commands(self) -> Dict[Hashable, SpectraCommand]:
        """ Bind all class command functions to the instance and return the raw commands. """
        return {key: SpectraCommand(getattr(self, attr), *rest) for attr, key, *rest in self._cmd_attr_list}

    def set_engine_callbacks(self, cb_call:callable=nop, cb_send:callable=nop) -> None:
        """ Set the callbacks used for direct engine calls and async engine calls. """
        self.engine_call = cb_call
        self.engine_send = cb_send
