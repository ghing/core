import datetime
import os

from openelex.base.cache import StateCache

CACHED_FILE_MISSING_MSG = ("Cached results file does not exist. Try running "
    "the fetch task before running this test")

def cache_file_exists(state, filename):
    """
    Does a cache file exist?
    
    This is designed to be a predicate for the skipUnless decorator.
    This allows us to skip tests that depend on a cached downloaded
    results file when that file doesn't exist.

    """
    cache = StateCache(state)
    path = os.path.join(cache.abspath, filename)
    return os.path.exists(path)


class LoaderPrepMixin(object):
    def _get_mapping(self, filename):
        return self.loader.datasource.mapping_for_file(filename)

    def _prep_loader_attrs(self, mapping):
        # HACK: set loader's mapping attribute
        # so we can test if loader._file_handle exists.  This
        # usually happens in the loader's run() method.
        self.loader.source = mapping['generated_filename']
        self.loader.election_id = mapping['election']
        self.loader.timestamp = datetime.datetime.now()
