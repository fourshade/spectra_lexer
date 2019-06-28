""" Module for generating steno board diagram elements. """

from math import ceil
from typing import Callable, Iterable

from .path import PathChain, PathInversion
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

    def _append_offset(self, child) -> None:
        child.translate(self.offset.real, self.offset.imag)
        self.append(child)

    def process(self, proc_defs:dict) -> None:
        """ Parse XML proc attributes and child nodes. Merge any redundant elements at the end. """
        for k in [*self.keys()]:
            if k in BoardElementProcs:
                attr = BoardElementProcs[k]
                proc = getattr(self, attr)
                proc(self.pop(k), proc_defs[k])

    def proc_path(self, id:str, d:dict) -> None:
        elem = SVGPath(d=d[id])
        self._append_offset(elem)

    def proc_pos(self, id:str, d:dict) -> None:
        """ Add to the total offset used in text and annotations (such as inversion arrows)."""
        self.offset += complex(*d[id])

    def proc_shape(self, id:str, d:dict) -> None:
        attrs = d[id]
        self.proc_path("d", attrs)
        self.offset += complex(*attrs["txtcenter"])
        self.txtmaxwidth = attrs["txtwidth"]
        self.txtspacing = attrs["txtspacing"]

    FONT_SIZE = 24  # Size is 24 pt.
    EM_SIZE = 1000  # Text paths are defined with an em box of 1000 units.
    RELATIVE_SIZE: float = FONT_SIZE / EM_SIZE

    def proc_text(self, text:str, glyphs:dict) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths. """
        n = len(text) or 1
        spacing = self.txtspacing
        scale = min(1.0, self.txtmaxwidth / (n * spacing))
        spacing *= scale
        font_scale = scale * self.RELATIVE_SIZE
        x = - n * spacing / 2
        y = (10 * scale) - 3
        for k in text:
            char = SVGPath(fill="#000000", d=glyphs[k])
            self._append_offset(char)
            char.transform(font_scale, -font_scale, x, y)
            x += spacing

    def add_final(self, add:Callable) -> None:
        """ Add any required elements to the final group. """
        add(self)


class BoardStrokeGap(BoardElement):
    """ Essentially a sentinel class for the gap between strokes. """

    def add_final(self, add:Callable) -> None:
        add(None)


class BoardConnectorGroup(BoardElement):
    """ Abstract class for a group of elements with a special connection. """

    PATH_DATA_CLS: type  # Constructor for a path data string from two complex endpoints.
    LAYER_DATA: list = []
    LAYER_OFFSET: complex = 0j

    def connector(self) -> BoardElement:
        """ Create paths in both directions between children shifted by an optional offset after each iteration.
            Useful to create a layered or drop shadow appearance. Requires at least two children. """
        elem = BoardElement()
        if len(self) < 2:
            return elem
        first, *_, last = self
        endpoints = first.offset, last.offset
        data_cls = self.PATH_DATA_CLS
        layer_data = self.LAYER_DATA
        offset = self.LAYER_OFFSET
        for reverse in (False, True):
            pts = endpoints
            for color, width in layer_data:
                path_data = data_cls(*pts, reverse).to_string()
                elem.append(SVGPath(d=path_data, fill="none", stroke=color, **{"stroke-width": width}))
                pts = [p + offset for p in pts]
        return elem


class BoardInversionGroup(BoardConnectorGroup):
    """ Draws bent arrows pointing between its children. """

    PATH_DATA_CLS = PathInversion
    LAYER_DATA = [("#800000", "1.5"),
                  ("#FF0000", "1.5")]
    LAYER_OFFSET = -1j

    def add_final(self, add:Callable) -> None:
        for elem in self:
            add(elem)
        add(self.connector())


class BoardLinkedGroup(BoardConnectorGroup):
    """ Draws a chain connecting its children."""

    PATH_DATA_CLS = PathChain
    LAYER_DATA = [("#000000", "5.0"),
                  ("#B0B0B0", "2.0")]

    class _LinkedElement(BoardElement):
        """ Chain endpoint element wrapper. """
        def set_offset(self, dx:float, dy:float) -> None:
            """ Shift chain elements independently of the main stroke groupings. """
            base, = self
            self.translate(dx, dy)
            self.offset = base.offset + complex(dx, dy)

    def __init__(self, *elems):
        """ Wrap elements involved in a chain so the originals aren't mutated. """
        super().__init__(*map(self._LinkedElement, elems))

    def add_final(self, add:Callable) -> None:
        add(None, on_tf=self.add_chain)

    def add_chain(self, sx:float, sy:float, ex:float, ey:float) -> BoardElement:
        first, *_, last = self
        first.set_offset(sx, sy)
        last.set_offset(ex, ey)
        return BoardElement(self.connector(), first, last)


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
        for i, (dx, dy), in enumerate(tfrms):
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
