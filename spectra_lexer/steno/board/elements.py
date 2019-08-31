""" Module for generating steno board diagram elements. """

from math import ceil
from typing import Dict, Iterable, List, Tuple

from .path import PathChain, PathGenerator, PathInversion
from .svg import SVGDefs, SVGDocument, SVGElement, SVGPath


class BoardElement(SVGElement):

    offset: complex = 0j       # Offsets are stored and added as complex numbers, which work well for 2D points.
    ends_stroke: bool = False  # Does this element signal the end of a stroke?
    add_global = None          # Reserved for elements that add to multiple strokes.

    def _add_offset(self, dx:float, dy:float) -> None:
        self.offset += complex(dx, dy)

    def _append_at_offset(self, elem) -> None:
        elem.translate(self.offset.real, self.offset.imag)
        self.append(elem)


class ProcessedBoardElement(BoardElement):

    _txtmaxarea: tuple = (20.0, 20.0)
    _txtspacing: float = 14.4

    def proc_path(self, e_id:str, d:dict) -> None:
        elem = SVGPath(d=d[e_id])
        self._append_at_offset(elem)

    def proc_pos(self, e_id:str, d:dict) -> None:
        """ Add to the total offset used in text and annotations (such as inversion arrows)."""
        self._add_offset(*d[e_id])

    def proc_shape(self, e_id:str, d:dict) -> None:
        attrs = d[e_id]
        elem = SVGPath(d=attrs["d"])
        self._append_at_offset(elem)
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

    def __init__(self, defs:Dict[str, dict]) -> None:
        # Record every processor method attribute (and its key) found in the elements class.
        self._proc_table = {attr[5:]: attr for attr in dir(ProcessedBoardElement) if attr.startswith("proc_")}
        self._proc_params = {k: defs.get(k) or {} for k in self._proc_table}
        self.bounds = defs["document"]["bounds"]

    def __call__(self, elem:dict) -> ProcessedBoardElement:
        """ Process node-type elements recursively into board elements. """
        board_elem = ProcessedBoardElement(*map(self, elem), **elem)
        self.process(board_elem)
        return board_elem

    def process(self, elem:ProcessedBoardElement) -> None:
        """ Parse XML proc attributes. Merge any redundant elements at the end. """
        for k in [*elem.keys()]:
            if k in self._proc_table:
                attr = self._proc_table[k]
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

    ends_stroke = True


class BoardInversionGroup(BoardElement):
    """ Draws bent arrows pointing between its children. """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        first, *_, last = self
        arrows = PathConnectorInversion().connection(first, last)
        self.append(arrows)


class BoardLinkedGroup(BoardElement):
    """ Draws a chain connecting its children, which are shifted independently of the main stroke groupings. """

    ends_stroke = True

    class _LinkedElement(BoardElement):
        """ Chain endpoint element wrapper. """
        def set_offset(self, dx:float, dy:float) -> None:
            base, = self
            self.offset = base.offset
            self.translate(dx, dy)
            self._add_offset(dx, dy)

    def add_global(self, sx:float, sy:float, ex:float, ey:float) -> BoardElement:
        """ Wrap elements involved in a chain so the originals aren't mutated. """
        first, *_, last = map(self._LinkedElement, self)
        first.set_offset(sx, sy)
        last.set_offset(ex, ey)
        chain = PathConnectorChain().connection(first, last)
        return BoardElement(chain, first, last)


class BoardFactory:
    """ Top-level class for preparing SVG steno board documents from elements. """

    def __init__(self, base:SVGElement, x:int, y:int, w:int, h:int) -> None:
        """ Groups and transforms SVG elements into a final series of SVG steno board graphics. """
        self._defs = defs = SVGDefs()
        self._base = defs.make_usable(base)  # Base SVG element (or group of elements) that is shown on every stroke.
        self._offset = x, y                  # x/y offset for the viewbox, per stroke diagram.
        self._size = w, h                    # width/height for the viewbox, per stroke diagram.

    def __call__(self, elems:Iterable[BoardElement], device_ratio:float) -> bytes:
        """ Split all given SVG elements into strokes, then create groups with defs that <use> the current base.
            Transform the groups according to the aspect ratio, then encode them in a new SVG document. """
        strokes = self._split(elems)
        count = len(strokes)
        rows, cols = self._dimensions(count, device_ratio)
        groups = self._arrange(strokes, cols)
        return self._make_document(groups, rows, cols)

    @staticmethod
    def _split(elems:Iterable[BoardElement]) -> List[List[BoardElement]]:
        """ Split the iterable of elements into a separate list for each stroke. """
        last = []
        strokes = [last]
        for elem in elems:
            last.append(elem)
            if elem.ends_stroke:
                last = []
                strokes.append(last)
        return strokes

    def _arrange(self, lists:List[Iterable[BoardElement]], cols:int) -> List[BoardElement]:
        """ Arrange all diagrams in their proper location, tiled left-to-right, top-to-bottom in a grid layout. """
        groups = [BoardElement(self._base) for _ in lists]
        tfrms = self._get_transforms(cols, len(lists))
        for i, (dx, dy) in enumerate(tfrms):
            g = groups[i]
            for el in lists[i]:
                if el.add_global is None:
                    g.append(el)
                else:
                    groups.append(el.add_global(dx, dy, *tfrms[i + 1]))
            g.translate(dx, dy)
        return groups

    def _dimensions(self, count:int, device_ratio:float) -> Tuple[int, int]:
        """ Calculate the best arrangement of <count> sub-diagrams in rows and columns for the best possible scale.
            <rel_ratio> is the aspect ratio of one diagram divided by that of the device viewing area. """
        w, h = self._size
        board_ratio = w / h
        rel_ratio = board_ratio / device_ratio
        r = min(rel_ratio, 1 / rel_ratio)
        s = int((count * r) ** 0.5) or 1
        s += r * ceil(count / s) > (s + 1)
        t = ceil(count / s)
        return (s, t) if rel_ratio < 1 else (t, s)

    def _get_transforms(self, cols:int, count:int) -> List[Tuple[int, int]]:
        """ Create a list of evenly spaced (dx, dy) grid translations for the current bounds. """
        w, h = self._size
        tfrms = []
        for i in range(count):
            step_y, step_x = divmod(i, cols)
            dx = w * step_x
            dy = h * step_y
            tfrms.append((dx, dy))
        return tfrms

    def _make_document(self, groups:Iterable[BoardElement], rows:int, cols:int) -> bytes:
        """ Encode all groups in a new SVG document. """
        document = SVGDocument(self._defs, *groups)
        x, y = self._offset
        w, h = self._size
        document.set_viewbox(x, y, w * cols, h * rows)
        return document.encode()
