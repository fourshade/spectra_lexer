from functools import lru_cache
from typing import Iterator, List, Tuple

from spectra_lexer.board.layout import GridLayoutEngine, Offset, OffsetSequence
from spectra_lexer.board.path import ArrowPathGenerator, ChainPathGenerator
from spectra_lexer.board.svg import SVGElement, SVGElements, SVGElementFactory, SVGPathCanvas, \
    SVGStyle, SVGTransform, SVGTranslation, SVGViewbox
from spectra_lexer.board.tfrm import TextOrientation, TextTransformer
from spectra_lexer.resource.board import FillColors, OffsetDict, ProcsDict, ShapeDict, StrDict
from spectra_lexer.resource.keys import StenoKeyConverter
from spectra_lexer.resource.rules import StenoRule

BoardDiagram = str  # Marker type for an SVG steno board diagram.
SVGIterator = Iterator[SVGElement]


class Group:
    """ A group of SVG steno board elements with metadata. """

    center = 0j           # Tracks the approximate center of the element in the current stroke.
    iter_overlays = None  # Reserved for special elements that add overlays covering multiple strokes.

    def __iter__(self) -> SVGIterator:
        """ Iterate over all SVG elements, positioned correctly within the context of a single stroke. """
        return iter(())


GroupIter = Iterator[Group]
GroupList = List[Group]


class SimpleGroup(Group):
    """ Sequence-based group of SVG steno board elements. """

    def __init__(self, elems:SVGElements=(), x=0.0, y=0.0) -> None:
        self._elems = elems
        self.center = x + y*1j

    def __iter__(self) -> SVGIterator:
        return iter(self._elems)


class InversionGroup(Group):
    """ Group of curved arrow paths connecting other element groups. """

    PATH_GENERATOR = ArrowPathGenerator()
    LAYER_STYLES = [SVGStyle(fill="none", stroke="#800000", stroke_width="1.5px"),
                    SVGStyle(fill="none", stroke="#FF0000", stroke_width="1.5px")]
    LAYER_SHIFT = -1j

    def __init__(self, factory:SVGElementFactory, *groups:Group) -> None:
        self._factory = factory
        self._groups = groups   # Element groups in order of connection.

    def _iter_layers(self, start:complex, end:complex) -> SVGIterator:
        """ Yield SVG path elements that compose an arrow pointing between <start> and <end>.
            Layers are shifted by an incremental offset to create a drop shadow appearance. """
        for style in self.LAYER_STYLES:
            path = SVGPathCanvas()
            self.PATH_GENERATOR.connect(start, end, path)
            yield self._factory.path(path, style)
            start += self.LAYER_SHIFT
            end += self.LAYER_SHIFT

    def __iter__(self) -> SVGIterator:
        """ Yield arrow paths connecting each pair of groups in both directions. """
        p1 = None
        for grp in self._groups:
            p2 = grp.center
            if p1 is not None:
                yield from self._iter_layers(p1, p2)
                yield from self._iter_layers(p2, p1)
            p1 = p2


class LinkedGroup(Group):
    """ Overlays chains connecting groups which are independent of the main stroke groupings.
        This group does not produce any elements in the normal manner. """

    PATH_GENERATOR = ChainPathGenerator()
    LAYER_STYLES = [SVGStyle(fill="none", stroke="#000000", stroke_width="5.0px"),
                    SVGStyle(fill="none", stroke="#B0B0B0", stroke_width="2.0px")]

    def __init__(self, factory:SVGElementFactory, *strokes:GroupList) -> None:
        self._factory = factory
        self._strokes = strokes  # Element group containers from one or more strokes.

    def _iter_layers(self, p1:complex, p2:complex) -> SVGIterator:
        """ Yield SVG paths that compose half of a chain between the endpoints. """
        path = SVGPathCanvas()
        self.PATH_GENERATOR.connect(p1, p2, path)
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
        """ For multi-element rules, connect each element group to the next. """
        pairs = [*zip(self._strokes, offsets)]
        p1 = None
        for stroke, offset in pairs:
            for grp in stroke:
                p2 = grp.center + complex(*offset)
                if p1 is not None:
                    yield from self._iter_layers(p1, p2)
                    yield from self._iter_layers(p2, p1)
                p1 = p2
        for stroke, offset in pairs:
            yield self._transformed_stroke(stroke, *offset)


SEPARATOR = Group()  # Stroke separator sentinel group.


