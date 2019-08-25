""" Package for the core components of Spectra. These are the building blocks of practically everything else:

    File/input - The most basic lexer operations requires a set of rules that map steno keys to letters as well
    as a steno layout that tells it which keys are valid and where they are. These must be loaded from disk.
    The first step on startup is to load everything from the built-in assets directory.

    Search/input - Translations for the program to parse have to come from somewhere, and usually it's a JSON
    dictionary loaded from outside. The search component handles all search functionality, including normal
    translation search, stroke search, regex search, and even search from a pre-analyzed index of rule examples.

    Plover/input - Translations and search dictionaries may also come from Plover when activated as a plugin.
    Strokes from Plover are handled independently of manual search; the output window will display the last
    translation no matter where it came from.

    Lexer/processing - A translation consists of a series of strokes mapped to an English word, and it is
    the lexer's job to match pieces of each using a dictionary of rules it has loaded from storage. All rules
    handling is done by the lexer component, including parsing them into categories and matching them to pieces
    of translations. There is also a facility for bulk processing of large numbers of translations in batch mode.

    Graph/output - The lexer output (usually a rule constructed from user input) may be sent to this component
    which puts it in its final form for the GUI to display as a text graph breakdown. After display, the mouse
    may be moved over the various rules to highlight them and show a more detailed description.

    Board/output - A steno board layout is also shown below the graph using information from the lexer output.
    Each stroke is shown separately, with certain rules shown as "compound" keys (such as `n` for -PB) in a
    different color. The board layout is updated to show individual rules when the mouse is moved over the graph.

    View/processing - In order to accept input from the user and display output, there must be a general GUI
    controller that decides how to handle all interaction from the outside world. The view layer translates GUI
    actions into calls to other components, and updates the GUI state with any results.

    GUI - As the frontend, the GUI is conceptually separate from the other components. It may run on a standalone
    framework with its own thread, meaning we can't directly call other components without some intermediary.
    Its connection to the view layer involves a single object representing the "state" of the GUI. It is a simple
    data object; a copy is passed to the view, updated with changes, then passed back. The original object is then
    overwritten with any changes made to the copy. Using copies in this manner ensures thread safety.

    App - Glues all of these components together, handling communication and passing information between them.
    Facilitating communication is *all* it should do; all other functionality should be implemented in components. """

from .base import analyze, console, index, Spectra
