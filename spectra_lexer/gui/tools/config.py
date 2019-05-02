from typing import Dict

from spectra_lexer import Component


class ConfigTool(Component):
    """ Config manager; allows editing of config values for any component. """

    config_menu = resource("menu:Tools:Edit Configuration...", ["config_tool_open"])
    info = resource("cfginfo", {}, desc="Dict with detailed config info from active components.")

    @on("config_tool_open")
    def open(self) -> None:
        """ Create and show GUI configuration manager dialog by combining info and data dict values. """
        self.open_dialog(self.send, self.info)

    def open_dialog(self, callback, info:Dict[str, dict]) -> None:
        raise NotImplementedError

    def send(self, d:Dict[str, dict]) -> None:
        """ Update and save the new config values. """
        self.engine_call("config_update", d)
        self.engine_call("config_save", d)