class SVGBoardFactory:
    """ Factory for SVG steno board diagrams.
        Elements are added by proc_* methods, which are executed in order according to an external file. """

    FONT_STYLE = SVGStyle(fill="#000000")

    def __init__(self, text_tf:TextTransformer, key_positions:OffsetDict,
                 shape_defs:ShapeDict, glyph_table:StrDict) -> None:
        self._factory = SVGElementFactory()  # Standard SVG element factory.
        self._text_tf = text_tf              # Transform generator for shape text.
        self._key_positions = key_positions  # Contains offsets for each basic key on the board layout.
        self._shape_defs = shape_defs        # Defines paths forming the shape and inside area of steno keys.
        self._glyph_table = glyph_table      # Defines paths for each valid text glyph (and a default).
        self._defs_elems = []                # Base definitions to add to every document.
        self._base_elems = []                # Base elements to add to every diagram.

    def _group_offset(self, pos_id:str) -> Offset:
        """ Return the base offset for an element group relative to the top-left corner of the board. """
        return self._key_positions[pos_id]

    def _shape_path(self, shape_id:str) -> str:
        """ Return the SVG path data for a shape by ID. """
        return self._shape_defs[shape_id]["d"]

    def _shape_orientation(self, shape_id:str, n:int) -> Tuple[TextOrientation, Offset]:
        """ Return the best orientation and center for a shape by ID. """
        areas = self._shape_defs[shape_id]["textareas"]
        orient_map = {TextOrientation(*area["size"], area["angle"]): area for area in areas}
        best_orient = self._text_tf.best_orient(n, orient_map)
        best_area = orient_map[best_orient]
        return best_orient, best_area["center"]

    def _glyph_path(self, char:str) -> str:
        """ Return the SVG path data for a single text character. """
        return self._glyph_table.get(char) or self._glyph_table["DEFAULT"]

    def processed_group(self, bg="#FFFFFF", *, pos:str, shape:str, text=None) -> Group:
        """ Each keyword defines data that positions and/or constructs SVG elements. """
        x, y = self._group_offset(pos)
        path_data = self._shape_path(shape)
        style = SVGStyle(fill=bg, stroke="#000000")
        trans = SVGTranslation(x, y)
        elems = [self._factory.path(path_data, style, trans)]
        if text:
            # SVG fonts are not supported on major browsers, so we must draw text using paths.
            # Keep track of the text center offset for any following annotations (such as inversion arrows).
            n = len(text)
            orient, center = self._shape_orientation(shape, n)
            cx, cy = center
            x += cx
            y += cy
            char_tfrms = self._text_tf.iter_tfrms(n, orient)
            for char, tfrm in zip(text, char_tfrms):
                glyph = self._glyph_path(char)
                tfrm.translate(x, y)
                coefs = tfrm.coefs()
                svg_transform = SVGTransform(*coefs)
                elems.append(self._factory.path(glyph, self.FONT_STYLE, svg_transform))
        return SimpleGroup(elems, x, y)

    def inversion_group(self, *groups:Group) -> Group:
        """ Return a group with arrow paths connecting the elements in other groups. """
        return InversionGroup(self._factory, *groups)

    def linked_group(self, *strokes:GroupList) -> Group:
        """ Return a group with chains connecting one or more strokes. """
        return LinkedGroup(self._factory, *strokes)

    def set_base(self, *groups:Group, base_id="_BASE") -> None:
        """ Set the base definitions with all elements in <groups>. """
        elems = [elem for grp in groups for elem in grp]
        ref_base = self._factory.group(elems, elem_id=base_id)
        self._defs_elems = [self._factory.defs(ref_base)]
        self._base_elems = [self._factory.use(base_id)]

    def build_svg(self, groups:GroupList, offsets:OffsetSequence, viewbox:SVGViewbox) -> str:
        """ Separate elements in <groups> into strokes using SEPARATOR as a delimiter sentinel.
            Translate each stroke group using data at the matching index from <offsets>.
            Add overlays (if any), put it all in a new SVG document, and return it in string form. """
        root_elems = [*self._defs_elems]
        if groups:
            overlays = []
            elems = []
            i = 0
            if groups[-1] is not SEPARATOR:
                groups.append(SEPARATOR)
            for grp in groups:
                if grp is SEPARATOR:
                    x, y = offsets[i]
                    trans = SVGTranslation(x, y)
                    stroke = self._factory.group(self._base_elems + elems, trans)
                    root_elems.append(stroke)
                    elems = []
                    i += 1
                else:
                    elems += grp
                    if grp.iter_overlays is not None:
                        overlays += grp.iter_overlays(offsets[i:])
            root_elems += overlays
        document = self._factory.svg(root_elems, viewbox)
        return str(document)


