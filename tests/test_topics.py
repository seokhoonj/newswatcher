import pytest

from newswatcher.errors import TopicError
from newswatcher.topics import Topic, add_topic, load_topics


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


def test_add_topic_rejects_an_empty_or_whitespace_name(tmp_path):
    path = tmp_path / "topics.toml"
    for blank in ("", "   "):
        with pytest.raises(TopicError):
            add_topic(Topic(blank), path)
    assert not path.exists()   # nothing written, so a later load still succeeds


def test_add_topic_writes_the_preserved_block_format(tmp_path):
    # The appended block is byte-identical to what the old whole-file renderer produced:
    # name, then a non-empty includes as an inline array; non-ASCII kept verbatim.
    path = tmp_path / "topics.toml"
    add_topic(Topic("보험", includes=("a", "b")), path)
    assert path.read_text(encoding="utf-8") == '[[topic]]\nname = "보험"\nincludes = ["a", "b"]\n'
