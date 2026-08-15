from newswatch.robots import RobotsGate


def _robots(txt):
    def fetch(url):
        assert url.endswith("/robots.txt")
        return txt
    return fetch


def test_disallow_blocks_only_matching_paths():
    gate = RobotsGate("newswatch", _robots(
        "User-agent: *\nDisallow: /admin/\n"))
    assert gate.can_fetch("https://e.com/news/1") is True
    assert gate.can_fetch("https://e.com/admin/x") is False


def test_missing_robots_allows_all():
    gate = RobotsGate("newswatch", _robots(None))  # no robots.txt -> allow
    assert gate.can_fetch("https://e.com/anything") is True


def test_crawl_delay_is_read():
    gate = RobotsGate("newswatch", _robots(
        "User-agent: *\nCrawl-delay: 30\nDisallow: /admin/\n"))
    assert gate.crawl_delay("https://e.com/news") == 30.0


def test_per_host_cache_fetches_once():
    calls = []
    def fetch(url):
        calls.append(url)
        return "User-agent: *\nDisallow:\n"
    gate = RobotsGate("newswatch", fetch)
    gate.can_fetch("https://e.com/a")
    gate.can_fetch("https://e.com/b")
    gate.can_fetch("https://other.com/a")
    assert calls == ["https://e.com/robots.txt", "https://other.com/robots.txt"]
