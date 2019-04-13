from spectra_lexer import Component
from spectra_lexer.utils import str_prefix


class ComponentFactory:
    """ Goes through a given list of modules and packages to find component classes, then creates one of each.
        Tracks every component made this way in a list for introspection purposes. """

    _components: list       # List of all created components.
    _already_searched: set  # Set of IDs for all objects that have already been searched for component classes.

    def __init__(self):
        """ The base class should not be instantiated, so initialize the blacklist set with its ID. """
        self._components = []
        self._already_searched = {id(Component)}

    def __call__(self, classes_or_modules) -> list:
        """ Create instances of all component classes found in the given modules and packages.
            Only create ones we haven't seen before. Add them to the global list when finished. """
        new_components = []
        for m in classes_or_modules:
            for obj in (m, *vars(m).values()):
                if id(obj) not in self._already_searched:
                    self._already_searched.add(id(obj))
                    if isinstance(obj, type) and issubclass(obj, Component):
                        new_components.append(obj())
        self._components += new_components
        return new_components

    def make_debug_dict(self) -> dict:
        """ Make a global component dict indexed by module path to send to debug components. """
        paths = ["_".join(str_prefix(type(c).__module__, ".base").rsplit(".", 2)[-2:]) for c in self._components]
        return dict(sorted(zip(paths, self._components), key=lambda x: x[0]))
