""" Module for generating steno board diagram elements. """

from math import ceil
from typing import Callable, Iterable

from .path import PathChain, PathGenerator, PathInversion
from .svg import SVGDefs, SVGDocument, SVGElement, SVGPath


class ProcsTable(dict):

    def __call__(self, procs_cls:type) -> type:
        """ Add every processor method attribute (and its key) found in the decorated class. """
        self.update({attr[5:]: attr for attr in dir(procs_cls) if attr.startswith("proc_")})
        return procs_cls


BoardElementProcs = ProcsTable()


@BoardElementProcs
class BoardElement(SVGElement):

    txtmaxwidth: float = 20.0
    txtspacing: float = 14.4
    offset: complex = 0j  # Offsets are stored and added as complex numbers, which work well for 2D points.

    def _add_offset(self, dx:float, dy:float):
        self.offset += complex(dx, dy)

    def process(self, proc_defs:dict) -> None:
        """ Parse XML proc attributes and child nodes. Merge any redundant elements at the end. """
        for k in [*self.keys()]:
            if k in BoardElementProcs:
                attr = BoardElementProcs[k]
                proc = getattr(self, attr)
                proc(self.pop(k), proc_defs[k])

    def proc_path(self, id:str, d:dict) -> None:
        elem = SVGPath(d=d[id])
        elem.translate(self.offset.real, self.offset.imag)
        self.append(elem)

    def proc_pos(self, id:str, d:dict) -> None:
        """ Add to the total offset used in text and annotations (such as inversion arrows)."""
        self._add_offset(*d[id])

    def proc_shape(self, id:str, d:dict) -> None:
        attrs = d[id]
        self.proc_path("d", attrs)
        self._add_offset(*attrs["txtcenter"])
        self.txtmaxwidth = attrs["txtwidth"]
        self.txtspacing = attrs["txtspacing"]

    def proc_text(self, text:str, glyphs:dict, _FONT_SIZE:int=24, _EM_SIZE:int=1000) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths.
            Max font size is 24 pt. Text paths are defined with an em box of 1000 units. """
        n = len(text) or 1
        spacing = self.txtspacing
        scale = min(1.0, self.txtmaxwidth / (n * spacing))
        spacing *= scale
        font_scale = scale * _FONT_SIZE / _EM_SIZE
        x = - n * spacing / 2 + self.offset.real
        y = (10 * scale) - 3 + self.offset.imag
        for k in text:
            char = SVGPath(fill="#000000", d=glyphs[k])
            char.transform(font_scale, -font_scale, x, y)
            self.append(char)
            x += spacing

    def add_final(self, add:Callable) -> None:
        """ Add any required elements to the final group. """
        add(self)


class PathConnector(PathGenerator):
    """ Abstract class for a special element connection. """

    LAYER_DATA: list = [("#000000", "1", 0j)]

    def connection(self, start_elem:BoardElement, end_elem:BoardElement) -> BoardElement:
        """ Create paths between two elements, layered to create a drop shadow appearance. """
        p1, p2 = start_elem.offset, end_elem.offset
        return self._make_connector(p1, p2)

    def _make_connector(self, p1:complex, p2:complex) -> BoardElement:
        """ Create paths in both directions between two points shifted by an optional offset after each iteration. """
        elem = BoardElement()
        for reverse in (False, True):
            path = ""
            for color, width, offset in self.LAYER_DATA:
                # If the path hasn't moved, don't regenerate the string data; it will be the same.
                if offset or not path:
                    self.clear()
                    self.draw(p1 + offset, p2 + offset, reverse)
                    path = self.to_string()
                elem.append(SVGPath(d=path, fill="none", stroke=color, **{"stroke-width": width}))
        return elem


class PathConnectorInversion(PathConnector, PathInversion):

    LAYER_DATA = [("#800000", "1.5", 0j),
                  ("#FF0000", "1.5", -1j)]


class PathConnectorChain(PathConnector, PathChain):

    LAYER_DATA = [("#000000", "5.0", 0j),
                  ("#B0B0B0", "2.0", 0j)]


class BoardStrokeGap(BoardElement):
    """ Essentially a sentinel class for the gap between strokes. """

    def add_final(self, add:Callable) -> None:
        add(None)


class BoardInversionGroup(BoardElement):
    """ Draws bent arrows pointing between its children. """

    def add_final(self, add:Callable) -> None:
        for elem in self:
            add(elem)
        first, *_, last = self
        arrows = PathConnectorInversion().connection(first, last)
        add(arrows)


class BoardLinkedGroup(BoardElement):
    """ Draws a chain connecting its children, which are shifted independently of the main stroke groupings. """

    class _LinkedElement(BoardElement):
        """ Chain endpoint element wrapper. """
        def set_offset(self, dx:float, dy:float) -> None:
            base, = self
            self.offset = base.offset
            self.translate(dx, dy)
            self._add_offset(dx, dy)

    def add_final(self, add:Callable) -> None:
        add(None, on_tf=self.add_chain)

    def add_chain(self, sx:float, sy:float, ex:float, ey:float) -> BoardElement:
        """ Wrap elements involved in a chain so the originals aren't mutated. """
        first, *_, last = map(self._LinkedElement, self)
        first.set_offset(sx, sy)
        last.set_offset(ex, ey)
        chain = PathConnectorChain().connection(first, last)
        return BoardElement(chain, first, last)


