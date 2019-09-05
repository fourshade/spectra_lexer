""" Module for generating steno board diagram elements. """

from collections import defaultdict
from math import ceil
from typing import Dict, List, Iterable, Iterator, Tuple

from .path import ArrowPathList, ChainPathList
from .svg import SVGElement, SVGDefs, SVGDocument, SVGPath
from .xml import XMLElement
from ..keys import KeyLayout
from ..rules import StenoRule


class BoardElements:
    """ Abstract base class for a group of SVG steno board elements. The internal representation may vary.
        Must return finished SVG elements on iteration, positioned correctly within the context of a single stroke. """

    offset = 0j           # (x + jy) offset of the approximate center of this element in the current stroke.
    ends_stroke = False   # If True, this element group is the last in the current stroke.
    iter_overlays = None  # Reserved for special elements that add overlays covering multiple strokes.

    def __iter__(self) -> Iterator[SVGElement]:
        return iter(())


class SeparatorBoardElements(BoardElements):
    """ Sentinel class for the gap between strokes. """

    ends_stroke = True


class ConnectedBoardElements(BoardElements):
    """ Elements which have some sort of connector between them. Only the first and last args are kept/connected. """

    def __init__(self, *board_elems:BoardElements) -> None:
        self._first, *_, self._last = board_elems


class InversionBoardElements(ConnectedBoardElements):
    """ Contains curved arrows pointing between its children. """

    def __iter__(self) -> Iterator[SVGElement]:
        """ Yield the first and last element sets, then a set of arrow path elements over top. """
        paths = ArrowPathList()
        paths += self._first
        paths += self._last
        paths.connect(self._first.offset, self._last.offset)
        return iter(paths)


class LinkedBoardElements(ConnectedBoardElements):
    """ Contains a chain connecting its children, which are shifted independently of the main stroke groupings. """

    ends_stroke = True

    def iter_overlays(self, sx:float, sy:float, ex:float, ey:float) -> Iterator[SVGElement]:
        """ Wrap elements involved in a chain so the originals aren't mutated.
            <sx, sy> is the offset of the beginning stroke, and <ex, ey> is the offset of the ending stroke. """
        paths = ChainPathList()
        paths.connect(self._first.offset + complex(sx, sy), self._last.offset + complex(ex, ey))
        elem = SVGElement(*self._first)
        elem.translate(sx, sy)
        paths.append(elem)
        elem = SVGElement(*self._last)
        elem.translate(ex, ey)
        paths.append(elem)
        return iter(paths)


