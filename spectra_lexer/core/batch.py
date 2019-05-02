from time import time

from spectra_lexer import Component


class BatchExecutor(Component):
    """ Component to run and time operations in batch mode. """

    @on("batch_run", pipe_to="batch_result")
    def run(self, data, command):
        """ Start the timer and run the <command> string on <data>.
            Commands are separated by a pipe character. Each one feeds its output to the next one. """
        s_time = time()
        print(f"Operation started.")
        for cmd in command.split("|"):
            data = self.engine_call(cmd.strip(), data)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return data
