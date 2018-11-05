Spectra Lexer
================

The Spectra Steno Lexer is an experimental tool for analyzing and matching patterns of steno keys against the text they produce using various rules from steno theories (mostly Plover theory). It also has advanced search functions for steno dictionaries which have been mostly lacking in Plover up to this point.

![Screenshot](doc/screenshot.png)

Installation
------------

To use this software, you must have a correctly installed Python distribution (3.6 or greater). Download or clone the source into a free directory, change to this directory in a terminal and type:

``python3 setup.py install``

This will install it to your Python distribution as a console script, allowing you to execute the main program by typing:

``spectra_lexer [DICT1 DICT2 ...]``

where each DICT is a path to a JSON file containing a single dictionary mapping steno key sequences to text (the dictionaries used by Plover are in the correct format). You can also execute the script without arguments and load the search dictionaries via a dialog from the menu bar.

With Plover
-----------

While it is possible to run Spectra by itself, this is not its main purpose. It is primarily designed as a plugin for Plover, though using it as such requires a bit more setup until I can get it packaged and added to PyPI. If you have also installed Plover from source as a standard Python package (rather than as a binary), it should automatically find Spectra in your installed packages and add the plugin to the main toolbar. Used this way, the main dialog will automatically load Plover's dictionaries and will attempt to analyze strokes sent from Plover in addition to the manual lookup methods.

Getting this to work on Plover any other way requires dragging-and-dropping two folders to the right place. After installing the program as above, there should now be a folder labeled ``spectra_lexer.egg-info`` sitting next to ``spectra_lexer``. Take these two folders and copy them to one of the following locations (paths may be slightly different depending on your OS and build of Plover).

```
%PROGRAMFILES(X86)%\Open Steno Project\Plover 4.0.0.dev8\data\Lib\site-packages
%USERPROFILE%\AppData\Local\plover\plover\plugins\win\Python36\site-packages
Basically, any folder named "site-packages" is a good bet.
```

By default, the pre-packaged binaries of Plover are essentially a self-contained Python distribution bundled with the program and all its required dependencies. Spectra's dependencies are a subset of Plover's, so it should be *technically* possible to run the setup script and install it to Plover's local environment without any other version of Python on your system at all. A less insane choice would be to wait for it to appear on PyPI and get it through the plugins manager. ;)



Operation
---------

This software is currently experimental with many rules unaccounted for, so do not rely on it to figure out the rules of stenography with 100% accuracy. If it cannot match every single steno key to letters in the word, it will simply not return a result at all (to avoid guessing wrong). Inversions and asterisks are particularly troublesome here; inversions of steno order violate the strict left-to-right parsing that lexers rely on, and oftentimes there is not enough context to figure out the meaning of an asterisk from just a stroke and the word it makes in the absence of other information. Briefs are often constructed by keeping only the most important parts or sounds of a word, and Spectra can usually match these, but briefs relying on strange phonetics or arbitrary sequences of keys simply cannot be matched without pre-programmed custom rules (which are included for some of the most common briefs, but not many).

When searching from the lookup tool, if a word is chosen and there is more than one stroke entry for it, the lexer will attempt to analyze each one and select the one that has the best possibility of being "correct" (i.e. not a misstroke), choosing shorter strokes over longer ones to break ties.