class ProcessedBoardElements(List[SVGElement], BoardElements):
    """ Group of elements with various processing functions applied based on XML attributes.
        Since XML attributes are not guaranteed any order, the procs must be applied in order of method definition. """

    _txtmaxarea: tuple = (20.0, 20.0)  # Maximum available area for text. Determines text scale and orientation.
    _txtspacing: float = 14.4          # Horizontal spacing of text in pixels at default scale.

    def _append_at_offset(self, elem:SVGElement) -> None:
        """ Translate an SVG element by the current offset and add it as a child. """
        elem.translate(self.offset.real, self.offset.imag)
        self.append(elem)

    def process(self, proc_defs:Dict[str, dict], **attrib:str) -> None:
        """ Pop XML attributes that match proc_ methods and call each method using the corresponding defs dict. """
        for k in self.PROCS:
            if k in attrib:
                getattr(self, "proc_" + k)(attrib.pop(k), proc_defs.get(k) or {})
        # If any attributes are left, propagate them to our children.
        if attrib:
            for child in self:
                child.update(attrib, **child)

    def proc_pos(self, e_id:str, d:dict) -> None:
        """ Add to the total offset used in text and annotations (such as inversion arrows)."""
        self.offset += complex(*d[e_id])

    def proc_shape(self, e_id:str, d:dict) -> None:
        """ Add an SVG path shape, then advance the offset to center any following text. """
        attrs = d[e_id]
        elem = SVGPath(d=attrs["d"])
        self._append_at_offset(elem)
        self.offset += complex(*attrs["txtcenter"])
        self._txtmaxarea = (*attrs["txtarea"],)
        self._txtspacing = attrs["txtspacing"]

    def proc_path(self, e_id:str, d:dict) -> None:
        """ Add an SVG path at the current offset. """
        elem = SVGPath(d=d[e_id])
        self._append_at_offset(elem)

    def proc_text(self, text:str, glyphs:dict, _FONT_SIZE:int=24, _EM_SIZE:int=1000) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths.
            Max font size is 24 pt. Text paths are defined with an em box of 1000 units. """
        elem = SVGElement(fill="#000000")
        self._append_at_offset(elem)
        n = len(text) or 1
        spacing = self._txtspacing
        w, h = self._txtmaxarea
        scale = min(1.0, w / (n * spacing))
        # If there is little horizontal space and plenty of vertical space, turn the text 90 degrees.
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

    # Record every processor method attribute in definition order.
    PROCS = [attr[5:] for attr in locals() if attr.startswith("proc_")]


class BoardElementIndex:
    """ Index for finding board elements corresponding to key strings and/or steno rules. """

    def __init__(self, layout:KeyLayout, rule_elems:Dict[StenoRule, BoardElements],
                 key_elems:Dict[str, BoardElements], unmatched_elems:Dict[str, BoardElements]) -> None:
        self._rule_elems = rule_elems                # Dict with elements for certain rules.
        self._key_elems = key_elems                  # Dict with normal steno key elements.
        self._unmatched_elems = unmatched_elems      # Dict with steno key elements in unmatched rules.
        self._convert_to_skeys = layout.from_rtfcre  # Conversion function from RTFCRE to s-keys.

    def match_keys(self, keys:str, unmatched=False) -> List[BoardElements]:
        """ Return board diagram elements from an ordinary steno key string. No special elements will be used. """
        d = self._unmatched_elems if unmatched else self._key_elems
        return [d[k] for k in self._convert_to_skeys(keys) if k in d]

    def match_rule(self, rule:StenoRule) -> List[BoardElements]:
        """ Return board diagram elements from a steno rule recursively, with a key finder as backup. """
        # If the rule itself has an entry in the dict, just return that element.
        if rule in self._rule_elems:
            return [self._rule_elems[rule]]
        elems = []
        for item in rule.rulemap:
            elems += self.match_rule(item.rule)
        flags = rule.flags
        if not elems:
            # If the rule has no children and no dict entry, just return elements for each raw key.
            return self.match_keys(rule.keys, flags.unmatched)
        if flags:
            # Rules using inversions or linked strokes may be drawn with connectors.
            if flags.inversion:
                return [InversionBoardElements(*elems)]
            elif flags.linked:
                return [LinkedBoardElements(*elems)]
        return elems


class BoardElementParser:
    """ Processes XML elements into steno board elements using a definitions dictionary. """

    def __init__(self, defs:Dict[str, dict]) -> None:
        self._proc_defs: dict = defaultdict(dict, defs)  # Dict of definitions for constructing SVG board elements.
        self._parsed_elems: dict = defaultdict(dict)     # Parsed board elements indexed by tag, then by ID.

    def parse_xml(self, xml:bytes) -> None:
        """ Parse all ID'd elements from a raw XML bytes document into full SVG board elements. """
        root = XMLElement.decode(xml)
        self._parse_xml(root)

    def _parse_xml(self, xml_elem:XMLElement) -> ProcessedBoardElements:
        """ Parse an XML element recursively. If it has an ID, save it into one combined board element structure.
            Each child inherits attributes (except ID) from its predecessor. """
        board_elems = ProcessedBoardElements()
        xml_id = xml_elem.pop("id", None)
        if xml_id is not None:
            self._parsed_elems[xml_elem.tag][xml_id] = board_elems
        board_elems.process(self._proc_defs, **xml_elem)
        for child in xml_elem:
            child.update(xml_elem, **child)
            board_elems += self._parse_xml(child)
        return board_elems

    def make_index(self, layout:KeyLayout, rules:Dict[str, StenoRule]) -> BoardElementIndex:
        """ Build an element index from various tag groups filled during parsing. """
        # Elements corresponding to single steno keys.
        key_elems = self._parsed_elems["key"]
        key_elems[layout.SEP] = SeparatorBoardElements()
        # Elements corresponding to unmatched steno keys.
        ukey_elems = self._parsed_elems["qkey"]
        ukey_elems[layout.SEP] = SeparatorBoardElements()
        # Elements corresponding to known rule identifiers.
        rule_elems = self._parsed_elems["rule"]
        rule_elems = {rules[k]: rule_elems[k] for k in rule_elems}
        return BoardElementIndex(layout, rule_elems, key_elems, ukey_elems)

    def defs_base_pair(self) -> Tuple[SVGDefs, SVGElement]:
        """ Return a <use> element for the base present in every stroke along with a matching <defs> element. """
        base_elems = self._parsed_elems["base"]
        base = SVGElement()
        for grp in base_elems.values():
            base.extend(grp)
        defs = SVGDefs()
        return defs, defs.make_usable(base)

    def diagram_bounds(self) -> List[int]:
        """ Return [x, y, w, h] integer coordinates for the bounds of one stroke diagram. """
        return self._proc_defs["document"]["bounds"]


