

def dump_yaml(data, filepath):
    """Dumps data to a YAML file
    :param data: Data to dump
    :param filepath: The path to the YAML file
    """
    import yaml

    with open(filepath, "w") as f:
        yaml.dump(data, f, sort_keys=False)


def get_col_widths(dataframe):
    """Gets the column widths for each data frame column
    Used for Excel exports
    :param dataframe: The data frame to inspect
    """
    idx_max = max(
        [len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))]
    )
    res = [idx_max] + [
        max([len(str(s)) for s in dataframe[col].values] + [len(col)])
        for col in dataframe.columns
    ]
    return res


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return _ClassPropertyDescriptor(func)


class _ClassPropertyDescriptor(object):
    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self
