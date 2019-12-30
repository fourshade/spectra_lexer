""" Contains useful types for introspection and/or interactive interpreter operations. """

import codeop
import inspect
import sys
import traceback


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

    ps1 = ">>> "  # Standard input prompt.
    ps2 = "... "  # Input prompt when more lines are needed.
    banner = "Spectra Console - Python " + sys.version + "\n" + \
             "Type 'dir()' to see a list of application components and other globals.\n"

    def __init__(self, namespace:dict=None, file=sys.stdout, *, show_banner=True) -> None:
        self._namespace = namespace or {}                                 # Globals namespace for exec().
        self._redirector = AttrRedirector(sys, stdout=file, stderr=file)  # Writes output text (to stdout by default).
        self._line_buffer = []                                            # Buffer for incomplete Python statements.
        # Override the interactive help() and print the opening message and prompt.
        self._namespace["help"] = xhelp(file)
        if show_banner:
            file.write(self.banner)
        file.write(self.ps1)
        file.flush()

    def send(self, text_in:str) -> None:
        """ When a new line is sent, push it to the interpreter and run it if it makes a complete statement.
            Redirect the standard output streams to our file during execution. """
        self._line_buffer.append(text_in)
        with self._redirector:
            if self._run_buffer():
                prompt = self.ps2
            else:
                prompt = self.ps1
                self._line_buffer = []
            # The prompt is not a full line, so the stream must be flushed manually.
            print(prompt, end="", flush=True)

    def _run_buffer(self) -> bool:
        """ Attempt to compile and run the buffer text as a Python source code string.
            Return True if the text makes an incomplete statement. """
        source = "\n".join(self._line_buffer)
        try:
            code = codeop.compile_command(source, "<console>")
        except (OverflowError, SyntaxError, ValueError) as exc:
            # The input is incorrect. There is no stack, so no traceback either.
            traceback.print_exception(type(exc), exc, None)
            return False
        if code is None:
            # The input is incomplete. Nothing happens (yet).
            return True
        try:
            # The input is complete. The code object is executed.
            exec(code, self._namespace)
        except SystemExit:
            raise
        except BaseException as exc:
            # We remove the first stack item because it is our own code.
            traceback.print_exception(type(exc), exc, exc.__traceback__.tb_next)
        return False

    def repl(self) -> None:
        """ Run a read-eval-print loop using standard input. """
        for line in iter(input, "exit"):
            self.send(line)
