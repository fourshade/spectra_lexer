from spectra_lexer import SpectraComponent


class ConfigManager(SpectraComponent):
    """ Configuration manager for the Spectra program. Must be called with command-line arguments
        before anything else is allowed to run (except the file I/O module). """

    _components: list

    def __init__(self):
        self._components = []

    def connect(self, component:SpectraComponent) -> None:
        self._components.append(component)

    def load(self, cfg=None, **opts) -> None:
        """ Load the config file given in the command line options, or defaults if none was given.
            Should be called before anything in the engine is allowed to run, and only once. """
        # Without a config file, all settings begin at default. There is nothing else to do.
        if not cfg:
            return
        for c in self._components:
            c.configure()


class Configurable(SpectraComponent):

    CFG_ROLE = "UNDEFINED"  # Heading for config dictionary
    CFG = {}  # Config dictionary; loaded with defaults on the class, overridden on instances at configure time.

    def configure(self, **cfg_dict) -> None:
        """ Copy the class dict of default CFG options and override those with the cfg_dict. """
        self.CFG = dict(self.CFG)
        self.CFG.update(cfg_dict)
