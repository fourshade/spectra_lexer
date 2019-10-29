""" Module for generating steno board diagram elements. """

from collections import defaultdict
from math import ceil
from typing import Container, Dict, Iterable, Iterator, List, Sequence, Tuple

from .path import ArrowPathGenerator, ChainPathGenerator
from .svg import SVGDefs, SVGDocument, SVGElement, SVGGroup, SVGPath, SVGUse


class BoardElements:
    """ Abstract base class for a group of SVG steno board elements. The internal representation may vary.
        Must return finished SVG elements on iteration, positioned correctly within the context of a single stroke. """

    offset = 0j           # (x + jy) offset of the approximate center of this element in the current stroke.
    ends_stroke = False   # If True, this element group is the last in the current stroke.
    iter_overlays = None  # Reserved for special elements that add overlays covering multiple strokes.

    def __iter__(self) -> Iterator[SVGElement]:
        return iter(())


class InversionBoardElements(BoardElements):
    """ A set of bidirectional curved arrows pointing between two other board element groups. """

    _path_gen = ArrowPathGenerator()  # Generator to connect points with path data.

    def __init__(self, first:BoardElements, second:BoardElements) -> None:
        self._centers = first.offset, second.offset  # Centers of the element groups of interest.

    def __iter__(self) -> Iterator[SVGElement]:
        """ Yield a set of arrow paths connecting our element groups in both directions. """
        p1, p2 = self._centers
        yield from self._iter_layers(p1, p2)
        yield from self._iter_layers(p2, p1)

    def _iter_layers(self, start:complex, end:complex) -> Iterator[SVGElement]:
        """ Yield SVG path elements that compose an arrow pointing between <start> and <end>.
            Layers are shifted by an incremental offset to create a drop shadow appearance. """
        path_data = self._path_gen.connect(start, end)
        upper = SVGPath(path_data, style="fill:none;stroke:#800000;stroke-width:1.5px;")
        yield upper
        lower = SVGPath(path_data, style="fill:none;stroke:#FF0000;stroke-width:1.5px;")
        lower.translate(0, -1)
        yield lower


class LinkedBoardElements(BoardElements):
    """ Contains a chain connecting two strokes, which are shifted independently of the main stroke groupings. """

    ends_stroke = True

    _path_gen = ChainPathGenerator()  # Generator to connect points with path data.

    def __init__(self, s_stroke:Sequence[BoardElements], e_stroke:Sequence[BoardElements]) -> None:
        self._strokes = s_stroke, e_stroke  # Element groups with the ending of one stroke and the start of another.

    def iter_overlays(self, sx:float, sy:float, ex:float, ey:float) -> Iterator[SVGElement]:
        """ <sx, sy> is the offset of the beginning stroke, and <ex, ey> is the offset of the ending stroke.
            For multi-element rules, connect the last element in the first stroke to the first element in the next. """
        s_stroke, e_stroke = self._strokes
        start_offset = s_stroke[-1].offset + sx + sy * 1j
        end_offset = e_stroke[0].offset + ex + ey * 1j
        yield from self._iter_layers(start_offset, end_offset)
        yield self._stroke_group(s_stroke, sx, sy)
        yield self._stroke_group(e_stroke, ex, ey)

    def _iter_layers(self, p1:complex, p2:complex) -> Iterator[SVGPath]:
        """ Yield SVG paths that compose a chain between the endpoints. """
        for path_data in self._path_gen.iter_halves(p1, p2):
            yield SVGPath(path_data, style="fill:none;stroke:#000000;stroke-width:5.0px;")
            yield SVGPath(path_data, style="fill:none;stroke:#B0B0B0;stroke-width:2.0px;")

    @staticmethod
    def _stroke_group(stroke:Iterable[BoardElements], dx:float, dy:float) -> SVGGroup:
        """ Create a new SVG group with every element in <stroke> and translate it by <dx, dy>. """
        elem = SVGGroup()
        for g in stroke:
            elem.extend(g)
        elem.translate(dx, dy)
        return elem


