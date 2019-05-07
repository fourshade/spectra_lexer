import pydoc


class _help(pydoc.Helper):
    """ Override for the builtin 'help', which will hang the console in interactive mode. """

    _SENTINEL = object()

    def __call__(self, request=_SENTINEL) -> None:
        if request is self._SENTINEL:
            self.output.write(f"{self!r}\n")
        elif request is None:
            self.output.write("Mu.\n")
        else:
            self.help(request)

    def __repr__(self):
        return "Type help(object) for help on any Python object."


class ConsoleTools:
    """ Contains additional objects to add to the console. Every non-dunder class-level object will end up there. """

    help = _help()
