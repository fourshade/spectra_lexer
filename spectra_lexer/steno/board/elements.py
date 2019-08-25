""" Module for generating steno board diagram elements. """

from math import ceil
from typing import Iterable

from .path import PathChain, PathGenerator, PathInversion
from .svg import SVGDefs, SVGDocument, SVGElement, SVGPath


class BoardElement(SVGElement):

    offset: complex = 0j  # Offsets are stored and added as complex numbers, which work well for 2D points.

    def _add_offset(self, dx:float, dy:float) -> None:
        self.offset += complex(dx, dy)

    def _append_at_offset(self, elem) -> None:
        elem.translate(self.offset.real, self.offset.imag)
        self.append(elem)

    def add_final(self, group:SVGElement) -> None:
        """ Add any required elements to the final group. """
        group.append(self)


class ProcessedBoardElement(BoardElement):

    _txtmaxarea: tuple = (20.0, 20.0)
    _txtspacing: float = 14.4

    def proc_path(self, id:str, d:dict) -> None:
        elem = SVGPath(d=d[id])
        self._append_at_offset(elem)

    def proc_pos(self, id:str, d:dict) -> None:
        """ Add to the total offset used in text and annotations (such as inversion arrows)."""
        self._add_offset(*d[id])

    def proc_shape(self, id:str, d:dict) -> None:
        attrs = d[id]
        self.proc_path("d", attrs)
        self._add_offset(*attrs["txtcenter"])
        self._txtmaxarea = (*attrs["txtarea"],)
        self._txtspacing = attrs["txtspacing"]

    def proc_text(self, text:str, glyphs:dict, _FONT_SIZE:int=24, _EM_SIZE:int=1000) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths.
            Max font size is 24 pt. Text paths are defined with an em box of 1000 units. """
        elem = BoardElement(fill="#000000")
        self._append_at_offset(elem)
        n = len(text) or 1
        spacing = self._txtspacing
        w, h = self._txtmaxarea
        scale = min(1.0, w / (n * spacing))
        if scale < 0.5 and h > w:
            scale = min(1.0, h / (n * spacing))
            elem.rotate(90)
        spacing *= scale
        font_scale = scale * _FONT_SIZE / _EM_SIZE
        x = - n * spacing / 2
        y = (10 * scale) - 3
        for k in text:
            char = SVGPath(d=glyphs[k])
            char.transform(font_scale, 0, 0, -font_scale, x, y)
            elem.append(char)
            x += spacing


class BoardElementProcessor:

    # Record every processor method attribute (and its key) found in the elements class.
    PROC_TABLE = {attr[5:]: attr for attr in dir(ProcessedBoardElement) if attr.startswith("proc_")}

    _proc_params: dict

    def __init__(self, defs:dict) -> None:
        self._proc_params = {k: defs.get(k) or {} for k in self.PROC_TABLE}

    def __call__(self, elem:dict) -> ProcessedBoardElement:
        """ Process node-type elements recursively into board elements. """
        board_elem = ProcessedBoardElement(*map(self, elem), **elem)
        self.process(board_elem)
        return board_elem

    def process(self, elem:ProcessedBoardElement) -> None:
        """ Parse XML proc attributes. Merge any redundant elements at the end. """
        for k in [*elem.keys()]:
            if k in self.PROC_TABLE:
                attr = self.PROC_TABLE[k]
                proc = getattr(elem, attr)
                proc(elem.pop(k), self._proc_params[k])


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

    def add_final(self, group:BoardElement) -> None:
        pass


class BoardInversionGroup(BoardElement):
    """ Draws bent arrows pointing between its children. """

    def add_final(self, group:BoardElement) -> None:
        group.extend(self)
        first, *_, last = self
        arrows = PathConnectorInversion().connection(first, last)
        group.append(arrows)


class BoardLinkedGroup(BoardElement):
    """ Draws a chain connecting its children, which are shifted independently of the main stroke groupings. """

    class _LinkedElement(BoardElement):
        """ Chain endpoint element wrapper. """
        def set_offset(self, dx:float, dy:float) -> None:
            base, = self
            self.offset = base.offset
            self.translate(dx, dy)
            self._add_offset(dx, dy)

    def add_final(self, group:BoardElement) -> None:
        group.on_tf = self.add_chain

    def add_chain(self, sx:float, sy:float, ex:float, ey:float) -> BoardElement:
        """ Wrap elements involved in a chain so the originals aren't mutated. """
        first, *_, last = map(self._LinkedElement, self)
        first.set_offset(sx, sy)
        last.set_offset(ex, ey)
        chain = PathConnectorChain().connection(first, last)
        return BoardElement(chain, first, last)


class DocumentGroups:
    """ Groups, transforms, and encodes SVG elements into a final SVG steno board document. """

    _defs: SVGDefs
    _groups: list

    def __init__(self, base:SVGElement, elems:Iterable[BoardElement]) -> None:
        """ Make a <use> element out of the base and add all given SVG elements to groups. """
        self._defs = SVGDefs()
        base_use = self._defs.make_usable(base)
        last = BoardElement(base_use)
        groups = self._groups = [last]
        for elem in elems:
            # Only provide the last group. If nothing is added, start a new group instead.
            start = len(last)
            elem.add_final(last)
            if len(last) == start:
                last = BoardElement(base_use)
                groups.append(last)

    def __len__(self) -> int:
        return len(self._groups)

    def transform(self, tfrms:list) -> None:
        """ Place all diagrams in their proper location, tiled left-to-right, top-to-bottom in a grid layout. """
        for i, (dx, dy) in enumerate(tfrms):
            group = self._groups[i]
            group.translate(dx, dy)
            if hasattr(group, "on_tf"):
                self._groups.append(group.on_tf(dx, dy, *tfrms[i+1]))

    def finish(self, *viewbox:int) -> bytes:
        """ Create the final document with the viewbox and all defs and return it encoded. """
        document = SVGDocument(self._defs, *self._groups)
        document.set_viewbox(*viewbox)
        return document.encode()


class BoardFactory:
    """ Top-level class for preparing SVG steno board documents from elements. """

    _base: BoardElement
    _bounds: Iterable[int]  # x/y offset and width/height for the viewbox, per stroke diagram.

    def __init__(self, base_elems:Iterable[BoardElement], bounds:Iterable[int]) -> None:
        """ Add all base elements to a new group (if more than one). """
        first, *others = [*base_elems] or [BoardElement()]
        self._base = BoardElement(first, *others) if others else first
        self._bounds = bounds

    def __call__(self, elems:Iterable[BoardElement], device_ratio:float) -> bytes:
        """ Group and transform each SVG element, then encode them in a new SVG document. """
        groups = DocumentGroups(self._base, elems)
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
