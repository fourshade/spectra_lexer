from typing import Any, Dict, Hashable


class Engine(Dict[Hashable, list]):
    """
    Base component communications class for the Spectra program. Routes messages and data structures between
    the application, the GUI, and all other constituent components. Has mappings for every command to a list
    of registered functions along with where to send the return value. Since the command dictionary may not
    be mutated after creation and all execution state is kept within the call stack, multiple threads may
    run off the same engine object.
    """

    def call(self, key:Hashable, *args, is_top:bool=True, **kwargs) -> Any:
        """ Re-entrant method for engine calls. Checks exceptions with a custom handler. """
        try:
            value = None
            # Run all commands under this key (if any) and return the last value.
            for func, next_key, cmd_kwargs in (self.get(key) or []):
                value = func(*args, **kwargs)
                # If there's a follow-up command to run and the output value wasn't None, run it with that value.
                if value is not None and next_key is not None:
                    # Normal tuples (not subclasses) will be automatically unpacked into the next command.
                    next_args = value if type(value) is tuple else (value,)
                    self.call(next_key, *next_args, is_top=False, **cmd_kwargs)
            return value
        except Exception as e:
            # The caller may want to catch this exception, so don't catch it here unless this is the top level.
            if not is_top or not self.call("new_exception", e):
                raise