class BoardEngine:
    """ Returns steno board diagrams corresponding to key strings and/or steno rules. """

    def __init__(self, converter:StenoKeyConverter, key_sep:str, key_combo:str,
                 key_procs:ProcsDict, rule_procs:ProcsDict,
                 bg:FillColors, factory:SVGBoardFactory, layout:GridLayoutEngine) -> None:
        self._to_skeys = converter.rtfcre_to_skeys  # Converts user RTFCRE steno strings to s-keys.
        self._key_sep = key_sep        # Key to replace with a separator sentinel group.
        self._key_combo = key_combo    # Key designated to combine with others without contributing to text.
        self._bg = bg                  # Namespace with background colors.
        self._factory = factory        # Factory for complete SVG board diagrams.
        self._layout = layout          # Layout for multi-stroke diagrams.
        self._key_procs = key_procs    # Procedures for constructing and positioning single keys.
        self._rule_procs = rule_procs  # Procedures for constructing and positioning key combos.
        base_groups = [grp for skeys, procs in rule_procs.items() if len(skeys) == 1
                       for grp in factory.processed_group(bg.base, **procs)]
        factory.set_base(*base_groups)

    def _iter_key_groups(self, keys:str, bg:str) -> GroupIter:
        """ Generate groups of elements from a set of steno keys. """
        skeys = self._to_skeys(keys)
        sep = self._key_sep
        for s in skeys:
            if s == sep:
                yield SEPARATOR
            elif s in self._key_procs:
                yield self._factory.processed_group(bg, **self._key_procs[s])

    @lru_cache(maxsize=None)
    def _matched_key_groups(self, keys:str) -> GroupList:
        return [*self._iter_key_groups(keys, self._bg.matched)]

    @lru_cache(maxsize=None)
    def _unmatched_key_groups(self, keys:str) -> GroupList:
        return [*self._iter_key_groups(keys, self._bg.unmatched)]

    def _rule_group(self, skeys:str, text:str, bg:str) -> Group:
        """ Generate a group of elements from a rule's text if procs using its s-keys exist. """
        if skeys in self._rule_procs:
            return self._factory.processed_group(bg, text=text, **self._rule_procs[skeys])

    @lru_cache(maxsize=None)
    def _find_shape(self, keys:str, letters:str, alt_text:str, bg:str=None) -> GroupList:
        text = letters or alt_text
        if not text:
            return []
        rbg = bg or (self._bg.letters if letters else self._bg.alt)
        skeys = self._to_skeys(keys)
        grp = self._rule_group(skeys, text, rbg)
        if grp is not None:
            return [grp]
        star = self._key_combo
        if star in skeys and star != skeys:
            # Rules using the star should have that key separate from their text.
            leftover = skeys.replace(star, "")
            cbg = bg or self._bg.combo
            grp = self._rule_group(leftover, text, cbg)
            if grp is not None:
                return [*self._iter_key_groups(star, cbg), grp]
        return []

    def _find_groups(self, rule:StenoRule, show_letters:bool, bg:str=None) -> GroupList:
        """ Generate board diagram elements from a steno rule recursively. Propagate any background colors. """
        keys = rule.keys
        letters = rule.letters.strip()
        alt_text = rule.alt
        children = [item.child for item in rule.rulemap]
        if letters and not any(map(str.isalpha, letters)):
            bg = self._bg.symbol if not any(map(str.isdigit, letters)) else self._bg.number
            if not alt_text:
                alt_text = letters
        if rule.is_linked:
            # A rule using linked strokes must follow this pattern: (.first)(~/~)(last.)
            strokes = [self._find_groups(child, show_letters, bg) for child in children]
            first, *_, last = strokes
            chain_grp = self._factory.linked_group(first, last)
            grps = [elem for grp in strokes for elem in grp]
            return [chain_grp, *grps]
        elif rule.is_inversion:
            # A rule using inversion connects the first two elements with arrows on top.
            grps = []
            for child in children:
                grps += self._find_groups(child, show_letters, bg)
            first, second = grps[:2]
            inv_grp = self._factory.inversion_group(first, second)
            return [*grps, inv_grp]
        elif rule.is_unmatched:
            return self._unmatched_key_groups(keys)
        elif rule.is_rare:
            bg = self._bg.rare
        elif rule.is_stroke:
            bg = self._bg.spelling
        elif rule.is_word:
            bg = self._bg.brief
        # A rule with one child using the same letters is usually an analysis. It should be unwrapped.
        if len(children) == 1:
            child = children[0]
            if letters == child.letters:
                return self._find_groups(child, show_letters, bg)
        # Try to find an existing key shape for this rule. If we find one, we're done.
        groups = self._find_shape(keys, letters * show_letters, alt_text, bg)
        if groups:
            return groups
        # If there are children, add elements recursively from each one.
        if children:
            return [elem for child in children
                    for elem in self._find_groups(child, show_letters, bg)]
        # There may not be compound elements for everything; in that case, use elements for each raw key.
        return self._matched_key_groups(keys)

    def _make_svg(self, groups:GroupList, aspect_ratio:float=None) -> BoardDiagram:
        """ Arrange all SVG elements in a document with a separate diagram for each stroke.
            If no aspect ratio is given, a ratio of 0.0001 ensures that all boards end up in one column.
            Copy the group list to to avoid possible cache corruption. """
        stroke_count = groups.count(SEPARATOR) + 1
        ncols = self._layout.column_count(stroke_count, aspect_ratio or 0.0001)
        offsets = self._layout.offsets(stroke_count, ncols)
        viewbox = self._layout.viewbox(stroke_count, ncols)
        return self._factory.build_svg([*groups], offsets, viewbox)

    def draw_keys(self, keys:str, aspect_ratio:float=None) -> BoardDiagram:
        """ Generate a board diagram from a steno key string arranged according to <aspect ratio>. """
        groups = self._matched_key_groups(keys)
        return self._make_svg(groups, aspect_ratio)

    def draw_rule(self, rule:StenoRule, aspect_ratio:float=None, *, show_letters=True) -> BoardDiagram:
        """ Generate a board diagram from a steno rule object arranged according to <aspect ratio>. """
        groups = self._find_groups(rule, show_letters)
        return self._make_svg(groups, aspect_ratio)
