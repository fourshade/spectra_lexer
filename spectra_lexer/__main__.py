#!/usr/bin/env python3

""" Master console script and primary entry point for the Spectra program. """

import sys

from spectra_lexer.util.entrypoints import EntryPoint, EntryPointSelector

ENTRY_POINTS = {
    "console": EntryPoint("spectra_lexer.main_console", "main", "Run commands interactively from console."),
    "discord": EntryPoint("spectra_lexer.main_discord", "main", "Run the experimental Discord bot."),
    "index":   EntryPoint("spectra_lexer.main_index",   "main", "Index a translations file by the rules it uses."),
    "http":    EntryPoint("spectra_lexer.main_http",    "main", "Run the application as an HTTP web server."),
    "gui":     EntryPoint("spectra_lexer.main_qt",      "main", "Run the standalone GUI application (default).")
}


def main() -> int:
    loader = EntryPointSelector(ENTRY_POINTS, default_mode="gui")
    return loader.main()


if __name__ == '__main__':
    sys.exit(main())
