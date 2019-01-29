from typing import Optional

from spectra_lexer import Component, on, pipe
from spectra_lexer.console.interpreter import InterpreterConsole
from spectra_lexer.utils import str_eval

# Prefix for entering commands. They will be mapped to either the shortcuts below or direct engine commands.
_COMMAND_PREFIX = "/"
# Map of shortcut commands (minus the slash) that can be sent from text entry.
_COMMAND_MAP = {"console": "console_open",
                "config":  "gui_config_open"}


class ConsoleManager(Component):
    """ Component for interactive engine and system interpreter operations. """

    ROLE = "console"

    console: InterpreterConsole = None  # Main console interpreter, run on a different thread.
    console_vars: dict = None           # Variables to load on interpreter startup.

    @on("start")
    def start(self, show_menu=True, console_vars:dict=None, **opts) -> None:
        """ If the menu is used, add the console dialog command. """
        if show_menu:
            self.engine_call("gui_menu_add", "Tools", "Open Console...", "console_open")
        # Use the vars dict on interpreter start if given, otherwise just use an engine reference.
        self.console_vars = console_vars or {}

    @pipe("console_open", "new_text_output", scroll_to="bottom")
    def open(self) -> str:
        """ Start the interpreter console with the current vars dict and return the initial generated text.
            If it already is started, just show the current text contents again. """
        if self.console is None:
            self.console = InterpreterConsole(self.console_vars)
        return self.console.run()

    @pipe("new_text_input", "new_text_output", scroll_to="bottom")
    def system_command(self, text:str) -> Optional[str]:
        """ Send direct engine commands on text entry. Pure whitespace is ignored. """
        text = text.strip()
        if not text.startswith(_COMMAND_PREFIX):
            # If there's no system command prefix, send the text to the console if it's started, else do nothing.
            if self.console is not None:
                return self.console.run(text)
            return
        # The first text item is the command; all others are passed as arguments to the engine.
        cmd = text[len(_COMMAND_PREFIX):]
        cmd, *args = cmd.split(' ')
        # If the command is one of the shortcuts, replace it, otherwise leave it alone.
        cmd = _COMMAND_MAP.get(cmd, cmd)
        # Parse all the other arguments as if they were Python literals.
        args = list(map(str_eval, args))
        self.engine_call(cmd, *args)
