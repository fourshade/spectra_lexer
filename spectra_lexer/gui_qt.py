import pkgutil
from typing import Callable, Sequence

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer.console.qt import ConsoleDialog
from spectra_lexer.gui_engine import DisplayPage, GUIEngine, GUIOptions, GUIOutput
from spectra_lexer.gui_ext import GUIExtension
from spectra_lexer.objtree.main import NamespaceTreeDialog
from spectra_lexer.qt import WINDOW_ICON_PATH
from spectra_lexer.qt.board import BoardPanel
from spectra_lexer.qt.config import ConfigDialog
from spectra_lexer.qt.dialog import DialogManager
from spectra_lexer.qt.graph import GraphPanel
from spectra_lexer.qt.index import INDEX_STARTUP_MESSAGE, IndexSizeDialog
from spectra_lexer.qt.main_window_ui import Ui_MainWindow
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.search import SearchPanel
from spectra_lexer.qt.system import QtTaskExecutor, QtExceptionHook
from spectra_lexer.qt.title import TitleDisplay
from spectra_lexer.qt.window import WindowController
from spectra_lexer.spc_lexer import TranslationFilter
from spectra_lexer.util.exception import ExceptionManager

EMPTY_PAGE = DisplayPage(" ", " ", "", "", "")


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
        self._page_dict = {}
        self._default_page = EMPTY_PAGE
        self._last_rule_id = ""
        self._last_translation = None

    def _set_title(self, text:str) -> None:
        self._title.set_static_text(text)

    def _set_caption(self, caption:str) -> None:
        """ Show a caption above the board diagram. """
        self._board.set_caption(caption)

    def _set_translation(self, keys:str, letters:str) -> None:
        """ Format a translation and show it in the search boxes and/or title bar. """
        self._last_translation = [keys, letters]
        self._search.select_translation(keys, letters)
        tr_text = " ".join([keys, self.TR_DELIMITER, letters])
        self._set_title(tr_text)

    def _set_rule_id(self, rule_id:str) -> None:
        """ Save the current rule ID and show/hide the link based on its contents. """
        self._last_rule_id = rule_id
        if rule_id:
            self._board.show_examples_link()
        else:
            self._board.hide_examples_link()

    def _show_page(self, page:DisplayPage, intense:bool) -> None:
        """ Change the currently displayed analysis page. """
        html_graph = page.intense_graph if intense else page.graph
        self._graph.set_html(html_graph)
        self._set_caption(page.caption)
        self._board.set_data(page.board)
        self._set_rule_id(page.rule_id)

    def _focus_page(self, page:DisplayPage, focused:bool) -> None:
        """ Forcibly reset the graph's focus before setting a new page. """
        self._graph.set_focus(focused)
        self._show_page(page, focused)

    def _show_start_page(self) -> None:
        """ Attempt to show a new page using the last link target, otherwise show the default. """
        if self._last_rule_id:
            for node_ref, page in self._page_dict.items():
                if page.rule_id == self._last_rule_id:
                    self._focus_page(page, True)
                    return
        self._focus_page(self._default_page, False)

    def _clear_display(self) -> None:
        """ Clear the current translation and all analysis pages. """
        self._last_translation = None
        self._page_dict = {}
        self._default_page = EMPTY_PAGE
        self._show_page(EMPTY_PAGE, False)
        self._graph.set_plaintext("")

    def _base_options(self) -> GUIOptions:
        """ Config settings form the base for a set of GUI engine options. """
        return GUIOptions(self._ext.get_config())

    def _get_options(self) -> GUIOptions:
        """ Return all values that may be needed by the steno engine as options. """
        opts = self._base_options()
        opts.search_mode_strokes = self._search.is_mode_strokes()
        opts.search_mode_regex = self._search.is_mode_regex()
        opts.board_aspect_ratio = self._board.aspect_ratio()
        opts.board_show_compound = self._board.is_compound()
        opts.board_show_letters = self._board.shows_letters()
        return opts

    def _update_gui(self, out:GUIOutput) -> None:
        """ Update each GUI component with anything it uses from <out>. """
        search_input = out.search_input
        if out.search_input is not None:
            self._search.update_input(search_input)
        results = out.search_results
        if results is not None:
            self._search.update_results(results.matches, can_expand=not results.is_complete)
        display_data = out.display_data
        if display_data is not None:
            self._set_translation(display_data.keys, display_data.letters)
            self._page_dict = display_data.pages_by_ref
            self._default_page = display_data.default_page
            self._show_start_page()

    def gui_search(self, pattern:str, pages:int) -> None:
        """ Run a translation search and update the GUI with any results. """
        opts = self._get_options()
        self._engine.set_options(opts)
        out = self._engine.search(pattern, pages)
        self._update_gui(out)

    def gui_query(self, keys_or_seq:Sequence[str], letters:str, strict:bool=None) -> None:
        """ Run a lexer query and update the GUI with any results. """
        opts = self._get_options()
        if strict is not None:
            opts.lexer_strict_mode = strict
        self._engine.set_options(opts)
        out = self._engine.query(keys_or_seq, letters)
        self._update_gui(out)

    def gui_search_examples(self, link_ref:str) -> None:
        """ Run an example search and update the GUI with any results. """
        opts = self._get_options()
        self._engine.set_options(opts)
        out = self._engine.search_examples(link_ref)
        self._update_gui(out)

    def _on_translation_edit(self, _:str) -> None:
        """ Display user entry instructions in the caption. """
        self._set_caption(self.TR_MSG_CHANGED)

    def _on_translation_submit(self, text:str) -> None:
        """ Display user entry errors in the caption. """
        self._clear_display()
        args = text.split(self.TR_DELIMITER, 1)
        if not len(args) == 2:
            self._set_caption(self.TR_MSG_EDELIMITERS)
            return
        keys, letters = map(str.strip, args)
        if not (keys and letters):
            self._set_caption(self.TR_MSG_EBLANK)
            return
        self.gui_query(keys, letters)

    def _on_graph_action(self, node_ref:str, intense:bool) -> None:
        """ On mouse actions, change the current analysis page to the one under <node_ref>.
            If <node_ref> is an empty string, show the default page. """
        page = self._page_dict.get(node_ref) or self._default_page
        self._show_page(page, intense)

    def _on_board_invalid(self) -> None:
        """ Send a query for the last valid translation to get a new board diagram. """
        if self._last_translation is not None:
            keys, letters = self._last_translation
            self.gui_query(keys, letters)

    def _on_board_save(self) -> None:
        """ Save the current board diagram on link click. """
        filename = self._dialogs.save_file("Save Board Diagram", "svg|png", "board.svg")
        if filename:
            self._board.dump_image(filename)

    def _on_request_examples(self) -> None:
        """ Start an example search based on the last valid link reference. """
        if self._last_rule_id:
            self.gui_search_examples(self._last_rule_id)

    def _connect_signals(self) -> None:
        self._title.connect_signals(self._on_translation_edit, self._on_translation_submit)
        self._search.connect_signals(self.gui_search, self.gui_query)
        self._graph.connect_signals(self._on_graph_action)
        self._board.connect_signals(self._on_board_invalid, self._on_board_save, self._on_request_examples)

    def has_focus(self) -> bool:
        return self._window.has_focus()

    def show(self) -> None:
        self._window.show()

    def close(self) -> None:
        self._window.close()

    def show_traceback(self, tb_text:str) -> None:
        """ Display a stack trace with an appropriate title. """
        self._set_title("Well, this is embarrassing...")
        self._graph.set_plaintext(tb_text)

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
            self._clear_display()
        self._menu.set_enabled(enabled)
        self._title.set_enabled(enabled)
        self._search.set_enabled(enabled)
        self._graph.set_enabled(enabled)
        self._board.set_enabled(enabled)

    def async_run(self, func:Callable, *args) -> None:
        """ Queue a function to execute on the worker thread. """
        self._tasks.on_worker(func, *args)

    def async_queue(self, func:Callable, *args) -> None:
        """ Queue a function to execute on the GUI thread. Only useful for sequencing. """
        self._tasks.on_main(func, *args)

    def async_start(self, msg_start:str) -> None:
        """ Disable the window controls and show <msg_start> first before running a blocking task on another thread.
            GUI events may misbehave unless explicitly processed before the async thread takes the GIL. """
        q_app = QApplication.instance()
        q_app.processEvents()
        self.async_queue(self.set_enabled, False)
        self.async_queue(self.set_status, msg_start)

    def async_finish(self, msg_finish:str) -> None:
        """ Queue callbacks that will re-enable the controls and show <msg_finish> when all worker tasks are done. """
        self.async_queue(self.set_enabled, True)
        self.async_queue(self.set_status, msg_finish)

    def _on_ready(self) -> None:
        """ When all major resources are ready, load the config and connect the GUI callbacks.
            If the config settings are blank, this is the first time the program has been run.
            Add the default config values and present an index generation dialog in this case. """
        self._connect_signals()
        if not self._ext.get_config():
            defaults = {key: getattr(GUIOptions, key) for key, *_ in GUIOptions.CFG_OPTIONS}
            self._ext.update_config(defaults)
            self.confirm_startup_index()

    def start(self, *funcs:Callable[[], None]) -> None:
        """ Load initial data from <funcs> asynchronously on a new thread to avoid blocking the GUI. """
        self._tasks.start()
        self.async_start("Loading...")
        for f in funcs:
            self.async_run(f)
        self.async_finish("Loading complete.")
        self.async_queue(self._on_ready)

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
        self._ext.update_config(options)
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

    def on_exception(self, exc:BaseException) -> None:
        """ Store unhandled exceptions and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        self.set_enabled(True)


def build_app(engine:GUIEngine, ext:GUIExtension, logger:Callable[[str], None]) -> QtGUIApplication:
    """ Build the interactive Qt GUI application with all necessary components. """
    exc_man = ExceptionManager()
    exc_man.add_logger(logger)
    exc_hook = QtExceptionHook(chain_hooks=False)
    exc_hook.connect(exc_man.on_exception)
    tasks = QtTaskExecutor()
    w_window = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(w_window)
    dialogs = DialogManager(w_window)
    window = WindowController(w_window)
    icon_data = pkgutil.get_data(*WINDOW_ICON_PATH)
    window.set_icon(icon_data)
    menu = MenuController(ui.w_menubar)
    title = TitleDisplay(ui.w_title)
    search = SearchPanel(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
    graph = GraphPanel(ui.w_graph)
    board = BoardPanel(ui.w_board, ui.w_caption, ui.w_slider, ui.w_link_save, ui.w_link_examples)
    app = QtGUIApplication(engine, ext, tasks, dialogs, window, menu, title, search, graph, board)
    app.set_status("Loading...")
    exc_man.add_logger(app.show_traceback)
    exc_man.add_handler(app.on_exception)
    f_menu = menu.get_section("File")
    f_menu.addItem(app.open_translations, "Load Translations...")
    f_menu.addItem(app.open_index, "Load Index...")
    f_menu.addSeparator()
    f_menu.addItem(app.close, "Close")
    t_menu = menu.get_section("Tools")
    t_menu.addItem(app.config_editor, "Edit Configuration...")
    t_menu.addItem(app.custom_index, "Make Index...")
    d_menu = menu.get_section("Debug")
    d_menu.addItem(app.debug_console, "Open Console...")
    d_menu.addItem(app.debug_tree, "View Object Tree...")
    app.set_enabled(False)
    app.show()
    # Some object references must be saved in an attribute or else Qt will disconnect the signals upon scope exit.
    app.sys_refs = [exc_man, exc_hook]
    return app
