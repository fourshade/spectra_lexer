from itertools import islice
import logging
from traceback import TracebackException


class SystemLogger:

    _FORMATTER = logging.Formatter('[%(asctime)s]: %(message)s', "%b %d %Y %H:%M:%S")
    _TB_MAX_LINES = 50

    _last_info: str = ""  # Most recently logged info string.

    def __init__(self, level=logging.INFO):
        self._logger = logging.getLogger('spectra')
        self._logger.setLevel(level)

    def add_stream(self, stream=None) -> None:
        stream_handler = logging.StreamHandler(stream)
        self._attach_handler(stream_handler)

    def add_file(self, filename:str, **kwargs) -> None:
        file_handler = logging.FileHandler(filename, encoding='utf-8', **kwargs)
        self._attach_handler(file_handler)

    def _attach_handler(self, handler) -> None:
        handler.setFormatter(self._FORMATTER)
        self._logger.addHandler(handler)

    def info(self, info:str) -> None:
        """ Log a basic info event. Omit details if identical to the last info event. """
        if info == self._last_info:
            info = "*"
        else:
            self._last_info = info
        self._logger.info('%s', info)

    def exception(self, exc:Exception) -> str:
        """ Log an exception as an error and return the formatted traceback. """
        tb_text = self._format_traceback(exc)
        try:
            self._logger.error('EXCEPTION\n%s', tb_text)
        except Exception as e:
            # stdout might be locked or redirected. We're probably screwed, but there may be other handlers.
            tb_text += f'\nFAILED TO WRITE LOG\n{self._format_traceback(e)}'
        return tb_text

    def _format_traceback(self, exc:Exception, **kwargs) -> str:
        """ Perform custom formatting of a traceback and return a string. """
        tb = TracebackException.from_exception(exc, **kwargs)
        return "".join(islice(tb.format(), self._TB_MAX_LINES))
