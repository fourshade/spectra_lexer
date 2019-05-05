from typing import Callable, Iterable, List, Tuple

from .component import ComponentMeta
from .mods import DebugPackageMod
from spectra_lexer.core.mods import CommandMod, ResourceMod


class ComponentFactory:
    """ Creates components from lists of component classes/modules (referred to as "class paths").
        Tracks every created component for introspection purposes. """

    def __init__(self):
        self._components = []

    def build(self, class_paths:Iterable[object], engine_cb:Callable) -> List[Tuple[str, Callable]]:
        """ Create instances of components from classes in a path and bind them to their commands. """
        components = list(ComponentMeta.build_from_paths(class_paths))
        self._components += components
        for cmp in components:
            cmp.engine_connect(engine_cb)
        return CommandMod.bind_all(components)

    def setup(self, engine_cb:Callable) -> None:
        """ Initialize all resources from the main engine. The mod classes will sort any dependencies out. """
        ResourceMod.setup(self._components, engine_cb)
        # Send a global dict with objects from all categories to debug tools.
        engine_cb("res:debug", DebugPackageMod.package_all(self._components))
        engine_cb("init_done")
