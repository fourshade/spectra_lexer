from typing import Callable, Sequence

from spectra_lexer.console.qt import ConsoleDialog
from spectra_lexer.gui_engine import GUIEngine, GUIOptions, QueryResults, SearchResults
from spectra_lexer.gui_ext import GUIExtension
from spectra_lexer.objtree.main import NamespaceTreeDialog
from spectra_lexer.qt.board import BoardPanel
from spectra_lexer.qt.config import ConfigDialog
from spectra_lexer.qt.dialog import DialogManager
from spectra_lexer.qt.graph import GraphPanel
from spectra_lexer.qt.index import INDEX_STARTUP_MESSAGE, IndexSizeDialog
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.search import SearchPanel
from spectra_lexer.qt.system import QtTaskExecutor
from spectra_lexer.qt.title import TitleDisplay
from spectra_lexer.qt.window import WindowController
from spectra_lexer.spc_lexer import TranslationFilter


class QtGUIApplication:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    TR_DELIMITER = '->'  # Delimiter between keys and letters of translations shown in title bar.
    TR_MSG_CHANGED = "Press Enter to parse any changes."
    TR_MSG_EDELIMITERS = 'ERROR: An arrow "->" must separate the steno keys and translated text.'
    TR_MSG_EBLANK = 'ERROR: One or both sides is empty.'

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, engine:GUIEngine, ext:GUIExtension, tasks:QtTaskExecutor, dialogs:DialogManager,
                 window:WindowController, menu:MenuController, title:TitleDisplay,
                 search:SearchPanel, graph:GraphPanel, board:BoardPanel) -> None:
        self._engine = engine
        self._ext = ext
        self._tasks = tasks
        self._dialogs = dialogs
        self._window = window
        self._menu = menu
        self._title = title
        self._search = search
        self._graph = graph
        self._board = board
        self._last_graph_ref = None
        self._last_example_id = ""

    def _set_title(self, text:str) -> None:
        self._title.set_static_text(text)

    def _set_caption(self, caption:str) -> None:
        """ Show a caption above the board diagram. """
        self._board.set_caption(caption)

    def _set_translation(self, keys:str, letters:str) -> None:
        """ Format a translation and show it in the search boxes and/or title bar. """
        self._search.select_translation(keys, letters)
        tr_text = " ".join([keys, self.TR_DELIMITER, letters])
        self._set_title(tr_text)

    def _set_example_id(self, example_id:str) -> None:
        """ Save the current example ID and show/hide the link based on its contents. """
        self._last_example_id = example_id
        if example_id:
            self._board.show_examples_link()
        else:
            self._board.hide_examples_link()

    def _show_page(self, ref:str, intense:bool) -> None:
        """ Change the currently displayed analysis page. """
        self._last_graph_ref = ref
        html_graph = self._engine.draw_graph(ref, intense)
        self._graph.set_html(html_graph)
        caption = self._engine.get_caption(ref)
        self._set_caption(caption)
        board = self._engine.draw_board(ref)
        self._board.set_data(board)
        example_id = self._engine.get_example_id(ref)
        self._set_example_id(example_id)

    def _clear_page(self) -> None:
        """ Clear the current display data. """
        self._last_graph_ref = None
        self._last_example_id = ""
        self._graph.set_plaintext("")
        self._set_caption("")
        self._board.set_data("")
        self._set_example_id("")

    def _update_search(self, results:SearchResults) -> None:
        """ Update each GUI search component with new results. """
        self._search.update_results(results.matches, can_expand=not results.is_complete)

    def _find_same_example(self, refs:Sequence[str]):
        """ Attempt to find a graph ref that has the same link target as the last selection. """
        if self._last_example_id:
            for ref in refs:
                if self._last_example_id == self._engine.get_example_id(ref):
                    return ref
        return ""

    def _update_display(self, results:QueryResults) -> None:
        """ Update the GUI display with a new analysis.
            Attempt to show a page using the last link target, otherwise show the default.
            Forcibly reset the graph's focus before setting the start page. """
        self._set_translation(results.keys, results.letters)
        start_ref = self._find_same_example(results.refs)
        intense = bool(start_ref)
        self._graph.set_focus(intense)
        self._show_page(start_ref, intense)

    def _get_config(self) -> dict:
        return self._ext.get_config()

    def _update_config(self, options:dict) -> None:
        self._ext.update_config(options)

    def _base_options(self) -> GUIOptions:
        """ Config settings form the base for a set of GUI engine options. """
        return GUIOptions(self._get_config())

    def set_options(self, **kwargs) -> None:
        """ Set all options that may be needed by the steno engine. Overriding options may be given as kwargs. """
        opts = self._base_options()
        opts.search_mode_strokes = self._search.is_mode_strokes()
        opts.search_mode_regex = self._search.is_mode_regex()
        opts.board_aspect_ratio = self._board.aspect_ratio()
        opts.board_show_compound = self._board.is_compound()
        opts.board_show_letters = self._board.shows_letters()
        if kwargs:
            vars(opts).update(kwargs)
        self._engine.set_options(opts)

    def set_translations(self, *args) -> None:
        self._ext.set_translations(*args)

    def gui_search(self, pattern:str, pages:int) -> None:
        """ Run a translation search and update the GUI with any results. """
        search_results = self._engine.search(pattern, pages)
        self._update_search(search_results)

    def gui_query(self, keys_or_seq:Sequence[str], letters:str) -> None:
        """ Run a lexer query and update the GUI with any results. """
        query_results = self._engine.query(keys_or_seq, letters)
        self._update_display(query_results)

    def gui_search_examples(self) -> None:
        """ Run an example search based on the last valid link reference and update the GUI with any results. """
        pattern = self._engine.random_pattern(self._last_example_id)
        if pattern:
            self._search.update_input(pattern)
            search_results = self._engine.search(pattern)
            self._update_search(search_results)
            query_results = self._engine.query_random(search_results)
            self._update_display(query_results)

    def _on_translation_edit(self, _:str) -> None:
        """ Display user entry instructions in the caption. """
        self._set_caption(self.TR_MSG_CHANGED)

    def _on_translation_submit(self, text:str) -> None:
        """ Display user entry errors in the caption. """
        self._clear_page()
        args = text.split(self.TR_DELIMITER, 1)
        if not len(args) == 2:
            self._set_caption(self.TR_MSG_EDELIMITERS)
            return
        keys, letters = map(str.strip, args)
        if not (keys and letters):
            self._set_caption(self.TR_MSG_EBLANK)
            return
        self.set_options()
        self.gui_query(keys, letters)

    def _on_graph_action(self, node_ref:str, intense:bool) -> None:
        """ On mouse actions, change the current analysis page to the one under <node_ref>. """
        self._show_page(node_ref, intense)

    def _on_board_invalid(self) -> None:
        """ Redraw the last board diagram with new options. """
        if self._last_graph_ref is not None:
            self.set_options()
            board = self._engine.draw_board(self._last_graph_ref)
            self._board.set_data(board)

    def _on_board_save(self) -> None:
        """ Save the current board diagram on link click. """
        filename = self._dialogs.save_file("Save Board Diagram", "svg|png", "board.svg")
        if filename:
            self._board.dump_image(filename)

    def _on_search_input(self, pattern:str, pages:int) -> None:
        self.set_options()
        self.gui_search(pattern, pages)

    def _on_search_query(self, keys_or_seq:Sequence[str], letters:str) -> None:
        self.set_options()
        self.gui_query(keys_or_seq, letters)

    def _on_request_examples(self) -> None:
        self.set_options()
        self.gui_search_examples()

    def _connect_signals(self) -> None:
        self._title.connect_signals(self._on_translation_edit, self._on_translation_submit)
        self._search.connect_signals(self._on_search_input, self._on_search_query)
        self._graph.connect_signals(self._on_graph_action)
        self._board.connect_signals(self._on_board_invalid, self._on_board_save, self._on_request_examples)

    def has_focus(self) -> bool:
        return self._window.has_focus()

    def show(self) -> None:
        self._window.show()

    def close(self) -> None:
        self._window.close()

    def set_status(self, text:str) -> None:
        """ Check if the status text ends in an ellipsis. If not, just show it in the title normally.
            Otherwise, animate the text with a • dot moving down the ellipsis until new text is shown:
            loading...  ->  loading•..  ->  loading.•.  ->  loading..• """
        if text.endswith("..."):
            body = text.rstrip(".")
            frames = [body + b for b in ("...", "•..", ".•.", "..•")]
            self._title.set_animated_text(frames, 200)
        else:
            self._set_title(text)

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all display widgets. Invalidate the current search, graph, and board on disable. """
        if not enabled:
            self._search.clear_results()
            self._clear_page()
        self._menu.set_enabled(enabled)
        self._title.set_enabled(enabled)
        self._search.set_enabled(enabled)
        self._graph.set_enabled(enabled)
        self._board.set_enabled(enabled)

    def _block(self, msg_start:str) -> None:
        """ Disable the window controls and show <msg_start> before running a blocking task on another thread. """
        self.set_enabled(False)
        self.set_status(msg_start)

    def _unblock(self, msg_finish:str) -> None:
        """ Re-enable the controls and show <msg_finish> when all worker tasks are done. """
        self.set_enabled(True)
        self.set_status(msg_finish)

    def async_run(self, func:Callable, *args) -> None:
        """ Queue a function to execute on the worker thread. """
        self._tasks.on_worker(func, *args)

    def async_queue(self, func:Callable, *args) -> None:
        """ Queue a function to execute on the GUI thread. Only useful for sequencing. """
        self._tasks.on_main(func, *args)

    def async_start(self, msg_start:str) -> None:
        self.async_queue(self._block, msg_start)

    def async_finish(self, msg_finish:str) -> None:
        self.async_queue(self._unblock, msg_finish)

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._dialogs.open_files("Load Translations", "json")
        if filenames:
            self.async_start("Loading files...")
            self.async_run(self._ext.load_translations, *filenames)
            self.async_finish("Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._dialogs.open_file("Load Index", "json")
        if filename:
            self.async_start("Loading file...")
            self.async_run(self._ext.load_examples, filename)
            self.async_finish("Loaded index from file dialog.")

    def _config_edited(self, options:dict) -> None:
        self._update_config(options)
        self.set_status("Configuration saved.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        dialog = self._dialogs.load(ConfigDialog)
        if dialog is not None:
            opts = self._base_options()
            for key, name, description in opts.CFG_OPTIONS:
                value = getattr(opts, key)
                dialog.add_option(key, value, "General", name, description)
                dialog.call_on_options_accept(self._config_edited)
            dialog.show()

    def _make_index(self, size:int) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.async_start("Making new index...")
        self.async_run(self._ext.compile_examples, size)
        self.async_finish("Successfully created index!")

    def confirm_startup_index(self) -> None:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        if self._dialogs.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE):
            self._make_index(TranslationFilter.SIZE_MEDIUM)

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        dialog = self._dialogs.load(IndexSizeDialog)
        if dialog is not None:
            dialog.setup(TranslationFilter.SIZES)
            dialog.call_on_size_accept(self._make_index)
            dialog.show()

    def debug_console(self) -> None:
        """ Create and show an interpreter console dialog. """
        dialog = self._dialogs.load(ConsoleDialog)
        if dialog is not None:
            namespace = {k: getattr(self, k) for k in dir(self) if not k.startswith('__')}
            dialog.start_console(namespace)
            dialog.show()

    def debug_tree(self) -> None:
        """ Create and show the debug tree dialog with this app's vars. """
        dialog = self._dialogs.load(NamespaceTreeDialog)
        if dialog is not None:
            dialog.set_namespace(vars(self), root_package=__package__)
            dialog.show()

    def _on_ready(self) -> None:
        """ When all major resources are ready, load the config and connect the GUI callbacks.
            If the config settings are blank, this is the first time the program has been run.
            Add the default config values and present an index generation dialog in this case. """
        self._connect_signals()
        if not self._get_config():
            defaults = {key: getattr(GUIOptions, key) for key, *_ in GUIOptions.CFG_OPTIONS}
            self._update_config(defaults)
            self.confirm_startup_index()

    def start(self) -> None:
        """ Show the window and load initial data asynchronously on a new thread to keep the GUI responsive. """
        self._block("Loading...")
        self.async_run(self._ext.load_initial)
        self.async_finish("Loading complete.")
        self.async_queue(self._on_ready)
        self.show()
        self._tasks.start()

    def on_exception(self, exc_type, exc_value, _) -> bool:
        """ Display an error message with an appropriate title. Save the exception afterward to allow debugging. """
        self._set_title("EXCEPTION - " + exc_type.__name__)
        text = str(exc_value) + '\n\nIn the menu, go to "Debug -> View Object Tree..." for debug details.'
        self._graph.set_plaintext(text)
        self.last_exception = exc_value
        return True
