import sys

import pkg_resources


def main() -> None:
    """ Main console entry point for the Spectra steno lexer. """
    script, *args = sys.argv
    # The first argument determines the entry point/mode to run.
    # All subsequent arguments are command-line options for that mode.
    # With no arguments, redirect to the standalone GUI app.
    if not args:
        args = ("gui",)
    mode, *cmd_opts = args
    # Make sure the mode matches exactly one operations entry point.
    ep_iter = pkg_resources.iter_entry_points('spectra_lexer.operations')
    matches = [ep for ep in ep_iter if ep.name.startswith(mode)]
    if not matches:
        print(f'No matches for operation "{mode}"')
        return
    if len(matches) > 1:
        print(f'Multiple matches for operation "{mode}". Use more characters.')
        return
    # Reassign the remaining arguments to sys.argv and run the entry point.
    sys.argv = [script, *cmd_opts]
    matches[0].load()()


if __name__ == '__main__':
    main()
