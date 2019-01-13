from typing import Optional

from spectra_lexer import Component, on, pipe
from spectra_lexer.console.interpreter import InterpreterConsole
from spectra_lexer.utils import str_eval

# Prefix for entering commands. They will be mapped to either the shortcuts below or direct engine commands.
_COMMAND_PREFIX = "/"
# Map of shortcut commands (minus the slash) that can be sent from text entry.
_COMMAND_MAP = {"console": "console_start",
                "config":  "gui_config_open"}


class ConsoleManager(Component):
    """ Component for interactive engine and system interpreter operations. """

    ROLE = "console"

    console: InterpreterConsole = None  # Main console interpreter, run on a different thread.

    @on("start")
    def start(self, **opts) -> None:
        """ If the menu is used, add the console dialog command. """
        self.engine_call("gui_menu_add", "Tools", "Open Console...", "console_start")

    @pipe("new_text_entry", "new_output_text", scroll_to="bottom")
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

    @pipe("console_start", "new_output_text", scroll_to="bottom")
    def console_start(self) -> str:
        """ Start the interpreter console with the engine state and return the initial generated text. """
        if self.console is None:
            self.console = InterpreterConsole(locals={"engine": self.engine_call.__self__})
            return self.console.run()
