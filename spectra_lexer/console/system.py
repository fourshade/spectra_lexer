""" Base module for interactive system interpreter operations. """

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
        self._file = file  # Output text stream (stdout by default).

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


class SourceInterpreter:
    """ Interprets and executes Python source strings. """

    def __init__(self, namespace:dict=None, filename="<console>", excepthook=None) -> None:
        self._namespace = namespace or {}  # Globals namespace dict for exec().
        self._filename = filename          # String shown in exceptions as the file name.
        self._excepthook = excepthook      # Optional 3-arg callable to handle exceptions instead of propagating them.

    def run(self, source:str) -> bool:
        """ Attempt to compile and run a Python <source> code string.
            Return True if the source makes an incomplete statement. """
        try:
            code = codeop.compile_command(source, self._filename)
            if code is None:
                # The input is incomplete. Nothing is executed.
                return True
            # The input is complete. The code object is executed.
            self._exec(code)
        except (OverflowError, SyntaxError, ValueError) as exc:
            # The input is incorrect. There is no stack, so no traceback either.
            exc.__traceback__ = None
            self._handle_exception(exc)
        return False

    def _exec(self, code) -> None:
        """ Execute a <code> object in our namespace. """
        try:
            exec(code, self._namespace)
        except SystemExit:
            raise
        except BaseException as exc:
            # We remove the first stack item from the traceback because it is our own code.
            exc.__traceback__ = exc.__traceback__.tb_next
            self._handle_exception(exc)

    def _handle_exception(self, exc:BaseException) -> None:
        """ If there is an exception hook, call it and swallow the exception. """
        if self._excepthook is None:
            raise exc
        self._excepthook(type(exc), exc, exc.__traceback__)


class PromptWriter:
    """ Writes interactive console prompts to a text stream. """

    def __init__(self, file=sys.stdout, *, ps1=">>> ", ps2="... ") -> None:
        self._file = file  # Output text stream (stdout by default).
        self._ps1 = ps1    # Normal interpreter input prompt.
        self._ps2 = ps2    # Input prompt when more lines are needed.

    def write(self, need_more=False) -> None:
        """ Write one of two prompt strings depending on if we <need_more> code to complete a statement.
            A prompt is not a full line, so the stream must be flushed manually after write. """
        prompt = self._ps2 if need_more else self._ps1
        self._file.write(prompt)
        self._file.flush()


class SystemConsole:
    """ Component for interactive system interpreter operations. """

    # Default opening message (trailing newline required).
    DEFAULT_BANNER = f"Spectra Console - Python {sys.version}\n"

    def __init__(self, interpreter:SourceInterpreter, redirector:AttrRedirector, prompts:PromptWriter) -> None:
        self._interpreter = interpreter  # Executes Python source.
        self._redirector = redirector    # Redirects console output from standard streams.
        self._prompts = prompts          # Prints Python interpreter prompt strings.
        self._line_buffer = []           # Buffer for incomplete Python statements.

    def send(self, line:str) -> None:
        """ When a new line is sent, push it to the interpreter and run it if it makes a complete statement. """
        self._line_buffer.append(line)
        source = "\n".join(self._line_buffer)
        need_more = self._run(source)
        if not need_more:
            self._line_buffer = []
        self._prompts.write(need_more)

    def _run(self, source:str) -> bool:
        """ Redirect the standard output streams to our file during execution of a Python <source> string. """
        with self._redirector:
            return self._interpreter.run(source)

    def repl(self) -> None:
        """ Run a read-eval-print loop using standard input. """
        for line in iter(input, "exit"):
            self.send(line)

    @classmethod
    def open(cls, namespace:dict=None, file=sys.stdout, *, banner=DEFAULT_BANNER, **kwargs) -> "SystemConsole":
        """ Make a new console, override the interactive help(), and print an opening message and prompt. """
        if namespace is None:
            namespace = {}
        namespace.setdefault("help", xhelp(file))
        interpreter = SourceInterpreter(namespace, excepthook=traceback.print_exception)
        redirector = AttrRedirector(sys, stdout=file, stderr=file)
        prompts = PromptWriter(file, **kwargs)
        if banner is not None:
            file.write(banner)
        prompts.write()
        return cls(interpreter, redirector, prompts)