class BoardGenerator:
    """ Top-level factory for creating SVG steno board documents from user input. """

    _DEFAULT_RATIO = 100.0  # If no aspect ratio is given, this ensures that all boards end up in one row.

    def __init__(self, index:BoardElementIndex, defs:SVGDefs, base:SVGElement, x:int, y:int, w:int, h:int) -> None:
        """ Groups and transforms SVG elements into a final series of SVG steno board graphics. """
        self._index = index  # Index for matching keys/rules to board elements.
        self._defs = defs    # SVG defs element to include at the beginning of every document.
        self._base = base    # Base SVG element that is shown under every stroke diagram.
        self._offset = x, y  # X/Y offset for the viewbox of one stroke diagram.
        self._size = w, h    # Width/height for the viewbox of one stroke diagram.
        self._ratio = w / h  # Aspect ratio of one stroke diagram.

    def from_keys(self, keys:str, aspect_ratio:float=_DEFAULT_RATIO) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a set of steno keys. """
        elems = self._index.match_keys(keys)
        return self._build_document(elems, aspect_ratio)

    def from_rule(self, rule:StenoRule, aspect_ratio:float=_DEFAULT_RATIO, compound=True) -> bytes:
        """ Generate encoded board diagram layouts arranged according to <aspect_ratio> from a steno rule.
            If <compound> is False, do not use compound keys. The rule will be shown only as single keys. """
        if not compound:
            return self.from_keys(rule.keys, aspect_ratio)
        elems = self._index.match_rule(rule)
        return self._build_document(elems, aspect_ratio)

    def _build_document(self, elems:List[BoardElements], device_ratio:float) -> bytes:
        """ Split elements into diagrams, arrange them to match the aspect ratio, and encode a new SVG document. """
        # Cap off the elements with an explicit stroke separator.
        elems.append(SeparatorBoardElements())
        stroke_count = len([1 for el in elems if el.ends_stroke])
        rows, cols = self._dimensions(stroke_count, device_ratio)
        tfrms = self._transforms(cols, stroke_count)
        w, h = self._size
        document = SVGDocument(self._defs)
        document.set_viewbox(*self._offset, w * cols, h * rows)
        self._arrange(document, elems, tfrms)
        return document.encode()

    def _dimensions(self, count:int, device_ratio:float) -> Tuple[int, int]:
        """ Calculate the best arrangement of <count> sub-diagrams in rows and columns for the best possible scale.
            <rel_ratio> is the aspect ratio of one diagram divided by that of the device viewing area. """
        rel_ratio = self._ratio / device_ratio
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

    def _arrange(self, parent:SVGElement, elems:Iterable[BoardElements], tfrms:List[Tuple[int, int]]) -> None:
        """ Arrange all elements within a parent SVG element, with a separate diagram for each stroke.
            Transform each diagram to be tiled left-to-right, top-to-bottom in a grid layout. """
        overlays = []
        stroke = []
        i = 0
        for el in elems:
            stroke += el
            if el.iter_overlays is not None:
                overlays += el.iter_overlays(*tfrms[i], *tfrms[i + 1])
            if el.ends_stroke:
                diagram = SVGElement(self._base, *stroke)
                diagram.translate(*tfrms[i])
                parent.append(diagram)
                stroke = []
                i += 1
        parent.extend(overlays)
