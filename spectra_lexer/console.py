""" Contains useful types for introspection and/or interactive interpreter operations. """

from code import InteractiveConsole
import inspect
import sys


class xhelp:
    """ You asked for help on help, didn't you? Boredom has claimed yet another victim.
        This object overrides the builtin 'help', which breaks custom Python consoles. """

    _HELP_SECTIONS = [lambda x: [f"OBJECT - {x!r}"],
                      lambda x: [f"  TYPE - {type(x).__name__}"],
                      lambda x: ["-----------SIGNATURE------------",
                                 str(inspect.signature(x))],
                      lambda x: ["-------PUBLIC ATTRIBUTES--------",
                                 ', '.join([k for k in dir(x) if not k.startswith('_')]) or "None"],
                      lambda x: ["--------------INFO--------------",
                                 *map(str.lstrip, str(x.__doc__).splitlines())]]

    def __init__(self, file=sys.stdout) -> None:
        self._file = file

    def __call__(self, *args:object) -> None:
        """ Write lines from each help section that doesn't raise an exception, in order. """
        lines = [] if args else [repr(self)]
        for obj in args:
            lines.append("")
            for fn in self._HELP_SECTIONS:
                try:
                    lines += fn(obj)
                except Exception:
                    # Arbitrary objects may raise arbitrary exceptions. Just skip sections that don't behave.
                    continue
            lines.append("")
        self._file.write("\n".join(lines))

    def __repr__(self) -> str:
        return "Type help(object) for auto-generated help on any Python object."


class AttrRedirector:
    """ Context manager that temporarily overwrites a number of attributes on a target object, then restores them.
        Only works on objects with a __dict__. The usual case is redirecting streams and hooks from the sys module. """

    def __init__(self, target:object, **attrs) -> None:
        """ We usually have specific literal attributes to redirect, so **keywords are best. """
        self._params = vars(target), attrs

    def __exit__(self, *args) -> None:
        """ Switch the attributes on both dicts. This operation is symmetrical and works for __enter__ as well. """
        d, attrs = self._params
        for a in attrs:
            d[a], attrs[a] = attrs[a], d[a]

    __enter__ = __exit__


class SystemConsole:
    """ Component for interactive system interpreter operations. """

    def __init__(self, locals_ns:dict=None, file=sys.stdout, *, ps1=">>> ", ps2="... ") -> None:
        """ Override the interactive help() and write an opening message before input begins. """
        locals_ns = locals_ns or {}
        locals_ns["help"] = xhelp(file)
        self._interpreter = InteractiveConsole(locals_ns)                 # Interpreter to evaluate text input.
        self._redirector = AttrRedirector(sys, stdout=file, stderr=file)  # Writes output text (to stdout by default).
        self._ps1 = ps1  # Standard input prompt.
        self._ps2 = ps2  # Input prompt when more lines are needed.

    def send(self, text_in:str) -> None:
        """ When a new line is sent, push it to the interpreter and run it if it makes a complete statement.
            Redirect the standard output streams to our file during execution. """
        with self._redirector:
            try:
                is_more = self._interpreter.push(text_in)
            except KeyboardInterrupt:
                print("KeyboardInterrupt\n")
                is_more = False
            self._write_prompt(is_more)

    def _write_prompt(self, is_more=False) -> None:
        """ The prompt is not a full line, so the buffer must be flushed manually. """
        prompt = self._ps2 if is_more else self._ps1
        print(prompt, end="", flush=True)

    def print_opening(self) -> None:
        """ Print an opening message using the redirector. """
        with self._redirector:
            print("Spectra Console - Python " + sys.version)
            print("Type 'dir()' to see a list of application components and other globals.")
            self._write_prompt()
