import json


class TextFileIO:

    def __init__(self, *, encoding='utf-8') -> None:
        self._encoding = encoding  # Character encoding. UTF-8 must be explicitly set on some platforms.

    def read(self, filename:str) -> str:
        """ Load a text file into a string. """
        with open(filename, 'r', encoding=self._encoding) as fp:
            return fp.read()

    def write(self, filename:str, s:str) -> None:
        """ Save a string into a text file. """
        with open(filename, 'w', encoding=self._encoding) as fp:
            fp.write(s)


def check_dict(d:object) -> None:
    if not isinstance(d, dict):
        raise TypeError('Expected a dictionary, got a ' + type(d).__name__)


class JSONDictionaryIO:
    """ Provides basic I/O for dictionary-based JSON resources. """

    def __init__(self, io:TextFileIO=None, *, comment_prefix="#") -> None:
        self._io = io or TextFileIO()          # IO for text files.
        self._comment_prefix = comment_prefix  # Prefix for comments allowed in non-standard JSON files.

    def _cson_strip(self, s:str) -> str:
        """ Strip a non-standard JSON string of full-line comments (CSON = commented JSON).
            JSON doesn't care about leading or trailing whitespace, so strip every line first. """
        lines = s.split("\n")
        stripped_line_iter = map(str.strip, lines)
        data_lines = [line for line in stripped_line_iter
                      if line and not line.startswith(self._comment_prefix)]
        return "\n".join(data_lines)

    def load_json_dict(self, filename:str) -> dict:
        """ Load a string dict from a JSON-based file. """
        s = self._io.read(filename)
        if filename.endswith(".cson"):
            s = self._cson_strip(s)
        try:
            d = json.loads(s)
        except json.JSONDecodeError as e:
            # Reraise decoding exceptions with the filename and context (original lineno may be wrong).
            i = e.pos
            before = e.doc[i-20:i]
            after = e.doc[i:i+20]
            context = repr(before + '<<!>>' + after)[1:-1]
            raise ValueError(f'JSON decoding error in {filename}: ...{context}...') from None
        check_dict(d)
        return d

    def save_json_dict(self, filename:str, d:dict) -> None:
        """ Save a string dict to a JSON file. Key sorting helps some algorithms run faster.
            ensure_ascii=False is required to preserve Unicode symbols. """
        check_dict(d)
        s = json.dumps(d, sort_keys=True, ensure_ascii=False, indent=0)
        self._io.write(filename, s)
