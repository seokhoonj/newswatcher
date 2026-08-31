import pytest

from newswatch.errors import TopicError
from newswatch.topics import Topic, add_topic, load_topics


def test_scalar_topic_key_is_rejected(tmp_path):
    # [topic] as a scalar instead of the [[topic]] table array is a clear error
    path = tmp_path / "topics.toml"
    path.write_text('topic = "x"\n', encoding="utf-8")
    with pytest.raises(TopicError):
        load_topics(path)


def test_add_then_load_roundtrip(tmp_path):
    path = tmp_path / "topics.toml"
    assert add_topic(Topic("insurance", includes=("보험", "손보")), path) is True
    assert add_topic(Topic("insurance"), path) is False  # duplicate name -> no-op
    topics = load_topics(path)
    assert len(topics) == 1
    assert topics[0].name == "insurance"
    assert topics[0].includes == ("보험", "손보")


def test_add_appends_second_topic(tmp_path):
    path = tmp_path / "topics.toml"
    add_topic(Topic("insurance", includes=("보험",)), path)
    add_topic(Topic("banking", includes=("은행",), excludes=("광고",)), path)
    names = {t.name for t in load_topics(path)}
    assert names == {"insurance", "banking"}


def test_string_include_is_one_word(tmp_path):
    path = tmp_path / "topics.toml"
    path.write_text('[[topic]]\nname = "x"\nincludes = "solo"\n', encoding="utf-8")
    assert load_topics(path)[0].includes == ("solo",)
