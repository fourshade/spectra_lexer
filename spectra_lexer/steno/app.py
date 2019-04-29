""" Main module and entry point for batch operations on Spectra. """

from time import time

from spectra_lexer import system, steno
from spectra_lexer.core import Application, Component


class ResourceComponent(Component):
    """ Component that gathers steno resources. """

    system = resource("system", {})
    translations = resource("translations", {})
    index = resource("index", {})

    @on("batch_resource")
    def get_res(self, attr:str):
        return getattr(self, attr)


class StenoApplication(Application):
    """ Simple shell class for calling engine commands from the command line in batch . """

    DESCRIPTION = "run a command set directly from console."
    CLASS_PATHS = [system, ResourceComponent, steno.basic]
    COMMANDS: list = []
    RESOURCE: str = "translations"

    def run(self, *args) -> int:
        """ Start the timer and run the <COMMANDS> on <RESOURCE>. Each command feeds its output to the next one. """
        s_time = time()
        print(f"Operation started.")
        data = self.call("batch_resource", self.RESOURCE)
        for cmd in self.COMMANDS:
            data = self.call(cmd, data)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0


class StenoAnalyzeApplication(StenoApplication):
    DESCRIPTION = "run the lexer on every item in a JSON steno translations dictionary."
    COMMANDS = ["lexer_query_all", "rules_save"]


class StenoIndexApplication(StenoApplication):
    DESCRIPTION = "analyze a translations file and index each translation by the rules it uses."
    COMMANDS = ["lexer_make_index", "index_save"]
