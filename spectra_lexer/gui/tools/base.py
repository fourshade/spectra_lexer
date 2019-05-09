from spectra_lexer.core import Component


class GUITool(Component):
    """ Tracks a dialog object so that no more than one ever exists. """

    _dialog = None  # Previous dialog object. Must be set to None on deletion.

    def open_dialog(self, *args, persistent=False, **kwargs) -> None:
        """ If a dialog exists but is not persistent, destroy it. """
        dlg = self._dialog
        if dlg is not None and not persistent:
            self.destroy_dialog(dlg)
            dlg = None
        # If no dialog exists (including because we destroyed it), make a new one.
        if dlg is None:
            dlg = self._dialog = self.create_dialog(*args, **kwargs)
        # Show the new/old dialog in any case.
        self.show_dialog(dlg)

    def create_dialog(self, *args, **kwargs):
        """ Create and return a new dialog with the given args. """
        raise NotImplementedError

    def destroy_dialog(self, dialog) -> None:
        """ Destroy the given dialog object. """
        raise NotImplementedError

    def show_dialog(self, dialog) -> None:
        """ Display the given dialog on the screen. """
        raise NotImplementedError
