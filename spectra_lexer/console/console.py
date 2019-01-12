
from code import InteractiveConsole
from io import StringIO
import sys
from threading import Condition, Thread

# How long to wait on the interpreter (in seconds) before giving up.
COMMAND_TIMEOUT = 1.0


class StreamDirector(StringIO):
    """ Redirects interpreter I/O (including that from exec()) to this StringIO object on demand. """

    _obj: object
    _streams: dict

    def __init__(self, *attrs:str, stream_obj=sys):
        """ Store copies of the original stream objects on initialization. """
        super().__init__()
        self._obj = stream_obj
        self._streams = {a: getattr(stream_obj, a) for a in attrs}

    def read_all(self) -> str:
        """ Read the entire contents of the buffer. """
        self.seek(0)
        return self.read()

    def restore(self):
        """ Restore streams to their original handles. """
        for (a, s) in self._streams.items():
            setattr(self._obj, a, s)

    def override(self):
        """ Temporarily replace streams with this buffer. """
        for a in self._streams:
            setattr(self._obj, a, self)

    def write_seek(self, s:str):
        """ Write a string and reset the pointer to the beginning of it. """
        oldpos = self.tell()
        self.write(s)
        self.seek(oldpos)


class InterpreterConsole(InteractiveConsole):

    condition: Condition
    in_stream: StreamDirector
    out_stream: StreamDirector

    def __init__(self, **kwargs):
        """ Create the interpreter shell and start it in a separate thread.
            Save the standard streams so they can be restored after interpreter activity. """
        super().__init__(**kwargs)
        self.condition = Condition()
        self.in_stream = StreamDirector("stdin")
        self.out_stream = StreamDirector("stdout", "stderr")
        self.in_stream.override()
        self.out_stream.override()
        Thread(target=self.interact, daemon=True).start()

    def raw_input(self, prompt="") -> str:
        """ Reaching this point means the console is done with the last input, so wait for more.
            Outside threads will notify after grabbing the input and providing more output. """
        self.write(prompt)
        self.out_stream.restore()
        self.in_stream.restore()
        with self.condition:
            self.condition.notify()
            self.condition.wait()
        self.in_stream.override()
        self.out_stream.override()
        val = self.in_stream.read()
        return val

    def run_command(self, command:str=None) -> str:
        """ Provide some input, notify the interpreter to continue, wait for the output, and return it.
            If command is None, attempt to read the current output without entering a command. """
        if command is not None:
            # Echo the command in the output for a little sanity.
            self.out_stream.write(command + '\n')
            # Write the command to input and reset the pointer so it can be read back.
            self.in_stream.write_seek(command)
            # Wait for the interpreter thread to process the command, with a timeout to avoid hanging.
            with self.condition:
                self.condition.notify()
                if not self.condition.wait(timeout=COMMAND_TIMEOUT):
                    return "Now you've done it...\n" \
                           "We've lost the interpreter thread.\n\n" \
                           "How could you trust a Python\n" \
                           "running loose inside your system???"
        # Read the entire output buffer, containing every line of output since starting.
        return self.out_stream.read_all()


