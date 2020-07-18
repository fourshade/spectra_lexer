""" Package for the core components of Spectra. These are the building blocks of practically everything else:

    options - Anything using Spectra, including the built-in application objects, must start by calling the main
    factory method on the Spectra class with configuration options, which reside here.

    resource - The most basic lexer operations requires a set of rules that map steno keys to letters as well
    as a steno layout that tells it which keys are valid and where they are. These must be loaded from disk.
    Graphical displays may also require some outside information to tell what to render and where.
    The first step on startup is to load everything from the built-in assets directory.

    spectra - Contains the primary program components. Intended to be used directly by applications i.e. as a library.

        search - Translations for the program to parse have to come from somewhere, and usually it's a JSON
        dictionary loaded from outside. The search component handles all search functionality, including normal
        translation search, stroke search, regex search, and even search from a pre-analyzed index of rule examples.

        lexer - A translation consists of a series of strokes mapped to an English word,
        and it is the lexer's job to match pieces of each using a dictionary of rules it has loaded.
        There is also a facility for bulk processing of large numbers of translations in parallel.

        graph - The lexer output (usually a rule constructed from user input) may be sent to this component
        which puts it in string form for the GUI to display as a text graph breakdown. After display, the mouse
        may be moved over the various rules to highlight them and show a more detailed description.

        board - A steno board layout is also shown below the graph using information from the lexer output.
        Each stroke is shown separately, with certain rules shown as "compound" keys (such as `n` for -PB) in a
        different color. The board layout is updated to show more detail when the mouse is moved over the graph.

    gui - As the frontend, the GUI variants are conceptually separate from the other components. The GUI may run
    on a standalone framework with its own threads, meaning we can't directly call into the engine without locks.

    app - Contains the engine and handles user-level tasks such as configuration and GUI requests.

        qt - The primary desktop GUI uses PyQt. There are several useful debug tools available as well.

        plover - There is an entry point hook to allow Plover to load the Qt GUI as a plugin. Search dictionaries will
        come from Plover instead of disk in this mode, and strokes entered by the user will be caught and analyzed.
        Strokes from Plover are handled independently of manual search; the output window will display the last
        translation no matter where it came from.

        http - An HTML version of the GUI using AJAX is accessible by running an HTTP server. There is little
        in the way of performance or security, but it works well enough to run on a Raspberry Pi.

        console - The engine may be run on its own in a Python console. This is usually not terribly useful.

        index - Perform batch index generation directly from a terminal shell.

        discord - A bot for Discord that parses user queries into board diagrams. Requires a good search dictionary.

    __main__ - When spectra_lexer is run directly as a script, the first command-line argument will be used
    to choose one of the application entry points described above, defaulting to the Qt GUI. """

from spectra_lexer.options import SpectraOptions
from spectra_lexer.spectra import Spectra
