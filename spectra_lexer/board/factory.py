""" Module for generating steno board diagram elements and SVG documents. """

from typing import Dict, Iterable, Iterator, List, Optional, Sequence

from .path import ArrowPathGenerator, ChainPathGenerator, PathCommands
from .svg import SVGElement, SVGElementFactory, SVGStyle
from .tfrm import GridLayoutEngine, TransformData

SVGIterator = Iterator[SVGElement]
SVGSequence = Sequence[SVGElement]
TransformSequence = Sequence[TransformData]


class Overlay:
    """ Contains elements which are shifted independently of the main stroke groupings. """

    def iter_elements(self, tfrms:TransformSequence) -> SVGIterator:
        raise NotImplementedError


class Group:
    """ A group of SVG steno board elements with metadata. """

    offset = 0j              # Tracks the approximate center of the element in the current stroke.
    ends_stroke = False      # If True, this element group is the last in the current stroke.
    overlay: Overlay = None  # Reserved for special elements that add overlays covering multiple strokes.

    def __init__(self, elems:SVGSequence=()) -> None:
        self._elems = elems  # Reusable iterable of SVG elements.

    def __iter__(self) -> SVGIterator:
        """ Iterate over all finished SVG elements, positioned correctly within the context of a single stroke. """
        return iter(self._elems)


GroupList = List[Group]


class InversionElements:

    PATH_GENERATOR = ArrowPathGenerator()
    LAYER_STYLES = [SVGStyle(fill="none", stroke="#800000", stroke_width="1.5px"),
                    SVGStyle(fill="none", stroke="#FF0000", stroke_width="1.5px")]

    def __init__(self, factory:SVGElementFactory, stroke:GroupList) -> None:
        self._factory = factory
        self._stroke = stroke

    def _iter_layers(self, start:complex, end:complex) -> SVGIterator:
        """ Yield SVG path elements that compose an arrow pointing between <start> and <end>.
            Layers are shifted by an incremental offset to create a drop shadow appearance. """
        for style in self.LAYER_STYLES:
            cmds = PathCommands()
            self.PATH_GENERATOR.connect(start, end, cmds)
            path_data = cmds.to_string()
            yield self._factory.path(path_data, style)
            start -= 1j
            end -= 1j

    def __iter__(self) -> SVGIterator:
        """ Make a set of arrow paths connecting the first two groups in a stroke in both directions. """
        for grp in self._stroke:
            yield from grp
        p1 = self._stroke[0].offset
        p2 = self._stroke[1].offset
        yield from self._iter_layers(p1, p2)
        yield from self._iter_layers(p2, p1)


class LinkedOverlay(Overlay):
    """ Contains a chain connecting two strokes, which are shifted independently of the main stroke groupings. """

    PATH_GENERATOR = ChainPathGenerator()
    LAYER_STYLES = [SVGStyle(fill="none", stroke="#000000", stroke_width="5.0px"),
                    SVGStyle(fill="none", stroke="#B0B0B0", stroke_width="2.0px")]

    def __init__(self, factory:SVGElementFactory, s_stroke:GroupList, e_stroke:GroupList) -> None:
        self._factory = factory
        self._strokes = s_stroke, e_stroke  # Element groups with the ending of one stroke and the start of another.

    def _iter_layers(self, p1:complex, p2:complex) -> SVGIterator:
        """ Yield SVG paths that compose a chain between the endpoints. """
        halves = [PathCommands(), PathCommands()]
        self.PATH_GENERATOR.connect(p1, p2, *halves)
        for cmds in halves:
            path_data = cmds.to_string()
            for style in self.LAYER_STYLES:
                yield self._factory.path(path_data, style)

    def _transformed_stroke(self, stroke:GroupList, tfrm:TransformData) -> SVGElement:
        """ Create a new SVG group with every element in <stroke> and translate it by <dx, dy>. """
        elems = []
        for g in stroke:
            elems += g
        return self._factory.group(*elems, transform=tfrm.to_string())

    def iter_elements(self, tfrms:TransformSequence) -> SVGIterator:
        """ For multi-element rules, connect the last element in the first stroke to the first element in the next. """
        first_tfrm, last_tfrm = tfrms[:2]
        s_stroke, e_stroke = self._strokes
        first_offset = s_stroke[-1].offset + first_tfrm.offset()
        last_offset = e_stroke[0].offset + last_tfrm.offset()
        yield from self._iter_layers(first_offset, last_offset)
        yield self._transformed_stroke(s_stroke, first_tfrm)
        yield self._transformed_stroke(e_stroke, last_tfrm)


ProcsDict = Dict[str, Dict[str, str]]


