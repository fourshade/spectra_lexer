""" Module for generating steno board diagram elements and SVG documents. """

from typing import Dict, Iterator, List, Optional

from .layout import GridLayoutEngine, OffsetSequence
from .path import ArrowPathGenerator, ChainPathGenerator
from .svg import SVGElement, SVGElements, SVGElementFactory, SVGPathCanvas, SVGStyle, SVGTransform, SVGTranslation
from .tfrm import TextOrientation, TextTransformer

SVGIterator = Iterator[SVGElement]


class Group:
    """ A group of SVG steno board elements with metadata. """

    center = 0j           # Tracks the approximate center of the element in the current stroke.
    iter_overlays = None  # Reserved for special elements that add overlays covering multiple strokes.

    def __iter__(self) -> SVGIterator:
        """ Iterate over all SVG elements, positioned correctly within the context of a single stroke. """
        raise NotImplementedError


GroupList = List[Group]


class SimpleGroup(Group):
    """ Sequence-based group of SVG steno board elements. """

    def __init__(self, elems:SVGElements=(), x=0.0, y=0.0) -> None:
        self._elems = elems
        self.center = x + y*1j

    def __iter__(self) -> SVGIterator:
        return iter(self._elems)


END_SENTINEL = SimpleGroup()  # This element group contains nothing and marks the end of a stroke.


class InversionGroup(Group):

    PATH_GENERATOR = ArrowPathGenerator()
    LAYER_STYLES = [SVGStyle(fill="none", stroke="#800000", stroke_width="1.5px"),
                    SVGStyle(fill="none", stroke="#FF0000", stroke_width="1.5px")]

    def __init__(self, factory:SVGElementFactory, first:Group, second:Group) -> None:
        self._factory = factory
        self._first = first
        self._second = second

    def _iter_layers(self, start:complex, end:complex) -> SVGIterator:
        """ Yield SVG path elements that compose an arrow pointing between <start> and <end>.
            Layers are shifted by an incremental offset to create a drop shadow appearance. """
        for style in self.LAYER_STYLES:
            path = SVGPathCanvas()
            self.PATH_GENERATOR.connect(start, end, path)
            yield self._factory.path(path, style)
            start -= 1j
            end -= 1j

    def __iter__(self) -> SVGIterator:
        """ Yield a set of arrow paths connecting the first two groups in a stroke in both directions. """
        p1 = self._first.center
        p2 = self._second.center
        yield from self._iter_layers(p1, p2)
        yield from self._iter_layers(p2, p1)


class LinkedGroup(Group):
    """ Contains a chain connecting two strokes, which are shifted independently of the main stroke groupings. """

    PATH_GENERATOR = ChainPathGenerator()
    LAYER_STYLES = [SVGStyle(fill="none", stroke="#000000", stroke_width="5.0px"),
                    SVGStyle(fill="none", stroke="#B0B0B0", stroke_width="2.0px")]

    def __init__(self, factory:SVGElementFactory, s_stroke:GroupList, e_stroke:GroupList) -> None:
        self._factory = factory
        self._strokes = s_stroke, e_stroke  # Element groups with the ending of one stroke and the start of another.

    def __iter__(self) -> SVGIterator:
        return iter(())

    def _iter_layers(self, p1:complex, p2:complex) -> SVGIterator:
        """ Yield SVG paths that compose a chain between the endpoints. """
        halves = [SVGPathCanvas(), SVGPathCanvas()]
        self.PATH_GENERATOR.connect(p1, p2, *halves)
        for path in halves:
            for style in self.LAYER_STYLES:
                yield self._factory.path(path, style)

    def _transformed_stroke(self, stroke:GroupList, x:float, y:float) -> SVGElement:
        """ Create a new SVG group with every element in <stroke> at offset <x, y>. """
        elems = []
        for g in stroke:
            elems += g
        trans = SVGTranslation(x, y)
        return self._factory.group(elems, trans)

    def iter_overlays(self, offsets:OffsetSequence) -> SVGIterator:
        """ For multi-element rules, connect the last element in the first stroke to the first element in the next. """
        sx, sy = offsets[0]
        ex, ey = offsets[1]
        s_stroke, e_stroke = self._strokes
        p1 = s_stroke[-1].center + sx + sy*1j
        p2 = e_stroke[0].center + ex + ey*1j
        yield from self._iter_layers(p1, p2)
        yield self._transformed_stroke(s_stroke, sx, sy)
        yield self._transformed_stroke(e_stroke, ex, ey)


ProcsDict = Dict[str, Dict[str, str]]