class ProcessedBoardElements(BoardElements):
    """ Group of elements with various processing functions applied based on a 'p-string'. """

    _bg = "#000000"             # Background color for key shapes.
    _txtmaxarea = [20.0, 20.0]  # Maximum available area for text. Determines text scale and orientation.

    def __init__(self) -> None:
        """ Elements are added by proc_* methods, which are executed in order according to an external file. """
        self._elems = []

    def __iter__(self) -> Iterator[SVGElement]:
        return iter(self._elems)

    def _append_at_offset(self, elem:SVGElement) -> None:
        """ Translate an SVG element by the current offset and add it as a child. """
        elem.translate(self.offset.real, self.offset.imag)
        self._elems.append(elem)

    def proc_sep(self, *_) -> None:
        """ Set this element to separate strokes. """
        self.ends_stroke = True

    def proc_bg(self, e_id:str, d:dict) -> None:
        """ Set the background color used by key shapes. """
        self._bg = d[e_id]

    def proc_pos(self, e_id:str, d:dict) -> None:
        """ Set the offset used in text and annotations (such as inversion arrows). """
        self.offset = complex(*d[e_id])

    def proc_shape(self, e_id:str, d:dict) -> None:
        """ Add an SVG path shape, then advance the offset to center any following text. """
        attrs = d[e_id]
        elem = SVGPath(attrs["d"], stroke="#000000", fill=self._bg)
        self._append_at_offset(elem)
        self.offset += complex(*attrs["txtcenter"])
        self._txtmaxarea = attrs["txtarea"]

    def proc_path(self, e_id:str, d:dict) -> None:
        """ Add an SVG path at the current offset. """
        elem = SVGPath(d[e_id], stroke="#000000")
        self._append_at_offset(elem)

    def proc_text(self, text:str, glyphs:dict, _FONT_SIZE=24, _EM_SIZE=1000, _TXTSPACING=14.4) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths.
            Max font size is 24 pt. Text paths are defined with an em box of 1000 units.
            14.4 px is the horizontal spacing of text in pixels. """
        grp = SVGGroup(fill="#000000")
        self._append_at_offset(grp)
        n = len(text) or 1
        spacing = _TXTSPACING
        w, h = self._txtmaxarea
        scale = min(1.0, w / (n * spacing))
        # If there is little horizontal space and plenty of vertical space, turn the text 90 degrees.
        if scale < 0.5 and h > w:
            scale = min(1.0, h / (n * spacing))
            grp.rotate(90)
        spacing *= scale
        font_scale = scale * _FONT_SIZE / _EM_SIZE
        x = - n * spacing / 2
        y = (10 * scale) - 3
        for k in text:
            char = SVGPath(glyphs[k])
            char.transform(font_scale, 0, 0, -font_scale, x, y)
            grp.append(char)
            x += spacing


class BoardDocumentFactory:
    """ Factory for SVG steno board documents corresponding to user input. """

    def __init__(self, defs:SVGElement, base:SVGElement, x:int, y:int, w:int, h:int) -> None:
        """ Groups and transforms SVG elements into a final series of SVG steno board graphics. """
        self._defs = defs    # SVG defs element to include at the beginning of every document.
        self._base = base    # Base SVG element that is shown under every stroke diagram.
        self._offset = x, y  # X/Y offset for the viewbox of one stroke diagram.
        self._size = w, h    # Width/height for the viewbox of one stroke diagram.

    def make_svg(self, elems:List[BoardElements], device_ratio:float) -> bytes:
        """ Split elements into diagrams, arrange them to match the aspect ratio, and encode a new SVG document. """
        stroke_count = 1 + len([1 for el in elems if el.ends_stroke])
        rows, cols = self._dimensions(stroke_count, device_ratio)
        tfrms = self._transforms(cols, stroke_count)
        w, h = self._size
        document = self._arrange(elems, tfrms)
        document.set_viewbox(*self._offset, w * cols, h * rows)
        return document.encode()

    def _dimensions(self, count:int, device_ratio:float) -> Tuple[int, int]:
        """ Calculate the best arrangement of <count> sub-diagrams in rows and columns for the best possible scale.
            <rel_ratio> is the aspect ratio of one diagram divided by that of the device viewing area. """
        w, h = self._size
        diagram_ratio = w / h
        rel_ratio = diagram_ratio / device_ratio
        r = min(rel_ratio, 1 / rel_ratio)
        s = int((count * r) ** 0.5) or 1
        s += r * ceil(count / s) > (s + 1)
        t = ceil(count / s)
        return (s, t) if rel_ratio < 1 else (t, s)

    def _transforms(self, cols:int, count:int) -> List[Tuple[int, int]]:
        """ Create a list of evenly spaced (dx, dy) grid translations for the current bounds and column count. """
        w, h = self._size
        tfrms = []
        for i in range(count):
            dx = w * (i % cols)
            dy = h * (i // cols)
            tfrms.append((dx, dy))
        return tfrms

    def _arrange(self, elems:Iterable[BoardElements], tfrms:List[Tuple[int, int]]) -> SVGDocument:
        """ Arrange all SVG elements in a document with a separate diagram for each stroke.
            Transform each diagram to be tiled left-to-right, top-to-bottom in a grid layout. """
        diagram_list = []
        overlay_list = []
        stroke_elems = []
        i = 0
        for el in elems:
            stroke_elems += el
            if el.iter_overlays is not None:
                overlay_list += el.iter_overlays(*tfrms[i], *tfrms[i + 1])
            if el.ends_stroke:
                diagram = SVGGroup(self._base, *stroke_elems)
                diagram.translate(*tfrms[i])
                diagram_list.append(diagram)
                stroke_elems = []
                i += 1
        last_diagram = SVGGroup(self._base, *stroke_elems)
        last_diagram.translate(*tfrms[i])
        return SVGDocument(self._defs, *diagram_list, last_diagram, *overlay_list)


class BoardEngine:
    """ Groups and transforms SVG elements into a final series of SVG steno board graphics.
        Has index for finding board elements corresponding to key strings and/or steno rules. """

    _DEFAULT_RATIO = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    def __init__(self, rule_elems:Dict[str, List[BoardElements]], compound_elems:Dict[str, List[BoardElements]],
                 key_elems:Dict[str, BoardElements], unmatched_elems:Dict[str, BoardElements],
                 doc_factory:BoardDocumentFactory) -> None:
        self._rule_elems = rule_elems            # Dict with steno key elements for every rule.
        self._compound_elems = compound_elems    # Dict with compound board elements for every rule.
        self._key_elems = key_elems              # Dict with normal steno key elements.
        self._unmatched_elems = unmatched_elems  # Dict with steno key elements in unmatched rules.
        self._doc_factory = doc_factory

    def from_keys(self, skeys:str, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a set of steno s-keys. """
        elems = [self._key_elems[k] for k in skeys]
        return self._doc_factory.make_svg(elems, aspect_ratio)

    def from_rules(self, rule_names:Iterable[str], unmatched_skeys="",
                   aspect_ratio:float=_DEFAULT_RATIO, compound=True) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from names of steno rules.
            If <compound> is False, do not use compound keys. The rules will be shown only as single keys. """
        elems = []
        d = self._compound_elems if compound else self._rule_elems
        for name in rule_names:
            elems += d[name]
        for k in unmatched_skeys:
            elems.append(self._unmatched_elems[k])
        return self._doc_factory.make_svg(elems, aspect_ratio)


class BoardElementParser:
    """ Processes steno board elements using a definitions dictionary. """

    # These are the acceptable string values for board element flags, as read from JSON.
    _INVERSION = "INV"  # Inversion of steno order. A transposition symbol will be added.
    _LINKED = "LINK"    # Rule that uses keys from two strokes. A linking symbol will be added.

    def __init__(self, defs:Dict[str, dict]) -> None:
        self._proc_defs: dict = defaultdict(dict, defs)  # Dict of definitions for constructing SVG board elements.
        self._parsed_elems: dict = defaultdict(dict)     # Parsed board elements indexed by tag, then by ID.
        self._key_elems = self._parsed_elems["key"]      # Elements corresponding to single steno keys.
        self._ukey_elems = self._parsed_elems["qkey"]    # Elements corresponding to unmatched steno keys.
        self._rule_elems = self._parsed_elems["rule"]
        self._base_elems = self._parsed_elems["base"]
        self._rule_key_elems = {}
        self._rule_flags = {}
        self._rule_child_names = {}

    def parse(self, board_elems:Dict[str, dict]) -> None:
        """ Parse all elements from a JSON document into full SVG board element structures. """
        for tag, d in board_elems.items():
            self._parsed_elems[tag].update({e_id: self._process_element(p) for e_id, p in d.items()})

    def _process_element(self, p:str) -> ProcessedBoardElements:
        """ Match p-string elements to proc_ methods and call each method using the corresponding defs dict. """
        board_elems = ProcessedBoardElements()
        for s in p.split(";"):
            k, v = s.split("=", 1)
            meth = getattr(board_elems, "proc_" + k, None)
            if meth is not None:
                meth(v, self._proc_defs[k])
        return board_elems

    def add_rule(self, name:str, skeys:str, flags:Container[str]=()) -> None:
        self._rule_key_elems[name] = [self._key_elems[k] for k in skeys]
        self._rule_flags[name] = flags
        self._rule_child_names[name] = []

    def add_connection(self, parent:str, child:str) -> None:
        child_names = self._rule_child_names[parent]
        child_names.append(child)

    def build_engine(self) -> BoardEngine:
        """ Build an element index and board-generating engine from our current resources. """
        basic_rule_elems = self._rule_key_elems
        compound_rule_elems = {name: self._process_compound_rule(name) for name in basic_rule_elems}
        doc_factory = self._build_doc_factory()
        return BoardEngine(basic_rule_elems, compound_rule_elems, self._key_elems, self._ukey_elems, doc_factory)

    def _process_compound_rule(self, name:str) -> List[BoardElements]:
        known_elems = self._rule_elems.get(name)
        if known_elems is not None:
            return [known_elems]
        # There may not be compound elements for everything; in that case, use elements for each raw key.
        child_names = self._rule_child_names[name]
        if not child_names:
            return self._rule_key_elems[name]
        # Add elements recursively from all child rules.
        groups = [self._process_compound_rule(name) for name in child_names]
        flags = self._rule_flags[name]
        if self._LINKED in flags:
            # A rule using linked strokes must follow this pattern: (.first)(~/~)(last.)
            return [LinkedBoardElements(groups[0], groups[-1])]
        elems = []
        for g in groups:
            elems += g
        if self._INVERSION in flags:
            # A rule using inversion connects the first two elements with arrows.
            elems.append(InversionBoardElements(elems[0], elems[1]))
        return elems

    def _build_doc_factory(self) -> BoardDocumentFactory:
        """ Make a <use> element for the base present in every stroke matching a <defs> element. """
        base_id = "_BASE"
        g = SVGGroup(id=base_id)
        for grp in self._base_elems.values():
            g.extend(grp)
        defs = SVGDefs(g)
        base = SVGUse(base_id)
        positions = self._proc_defs["pos"]
        return BoardDocumentFactory(defs, base, *positions["min"], *positions["max"])
