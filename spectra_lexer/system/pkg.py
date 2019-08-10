import os
import sys
import zipfile
import zipimport


class FileProvider:
    """ Provides access to package resources in the filesystem """

    module_path: str

    def __init__(self, module):
        self.module_path = os.path.dirname(getattr(module, '__file__', ''))

    def get_resource_string(self, resource_name):
        return self._get(self._path_from(resource_name))

    def has_resource(self, resource_name):
        return self._has(self._path_from(resource_name))

    def resource_isdir(self, resource_name):
        return self._isdir(self._path_from(resource_name))

    def resource_listdir(self, resource_name):
        return self._listdir(self._path_from(resource_name))

    def _path_from(self, resource_name):
        path = self.module_path
        if resource_name:
            path = os.path.join(path, *resource_name.split('/'))
        return path

    def _get(self, path):
        with open(path, 'rb') as stream:
            return stream.read()

    def _has(self, fspath):
        return os.path.exists(fspath)

    def _isdir(self, fspath):
        return os.path.isdir(fspath)

    def _listdir(self, fspath):
        return os.listdir(fspath)


class ZipProvider(FileProvider):

    loader = None

    _zipinfo: dict
    _dirindex: dict

    def __init__(self, module, loader):
        """ Load a manifest at path. """
        super().__init__(module)
        self.loader = loader
        path = os.path.normpath(loader.archive)
        with zipfile.ZipFile(path) as zfile:
            self._zipinfo = {name.replace('/', os.sep): zfile.getinfo(name) for name in zfile.namelist()}
        self._dirindex = ind = {}
        for path in self._zipinfo:
            parts = path.split(os.sep)
            while parts:
                parent = os.sep.join(parts[:-1])
                if parent in ind:
                    ind[parent].append(parts[-1])
                    break
                else:
                    ind[parent] = [parts.pop()]

    def _zipinfo_name(self, fspath):
        # Convert a virtual filename (full path to file) into a zipfile subpath
        # usable with the zipimport directory cache for our target archive
        fspath = fspath.rstrip(os.sep)
        if fspath == self.loader.archive:
            return ''
        zip_pre = self.loader.archive + os.sep
        if fspath.startswith(zip_pre):
            return fspath[len(zip_pre):]

    def _get(self, path):
        return self.loader.get_data(path)

    def _has(self, fspath):
        zip_path = self._zipinfo_name(fspath)
        return zip_path in self._zipinfo or zip_path in self._dirindex

    def _isdir(self, fspath):
        zip_path = self._zipinfo_name(fspath)
        return zip_path in self._dirindex

    def _listdir(self, fspath):
        zip_path = self._zipinfo_name(fspath)
        return list(self._dirindex.get(zip_path, ()))


def get_provider(module_name):
    if module_name not in sys.modules:
        __import__(module_name)
    module = sys.modules[module_name]
    loader = getattr(module, '__loader__', None)
    if isinstance(loader, zipimport.zipimporter):
        return ZipProvider(module, loader)
    else:
        return FileProvider(module)


def resource_exists(package, resource_name):
    """Does the named resource exist?"""
    return get_provider(package).has_resource(resource_name)


def resource_isdir(package, resource_name):
    """Is the named resource an existing directory?"""
    return get_provider(package).resource_isdir(resource_name)


def resource_string(package, resource_name):
    """Return specified resource as a string"""
    return get_provider(package).get_resource_string(resource_name)


def resource_listdir(package, resource_name):
    """List the contents of the named resource directory"""
    return get_provider(package).resource_listdir(resource_name)
