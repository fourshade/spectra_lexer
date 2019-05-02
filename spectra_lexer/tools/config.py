from typing import Dict

from spectra_lexer import Component


class ConfigTool(Component):
    """ Config manager; allows editing of config values for any component. """

    config_menu = resource("menu:Tools:Edit Configuration...", ["config_tool_open"])
    info = resource("cfginfo", {}, desc="Dict with detailed config info from active components.")

    @on("config_tool_open", pipe_to="new_dialog")
    def open(self) -> tuple:
        """ Create and show GUI configuration manager dialog by combining info and data dict values. """
        return "config", ["config_tool_send"], self.info

    @on("config_tool_send", pipe_to="config_save")
    def send(self, d:Dict[str, dict]) -> Dict[str, dict]:
        """ Update and save the new config values. """
        self.engine_call("config_update", d)
        return d
