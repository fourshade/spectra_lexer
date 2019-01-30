# Subtypes to draw method attributes from. Later subtypes override methods of earlier ones with the same name.
_SUBTYPES = [list, set, dict]
# Method attribute names for each subtype. Method names used in type() can cause problems - exclude them.
_METHOD_ATTRS = {attr: subtype for subtype in _SUBTYPES for attr in set(vars(subtype)).difference(vars(type))}


class _ConstantsMetaMeta(type):
    """ Dunder methods get looked up on the metaclass. Adding them dynamically requires...a metametaclass. """

    def __prepare__(mmcs, *ignored):
        """ Load the metaclass namespace dict with redirects for all subtype method calls to the class. """
        return {attr: lambda cls, *args, attr=attr: getattr(cls, attr)(*args) for attr in _METHOD_ATTRS}


class _ConstantsMeta(type, metaclass=_ConstantsMetaMeta):
    """ Make attributes of constants classes accessible through methods of container subtypes. """

    def __new__(mcs, name:str, bases:tuple, dct:dict, **kwargs):
        """ Create containers of each subtype with copies of the user constants from the class attribute dict.
            Gather all constants from base classes as well. Subclass constants and kwargs must take precedence. """
        data = {**{k: v for b in bases for k, v in getattr(b, "_constants", {}).items()}, **dct, **kwargs}
        for subtype in _SUBTYPES:
            try:
                dct[subtype] = subtype(data.values())
            except (TypeError, ValueError):
                dct[subtype] = subtype(data)
        # The finished class namespace consists of container methods with the original class dict on top.
        methods = {attr: getattr(dct[tp], attr) for attr, tp in _METHOD_ATTRS.items()}
        return super().__new__(mcs, name, bases, {**methods, **data, "_constants": data})


class Constants(metaclass=_ConstantsMeta):
    """ Data class with attributes readable directly, as dict items, as set values, or as list values. """
