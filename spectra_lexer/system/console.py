from code import InteractiveConsole
from io import StringIO
from threading import Condition, Thread


class InterpreterConsole(InteractiveConsole):

    condition: Condition
    in_buffer: str = ""
    out_buffer: StringIO

    def __init__(self, **kwargs):
        """ Create the interpreter shell and start it in a separate thread. """
        super().__init__(**kwargs)
        self.out_buffer = StringIO()
        self.condition = Condition()
        Thread(target=self.interact, daemon=True).start()

    def read(self):
        """ Read the entire output buffer. Used by the application. """
        self.out_buffer.seek(0)
        return self.out_buffer.read()

    def write(self, data):
        """ Write a string to the output buffer. Used by the console. """
        self.out_buffer.write(data)

    def raw_input(self, prompt="") -> str:
        """ Reaching this point means the console is done with the last input, so wait for more.
            Outside threads will notify after grabbing the input and providing more output. """
        self.write(prompt)
        with self.condition:
            self.condition.notify()
            self.condition.wait()
        return self.in_buffer

    def runcode(self, code):
        """ Run the code object, then print the result's representation. Used by the console. """
        super().runcode(code)
        try:
            self.write(repr(self.locals["__builtins__"]["_"]) + "\n")
        except KeyError:
            pass

    def run_command(self, command:str=None) -> str:
        """ Provide some input, notify the interpreter to continue, wait for the output, and return it. """
        # Echo the command in the output for a little sanity.
        self.in_buffer = command
        self.write(command + '\n')
        with self.condition:
            self.condition.notify()
            self.condition.wait()
        return self.read()
