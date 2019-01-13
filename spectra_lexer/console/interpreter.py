from code import InteractiveConsole
from io import StringIO, TextIOBase
import sys
from threading import Condition, Thread

# How long to wait on the interpreter (in seconds) before giving up.
COMMAND_TIMEOUT = 1.0


class InterpreterConsole(TextIOBase):
    """ A hacky object meant to run an interactive interpreter inside the main Spectra program.
        It runs on a separate thread with a reference to the engine object.
        It is unknown whether or not this object can execute engine commands thread safely. """

    _sys_streams: dict      # Dict of the original system standard stream handles.
    _out_stream: StringIO   # Output stream; takes the place of both stdout and stderr.
    _input_line: str = ""   # Holds the last input line sent by the main program.
    _condition: Condition   # Wakes the interpreter thread only when new input is available.

    def __init__(self, **kwargs):
        """ Save the standard stream handles so they can be overridden during interpreter activity.
            This object itself overrides stdin, blocking until other threads provide input. """
        self._sys_streams = {a: getattr(sys, a) for a in ("stdin", "stdout", "stderr")}
        self._out_stream = StringIO()
        self._condition = Condition()
        self._override_streams()
        # Create the interpreter shell and start it in a separate thread.
        console = InteractiveConsole(**kwargs)
        Thread(target=console.interact, daemon=True).start()

    def _override_streams(self) -> None:
        """ Temporarily replace standard stream handles with our objects. """
        sys.stdin = self
        sys.stdout = sys.stderr = self._out_stream

    def _restore_streams(self) -> None:
        """ Restore standard streams to their original handles. """
        sys.__dict__.update(self._sys_streams)

    def read(self, size:int=-1) -> str:
        """ The interpreter is attempting to read more input, but we don't have any more.
            Go to sleep and wait for other threads to notify after providing more input. """
        self._restore_streams()
        with self._condition:
            self._condition.notify()
            self._condition.wait()
        self._override_streams()
        return self._input_line

    # We only provide one full line at a time, so all read operations are the same.
    readline = read

    def run(self, line:str=None) -> str:
        """ Provide a new line of input, notify the interpreter to continue, wait for the output, and return it.
            If <line> is None, attempt to read the current output without waking the interpreter thread. """
        if line is not None:
            # Save the input text and echo it to output for a little sanity.
            self._input_line = line
            self._out_stream.write(line + '\n')
            # Wait for the interpreter thread to process the text, with a timeout to avoid hanging.
            with self._condition:
                self._condition.notify()
                if not self._condition.wait(timeout=COMMAND_TIMEOUT):
                    return "Now you've done it...\n" \
                           "We've lost the interpreter thread.\n\n" \
                           "How could you trust a Python\n" \
                           "running loose inside your system???"
        # Read the entire output buffer, containing every line of output since starting.
        self._out_stream.seek(0)
        return self._out_stream.read()