class DocumentGroups(list):
    """ Groups, transforms, and encodes SVG elements into a final SVG steno board document. """

    _defs: SVGDefs
    _base: SVGElement

    def __init__(self, base:SVGElement):
        """ Make a <use> element out of the base. """
        super().__init__()
        self._defs = SVGDefs()
        self._base = self._defs.make_usable(base)

    def add_all(self, elems:Iterable[BoardElement]) -> None:
        """ Add all given SVG elements to groups. """
        add = self.add
        add(None)
        for elem in elems:
            elem.add_final(add)

    def add(self, elem:BoardElement=None, on_tf:Callable=None) -> None:
        """ Only add to the last group. If None is added, start a new group instead. """
        if elem is None:
            self.append(BoardElement(self._base))
        else:
            self[-1].append(elem)
        if on_tf is not None:
            self[-1].on_tf = on_tf

    def transform(self, tfrms:list) -> None:
        for i, (dx, dy) in enumerate(tfrms):
            group = self[i]
            group.translate(dx, dy)
            if hasattr(group, "on_tf"):
                self.append(group.on_tf(*tfrms[i-1], dx, dy))

    def finish(self, *viewbox:int) -> bytes:
        """ Create the final document with the viewbox and all defs and return it encoded. """
        document = SVGDocument(self._defs, *self)
        document.set_viewbox(*viewbox)
        return document.encode()


class BoardFactory:
    """ Top-level class for preparing SVG steno board documents from elements. """

    _base: BoardElement
    _bounds: Iterable[int]  # x/y offset and width/height for the viewbox, per stroke diagram.

    def __init__(self, base_elems:Iterable[BoardElement], bounds:Iterable[int]):
        """ Add all base elements to a new group (if more than one). """
        first, *others = [*base_elems] or [BoardElement()]
        self._base = BoardElement(first, *others) if others else first
        self._bounds = bounds

    def __call__(self, elems:Iterable[BoardElement], aspect_ratio:float) -> bytes:
        """ Group and transform each SVG element, then encode them in a new SVG document. """
        groups = DocumentGroups(self._base)
        groups.add_all(elems)
        return self._arranged(groups, aspect_ratio)

    def _arranged(self, groups:DocumentGroups, device_ratio:float) -> bytes:
        """ Diagrams are tiled left-to-right, top-to-bottom in a grid layout.
            Place all diagrams in their proper location and return the final encoded document. """
        count = len(groups)
        x, y, w, h = self._bounds
        board_ratio = w / h
        rows, cols = self._dimensions(count, board_ratio / device_ratio)
        tfrms = []
        for i in range(count):
            step_y, step_x = divmod(i, cols)
            dx = w * step_x
            dy = h * step_y
            tfrms.append((dx, dy))
        groups.transform(tfrms)
        return groups.finish(x, y, w * cols, h * rows)

    def _dimensions(self, count:int, rel_ratio:float) -> tuple:
        """ Calculate the best arrangement of <count> sub-diagrams in rows and columns for the best possible scale.
            <rel_ratio> is the aspect ratio of one diagram divided by that of the device viewing area. """
        r = min(rel_ratio, 1 / rel_ratio)
        s = int((count * r) ** 0.5) or 1
        s += r * ceil(count / s) > (s + 1)
        t = ceil(count / s)
        return (s, t) if rel_ratio < 1 else (t, s)
