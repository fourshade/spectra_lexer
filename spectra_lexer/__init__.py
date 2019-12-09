""" Package for the core components of Spectra. These are the building blocks of practically everything else:

    resource - The most basic lexer operations requires a set of rules that map steno keys to letters as well
    as a steno layout that tells it which keys are valid and where they are. These must be loaded from disk.
    Graphical displays may also require some outside information to tell what to render and where.
    The first step on startup is to load everything from the built-in assets directory.

    engine - Glues all primary components together, handling communication and passing information between them.
    The engine layer is intended to be called directly by applications i.e. as a library.

        search - Translations for the program to parse have to come from somewhere, and usually it's a JSON
        dictionary loaded from outside. The search component handles all search functionality, including normal
        translation search, stroke search, regex search, and even search from a pre-analyzed index of rule examples.

        analysis - Handles tasks relates to the lexer, such as parsing rules into categories, converting key formats,
        and running queries. There is also a facility for bulk processing of large numbers of translations in parallel.

            lexer - A translation consists of a series of strokes mapped to an English word, and it is the lexer's job
            to match pieces of each using a dictionary of rules it has loaded.

        display - Generates all graphical output. This is the most demanding job in the program. Steno rules may
        be parsed into a tree of nodes, each of which may have information that can be displayed in several forms.
        All information for a single node is combined into a display "page", which may be loaded into the GUI.
        All display pages for to a single rule or lexer query are further stored in a single data object.
        This allows for fewer requests in HTTP mode and more opportunities for caching.

            graph - The lexer output (usually a rule constructed from user input) may be sent to this component
            which puts it in string form for the GUI to display as a text graph breakdown. After display, the mouse
            may be moved over the various rules to highlight them and show a more detailed description.

            board - A steno board layout is also shown below the graph using information from the lexer output.
            Each stroke is shown separately, with certain rules shown as "compound" keys (such as `n` for -PB) in a
            different color. The board layout is updated to show more detail when the mouse is moved over the graph.

    app - Contains the engine and handles user-level tasks such as configuration and GUI requests.
    Facilitating communication is *all* it should do; other functionality should be implemented in its components.

    gui - As the frontend, the GUI variants are conceptually separate from the other components. The GUI may run
    on a standalone framework with its own threads, meaning we can't directly call into the engine without locks.
    Most interaction with the rest of the app involves a single object representing the "state" of the GUI.
    It is a simple data object which is passed to the app, updated with changes, then passed back.

        qt - The primary desktop GUI uses PyQt. There are several useful debug tools available as well.

        plover - There is an entry point hook to allow Plover to load the Qt GUI as a plugin. Search dictionaries will
        come from Plover instead of disk in this mode, and strokes entered by the user will be caught and analyzed.
        Strokes from Plover are handled independently of manual search; the output window will display the last
        translation no matter where it came from.

        http - An HTML version of the GUI using AJAX is accessible by running an HTTP server. There is little
        in the way of performance or security, but it works well enough to run on a Raspberry Pi.

        none - The engine may be run on its own in a Python console. This is usually not terribly useful, but it does
        allow for batch operations such as example index generation directly from a terminal shell.

    base - Anything using Spectra, including the built-in application objects, must start by calling one of the main
    factory methods on the Spectra class. All entry points to the program descend from this in some manner. """
