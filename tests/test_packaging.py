import newswatch
from newswatch import errors


def test_version_is_a_string():
    assert isinstance(newswatch.__version__, str)
    assert newswatch.__version__.count(".") >= 2


def test_error_hierarchy_roots_at_newswatch_error():
    for name in errors.__all__:
        cls = getattr(errors, name)
        assert issubclass(cls, errors.NewswatchError)
