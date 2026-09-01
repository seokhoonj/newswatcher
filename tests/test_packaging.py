import newswatcher
from newswatcher import errors


def test_version_is_a_string():
    assert isinstance(newswatcher.__version__, str)
    assert newswatcher.__version__.count(".") >= 2


def test_error_hierarchy_roots_at_newswatcher_error():
    for name in errors.__all__:
        cls = getattr(errors, name)
        assert issubclass(cls, errors.NewswatcherError)
