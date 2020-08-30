from typing import Iterable

from .io import ConfigIO, ConfigMapping, SectionMapping
from .qt import ConfigDialog
from .spec import ConfigSpec


class QtConfigManager:
    """ Config settings handler for Qt-based GUIs. Settings are currently only mutable through a dialog. """

    def __init__(self, filename:str, specs:Iterable[ConfigSpec]=(), *, io:ConfigIO=None) -> None:
        """ At minimum, the starting options include all default values from <specs>. """
        self._filename = filename    # Full name of valid file in CFG format.
        self._specs = specs          # Specifications for sections shown in the config manager.
        self._io = io or ConfigIO()  # Performs whole reads/writes to CFG files.
        self._options = {spec.name: {opt.name: opt.default for opt in spec.options} for spec in specs}

    def load(self) -> bool:
        """ Try to read config options from the CFG file. Return True if successful. """
        try:
            options = self._io.read(self._filename)
            for section, page in options.items():
                self._options.setdefault(section, {}).update(page)
            return True
        except OSError:
            return False

    def save(self) -> bool:
        """ Save all config options to the CFG file. Return True if successful. """
        try:
            self._io.write(self._filename, self._options)
            return True
        except OSError:
            return False

    def get_section(self, section:str) -> SectionMapping:
        """ Return a copy of the options in <section>. Missing sections are considered empty. """
        if section not in self._options:
            return {}
        return {**self._options[section]}

    # FIXME horrible pipe-delimited string kludge follows.

    def _on_submit(self, options:ConfigMapping) -> None:
        """ Update the config options with values from the dialog and save them. """
        for k, v in options.items():
            section, name = k.split('|')
            self._options[section][name] = v
        self.save()

    def open_dialog(self) -> ConfigDialog:
        """ Open a configuration manager dialog using the specs and our current values. """
        dialog = ConfigDialog()
        for spec in self._specs:
            section = spec.name
            page = self._options[section]
            for opt in spec.options:
                key = '|'.join([section, opt.name])
                value = page[opt.name]
                dialog.add_option(key, value, spec.title, opt.title, opt.description)
        dialog.submitted.connect(self._on_submit)
        return dialog
