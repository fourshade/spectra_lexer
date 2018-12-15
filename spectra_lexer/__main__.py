import spectra_lexer.gui_qt.app


def main() -> None:
    """ Main console entry point for the Spectra steno lexer. For now, redirect to the standalone GUI app. """
    spectra_lexer.gui_qt.app.main()


if __name__ == '__main__':
    main()
