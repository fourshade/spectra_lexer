""" Module for generating steno board diagram elements and SVG documents. """

from functools import lru_cache
from typing import Dict, Iterable, Iterator, List, Sequence

from .path import ArrowPathGenerator, ChainPathGenerator, PathCommands
from .rule import BoardRule
from .svg import SVGElement, SVGElementFactory, SVGStyle
from .tfrm import GridLayoutEngine, TransformData


class Overlay:
    """ Contains elements which are shifted independently of the main stroke groupings. """

    def iter_elements(self, *tfrms:TransformData) -> Iterator[SVGElement]:
        raise NotImplementedError


class BoardElementGroup:
    """ A group of SVG steno board elements with metadata. """

    bg = "#000000"             # Background color for key shapes.
    txtmaxarea = [20.0, 20.0]  # Maximum available area for text. Determines text scale and orientation.
    altangle = 0.0             # Alternate text orientation in degrees.
    ends_stroke = False        # If True, this element group is the last in the current stroke.
    overlay: Overlay = None    # Reserved for special elements that add overlays covering multiple strokes.

    def __init__(self, *elems:SVGElement) -> None:
        self.tfrm = TransformData()  # Contains the approximate center of this element in the current stroke.
        self._elems = [*elems]

    def append(self, elem:SVGElement) -> None:
        self._elems.append(elem)

    def get_offset(self) -> complex:
        return self.tfrm.offset()

    def __iter__(self) -> Iterator[SVGElement]:
        """ Iterate over all finished SVG elements, positioned correctly within the context of a single stroke. """
        return iter(self._elems)


class LinkedOverlay(Overlay):
    """ Contains a chain connecting two strokes, which are shifted independently of the main stroke groupings. """

    PATH_GENERATOR = ChainPathGenerator()
    LAYER_STYLES = [SVGStyle(fill="none", stroke="#000000", stroke_width="5.0px"),
                    SVGStyle(fill="none", stroke="#B0B0B0", stroke_width="2.0px")]

    def __init__(self, factory:SVGElementFactory, s_stroke:Sequence[BoardElementGroup],
                 e_stroke:Sequence[BoardElementGroup]) -> None:
        self._factory = factory
        self._strokes = s_stroke, e_stroke  # Element groups with the ending of one stroke and the start of another.

    def iter_elements(self, first_tfrm:TransformData, last_tfrm:TransformData, *_) -> Iterator[SVGElement]:
        """ For multi-element rules, connect the last element in the first stroke to the first element in the next. """
        s_stroke, e_stroke = self._strokes
        first_offset = s_stroke[-1].get_offset() + first_tfrm.offset()
        last_offset = e_stroke[0].get_offset() + last_tfrm.offset()
        yield from self._iter_layers(first_offset, last_offset)
        yield self._stroke_group(s_stroke, first_tfrm)
        yield self._stroke_group(e_stroke, last_tfrm)

    def _iter_layers(self, p1:complex, p2:complex) -> Iterator[SVGElement]:
        """ Yield SVG paths that compose a chain between the endpoints. """
        halves = [PathCommands(), PathCommands()]
        self.PATH_GENERATOR.connect(p1, p2, *halves)
        for cmds in halves:
            path_data = cmds.to_string()
            for style in self.LAYER_STYLES:
                yield self._factory.path(path_data, style)

    def _stroke_group(self, stroke:Iterable[BoardElementGroup], tfrm:TransformData) -> SVGElement:
        """ Create a new SVG group with every element in <stroke> and translate it by <dx, dy>. """
        elems = []
        for g in stroke:
            elems += g
        return self._factory.group(*elems, transform=tfrm.to_string())


