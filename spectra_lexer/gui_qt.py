import pkgutil
from typing import Callable, Sequence

from PyQt5.QtWidgets import QDialog, QMainWindow

from spectra_lexer.config.main import QtConfigManager
from spectra_lexer.config.spec import BoolOption, ConfigSpec, IntOption
from spectra_lexer.console.main import ConsoleDialog
from spectra_lexer.engine import Engine, EngineOptions
from spectra_lexer.objtree.main import NamespaceTreeDialog
from spectra_lexer.qt import ICON_PACKAGE, ICON_PATH
from spectra_lexer.qt.dialog import DialogManager
from spectra_lexer.qt.index_dialog import index_size_dialog
from spectra_lexer.qt.main_window import build_gui, GUIController, GUIHooks
from spectra_lexer.qt.system import QtTaskExecutor
from spectra_lexer.qt.window import WindowController
from spectra_lexer.resource.translations import TranslationsDict, TranslationFilter
from spectra_lexer.spc_search import EXPAND_KEY

INDEX_STARTUP_MESSAGE = """<p>
In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk.
</p><p>
Would you like to create one now? You will not be asked again.
</p><p>
(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).
</p>"""

TR_DELIMITER = '->'  # Delimiter between keys and letters of translations shown in title bar.
TR_MSG_CHANGED = "Press Enter to parse any changes."
TR_MSG_EDELIMITERS = 'ERROR: An arrow "->" must separate the steno keys and translated text.'
TR_MSG_EBLANK = 'ERROR: One or both sides is empty.'

CONFIG_SECTION = "app_qt"  # We only need one CFG section; this is its name.


def cfg_spec() -> ConfigSpec:
    """ Return a spec for engine options which should be kept in a CFG file (not GUI controlled). """
    return ConfigSpec(name=CONFIG_SECTION, title='General', options=[
        IntOption(name="search_match_limit",
                  default=EngineOptions.search_match_limit,
                  title="Match Limit",
                  description="Maximum number of matches returned on one page of a search."),
        BoolOption(name="lexer_strict_mode",
                   default=EngineOptions.lexer_strict_mode,
                   title="Strict Mode",
                   description="Only return lexer results that match every key in a translation."),
        BoolOption(name="graph_compressed_layout",
                   default=EngineOptions.graph_compressed_layout,
                   title="Compressed Layout",
                   description="Compress the graph layout vertically to save space.")
    ])


