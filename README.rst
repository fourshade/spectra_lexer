Spectra Lexer
=============

The Spectra Steno Lexer is an experimental tool for analyzing and matching patterns of steno keys against the text they produce using various rules from steno theories (mostly Plover theory). It also has advanced search functions for steno dictionaries which have been mostly lacking in Plover up to this point.

|Main Screenshot|

Installation and Operation
--------------------------

Spectra is primarily designed as a plugin for Plover. If you have installed the latest binary release of Plover (4.0.0.dev8 as of this writing), the plugins manager should be able to find this program in the PyPI database and set it up automatically for you. When opened from the main toolbar, Spectra will automatically load Plover's dictionaries for manual searching and will also attempt to analyze strokes sent from Plover as you type.

If you have built and installed Plover from source, it is not likely to have the plugins manager by default. In this case it is possible to install Spectra through pip like any other Python package. Plover searches through all available Python paths to find plugins; so long as it ends up in the same general place that Plover looks for its other dependencies, it should find it just fine.

Source Installation
-------------------

To run this software on its own from source, you must have a correctly installed Python distribution (3.6 or greater). Download or clone the source into a free directory, change to this directory in a terminal and type:

``python3 setup.py install``

This will install it to your Python distribution with all features.

Advanced Operation (from console)
---------------------------------

From the console, you can execute the main GUI program on its own by typing:

``spectra_lexer gui``

The standalone mode operates identically to the plugin in all respects except that it cannot decipher strokes in real-time. By default, the program will look for your Plover dictionaries in the default user data directories; it may not find them if you have them somewhere else, or have a strange user configuration. But unlike the plugin, there is a menu bar with experimental tools where dictionaries can be loaded manually.

There is also a batch mode available for analysis purposes. Run it by typing:

``spectra_lexer batch IN_DICT OUT_DICT``

where IN_DICT is a path to a JSON dictionary of steno translations, and OUT_DICT is a path to a (new) JSON file that will store the output. The lexer will run on each translation and store the output in the same format as the rules dictionary files.

There are other command line arguments available, but they are usually redundant and/or unnecessary. See __main__.py for more details.

Details
-------

This software is currently experimental with many rules unaccounted for, so do not rely on it to figure out the rules of stenography with 100% accuracy. If it cannot match every single steno key to letters in the word, it will simply not return a result at all (to avoid guessing wrong). Inversions and asterisks are particularly troublesome here; inversions of steno order violate the strict left-to-right parsing that lexers rely on, and oftentimes there is not enough context to figure out the meaning of an asterisk from just a stroke and the word it makes in the absence of other information. Briefs are often constructed by keeping only the most important parts or sounds of a word, and Spectra can usually match these, but briefs relying on strange phonetics or arbitrary sequences of keys simply cannot be matched without pre-programmed custom rules (which are included for some of the most common briefs, but not many).

When searching from the lookup tool, if a word is chosen and there is more than one stroke entry for it, the lexer will attempt to analyze each one and select the one that has the best possibility of being "correct" (i.e. not a misstroke), choosing shorter strokes over longer ones to break ties.

.. |Main Screenshot| image:: https://raw.githubusercontent.com/fourshade/spectra_lexer/master/doc/screenshot.png
