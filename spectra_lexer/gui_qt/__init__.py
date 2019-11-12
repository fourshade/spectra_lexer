""" Package for the Qt-based GUI components of Spectra. """

# Standalone GUI Qt application entry point.
from .main import main as gui
# Plover GUI Qt plugin entry point.
from .plover import PloverPlugin as plugin
