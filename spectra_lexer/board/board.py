""" Module for generating steno board diagram elements. """

from math import ceil
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

from .path import ArrowPathGenerator, ChainPathGenerator
from .svg import SVGElementFactory, TransformData, XMLElement

# Marker type for an SVG steno board diagram.
BoardDiagram = str


class BoardElementGroup:
    """ A group of SVG steno board elements with metadata. """

    bg = "#000000"             # Background color for key shapes.
    txtmaxarea = [20.0, 20.0]  # Maximum available area for text. Determines text scale and orientation.
    altangle = 0.0             # Alternate text orientation in degrees.
    ends_stroke = False        # If True, this element group is the last in the current stroke.
    iter_overlays = None       # Reserved for special elements that add overlays covering multiple strokes.

    def __init__(self, *elems:XMLElement) -> None:
        self.tfrm = TransformData()  # Contains the approximate center of this element in the current stroke.
        self._elems = [*elems]

    def append(self, elem:XMLElement) -> None:
        self._elems.append(elem)

    def get_offset(self) -> complex:
        return self.tfrm.offset()

    def __iter__(self) -> Iterator[XMLElement]:
        """ Iterate over all finished SVG elements, positioned correctly within the context of a single stroke. """
        return iter(self._elems)


class LinkedOverlay:
    """ Contains a chain connecting two strokes, which are shifted independently of the main stroke groupings. """

    def __init__(self, factory:SVGElementFactory, s_stroke:Sequence[BoardElementGroup],
                 e_stroke:Sequence[BoardElementGroup]) -> None:
        self._factory = factory
        self._strokes = s_stroke, e_stroke  # Element groups with the ending of one stroke and the start of another.

    def iter_overlays(self, first_tfrm:TransformData, last_tfrm:TransformData) -> Iterator[XMLElement]:
        """ For multi-element rules, connect the last element in the first stroke to the first element in the next. """
        s_stroke, e_stroke = self._strokes
        first_offset = s_stroke[-1].get_offset() + first_tfrm.offset()
        last_offset = e_stroke[0].get_offset() + last_tfrm.offset()
        yield from self._iter_layers(first_offset, last_offset)
        yield self._stroke_group(s_stroke, first_tfrm)
        yield self._stroke_group(e_stroke, last_tfrm)

    def _iter_layers(self, p1:complex, p2:complex) -> Iterator[XMLElement]:
        """ Yield SVG paths that compose a chain between the endpoints. """
        for path_data in ChainPathGenerator().iter_halves(p1, p2):
            yield self._factory.path(path_data, fill="none", stroke="#000000", stroke_width="5.0px")
            yield self._factory.path(path_data, fill="none", stroke="#B0B0B0", stroke_width="2.0px")

    def _stroke_group(self, stroke:Iterable[BoardElementGroup], tfrm:TransformData) -> XMLElement:
        """ Create a new SVG group with every element in <stroke> and translate it by <dx, dy>. """
        elems = []
        for g in stroke:
            elems += g
        return self._factory.group(*elems, transform=tfrm)


