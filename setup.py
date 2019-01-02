#!/usr/bin/env python3

""" Main build script for lexer program, originally copied from Plover and stripped down. Work in progress. """

from glob import glob
from importlib import import_module
import os
import shutil
import subprocess
import sys

import pkg_resources
import setuptools.command


CMDCLASS_DICT = {}
class CommandMeta(type):
    """ Build command metaclass. Creates and records setuptools command classes. """
    def __new__(mcs, name, bases, dct):
        # If no run method is given and the name matches one from setuptools, use that as the base.
        if "run" not in dct and name in setuptools.command.__all__:
            bases = (getattr(import_module("setuptools.command."+name), name),)
        # If there are dependencies or finishers, make a new run method to run them before/after the original.
        deps = dct.get("requires", "")
        finishers = dct.get("finish_with", "")
        if deps or finishers:
            run = dct.get("run") or bases[0].run
            def run_sequence(self):
                for cmd in deps.split():
                    self.run_command(cmd)
                run(self)
                for cmd in finishers.split():
                    self.run_command(cmd)
            dct["run"] = run_sequence
        # Each class is recorded in a dict to give to setuptools.setup().
        cls = super().__new__(mcs, name, bases, dct)
        CMDCLASS_DICT[name] = cls
        return cls


class Command(setuptools.Command, metaclass=CommandMeta):
    """ setuptools.Command with default fields and methods defined. """
    user_options = []
    def initialize_options(self): self.args = []
    def finalize_options(self): pass
    def run(self): pass


class build_ui(Command):
    description = "Build new/modified UI files."

    def _build_ui(self, src):
        """ Build Python code from a QT UI file. """
        dst = os.path.splitext(src)[0] + '_ui.py'
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            return
        cmd = (sys.executable, '-m', 'PyQt5.uic.pyuic', '--from-import', src)
        contents = subprocess.check_output(cmd).decode('utf-8')
        with open(dst, 'w') as fp:
            fp.write(contents)

    def _build_resources(self, src):
        """ Build Python code from a QT resource package. """
        dst = os.path.join(os.path.dirname(src), '..', os.path.splitext(os.path.basename(src))[0]) + '_rc.py'
        cmd = (sys.executable, '-m', 'PyQt5.pyrcc_main', src, '-o', dst)
        subprocess.check_call(cmd)

    def run(self):
        for src in glob('**/*.qrc', recursive=True):
            self._build_resources(src)
        for src in glob('**/*.ui', recursive=True):
            self._build_ui(src)


class clean(Command):
    description = "Remove all build and test-generated files."
    patterns = ('.pytest_cache', 'build', 'dist', '*.egg-info', '**/__pycache__', '**/*_ui.py', '**/*_rc.py')

    def run(self):
        matches = [m for p in self.patterns for m in glob(p, recursive=True)]
        for f in filter(os.path.exists, matches):
            if os.path.isdir(f):
                shutil.rmtree(f)
            else:
                os.remove(f)


class develop(Command):
    requires = "build_ui"


class install(Command):
    requires = "build_ui"


class run(Command):
    description = "Build UI, then run from source."
    command_consumes_arguments = True
    requires = "build_ui"

    def run(self):
        cmd = (sys.executable, '-m', 'spectra_lexer', *self.args)
        subprocess.check_call(cmd)


class sdist(Command):
    requires = "build_ui"


class test(Command):
    description = "Build UI, then run all unit tests."
    requires = "build_ui"

    def run(self):
        pkg_resources.working_set.__init__()
        pkg_resources.load_entry_point('pytest', 'console_scripts', 'py.test')()


# Any command above may be run by name, e.g. > python3 setup.py clean
setuptools.setup(cmdclass=CMDCLASS_DICT)
