from spectra_lexer import Component


class ComponentFactory:
    """ Goes through a given list of modules and packages to find component classes, then creates one of each.
        Tracks every component made this way in a list for introspection purposes. """

    components: list       # List of all created components.
    already_searched: set  # Set of IDs for all objects that have already been searched for component classes.

    def __init__(self):
        """ The base class should not be instantiated, so initialize the blacklist set with its ID. """
        self.components = []
        self.already_searched = {id(Component)}

    def __call__(self, classes_or_modules) -> list:
        """ Create instances of all component classes found in the given modules and packages.
            Only create ones we haven't seen before. Add them to the global list when finished. """
        new_components = []
        for m in classes_or_modules:
            for obj in (m, *vars(m).values()):
                if id(obj) not in self.already_searched:
                    self.already_searched.add(id(obj))
                    if isinstance(obj, type) and issubclass(obj, Component):
                        new_components.append(obj())
        self.components += new_components
        return new_components