class BoardElementFactory:
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
    ARROW_GENERATOR = ArrowPathGenerator()
    ARROW_STYLES = [SVGStyle(fill="none", stroke="#800000", stroke_width="1.5px"),
                    SVGStyle(fill="none", stroke="#FF0000", stroke_width="1.5px")]

    def __init__(self, key_positions:Dict[str, List[int]], shape_defs:Dict[str, dict],
                 glyph_table:Dict[str, str]) -> None:
        self._key_positions = key_positions  # Contains offsets of the board layout.
        self._shape_defs = shape_defs        # Defines paths forming the shape and inside area of steno keys.
        self._glyph_table = glyph_table      # Defines paths for each valid text glyph (and a default).
        self._factory = SVGElementFactory()  # Standard SVG element factory.

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
        path_data = attrs["d"]
        style = SVGStyle(fill=grp.bg, stroke="#000000")
        elem = self._factory.path(path_data, style, transform=grp.tfrm.to_string())
        grp.append(elem)
        grp.tfrm.translate(*attrs["txtcenter"])
        grp.txtmaxarea = attrs["txtarea"]
        grp.altangle = attrs["altangle"]

    def proc_text(self, grp:BoardElementGroup, text:str) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths. """
        n = len(text) or 1
        spacing = self.FONT_SPACING_PX
        w, h = grp.txtmaxarea
        scale = min(1.0, w / (n * spacing))
        # If there is little horizontal space and plenty in another direction, rotate the text.
        if scale < 0.5 and h > w:
            scale = min(1.0, h / (n * spacing))
            grp.tfrm.rotate(grp.altangle)
        spacing *= scale
        font_scale = scale * self.FONT_PX_PER_UNIT
        x = - n * spacing / 2
        y = (10 * scale) - 3
        elems = []
        style = self.FONT_STYLE
        for k in text:
            tfrm = TransformData()
            tfrm.scale(font_scale, -font_scale)
            tfrm.translate(x, y)
            glyph = self._glyph_table.get(k) or self._glyph_table["DEFAULT"]
            char = self._factory.path(glyph, style, transform=tfrm.to_string())
            elems.append(char)
            x += spacing
        g = self._factory.group(*elems, transform=grp.tfrm.to_string())
        grp.append(g)

    def inversion_group(self, strk:Sequence[BoardElementGroup]) -> BoardElementGroup:
        """ Make a new group with a set of arrow paths connecting two other groups in both directions. """
        items = []
        for grp in strk:
            items += grp
        p1 = strk[0].get_offset()
        p2 = strk[1].get_offset()
        items += self._arrow_layers(p1, p2)
        items += self._arrow_layers(p2, p1)
        return BoardElementGroup(*items)

    def _arrow_layers(self, start:complex, end:complex) -> Iterator[SVGElement]:
        """ Yield SVG path elements that compose an arrow pointing between <start> and <end>.
            Layers are shifted by an incremental offset to create a drop shadow appearance. """
        for style in self.ARROW_STYLES:
            cmds = PathCommands()
            self.ARROW_GENERATOR.connect(start, end, cmds)
            path_data = cmds.to_string()
            yield self._factory.path(path_data, style)
            start -= 1j
            end -= 1j

    def linked_group(self, strk1:Sequence[BoardElementGroup], strk2:Sequence[BoardElementGroup]) -> BoardElementGroup:
        """ Make a chain connecting two strokes, which are shifted independently of the main stroke groupings. """
        grp = BoardElementGroup()
        grp.ends_stroke = True
        grp.overlay = LinkedOverlay(self._factory, strk1, strk2)
        return grp

    @staticmethod
    def _stroke_groups(elems:Iterable[BoardElementGroup]) -> List[List[SVGElement]]:
        stroke_elems = []
        stroke_list = [stroke_elems]
        for grp in elems:
            stroke_elems += grp
            if grp.ends_stroke:
                stroke_elems = []
                stroke_list.append(stroke_elems)
        return stroke_list

    @staticmethod
    def _overlays(elems:Iterable[BoardElementGroup], tfrms:Sequence[TransformData]) -> List[SVGElement]:
        overlay_list = []
        i = 0
        for grp in elems:
            if grp.overlay is not None:
                overlay_list += grp.overlay.iter_elements(*tfrms[i:])
            if grp.ends_stroke:
                i += 1
        return overlay_list

    def make_svg(self, base_group:BoardElementGroup, elems:Iterable[BoardElementGroup],
                 layout:GridLayoutEngine, aspect_ratio:float=None) -> str:
        """ Arrange all SVG elements in a document with a separate diagram for each stroke.
            Transform each diagram to be tiled in a grid layout to match the aspect ratio.
            Add overlays (if any), put it all in a new SVG document, and return it in string form. """
        strokes = self._stroke_groups(elems)
        stroke_count = len(strokes)
        # If no aspect ratio is given, aspect_ratio=0.0001 ensures that all boards end up in one column.
        rows, cols = layout.arrange(stroke_count, aspect_ratio or 0.0001)
        tfrms = layout.transforms(stroke_count, cols)
        viewbox = layout.viewbox(rows, cols)
        if stroke_count > 1:
            base_id = "_BASE"
            ref_base = self._factory.group(*base_group, id=base_id)
            defs = self._factory.defs(ref_base)
            base = self._factory.use(base_id)
            root_elements = [defs]
        else:
            base = self._factory.group(*base_group)
            root_elements = []
        for stroke, tfrm in zip(strokes, tfrms):
            group = self._factory.group(base, *stroke, transform=tfrm.to_string())
            root_elements.append(group)
        root_elements += self._overlays(elems, tfrms)
        document = self._factory.svg(*root_elements, viewbox=viewbox)
        return str(document)


class BoardFactory:
    """ Builds steno board diagrams from rules in the given dictionaries.
        The main dict contains of a list of strings for each shape of board element.
        Each of these strings defines a "proc": a process that positions and/or constructs SVG elements.
        Execution involves running every proc in the list, in order. """

    FILL_BASE = "#7F7F7F"
    FILL_MATCHED = "#007FFF"
    FILL_UNMATCHED = "#DFDFDF"
    FILL_LETTERS = "#00AFFF"
    FILL_ALT = "#00AFAF"
    FILL_RARE = "#9FCFFF"
    FILL_COMBO = "#8F8FFF"
    FILL_NUMBER = "#3F7F00"
    FILL_SYMBOL = "#AFAF00"
    FILL_SPELLING = "#7FFFFF"
    FILL_BRIEF = "#FF7F00"

    def __init__(self, elem_factory:BoardElementFactory, layout:GridLayoutEngine, special_key:str,
                 key_procs:Dict[str, List[str]], rule_procs:Dict[str, List[str]]) -> None:
        self._elem_factory = elem_factory  # Factory for board element groups.
        self._layout = layout              # Layout for multi-stroke diagrams.
        self._special_key = special_key    # Key combined with others without contributing to text.
        self._key_procs = key_procs        # Procedures for constructing and positioning single keys.
        self._rule_procs = rule_procs      # Procedures for constructing and positioning key combos.

    @lru_cache(maxsize=None)
    def _base_group(self) -> BoardElementGroup:
        """ Generate board diagram elements for the base with all keys darkened. """
        base_procs = [p for procs in self._key_procs.values() for p in procs[:-1]]
        return self._elem_factory.processed_group(base_procs, self.FILL_BASE)

    @lru_cache(maxsize=None)
    def _elems_from_skeys(self, skeys:str, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a set of steno s-keys. """
        return [self._elem_factory.processed_group(self._key_procs[s], bg or self.FILL_MATCHED)
                for s in skeys if s in self._key_procs]

    @lru_cache(maxsize=None)
    def _elems_from_rule_info(self, skeys:str, letters:str, alt_text:str, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a rule's properties if procs using its s-keys exist. """
        elems = []
        procs = self._rule_procs.get(skeys)
        star = self._special_key
        if procs is None and star in skeys and star != skeys:
            # Rules using the star should have that key separate from their text.
            leftover = skeys.replace(star, "")
            if bg is None:
                bg = self.FILL_COMBO
            elems += self._elems_from_skeys(star, bg)
            procs = self._rule_procs.get(leftover)
        if procs is not None:
            if letters:
                return [*elems, self._elem_factory.processed_group(procs, bg or self.FILL_LETTERS, letters)]
            elif alt_text:
                return [*elems, self._elem_factory.processed_group(procs, bg or self.FILL_ALT, alt_text)]
        return []

    def _linked_group(self, rule:BoardRule, show_letters:bool, bg:str=None) -> BoardElementGroup:
        """ A rule using linked strokes must follow this pattern: (.first)(~/~)(last.) """
        strokes = [self._elems_from_rule(child, show_letters, bg) for child in rule.children]
        return self._elem_factory.linked_group(strokes[0], strokes[-1])

    def _inversion_group(self, rule:BoardRule, show_letters:bool, bg:str=None) -> BoardElementGroup:
        """ A rule using inversion connects the first two elements with arrows. """
        grps = []
        for child in rule.children:
            grps += self._elems_from_rule(child, show_letters, bg)
        return self._elem_factory.inversion_group(grps)

    def _elems_from_rule(self, rule:BoardRule, show_letters:bool, bg:str=None) -> List[BoardElementGroup]:
        """ Generate board diagram elements from a steno rule recursively. Propagate any background colors. """
        skeys = rule.skeys
        letters = rule.letters
        alt_text = rule.alt_text
        children = rule.children
        if letters and not any(map(str.isalpha, letters)):
            bg = self.FILL_SYMBOL if not any(map(str.isdigit, letters)) else self.FILL_NUMBER
            if not alt_text:
                alt_text = letters
        if rule.is_linked:
            return [self._linked_group(rule, show_letters, bg)]
        elif rule.is_inversion:
            return [self._inversion_group(rule, show_letters, bg)]
        elif rule.is_unmatched:
            return self._elems_from_skeys(skeys, self.FILL_UNMATCHED)
        elif rule.is_rare:
            bg = self.FILL_RARE
        elif rule.is_fingerspelling:
            bg = self.FILL_SPELLING
        elif rule.is_brief:
            bg = self.FILL_BRIEF
        # A rule with one child using the same letters is usually an analysis. It should be unwrapped.
        if len(children) == 1:
            child = children[0]
            if letters == child.letters:
                return self._elems_from_rule(child, show_letters, bg)
        # Try to find an existing key shape for this rule. If we find one, we're done.
        elems = self._elems_from_rule_info(skeys, letters if show_letters else "", alt_text, bg)
        if elems:
            return elems
        # If there are children, add elements recursively from each one.
        if children:
            return [elem for child in children for elem in self._elems_from_rule(child, show_letters, bg)]
        # There may not be compound elements for everything; in that case, use elements for each raw key.
        return self._elems_from_skeys(skeys)

    def _make_svg(self, elems:List[BoardElementGroup], aspect_ratio:float=None) -> str:
        """ Copy the element list to avoid corrupting the caches. """
        base_group = self._base_group()
        return self._elem_factory.make_svg(base_group, elems[:], self._layout, aspect_ratio)

    def draw_keys(self, skeys:str, aspect_ratio:float=None) -> str:
        """ Generate a board diagram from a key string arranged according to <aspect ratio>. """
        elems = self._elems_from_skeys(skeys)
        return self._make_svg(elems, aspect_ratio)

    def draw_rule(self, rule:BoardRule, aspect_ratio:float=None, *, show_letters=True) -> str:
        """ Generate a board diagram from a rule object arranged according to <aspect ratio>. """
        elems = self._elems_from_rule(rule, show_letters)
        return self._make_svg(elems, aspect_ratio)