class BoardFactory:
    """ Factory for steno board element groups.
        Elements are added by proc_* methods, which are executed in order according to an external file. """

    # Max font size is 24 px. Text paths are defined with an em box of 1000 units.
    # 600 units (or 14.4 px) is the horizontal spacing of text.
    _FONT_SIZE = 24
    _EM_SIZE = 1000
    _FONT_SPACING = 600
    FONT_PX_PER_UNIT = _FONT_SIZE / _EM_SIZE
    FONT_SPACING_PX = _FONT_SPACING * FONT_PX_PER_UNIT
    FONT_STYLE = SVGStyle(fill="#000000")

    class ProcTransformData(TransformData):
        txtmaxarea = (20.0, 20.0)  # Maximum available area for text. Determines text scale and orientation.
        altangle = 0.0             # Alternate text orientation in degrees.

    def __init__(self, factory:SVGElementFactory, key_procs:ProcsDict, rule_procs:ProcsDict,
                 key_positions:Dict[str, List[int]], shape_defs:Dict[str, dict], glyph_table:Dict[str, str],
                 layout:GridLayoutEngine) -> None:
        self._factory = factory              # Standard SVG element factory.
        self._key_procs = key_procs          # Procedures for constructing and positioning single keys.
        self._rule_procs = rule_procs        # Procedures for constructing and positioning key combos.
        self._key_positions = key_positions  # Contains offsets of the board layout.
        self._shape_defs = shape_defs        # Defines paths forming the shape and inside area of steno keys.
        self._glyph_table = glyph_table      # Defines paths for each valid text glyph (and a default).
        self._layout = layout                # Layout for multi-stroke diagrams.
        self._defs_elems = []                # Base definitions to add to every document
        self._base_elems = []                # Base elements to add to every diagram

    def _proc_pos(self, pos_id:str, tfrm:ProcTransformData) -> None:
        """ Move the offset used for the element shape. """
        dx, dy = self._key_positions[pos_id]
        tfrm.translate(dx, dy)

    def _proc_shape(self, shape_id:str, bg:str, tfrm:ProcTransformData) -> SVGElement:
        """ Add an SVG path shape with the given fill and transform offset.
            Then advance the offset to center any following text and annotations (such as inversion arrows). """
        attrs = self._shape_defs[shape_id]
        path_data = attrs["d"]
        style = SVGStyle(fill=bg, stroke="#000000")
        elem = self._factory.path(path_data, style, transform=tfrm.to_string())
        dx, dy = attrs["txtcenter"]
        tfrm.translate(dx, dy)
        tfrm.txtmaxarea = attrs["txtarea"]
        tfrm.altangle = attrs["altangle"]
        return elem

    def _proc_text(self, text:str, tfrm:ProcTransformData) -> SVGElement:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths. """
        n = len(text) or 1
        spacing = self.FONT_SPACING_PX
        w, h = tfrm.txtmaxarea
        scale = min(1.0, w / (n * spacing))
        # If there is little horizontal space and plenty in another direction, rotate the text.
        if scale < 0.5 and h > w:
            scale = min(1.0, h / (n * spacing))
            tfrm.rotate(tfrm.altangle)
        spacing *= scale
        font_scale = scale * self.FONT_PX_PER_UNIT
        x = - n * spacing / 2
        y = (10 * scale) - 3
        elems = []
        style = self.FONT_STYLE
        for k in text:
            char_tfrm = TransformData()
            char_tfrm.scale(font_scale, -font_scale)
            char_tfrm.translate(x, y)
            glyph = self._glyph_table.get(k) or self._glyph_table["DEFAULT"]
            char = self._factory.path(glyph, style, transform=char_tfrm.to_string())
            elems.append(char)
            x += spacing
        return self._factory.group(*elems, transform=tfrm.to_string())

    def _processed_group(self, bg="#FFFFFF", pos=None, shape=None, text=None, sep=None) -> Group:
        """ Each keyword defines a process that positions and/or constructs SVG elements.
            Execution involves running every process, in order, on an empty BoardElementGroup. """
        elems = []
        params = self.ProcTransformData()
        if pos is not None:
            self._proc_pos(pos, params)
        if shape is not None:
            elem = self._proc_shape(shape, bg, params)
            elems.append(elem)
        if text is not None:
            elem = self._proc_text(text, params)
            elems.append(elem)
        grp = Group(elems)
        if sep is not None:
            grp.ends_stroke = True
        grp.offset = params.offset()
        return grp

    def inversion_group(self, strk:GroupList) -> Group:
        """ Make a set of arrow paths connecting the first two groups in a stroke in both directions. """
        elems = [*InversionElements(self._factory, strk)]
        return Group(elems)

    def linked_group(self, strk1:GroupList, strk2:GroupList) -> Group:
        """ Make a chain connecting two strokes, which are shifted independently of the main stroke groupings. """
        grp = self._processed_group(sep="1")
        grp.overlay = LinkedOverlay(self._factory, strk1, strk2)
        return grp

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
        ref_base = self._factory.group(*elems, id=base_id)
        self._defs_elems = [self._factory.defs(ref_base)]
        self._base_elems = [self._factory.use(base_id)]

    def _iter_strokes(self, groups:GroupList) -> Iterator[SVGSequence]:
        elems = [*self._base_elems]
        for grp in groups:
            elems += grp
            if grp.ends_stroke:
                yield elems
                elems = [*self._base_elems]
        yield elems

    def _iter_diagrams(self, strokes:Iterable[SVGSequence], tfrms:TransformSequence) -> SVGIterator:
        for stroke, tfrm in zip(strokes, tfrms):
            yield self._factory.group(*stroke, transform=tfrm.to_string())

    @staticmethod
    def _iter_overlays(groups:GroupList, tfrms:TransformSequence) -> SVGIterator:
        i = 0
        for grp in groups:
            if grp.overlay is not None:
                yield from grp.overlay.iter_elements(tfrms[i:])
            if grp.ends_stroke:
                i += 1

    def make_svg(self, groups:GroupList, aspect_ratio:float=None) -> str:
        """ Arrange all SVG elements in a document with a separate diagram for each stroke.
            Transform each diagram to be tiled in a grid layout to match the aspect ratio.
            Add overlays (if any), put it all in a new SVG document, and return it in string form. """
        strokes = [*self._iter_strokes(groups)]
        stroke_count = len(strokes)
        # If no aspect ratio is given, aspect_ratio=0.0001 ensures that all boards end up in one column.
        rows, cols = self._layout.arrange(stroke_count, aspect_ratio or 0.0001)
        tfrms = self._layout.transforms(stroke_count, cols)
        elements = [*self._defs_elems]
        elements += self._iter_diagrams(strokes, tfrms)
        elements += self._iter_overlays(groups, tfrms)
        viewbox = self._layout.viewbox(rows, cols)
        document = self._factory.svg(*elements, viewbox=viewbox)
        return str(document)