class BoardFactory:
    """ Factory for steno board element groups.
        Elements are added by proc_* methods, which are executed in order according to an external file. """

    FONT_STYLE = SVGStyle(fill="#000000")

    class ProcParams:
        x = 0.0
        y = 0.0
        txtmaxarea = (20.0, 20.0)  # Maximum available area for text. Determines text scale and orientation.
        altangle = 0.0             # Alternate text orientation in degrees.

    def __init__(self, factory:SVGElementFactory, key_procs:ProcsDict, rule_procs:ProcsDict,
                 key_positions:Dict[str, List[int]], shape_defs:Dict[str, dict], glyph_table:Dict[str, str],
                 text_tf:TextTransformer, layout:GridLayoutEngine) -> None:
        self._factory = factory              # Standard SVG element factory.
        self._key_procs = key_procs          # Procedures for constructing and positioning single keys.
        self._rule_procs = rule_procs        # Procedures for constructing and positioning key combos.
        self._key_positions = key_positions  # Contains offsets of the board layout.
        self._shape_defs = shape_defs        # Defines paths forming the shape and inside area of steno keys.
        self._glyph_table = glyph_table      # Defines paths for each valid text glyph (and a default).
        self._text_tf = text_tf              # Transform generator for shape text.
        self._layout = layout                # Layout for multi-stroke diagrams.
        self._defs_elems = []                # Base definitions to add to every document
        self._base_elems = []                # Base elements to add to every diagram

    def _proc_pos(self, pos_id:str, params:ProcParams) -> None:
        """ Move the offset used for the element shape. """
        dx, dy = self._key_positions[pos_id]
        params.x += dx
        params.y += dy

    def _proc_shape(self, shape_id:str, bg:str, params:ProcParams) -> SVGIterator:
        """ Add an SVG path shape with the given fill and transform offset.
            Then advance the offset to center any following text and annotations (such as inversion arrows). """
        attrs = self._shape_defs[shape_id]
        path_data = attrs["d"]
        style = SVGStyle(fill=bg, stroke="#000000")
        trans = SVGTranslation(params.x, params.y)
        yield self._factory.path(path_data, style, trans)
        dx, dy = attrs["txtcenter"]
        params.x += dx
        params.y += dy
        params.txtmaxarea = attrs["txtarea"]
        params.altangle = attrs["altangle"]

    def _proc_text(self, text:str, params:ProcParams) -> SVGIterator:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths. """
        width, altwidth = params.txtmaxarea
        # Choose horizontal orientation unless the difference is more than double.
        orients = [TextOrientation(width), TextOrientation(altwidth, params.altangle, 0.5)]
        n = len(text)
        tfrms = self._text_tf.iter_transforms(n, orients)
        for k, tfrm in zip(text, tfrms):
            glyph = self._glyph_table.get(k) or self._glyph_table["DEFAULT"]
            tfrm.translate(params.x, params.y)
            coefs = tfrm.coefs()
            svg_tfrm = SVGTransform(*coefs)
            yield self._factory.path(glyph, self.FONT_STYLE, svg_tfrm)

    def _processed_group(self, bg="#FFFFFF", pos=None, shape=None, text=None, sep=None) -> Group:
        """ Each keyword defines a process that positions and/or constructs SVG elements.
            Execution involves running every process, in order, on an empty BoardElementGroup. """
        if sep is not None:
            return END_SENTINEL
        params = self.ProcParams()
        if pos is not None:
            self._proc_pos(pos, params)
        elems = []
        if shape is not None:
            elems += self._proc_shape(shape, bg, params)
        if text is not None:
            elems += self._proc_text(text, params)
        return SimpleGroup(elems, params.x, params.y)

    def inversion_group(self, first:Group, second:Group) -> Group:
        """ Add a set of arrow paths connecting the first two groups in a stroke in both directions. """
        return InversionGroup(self._factory, first, second)

    def linked_group(self, strk1:GroupList, strk2:GroupList) -> Group:
        """ Add a chain connecting two strokes, which are shifted independently of the main stroke groupings. """
        return LinkedGroup(self._factory, strk1, strk2)

    def key_groups(self, skeys:str, bg:str) -> GroupList:
        """ Generate groups of elements from a set of steno s-keys. """
        return [self._processed_group(bg, **self._key_procs[s])
                for s in skeys if s in self._key_procs]

    def rule_group(self, skeys:str, text:str, bg:str) -> Optional[Group]:
        """ Generate a group of elements from a rule's text if procs using its s-keys exist. """
        procs = self._rule_procs.get(skeys)
        if procs is None:
            return None
        return self._processed_group(bg, text=text, **procs)

    def set_base(self, bg:str, *, base_id="_BASE") -> None:
        """ Set the base defintions with all single keys unlabeled. """
        elems = [elem
                 for skeys, procs in self._rule_procs.items() if len(skeys) == 1
                 for grp in self._processed_group(bg, **procs)
                 for elem in grp]
        ref_base = self._factory.group(elems, elem_id=base_id)
        self._defs_elems = [self._factory.defs(ref_base)]
        self._base_elems = [self._factory.use(base_id)]

    def _iter_elements(self, groups:GroupList, offsets:OffsetSequence) -> SVGIterator:
        yield from self._defs_elems
        overlays = []
        elems = []
        i = 0
        for grp in groups:
            elems += grp
            if grp.iter_overlays is not None:
                overlays += grp.iter_overlays(offsets[i:])
            if grp is END_SENTINEL:
                x, y = offsets[i]
                trans = SVGTranslation(x, y)
                yield self._factory.group(self._base_elems + elems, trans)
                elems = []
                i += 1
        yield from overlays

    def make_svg(self, groups:GroupList, aspect_ratio:float) -> str:
        """ Arrange all SVG elements in a document with a separate diagram for each stroke.
            Transform each diagram to be tiled in a grid layout to match the aspect ratio.
            Add overlays (if any), put it all in a new SVG document, and return it in string form. """
        groups.append(END_SENTINEL)
        stroke_count = groups.count(END_SENTINEL)
        rows, cols = self._layout.arrange(stroke_count, aspect_ratio)
        offsets = self._layout.offsets(stroke_count, cols)
        elements = [*self._iter_elements(groups, offsets)]
        viewbox = self._layout.viewbox(rows, cols)
        document = self._factory.svg(elements, viewbox)
        return str(document)
