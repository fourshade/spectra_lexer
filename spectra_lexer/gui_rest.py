from threading import Lock
from typing import Iterable

from spectra_lexer.gui_engine import DisplayData, GUIEngine, GUIOptions, SearchResults


class RESTUpdate:
    """ Data class that contains an entire REST GUI update. All fields are optional. """

    def __init__(self, search_results:SearchResults=None, display_data:DisplayData=None) -> None:
        self.search_results = search_results  # Product of a search action.
        self.display_data = display_data      # Product of a query action.


class RESTGUIApplication:
    """ Thread-safe GUI application for use in a web server. """

    def __init__(self, gui:GUIEngine) -> None:
        self._gui = gui      # Main REST GUI engine.
        self._lock = Lock()  # Lock to protect this engine, which may not be thread-safe.

    def run(self, action:str, args:Iterable=(), options:dict=None) -> RESTUpdate:
        """ Perform a REST app action. Input data includes an action method, its arguments (if any), and GUI options.
            Option state is not thread-safe and must be set separately. """
        opts = GUIOptions(options)
        with self._lock:
            self._gui.set_options(opts)
            method = getattr(self, "REST_" + action)
            update = method(*args)
            return update

    def REST_query(self, keys:Iterable[str], letters:str) -> RESTUpdate:
        """ Execute and return a full display of a lexer query. """
        display = self._gui.query(keys, letters)
        return RESTUpdate(display_data=display)

    def REST_search(self, pattern:str, pages=1) -> RESTUpdate:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        results = self._gui.search(pattern, pages)
        return RESTUpdate(search_results=results)

    def REST_search_examples(self, link_ref:str) -> RESTUpdate:
        """ When a link is clicked, search for examples of the named rule and select one at random. """
        pattern = self._gui.random_pattern(link_ref)
        if not pattern:
            results = display = None
        else:
            results = self._gui.search(pattern)
            display = self._gui.query_random(results)
        return RESTUpdate(search_results=results, display_data=display)
