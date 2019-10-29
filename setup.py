#!/usr/bin/env python3

""" Build script for main program; originally copied from Plover and stripped down. """

from glob import glob
import os
import shutil
import subprocess
import sys

from setuptools import Command as stCommand, setup
from setuptools.command import develop, install, sdist


class BaseCommand(stCommand):
    """ Abstract command class that runs dependencies before the command itself. """
    requires = ""
    def __init__(self, *args):
        """ Run all dependency commands in order before touching the main one. """
        super().__init__(*args)
        for cmd in self.requires.split():
            self.run_command(cmd)


class Command(BaseCommand):
    """ BaseCommand with default fields and methods defined. """
    user_options = []
    def initialize_options(self):
        self.args = []
    def finalize_options(self):
        pass


class CommandNamespace:
    """ Contains all command classes for use in setuptools.setup().
        Any command here may be run by name, e.g. > python3 setup.py clean. """

    class build_ui(Command):
        description = "Build Python code from new/modified Qt UI files."
        requires = "clean"
        def run(self):
            for src in glob('**/*.ui', recursive=True):
                dst = os.path.splitext(src)[0] + '_ui.py'
                if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                    continue
                cmd = (sys.executable, '-m', 'PyQt5.uic.pyuic', '--from-import', src)
                with open(dst, 'w') as fp:
                    subprocess.run(cmd, stdout=fp, text=True)

    class clean(Command):
        description = "Remove all build and test-generated files."
        def run(self):
            for pattern in ('.pytest_cache', 'build', 'dist', '*.egg-info', '**/__pycache__', '**/*_ui.py'):
                for path in glob(pattern, recursive=True):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    elif os.path.exists(path):
                        os.remove(path)

    class develop(BaseCommand, develop.develop):
        requires = "build_ui"

    class install(BaseCommand, install.install):
        requires = "build_ui"

    class run(Command):
        description = "Build UI, then run from source."
        requires = "build_ui"
        command_consumes_arguments = True
        def run(self):
            cmd = (sys.executable, '-m', 'spectra_lexer', *self.args)
            subprocess.run(cmd, check=True)

    class sdist(BaseCommand, sdist.sdist):
        requires = "build_ui"

    class test(Command):
        description = "Build UI, then run all unit tests."
        requires = "build_ui"
        def run(self):
            import pytest
            pytest.main()


setup(cmdclass=dict(vars(CommandNamespace)))
