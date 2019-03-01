"""
The Spectra program is conceptually divided into several parts that form a pipeline:

    File/input - The most basic operation of the lexer requires a set of rules that map steno keys to letters,
    and these must be loaded from disk. The first step on startup after connecting the components is for this
    module to load the configuration from user data and rules from the built-in assets directory.

    Search/input - Translations for the program to parse have to come from somewhere, and usually it's a JSON
    dictionary loaded from outside. The search component handles all search functionality and sends queries
    to the lexer any time a selection has narrowed down to a single entry.

    Plover/input - Translations and search dictionaries may also come from Plover when activated as a plugin.
    Strokes from Plover are handled independently of search results; the output window will display the last
    translation no matter where it came from.

    Lexer/processing - A translation consists of a series of strokes mapped to an English word, and it is
    the lexer's job to match pieces of each using a dictionary of rules it has loaded from storage. All rules
    handling is done by the lexer component, including parsing them into categories and matching them to pieces
    of translations. All results are handed off to the output component, which decides their fate.

    Graph/output - The lexer provides its output (usually a rule constructed from user input) to this component
    which puts it in its final form for the GUI to display as a text graph breakdown. After display, the mouse
    may be moved over the various rules to highlight them and show a more detailed description.

    Board/output - A steno board layout is also shown below the graph using information from the lexer output.
    Each stroke is shown separately, with certain rules shown as "compound" keys (such as `n` for -PB) in a
    different color. The board layout is updated to show individual rules when the mouse is moved over the graph.

    Engine - Glues all of these components together, handling communication between each one as well as passing
    information from one stage of the pipeline to the next. Facilitating communication is *all* it should do;
    any actual software functionality should be implemented in one of the component classes.

    GUI - As the frontend for accepting user input and displaying lexer output, the GUI is conceptually separate
    from any of the other components. It may run on a standalone framework, meaning we can't call its methods from
    anywhere except the main thread without going through an intermediary layer.
"""

from .base import Component, fork, on, pipe, respond_to
