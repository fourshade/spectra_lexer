from PyQt5.QtWidgets import QFileDialog

from .base import GUIQT_TOOL


class QtFileTool(GUIQT_TOOL):
    """ Controls user-based file loading and program exit. """

    def TOOLFileOpenTranslations(self) -> None:
        self._load_dialog("translations", ".json")

    def TOOLFileOpenIndex(self) -> None:
        self._load_dialog("index", ".json")

    def TOOLFileExit(self) -> None:
        self.Exit()

    def _load_dialog(self, res_type:str, *fmts:str) -> None:
        """ Present a modal dialog for <res_type> to select files with an extension in <fmts> for loading.
            Send a command to load the file selection list unless it is empty or the dialog is cancelled. """
        title = f"Load {res_type.title()}"
        filter_msg = f"Supported files (*{' *'.join(fmts)})"
        filenames = QFileDialog.getOpenFileNames(self.WINDOW, title, ".", filter_msg)[0]
        if filenames:
            self.VIEWDialogFileLoad(filenames, res_type)
