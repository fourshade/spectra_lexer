from code import InteractiveConsole
from io import StringIO, TextIOBase
import sys
from threading import Condition, Thread
from typing import Callable

# Banner containing the Python version after formatting once, and the locals dict after formatting twice.
_BANNER_FORMAT = f"Python {sys.version}\nSPECTRA DEBUG CONSOLE - Current global objects and options:\n{{}}"


class ConsoleIO(TextIOBase):
    """ Controls all input/output streams necessary for interpreter operation. """

    _return_fn: Callable[[str], str]  # Callback to return control on read.
    _sys_streams: dict                # Dict of the original system standard stream handles.
    _out: StringIO                    # Output stream; takes the place of both stdout and stderr.

    def __init__(self, return_fn:Callable[[str],str]):
        """ Save the standard stream handles so they can be overridden during interpreter activity.
            This object itself overrides stdin, blocking until other threads provide input. """
        self._return_fn = return_fn
        self._sys_streams = {a: getattr(sys, a) for a in ("stdin", "stdout", "stderr")}
        self._out = StringIO()
        self._override_streams()

    def _override_streams(self) -> None:
        """ Temporarily replace standard stream handles with our objects. """
        sys.stdin = self
        sys.stdout = sys.stderr = self._out

    def _restore_streams(self) -> None:
        """ Restore standard streams to their original handles. """
        sys.__dict__.update(self._sys_streams)

    def read(self, size:int=-1) -> str:
        """ Put the streams back to normal, send the output, and wait until more input is given. """
        self._restore_streams()
        self._out.seek(0)
        output = self._out.read()
        line = self._return_fn(output)
        # Echo the input text to output for a little sanity.
        self._out.write(line)
        self._override_streams()
        return line

    # We only provide one full line at a time, so both read operations are the same.
    readline = read


class InterpreterThread(Thread):

    _condition: Condition  # Switches between the main thread and the interpreter thread.

    def __init__(self, *args, **kwargs):
        """ Create the mutex and initialize the thread as a daemon (so it dies when the main program does). """
        self._condition = Condition()
        super().__init__(*args, daemon=True, **kwargs)

    def switch(self) -> None:
        """ Using the mutex, switch between the active and inactive thread. """
        with self._condition:
            self._condition.notify()
            self._condition.wait()


class InterpreterConsole(InteractiveConsole):
    """ A hacky object meant to run an interactive interpreter console inside the main Spectra program. """

    _io: ConsoleIO              # Handles all standard stream functionality.
    _thread: InterpreterThread  # A separate thread to run the console indefinitely.
    _input: str = ""            # Holds the last input lines sent by the main program.
    _output: str = ""           # Holds the last output buffer contents.
    _code = None                # Holds the next code object ready to execute.

    def __init__(self, cvars:dict):
        """ Create the stream handler and vars dict and start the interpreter in a separate thread. """
        super().__init__(cvars)
        self._io = ConsoleIO(self.complete)
        banner = _BANNER_FORMAT.format(list(cvars))
        self._thread = InterpreterThread(target=self.interact, args=(banner,))
        self._thread.start()

    def send(self, lines_in:str=None) -> str:
        """ Provide a new line of input, notify the interpreter to continue, wait for the output, and return it.
            If <line> is None, attempt to read the current output without waking the interpreter thread. """
        if lines_in is not None:
            # Save the input text and wait for the interpreter thread to process it.
            self._input = lines_in
            self._thread.switch()
            # Execute the code object (if any) on the main thread.
            if self._code is not None:
                super().runcode(self._code)
                self._code = None
                self._thread.switch()
        # The output buffer contains every line of output since starting.
        return self._output

    def complete(self, lines_out:str) -> str:
        """ The interpreter is done and asking for more input, but we don't have any more.
            Switch to the main thread for more input. """
        self._output = lines_out
        self._thread.switch()
        return self._input

    def runcode(self, code) -> None:
        """ Run the current code object on the main thread (so that Qt objects are accessible). """
        self._code = code
        self._thread.switch()
