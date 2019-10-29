""" Package for the Qt-based GUI components of Spectra. """

from .main import QtMain
from .plover import PloverProxy

# Standalone GUI Qt application entry point.
gui = QtMain()
# Plover GUI Qt plugin entry point.
plugin = PloverProxy
