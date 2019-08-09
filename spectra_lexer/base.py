from typing import List

from spectra_lexer.cmdline import CmdlineOption, CmdlineParser
from spectra_lexer.steno import StenoEngine
from spectra_lexer.system import SystemLayer


class StenoApplication:
    """ Base application class with all required system and steno components. The starting point for program logic. """

    log_file: str = CmdlineOption("log-file", default="~/status.log",
                                  desc="Text file to log status and exceptions.")
    resource_path: str = CmdlineOption("resource-dir", default=":/assets/",
                                       desc="Directory with static steno resources")
    translation_files: List[str] = CmdlineOption("translations-files", default=["~PLOVER/plover.cfg"],
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
        self.load()

    def parse_cmdline(self, *argv):
        """ Command-line arguments *must* be passed by the caller; sys.argv is not safe here. """
        if argv:
            parser = CmdlineParser()
            parser.add_host(self)
            parser.parse(*argv)

    def load(self) -> None:
        """ Load every available asset into its resource attribute before startup. """
        self.system.log_to(self.log_file)
        self.status("Loading...")
        self.steno.RSResourcesLoad(self.resource_path)
        self.steno.RSTranslationsLoad(*self.translation_files)
        self.steno.RSIndexLoad(self.index_file)
        self.steno.RSConfigLoad(self.config_file)
        self.status("Loading complete.")

    def repl(self) -> None:
        """ Run an interactive read-eval-print loop indefinitely. """
        self.system.repl()

    def status(self, status:str) -> None:
        """ Log and print status messages (non-error) to stdout by default. """
        self.system.log(status)

    def __setitem__(self, key:str, value:object) -> None:
        """ Add an app component to be tracked by the system. """
        self.system[key] = value