class QtGUIApplication(GUIHooks):
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, engine:Engine, config:QtConfigManager, tasks:QtTaskExecutor, dialogs:DialogManager,
                 window:WindowController, gui:GUIController) -> None:
        self._engine = engine
        self._config = config
        self._tasks = tasks
        self._dialogs = dialogs
        self._window = window
        self._gui = gui

    def _show_page(self, intense:bool) -> None:
        """ Display the current analysis page. """
        html_graph = self._engine.draw_graph(intense=intense)
        self._gui.set_graph(html_graph, focused=intense)
        caption = self._engine.get_caption()
        self._gui.set_caption(caption)
        board = self._engine.draw_board()
        self._gui.set_board(board)
        example_id = self._engine.get_example_id()
        self._gui.set_link_visible(bool(example_id))

    def _clear_page(self) -> None:
        """ Clear the current display data. """
        self._gui.set_graph_plain("")
        self._gui.set_caption("")
        self._gui.set_board("")
        self._gui.set_link_visible(False)

    def set_options(self, **kwargs) -> None:
        """ Set all options that may be needed by the steno engine from various sources.
            Source priority is: config file < GUI controls < keyword arguments. """
        options = {**self._config.get_section(CONFIG_SECTION),
                   "search_mode_strokes": self._gui.is_mode_strokes(),
                   "search_mode_regex":   self._gui.is_mode_regex(),
                   "board_aspect_ratio":  self._gui.aspect_ratio(),
                   "board_show_compound": self._gui.is_compound(),
                   "board_show_letters":  self._gui.shows_letters(),
                   **kwargs}
        self._engine.set_options(options)

    def run_query(self, keys:str, letters:str) -> None:
        """ Run a lexer query and update the GUI with the new analysis. Show the translation in the title bar.
            Attempt to show a page using the last link target, otherwise show the default. """
        match, mapping = self._engine.search_selection(keys, letters)
        self._gui.set_selections(match, mapping)
        tr_text = " ".join([keys, TR_DELIMITER, letters])
        self._gui.set_title(tr_text)
        last_id = self._engine.get_example_id()
        self._engine.run_query(keys, letters)
        if last_id:
            for ref in self._engine.get_refs():
                self._engine.select_ref(ref)
                if last_id == self._engine.get_example_id():
                    self._show_page(True)
                    return
        self._show_page(False)

    def on_translation_edit(self) -> None:
        """ Display user entry instructions in the caption. """
        self._gui.set_caption(TR_MSG_CHANGED)

    def on_translation_submit(self, text:str) -> None:
        """ Display user entry errors in the caption. """
        self._clear_page()
        args = text.split(TR_DELIMITER, 1)
        if not len(args) == 2:
            self._gui.set_caption(TR_MSG_EDELIMITERS)
            return
        keys, letters = map(str.strip, args)
        if not (keys and letters):
            self._gui.set_caption(TR_MSG_EBLANK)
            return
        self.set_options()
        self.run_query(keys, letters)

    def on_search_input(self, pattern:str, pages:int) -> None:
        """ Run a translation search and update the GUI with any results. """
        self.set_options()
        matches = self._engine.search(pattern, pages)
        can_expand = (matches.pop(EXPAND_KEY, None) is not None)
        self._gui.set_matches(matches, can_expand=can_expand)

    def on_search_multiquery(self, match:str, mappings:Sequence[str]) -> None:
        self.set_options()
        keys, letters = self._engine.best_translation(match, mappings)
        self.run_query(keys, letters)

    def on_search_query(self, match:str, mapping:str) -> None:
        self.on_search_multiquery(match, [mapping])

    def on_request_examples(self) -> None:
        """ Run an example search and update the GUI with any results. """
        self.set_options()
        example_id = self._engine.get_example_id()
        pattern = self._engine.random_pattern(example_id)
        if pattern:
            self._gui.set_input(pattern)
            results = self._engine.search(pattern)
            self._gui.set_matches(results)
            keys, letters = self._engine.random_translation(results)
            self.run_query(keys, letters)

    def on_graph_action(self, node_ref:str, intense:bool) -> None:
        """ On mouse actions, change the current analysis page to the one under <node_ref>. """
        self._engine.select_ref(node_ref)
        self._show_page(intense)

    def on_board_invalid(self) -> None:
        """ Redraw the last board diagram with new options. """
        self.set_options()
        board = self._engine.draw_board()
        self._gui.set_board(board)

    def on_board_save(self) -> None:
        """ Save the current board diagram on link click. """
        filename = self._dialogs.save_file("Save Board Diagram", "svg|png", "board.svg")
        if filename:
            self._gui.dump_board(filename)

    def has_focus(self) -> bool:
        return self._window.has_focus()

    def show(self) -> None:
        self._window.show()

    def close(self) -> None:
        self._window.close()

    def _block(self, msg_loading:str) -> None:
        """ Disable the window controls and invalidate the current search, graph, and board.
            Animate <msg_loading> in the title bar until unblocked. """
        self._clear_page()
        self._gui.set_matches({})
        self._gui.set_enabled(False)
        self._gui.set_loading_title(msg_loading)

    def _unblock(self, msg_done:str) -> None:
        """ Re-enable the controls and show <msg_done> when all worker tasks are done. """
        self._gui.set_enabled(True)
        self._gui.set_title(msg_done)

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

    def set_translations(self, translations:TranslationsDict) -> None:
        self._engine.set_translations(translations)

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._dialogs.open_files("Load Translations", "json")
        if filenames:
            self.async_start("Loading files...")
            self.async_run(self._engine.load_translations, *filenames)
            self.async_finish("Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._dialogs.open_file("Load Index", "json")
        if filename:
            self.async_start("Loading file...")
            self.async_run(self._engine.load_examples, filename)
            self.async_finish("Loaded index from file dialog.")

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.async_start("Making new index...")
        self.async_run(self._engine.compile_examples, TranslationFilter(size))
        self.async_finish("Successfully created index!")

    def confirm_startup_index(self) -> None:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        if self._dialogs.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE):
            self._make_index()

    def _index_opener(self) -> QDialog:
        """ Open a dialog with an index size slider that submits a positive number on accept. """
        return index_size_dialog(min_size=TranslationFilter.SIZE_MINIMUM,
                                 max_size=TranslationFilter.SIZE_MAXIMUM,
                                 default_size=TranslationFilter.SIZE_DEFAULT,
                                 on_accept=self._make_index)

    def custom_index(self) -> None:
        self._dialogs.open_unique(self._index_opener)

    def _on_config_updated(self) -> None:
        self._gui.set_title("Configuration saved.")

    def _config_opener(self) -> QDialog:
        """ Create a configuration manager dialog. """
        dialog = self._config.open_dialog()
        dialog.accepted.connect(self._on_config_updated)
        return dialog

    def config_editor(self) -> None:
        self._dialogs.open_unique(self._config_opener)

    def _debug_opener(self) -> QDialog:
        """ Create an interpreter console dialog with this app as the namespace. """
        dialog = ConsoleDialog()
        dialog.introspect(self)
        return dialog

    def debug_console(self) -> None:
        self._dialogs.open_unique(self._debug_opener)

    def _tree_opener(self) -> QDialog:
        """ Create a debug tree dialog with this app's vars. """
        dialog = NamespaceTreeDialog()
        dialog.set_namespace(vars(self), root_package=__package__)
        return dialog

    def debug_tree(self) -> None:
        self._dialogs.open_unique(self._tree_opener)

    def _on_ready(self) -> None:
        """ When all major resources are ready, load the config and connect the GUI callbacks.
            If the config settings are blank, this is the first time the program has been run.
            Create the config file and present an index generation dialog in this case. """
        self._gui.connect(self)
        if not self._config.load():
            self._config.save()
            self.confirm_startup_index()

    def start(self) -> None:
        """ Show the window and load initial data asynchronously on a new thread to keep the GUI responsive. """
        self._block("Loading...")
        self.async_run(self._engine.load_initial)
        self.async_finish("Loading complete.")
        self.async_queue(self._on_ready)
        self.show()
        self._tasks.start()

    def on_exception(self, exc_type:type, exc_value:Exception, _) -> bool:
        """ Display an error message with an appropriate title. Save the exception afterward to allow debugging. """
        title = f'EXCEPTION - {exc_type.__name__}'
        text = f'{exc_value}\n\nIn the menu, go to "Debug -> View Object Tree..." for debug details.'
        self._gui.set_title(title)
        self._gui.set_graph_plain(text)
        self.last_exception = exc_value
        return True


def build_gui_app(engine:Engine, cfg_path:str) -> QtGUIApplication:
    spec = cfg_spec()
    config = QtConfigManager(cfg_path, [spec])
    tasks = QtTaskExecutor()
    w_window = QMainWindow()
    dialogs = DialogManager(w_window)
    window = WindowController(w_window)
    icon_data = pkgutil.get_data(ICON_PACKAGE, ICON_PATH)
    window.set_icon(icon_data)
    gui = build_gui(w_window)
    app = QtGUIApplication(engine, config, tasks, dialogs, window, gui)
    gui.add_menu_action("File", "Load Translations...", app.open_translations)
    gui.add_menu_action("File", "Load Index...", app.open_index)
    gui.add_menu_separator("File")
    gui.add_menu_action("File", "Close", app.close)
    gui.add_menu_action("Tools", "Edit Configuration...", app.config_editor)
    gui.add_menu_action("Tools", "Make Index...", app.custom_index)
    gui.add_menu_action("Debug", "Open Console...", app.debug_console)
    gui.add_menu_action("Debug", "View Object Tree...", app.debug_tree)
    return app
