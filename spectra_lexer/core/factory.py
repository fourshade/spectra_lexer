import sys
from typing import Callable, Dict, Iterable, List, Tuple

from .builder import ClassBuilder
from .component import Component
from .mods import CommandMod, PackagedModMeta, ResourceMod
from spectra_lexer.types import package


class ComponentFactory:
    """ Creates components from lists of component classes/modules (referred to as "class paths").
        Tracks every created component and mod for introspection purposes. """

    _cmp_builder: ClassBuilder

    def __init__(self):
        self._cmp_builder = ClassBuilder(Component)

    def build(self, class_paths:Iterable[object], engine_cb:Callable) -> List[Tuple[str, Callable]]:
        """ Create instances of components from classes in a path and bind them to their commands and resources. """
        all_commands = []
        components = self._cmp_builder.build(class_paths)
        for cmp in components:
            cmp.engine_connect(engine_cb)
            all_commands += CommandMod.bind_all(cmp)
        return all_commands

    def setup(self, engine_cb:Callable) -> None:
        """ Initialize all resources in order. The manager will sort any dependencies out. """
        ResourceMod.setup(engine_cb)
        # Send a global object dict to debug tools.
        engine_cb("res:debug", self._all_objects())
        engine_cb("init_done")

    def _all_objects(self) -> Dict[str, package]:
        """ Return a dict with objects from all categories for debug purposes. """
        d = {"components": self._cmp_builder.package()}
        d.update(PackagedModMeta.all_packages())
        d["modules"] = package(sys.modules, root_key="__init__")
        return d
