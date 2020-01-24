#!/usr/bin/env python3

""" Master console script and primary entry point for the Spectra program. """

import sys

from spectra_lexer.util.cmdline import EntryPoint, EntryPointSelector


ENTRY_POINTS = {
    "console": EntryPoint("spectra_lexer.gui_none", "console_main", "Run commands interactively from console."),
    "index":   EntryPoint("spectra_lexer.gui_none", "index_main",   "Index a translations file by the rules it uses."),
    "http":    EntryPoint("spectra_lexer.gui_http", "http_main",    "Run the application as an HTTP web server."),
    "gui":     EntryPoint("spectra_lexer.gui_qt",   "gui_main",     "Run the standalone GUI application (default).")
}
MAIN_LOADER = EntryPointSelector(ENTRY_POINTS, default_mode="gui")


if __name__ == '__main__':
    sys.exit(MAIN_LOADER.main())
