#!/usr/bin/env python3

""" Unit test utility functions, usable by any test module. """

import os

import pytest


def get_test_filename(r_type:str) -> str:
    """ Get the filename for the program test data by type (i.e. translations that should all pass with matches). """
    return os.path.join(__file__, "..", f"data/{r_type}.json")


def class_tester(*test_classes:type):
    """ Using a series of relevant test classes, create a decorator which configures test functions to run
        not only on the designated classes, but also on any derived classes that appear in the test set. """
    def using_bases(*bases:type):
        """ Decorator to define the base classes for a class test, so that it may also be run on subclasses.
            Make sure the test is still run on the defined bases at minimum even if they aren't in the list. """
        targets = {c for cls in bases for c in test_classes if issubclass(c, cls)}
        return pytest.mark.parametrize("cls", targets.union(bases))
    return using_bases
