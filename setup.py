#!/usr/bin/env python3

""" Main build script for lexer program, originally copied from Plover and stripped down. Work in progress. """

from glob import glob
import os
import shutil
import subprocess
import sys

import pkg_resources
import setuptools.command.develop
import setuptools.command.install

CMDCLASS_DICT = {}


class _EntrancyCounter:
    """ Simple context manager to count stack depth and print corresponding indentations. """
    depth = 0
    def __enter__(self): self.depth += 1
    def __exit__(self, *args): self.depth -= 1
    def indent_for_depth(self, count): print(" " * (self.depth * count), end='')


class Command:
    """ Abstract command class that runs dependencies before the command itself. """
    requires = ""

    def __init_subclass__(cls):
        """ Each class is recorded in a dict to give to setuptools.setup(). """
        CMDCLASS_DICT[cls.__name__] = cls

    def finalize_options(self):
        """ Run all commands in order, including dependencies. Make sure not to redo any. """
        super().finalize_options()
        getvar = vars(self.distribution).setdefault
        stack = getvar("stack", _EntrancyCounter())
        tracker = getvar("tracker", set())
        with stack:
            for cmd in self.requires.split():
                if cmd not in tracker:
                    stack.indent_for_depth(4)
                    self.run_command(cmd)
                    tracker.add(cmd)


class CustomCommand(setuptools.Command):
    """ setuptools.Command with default fields and methods defined. """
    user_options = []
    def initialize_options(self): self.args = []
    def finalize_options(self): pass


class build_ui(Command, CustomCommand):
    description = "Build new/modified UI files."
    requires = "clean"

    def run(self):
        """ Build Python code from QT UI files. """
        for src in glob('**/*.ui', recursive=True):
            dst = os.path.splitext(src)[0] + '_ui.py'
            if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                continue
            cmd = (sys.executable, '-m', 'PyQt5.uic.pyuic', '--from-import', src)
            contents = subprocess.check_output(cmd).decode('utf-8')
            with open(dst, 'w') as fp:
                fp.write(contents)


class clean(Command, CustomCommand):
    description = "Remove all build and test-generated files."
    patterns = ('.pytest_cache', 'build', 'dist', '*.egg-info', '**/__pycache__', '**/*_ui.py')

    def run(self):
        matches = [m for p in self.patterns for m in glob(p, recursive=True)]
        for f in filter(os.path.exists, matches):
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.remove(f)


class develop(Command, setuptools.command.develop.develop):
    requires = "build_ui"


class install(Command, setuptools.command.install.install):
    requires = "build_ui"


class run(Command, CustomCommand):
    description = "Build UI, then run from source."
    command_consumes_arguments = True
    requires = "build_ui"

    def run(self):
        cmd = (sys.executable, '-m', 'spectra_lexer', *self.args)
        subprocess.check_call(cmd)


class sdist(Command, setuptools.command.sdist.sdist):
    requires = "build_ui"


class test(Command, CustomCommand):
    description = "Build UI, then run all unit tests."
    requires = "build_ui"

    def run(self):
        pkg_resources.working_set.__init__()
        pkg_resources.load_entry_point('pytest', 'console_scripts', 'py.test')()


# Any command above may be run by name, e.g. > python3 setup.py clean
setuptools.setup(cmdclass=CMDCLASS_DICT)