class BoardElementFactory:
    """ Factory for steno board element groups.
        Elements are added by proc_* methods, which are executed in order according to an external file. """

    def __init__(self, factory:SVGElementFactory, key_positions:Dict[str, List[int]],
                 shape_defs:Dict[str, dict], glyph_table:Dict[str, str]) -> None:
        self._factory = factory              # Standard SVG element factory.
        self._key_positions = key_positions  # Contains offsets of the board layout.
        self._shape_defs = shape_defs        # Defines paths forming the shape and inside area of steno keys.
        self._glyph_table = glyph_table      # Defines paths for each valid text glyph (and a default).

    def processed_group(self, procs:Iterable[str], bg:str, text:str=None) -> BoardElementGroup:
        """ Each string in <procs> defines a `proc`ess that positions and/or constructs SVG elements.
            Execution involves running every proc in the list, in order, on an empty BoardElementGroup. """
        grp = BoardElementGroup()
        grp.bg = bg
        # Match proc string keys to proc_* methods and call each method using the corresponding value.
        for proc_str in procs:
            p_type, p_value = proc_str.split("=", 1)
            meth = getattr(self, "proc_" + p_type, None)
            if meth is not None:
                meth(grp, p_value)
        if text is not None:
            self.proc_text(grp, text)
        return grp

    @staticmethod
    def proc_sep(grp:BoardElementGroup, *_) -> None:
        """ Set this element to separate strokes. """
        grp.ends_stroke = True

    def proc_pos(self, grp:BoardElementGroup, pos_id:str) -> None:
        """ Set the offset used in text and annotations (such as inversion arrows). """
        offset = self._key_positions[pos_id]
        grp.tfrm = TransformData.translation(*offset)

    def proc_shape(self, grp:BoardElementGroup, shape_id:str) -> None:
        """ Add an SVG path shape, then advance the offset to center any following text. """
        attrs = self._shape_defs[shape_id]
        elem = self._factory.path(attrs["d"], fill=grp.bg, stroke="#000000", transform=grp.tfrm)
        grp.append(elem)
        grp.tfrm.translate(*attrs["txtcenter"])
        grp.txtmaxarea = attrs["txtarea"]
        grp.altangle = attrs["altangle"]

    def proc_text(self, grp:BoardElementGroup, text:str, _FONT_SIZE=24, _EM_SIZE=1000, _SPACING=600) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths.
            Max font size is 24 px. Text paths are defined with an em box of 1000 units.
            600 units (or 14.4 px) is the horizontal spacing of text. """
        n = len(text) or 1
        px_per_unit = _FONT_SIZE / _EM_SIZE
        spacing = _SPACING * px_per_unit
        w, h = grp.txtmaxarea
        scale = min(1.0, w / (n * spacing))
        # If there is little horizontal space and plenty in another direction, rotate the text.
        if scale < 0.5 and h > w:
            scale = min(1.0, h / (n * spacing))
            grp.tfrm.rotate(grp.altangle)
        spacing *= scale
        font_scale = scale * px_per_unit
        x = - n * spacing / 2
        y = (10 * scale) - 3
        elems = []
        for k in text:
            tfrm = TransformData()
            tfrm.scale(font_scale, -font_scale)
            tfrm.translate(x, y)
            glyph = self._glyph_table.get(k) or self._glyph_table["DEFAULT"]
            char = self._factory.path(glyph, fill="#000000", transform=tfrm)
            elems.append(char)
            x += spacing
        g = self._factory.group(*elems, transform=grp.tfrm)
        grp.append(g)

    def inversion_group(self, strk:Sequence[BoardElementGroup]) -> BoardElementGroup:
        """ Make a new group with a set of arrow paths connecting two other groups in both directions. """
        items = []
        for grp in strk:
            items += grp
        grp = BoardElementGroup(*items)
        p1 = strk[0].get_offset()
        p2 = strk[1].get_offset()
        self._add_layers(grp, p1, p2)
        self._add_layers(grp, p2, p1)
        return grp

    def _add_layers(self, grp:BoardElementGroup, start:complex, end:complex) -> None:
        """ Add SVG path elements that compose an arrow pointing between <start> and <end>.
            Layers are shifted by an incremental offset to create a drop shadow appearance. """
        gen = ArrowPathGenerator()
        for color in "#800000", "#FF0000":
            path_data = gen.connect(start, end)
            elem = self._factory.path(path_data, fill="none", stroke=color, stroke_width="1.5px")
            grp.append(elem)
            start -= 1j
            end -= 1j

    def linked_group(self, strk1:Sequence[BoardElementGroup], strk2:Sequence[BoardElementGroup]) -> BoardElementGroup:
        """ Make a chain connecting two strokes, which are shifted independently of the main stroke groupings. """
        grp = BoardElementGroup()
        grp.ends_stroke = True
        grp.iter_overlays = LinkedOverlay(self._factory, strk1, strk2).iter_overlays
        return grp

    def base_pair(self, base_groups:Sequence[BoardElementGroup]) -> Tuple[XMLElement, XMLElement]:
        """ Make a <use> element for the base present in every stroke matching a <defs> element. """
        base_id = "_BASE"
        items = []
        for grp in base_groups:
            items += grp
        g = self._factory.group(*items, id=base_id)
        defs = self._factory.defs(g)
        base = self._factory.use(base_id)
        return defs, base


class GridLayoutEngine:
    """ Calculates dimensions and transforms for items arranged in a grid. """

    def __init__(self, x:int, y:int, w:int, h:int) -> None:
        self._x = x  # X offset for the full grid.
        self._y = y  # Y offset for the full grid.
        self._w = w  # Width of a single cell.
        self._h = h  # Height of a single cell.

    def arrange(self, count:int, aspect_ratio:float) -> Tuple[int, int]:
        """ Calculate the best arrangement of <count> cells in rows and columns
            for the best possible scale in a viewing area of <aspect_ratio>. """
        diagram_ratio = self._w / self._h
        # rel_ratio is the aspect ratio of one cell divided by that of the viewing area.
        rel_ratio = diagram_ratio / aspect_ratio
        r = min(rel_ratio, 1 / rel_ratio)
        s = int((count * r) ** 0.5) or 1
        if r * ceil(count / s) > (s + 1):
            s += 1
        t = ceil(count / s)
        return (s, t) if rel_ratio < 1 else (t, s)

    def _offset_tfrm(self, i:int, ncols:int) -> TransformData:
        """ Create a (dx, dy) translation for row-major cell <i> in a grid with <ncols> columns. """
        dx = self._w * (i % ncols)
        dy = self._h * (i // ncols)
        return TransformData.translation(dx, dy)

    def transforms(self, count:int, ncols:int) -> Sequence[TransformData]:
        """ Create evenly spaced offset transformations for a grid with <count> cells in <ncols> columns. """
        return [self._offset_tfrm(i, ncols) for i in range(count)]

    def viewbox(self, rows:int, cols:int) -> Tuple[int, int, int, int]:
        """ Return the final offset and dimensions for a grid of size <rows, cols>. """
        return (self._x, self._y, self._w * cols, self._h * rows)


class BoardDocumentFactory:
    """ Factory for SVG steno board documents corresponding to user input. """

    def __init__(self, factory:SVGElementFactory, defs:XMLElement, base:XMLElement, layout:GridLayoutEngine) -> None:
        self._factory = factory  # Standard SVG element factory.
        self._defs = defs        # SVG defs element to include at the beginning of every document.
        self._base = base        # Base SVG element that is shown under every stroke diagram.
        self._layout = layout    # Layout engine to position each stroke diagram on the document.

    @staticmethod
    def _stroke_groups(elems:Iterable[BoardElementGroup]) -> List[List[XMLElement]]:
        stroke_elems = []
        stroke_list = [stroke_elems]
        for el in elems:
            stroke_elems += el
            if el.ends_stroke:
                stroke_elems = []
                stroke_list.append(stroke_elems)
        return stroke_list

    @staticmethod
    def _overlays(elems:Iterable[BoardElementGroup], tfrms:Sequence[TransformData]) -> List[XMLElement]:
        overlay_list = []
        i = 0
        for el in elems:
            if el.iter_overlays is not None:
                overlay_list += el.iter_overlays(tfrms[i], tfrms[i + 1])
            if el.ends_stroke:
                i += 1
        return overlay_list

    def make_svg(self, elems:Iterable[BoardElementGroup], aspect_ratio:float=None) -> BoardDiagram:
        """ Arrange all SVG elements in a document with a separate diagram for each stroke.
            Transform each diagram to be tiled in a grid layout to match the aspect ratio.
            Add overlays (if any), put it all in a new SVG document, and return the final encoded string. """
        strokes = self._stroke_groups(elems)
        stroke_count = len(strokes)
        # If no aspect ratio is given, aspect_ratio=0.0001 ensures that all boards end up in one column.
        rows, cols = self._layout.arrange(stroke_count, aspect_ratio or 0.0001)
        tfrms = self._layout.transforms(stroke_count, cols)
        viewbox = self._layout.viewbox(rows, cols)
        diagrams = [self._factory.group(self._base, *stroke, transform=tfrm) for stroke, tfrm in zip(strokes, tfrms)]
        overlays = self._overlays(elems, tfrms)
        document = self._factory.svg(self._defs, *diagrams, *overlays, viewbox=viewbox)
        return document.serialize()
