from .io import ConfigIO
from .parser import parse_opts, unparse_opts
from .qt import ConfigDialog
from .spec import ConfigDict, ConfigSpec, SectionDict


class QtConfigManager:
    """ Config settings handler for Qt-based GUIs. Settings are currently only mutable through a dialog. """

    def __init__(self, filename:str, spec:ConfigSpec=()) -> None:
        self._io = ConfigIO(filename)     # Performs whole reads/writes to CFG files.
        self._spec = spec                 # Specification for sections shown in the config manager.
        self._options = parse_opts(spec)  # Current config values. Start with defaults from the spec.

    def load(self) -> bool:
        """ Try to read config options from the CFG file. Return True if successful. """
        try:
            str_options = self._io.read()
            self._options = parse_opts(self._spec, str_options)
            return True
        except OSError:
            return False

    def save(self) -> bool:
        """ Save all config options to the CFG file. Return True if successful. """
        try:
            str_options = unparse_opts(self._spec, self._options)
            self._io.write(str_options)
            return True
        except OSError:
            return False

    def __getitem__(self, section:str) -> SectionDict:
        """ Return a copy of the options in <section>. Missing sections are considered empty. """
        if section not in self._options:
            return {}
        return {**self._options[section]}

    def _on_submit(self, options:ConfigDict) -> None:
        """ Update the config options with values from the dialog and save them. """
        for k, v in options.items():
            self._options.setdefault(k, {}).update(v)
        self.save()

    def open_dialog(self, parent=None) -> ConfigDialog:
        """ Open a configuration manager dialog using the spec and our current values. """
        dialog = ConfigDialog(parent)
        dialog.add_tabs(self._spec, self._options)
        dialog.submitted.connect(self._on_submit)
        return dialog
