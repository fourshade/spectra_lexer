import sys
import traceback
from typing import Optional, Set

from spectra_lexer import fork, on, pipe, SpectraComponent
from spectra_lexer.rules import StenoRule

from spectra_lexer.system.console import InterpreterConsole

# Map of commands that can be sent from text entry.
_COMMAND_MAP = {"/console": "system_console_start",
                "/save":    "system_rule_save"}


class SystemModule(SpectraComponent):
    """ Module for low-level system interpreter operations such as exception handling and debugging. """

    console = None
    _recorded_rules: Set[StenoRule]

    def __init__(self):
        self._recorded_rules = set()

    @on("new_status")
    def print_status(self, msg:str) -> None:
        """ Default system response to status messages is to print them to console. """
        print(msg)

    @fork("handle_exception", "new_output_text")
    def display_exception(self, e:Exception) -> str:
        """ The stack trace for unhandled exceptions are piped to every main display surface, including the main
            GUI window and the console. To avoid crashing Plover, exceptions are marked as handled after display. """
        tb_lines = traceback.TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        return "".join(tb_text)

    @pipe("new_text_entry", "new_output_text", scroll_to="bottom")
    def system_command(self, text:str) -> Optional[str]:
        """ Enable special system features on text entry. Pure whitespace is ignored. """
        cmd_args = text.split()
        if not cmd_args:
            return
        # The first text item is the system command; all others are passed as arguments to the engine.
        cmd, *args = cmd_args
        engine_command = _COMMAND_MAP.get(cmd)
        if engine_command:
            self.engine_send(engine_command, *args)
            return
        # If no system commands match, send the input to the console and output any new generated text.
        if self.console is not None:
            return self.console.run_command(text)

    @pipe("system_console_start", "new_output_text", scroll_to="bottom")
    def console_start(self, *args) -> str:
        """ Start the interpreter console with the engine state and return the initial generated text. """
        if self.console is None:
            self.console = InterpreterConsole(locals={"engine": self.engine_call.__self__})
            return self.console.read()

    @on("new_lexer_result")
    def record_results(self, rule:StenoRule):
        """ Record each lexer result to a set for later analysis. """
        self._recorded_rules.add(rule)

    @pipe("system_rule_save", "dict_save_rules", unpack=True)
    def save_results(self, *args):
        """ Save all recorded lexer results to a file. """
        filename = args[0] if args else "rules.json"
        return filename, self._recorded_rules
