""" Package for the core components of Spectra. These are the building blocks of practically everything else. """

from time import time
from typing import List

from .cmdline import CmdlineOption, CmdlineParser
from .steno import StenoEngine
from .system import SystemLayer


class StenoApplication:
    """ Base application class with all required system and steno components. The starting point for program logic. """

    log_file: str = CmdlineOption("log-file", default="~/status.log",
                                  desc="Text file to log status and exceptions.")
    system_path: str = CmdlineOption("system-dir", default=":/assets/",
                                     desc="Directory with system resources")
    translation_files: List[str] = CmdlineOption("translations-files", default=[],
                                                 desc="JSON translation files to load on start.")
    index_file: str = CmdlineOption("index-file", default="~/index.json",
                                    desc="JSON index file to load on start and/or write to.")
    config_file: str = CmdlineOption("config-file", default="~/config.cfg",
                                     desc="CFG file with config settings to load at start and/or write to.")

    system: SystemLayer  # Logs system events to standard streams and/or files.
    steno: StenoEngine   # Primary runtime engine for steno operations such as parsing and graphics.

    def __init__(self, *argv:str):
        """ Load command line options, assemble components, and run the application. """
        self.parse_cmdline(*argv)
        self.system = SystemLayer()
        self["app"] = self
        self["system"] = self.system
        self.steno = self["steno"] = StenoEngine(self.system)
        self.system.log_to(self.log_file)
        self.load()
        self.run()

    def parse_cmdline(self, *argv):
        """ Command-line arguments *must* be passed by the caller; sys.argv is not safe here. """
        if argv:
            parser = CmdlineParser()
            parser.add_host(self)
            parser.parse(*argv)

    def load(self) -> None:
        """ Load every available asset into its resource attribute before startup. """
        self.status("Loading...")
        self.steno.RSSystemLoad(self.system_path)
        self.load_translations()
        self.steno.RSIndexLoad(self.index_file)
        self.steno.RSConfigLoad(self.config_file)
        self.status("Loading complete.")

    def load_translations(self) -> None:
        """ Search for translation dictionaries from Plover if no changes were made to the command line option. """
        files = self.translation_files or self.system.get_plover_files()
        self.steno.RSTranslationsLoad(*files)

    def repl(self, input_fn=input) -> None:
        """ Run an interactive read-eval-print loop. Only a SystemExit can break out of this. """
        console = self.system.open_console()
        while True:
            console(input_fn())

    def run(self) -> int:
        """ After everything else is ready, a primary task may be run. It may return an exit code to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        return 0

    def status(self, status:str) -> None:
        """ Log and print status messages (non-error) to stdout by default. """
        self.system.log(status)

    def __setitem__(self, key:str, value:object) -> None:
        """ Add an app component to be tracked by the system. """
        self.system[key] = value


class StenoConsoleApplication(StenoApplication):
    """ Runs interactive console operations. """

    def run(self) -> int:
        self.repl()
        return 0


class _StenoBatchApplication(StenoApplication):
    """ Runs large batch operations. """

    def run(self) -> int:
        """ Run a batch operation and time its execution. """
        start_time = time()
        print("Operation started...")
        self.operation()
        print(f"Operation done in {time() - start_time:.1f} seconds.")
        return 0

    def operation(self) -> None:
        raise NotImplementedError


class StenoAnalyzeApplication(_StenoBatchApplication):
    """ Runs the lexer on every item in a JSON steno translations dictionary. """

    rules_out: str = CmdlineOption("rules-out", default="./rules.json",
                                   desc="Output file name for lexer-generated rules.")

    def operation(self) -> None:
        rules = self.steno.LXAnalyzerMakeRules()
        self.steno.RSRulesSave(rules, self.rules_out)


class StenoIndexApplication(_StenoBatchApplication):
    """ Analyzes translations files and creates indices from them. """

    def operation(self) -> None:
        index = self.steno.LXAnalyzerMakeIndex()
        self.steno.RSIndexSave(index)


console = StenoConsoleApplication
analyze = StenoAnalyzeApplication
index = StenoIndexApplication
