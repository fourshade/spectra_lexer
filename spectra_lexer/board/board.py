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


class ColumnTransforms:
    """ Creates evenly spaced offset transformations for a grid with a given size and column count. """

    def __init__(self, w:int, h:int, ncols:int) -> None:
        self._w = w
        self._h = h
        self._ncols = ncols

    def __getitem__(self, i:int) -> TransformData:
        """ Create a (dx, dy) translation for row-major item <i> in the grid. """
        dx = self._w * (i % self._ncols)
        dy = self._h * (i // self._ncols)
        return TransformData.translation(dx, dy)


class LinkedOverlay:
    """ Contains a chain connecting two strokes, which are shifted independently of the main stroke groupings. """

    def __init__(self, factory:SVGElementFactory, s_stroke:Sequence[BoardElementGroup],
                 e_stroke:Sequence[BoardElementGroup]) -> None:
        self._factory = factory
        self._strokes = s_stroke, e_stroke  # Element groups with the ending of one stroke and the start of another.

    def iter_overlays(self, tfrms:ColumnTransforms, i:int) -> Iterator[XMLElement]:
        """ <sx, sy> is the offset of the beginning stroke, and <ex, ey> is the offset of the ending stroke.
            For multi-element rules, connect the last element in the first stroke to the first element in the next. """
        s_stroke, e_stroke = self._strokes
        first_tfrm = tfrms[i]
        last_tfrm = tfrms[i + 1]
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

    def proc_text(self, grp:BoardElementGroup, text:str, _FONT_SIZE=24, _EM_SIZE=1000, _TXTSPACING=14.4) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths.
            Max font size is 24 pt. Text paths are defined with an em box of 1000 units.
            14.4 px is the horizontal spacing of text in pixels. """
        n = len(text) or 1
        spacing = _TXTSPACING
        w, h = grp.txtmaxarea
        scale = min(1.0, w / (n * spacing))
        # If there is little horizontal space and plenty in another direction, rotate the text.
        if scale < 0.5 and h > w:
            scale = min(1.0, h / (n * spacing))
            grp.tfrm.rotate(grp.altangle)
        spacing *= scale
        font_scale = scale * _FONT_SIZE / _EM_SIZE
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

    def base_group(self, *base_elems:BoardElementGroup) -> BoardElementGroup:
        """ Make a <use> element for the base present in every stroke matching a <defs> element. """
        base_id = "_BASE"
        items = []
        for grp in base_elems:
            items += grp
        g = self._factory.group(*items, id=base_id)
        defs = self._factory.defs(g)
        base = self._factory.use(base_id)
        return BoardElementGroup(defs, base)


class BoardDocumentFactory:
    """ Factory for SVG steno board documents corresponding to user input. """

    _DEFAULT_RATIO = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    def __init__(self, factory:SVGElementFactory, defs:XMLElement, base:XMLElement, x:int, y:int, w:int, h:int) -> None:
        self._factory = factory  # Standard SVG element factory.
        self._defs = defs        # SVG defs element to include at the beginning of every document.
        self._base = base        # Base SVG element that is shown under every stroke diagram.
        self._offset = x, y      # X/Y offset for the viewbox of one stroke diagram.
        self._size = w, h        # Width/height for the viewbox of one stroke diagram.

    def make_svg(self, elems:List[BoardElementGroup], aspect_ratio:float=None) -> BoardDiagram:
        """ Split elements into diagrams, arrange them to match the aspect ratio, and encode a new SVG document. """
        stroke_count = 1 + len([1 for el in elems if el.ends_stroke])
        rows, cols = self._dimensions(stroke_count, aspect_ratio or self._DEFAULT_RATIO)
        w, h = self._size
        tfrms = ColumnTransforms(w, h, cols)
        diagrams = self._arrange(elems, tfrms)
        document = self._factory.svg(*self._offset, w * cols, h * rows, *diagrams)
        return document.serialize()

    def _dimensions(self, count:int, device_ratio:float) -> Tuple[int, int]:
        """ Calculate the best arrangement of <count> sub-diagrams in rows and columns for the best possible scale. """
        w, h = self._size
        diagram_ratio = w / h
        # rel_ratio is the aspect ratio of one diagram divided by that of the device viewing area.
        rel_ratio = diagram_ratio / device_ratio
        r = min(rel_ratio, 1 / rel_ratio)
        s = int((count * r) ** 0.5) or 1
        if r * ceil(count / s) > (s + 1):
            s += 1
        t = ceil(count / s)
        return (s, t) if rel_ratio < 1 else (t, s)

    def _arrange(self, elems:Iterable[BoardElementGroup], tfrms:ColumnTransforms) -> List[XMLElement]:
        """ Arrange all SVG elements in a document with a separate diagram for each stroke.
            Transform each diagram to be tiled left-to-right, top-to-bottom in a grid layout. """
        diagram_list = [self._defs]
        overlay_list = []
        stroke_elems = []
        i = 0
        for el in elems:
            stroke_elems += el
            if el.iter_overlays is not None:
                overlay_list += el.iter_overlays(tfrms, i)
            if el.ends_stroke:
                diagram = self._factory.group(self._base, *stroke_elems, transform=tfrms[i])
                diagram_list.append(diagram)
                stroke_elems = []
                i += 1
        diagram_list.append(self._factory.group(self._base, *stroke_elems, transform=tfrms[i]))
        diagram_list += overlay_list
        return diagram_list
