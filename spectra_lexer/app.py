""" Package for the core components of Spectra. These are the building blocks of practically everything else. """

from time import time
from typing import List

from spectra_lexer.steno import StenoEngine
from spectra_lexer.system import SystemLayer

from argparse import ArgumentParser, SUPPRESS


class CmdlineParser(ArgumentParser):
    """ Command line parser for the Spectra program. """

    # Extra keywords for argument parsing based on the option's data type.
    _TYPE_KWDS = {int:  {"type": int},
                  list: {"nargs": "+"}}

    def __init__(self, *options):
        """ Suppress defaults from unused arguments (resources have their own default settings). """
        super().__init__(argument_default=SUPPRESS)
        for opt_args in options:
            self.add_option(*opt_args)

    def add_option(self, key:str, default, desc:str="") -> None:
        """ All options handled here must be parsed as long options connected by hyphens. """
        key_suffix = key.rsplit("-", 1)[-1]
        kwds = {"help": desc, "metavar": key_suffix.upper()}
        tp = type(default)
        if tp in self._TYPE_KWDS:
            kwds.update(self._TYPE_KWDS[tp])
        self.add_argument(f"--{key}", **kwds)

    def parse(self) -> dict:
        """ The parser replaces hyphens with underscores, but our keys need the hyphens. """
        args = vars(self.parse_args())
        return {k.replace("_", "-"): args[k] for k in args}


class CmdlineOption:
    """ Class option settable by the command line. """

    _ALL_OPTIONS: dict = {}  # Contains all options declared by imported classes.

    _value: object  # Read-only value for the option.

    def __init__(self, key:str, default=None, desc:str=""):
        self._value = default
        self._ALL_OPTIONS[self] = key, default, desc

    def __get__(self, instance:object, owner:type=None):
        return self._value

    @classmethod
    def process_all(cls) -> None:
        """ Get parameter tuples from every declared option and process them.
            Update all options by setting the value attributes manually. """
        all_opts = cls._ALL_OPTIONS
        parser = CmdlineParser(*all_opts.values())
        parsed_opts = parser.parse()
        for opt, (key, default, desc) in all_opts.items():
            if key in parsed_opts:
                opt._value = parsed_opts[key]


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

    def __init__(self):
        """ Load command line options, assemble components, and run the application. """
        CmdlineOption.process_all()
        self.system = SystemLayer()
        self["app"] = self
        self["system"] = self.system
        self.steno = self["steno"] = StenoEngine(self.system)
        self.system.log_to(self.log_file)
        self.load()
        self.run()

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

    def exc_traceback(self, tb_text:str) -> None:
        self.system.log(f'EXCEPTION\n{tb_text}')

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
