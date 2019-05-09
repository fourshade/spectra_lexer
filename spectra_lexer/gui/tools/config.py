from collections import defaultdict
from typing import Dict

from .base import GUITool


class ConfigTool(GUITool):
    """ Config manager; allows editing of config values for any component. """

    config_menu = resource("menu:Tools:Edit Configuration...", ["config_tool_open"])
    data = resource("config", {})  # Dict with config values from every capable component.

    _info: Dict[str, dict]  # Dict with detailed config info from active components, including the values.

    @init("config")
    def start(self, config:dict) -> None:
        """ Store all info and default data values for active config settings. """
        info = self._info = defaultdict(dict)
        for sect, page in config.items():
            d = info[sect]
            for key, res in page.items():
                default, desc = res.info()
                v = default
                tp = type(v)
                label = key.replace("_", " ").title()
                if "name" in d:
                    v = d[key][0]
                d[key] = [v, tp, label, desc]

    @on("config_tool_open")
    def open(self) -> None:
        """ Create and show GUI configuration manager dialog by combining info and data dict values. """
        info = self._info
        for sect, page in self.data.items():
            p = info[sect]
            for name, val in page.items():
                if name in p:
                    p[name] = [val, *p[name][1:]]
        self.open_dialog(self.send, info)

    def send(self, d:Dict[str, dict]) -> None:
        """ Save the new config values. This will update the values on components as well. """
        self.engine_call("config_save", d)
