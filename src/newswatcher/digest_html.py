"""Render a digest of stories as one self-contained HTML page.

The same stories the email/chat digest carries, laid out for a browser: a masthead with
the collect -> dedup -> stories summary, a few headline figures, and the stories as cards
grouped by topic and split into domestic (국내) / overseas (해외) tabs. It is a pure
function of the stories plus a title and a period label -- no I/O, no network, every
figure derived from the input -- so a poll can hand it this run's stories and an archive
query can hand it a week's. The page inlines its own CSS and a little JavaScript for the
tab / topic filtering and the light-dark toggle; it links no external resource, so it
opens the same from a file:// path or behind any host."""

from __future__ import annotations

import html
from urllib.parse import urlsplit

from newswatcher.region import DEFAULT_REGION, REGIONS, region_label
from newswatcher.stories import Story

__all__ = ["render_html"]

_SAFE_HREF_SCHEMES = frozenset({"http", "https", "mailto"})

# A muted categorical palette, assigned to topics in first-appearance order. Kept
# low-saturation so several dots on one page read as a set, not a rainbow, and legible on
# both the light and the dark ground.
_TOPIC_COLORS = (
    "#2f8f94", "#5f7ea0", "#7d6cab", "#b0862f",
    "#4e8c6a", "#b26670", "#3a8fa0", "#8a7f4e",
)
_ALL_TOPICS = "__all__"


def render_html(stories: tuple[Story, ...], *, title: str, period_label: str,
                generated_at: str) -> str:
    """Return the digest of ``stories`` as one HTML document. ``title`` is the masthead
    heading, ``period_label`` names the span it covers (e.g. ``"오늘"`` / ``"지난 7일"``),
    and ``generated_at`` is a display timestamp. Stories are split into 국내 / 해외 tabs
    (국내 shown first) and, within each, grouped by their lead's first topic; every headline
    figure is counted from ``stories``, so an empty digest still renders a valid page."""
    colors = _topic_colors(stories)
    body = "".join((
        _topbar(),
        '<div class="wrap">',
        _masthead(title, period_label, generated_at, stories),
        _stats(stories),
        _render_tabs(stories),
        _render_topic_filter(stories, colors),
        _render_story_feed(stories, colors),
        _footer(period_label),
        "</div>",
    ))
    return (
        "<!doctype html>\n"
        '<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_escape_html(title)}</title>\n<style>{_CSS}</style>\n</head>\n"
        f"<body>\n{body}\n<script>{_SCRIPT}</script>\n</body>\n</html>\n"
    )


def _escape_html(text: str) -> str:
    """HTML-escape ``text`` for both element content and double-quoted attributes."""
    return html.escape(text, quote=True)


def _safe_href(link: str) -> str:
    """An escaped ``href="..."`` for a web-safe scheme, or ``""`` to drop the link. A
    stored article link comes from a third-party feed, and ``html.escape`` neutralizes an
    attribute breakout but NOT the URL scheme -- a ``javascript:`` / ``data:`` link would
    otherwise render as a clickable one-click code-exec. Allowlist http/https/mailto by the
    parsed scheme (which lower-cases it and strips the leading tab/newline tricks a bare
    prefix check would miss); a dropped link renders as an hrefless title, the same as a
    missing link."""
    try:
        scheme = urlsplit(link).scheme.lower()
    except ValueError:
        return ""
    return f' href="{_escape_html(link)}"' if scheme in _SAFE_HREF_SCHEMES else ""


def _topic_colors(stories: tuple[Story, ...]) -> dict[str, str]:
    """Map each topic to a stable color by the order topics first appear across the leads,
    cycling the palette if there are more topics than colors."""
    colors: dict[str, str] = {}
    for story in stories:
        topic = _select_primary_topic(story)
        if topic not in colors:
            colors[topic] = _TOPIC_COLORS[len(colors) % len(_TOPIC_COLORS)]
    return colors


def _select_primary_topic(story: Story) -> str:
    return story.lead.topics[0] if story.lead.topics else "기타"


def _resolve_story_region(story: Story) -> str:
    return story.lead.region if story.lead.region in REGIONS else DEFAULT_REGION


def _format_short_date(published: str) -> str:
    """``MM.DD`` from an ISO-8601 ``YYYY-MM-DD...`` string, or ``""`` when there is no date.
    Deliberately date-only: the stored time is UTC, and a bare month-day avoids showing a
    reader a timezone-shifted clock."""
    return f"{published[5:7]}.{published[8:10]}" if len(published) >= 10 else ""


def _counts(stories: tuple[Story, ...]) -> dict[str, int]:
    kr = sum(1 for s in stories if _resolve_story_region(s) == "kr")
    article_count = sum(1 + len(s.duplicates) for s in stories)
    return {"stories": len(stories), "articles": article_count,
            "merged": article_count - len(stories), "kr": kr, "intl": len(stories) - kr}


def _outlets(stories: tuple[Story, ...]) -> tuple[int, int, int]:
    """(distinct outlets overall, distinct domestic outlets, distinct overseas outlets)."""
    total: set[str] = set()
    by_region: dict[str, set[str]] = {"kr": set(), "intl": set()}
    for story in stories:
        region = _resolve_story_region(story)
        for article in (story.lead, *story.duplicates):
            total.add(article.source_name)
            by_region[region].add(article.source_name)
    return len(total), len(by_region["kr"]), len(by_region["intl"])


def _topbar() -> str:
    return (
        '<header class="topbar">'
        '<div class="brand"><span class="brand__mark">newswatcher</span>'
        '<span class="brand__sub">digest</span></div>'
        '<button class="theme-btn" id="themeBtn" type="button" '
        'aria-label="라이트/다크 전환">◑ 테마</button>'
        "</header>"
    )


def _masthead(title: str, period_label: str, generated_at: str,
              stories: tuple[Story, ...]) -> str:
    c = _counts(stories)
    n_outlets = _outlets(stories)[0]
    return (
        '<section class="masthead">'
        f'<p class="eyebrow">{_escape_html(period_label)}의 브리핑</p>'
        f"<h1>{_escape_html(title)}</h1>"
        '<p class="masthead__meta">'
        f"{_escape_html(generated_at)} 집계 · <b>{n_outlets}</b>개 매체에서 <b>{c['articles']}</b>건을 "
        f"수집해, 같은 사건을 다룬 기사를 묶어 <b>{c['stories']}</b>개 스토리로 정리했습니다."
        "</p></section>"
    )


def _stats(stories: tuple[Story, ...]) -> str:
    c = _counts(stories)
    total_outlets, kr_outlets, intl_outlets = _outlets(stories)
    top_topic, topic_bar = _topic_summary(stories)
    region_bar = _render_bar([(c["kr"], "var(--dot-kr)"), (c["intl"], "var(--dot-intl)")])
    return (
        '<section class="stats" aria-label="요약 지표">'
        + _render_stat("스토리", str(c["stories"]), f"원문 {c['articles']}건 · 중복 {c['merged']}건 병합")
        + _render_stat("출처 매체", f"{total_outlets}<small> 곳</small>",
                f"국내 {kr_outlets} · 해외 {intl_outlets}")
        + _render_stat("국내 / 해외", f"{c['kr']} / {c['intl']}", "", extra=region_bar)
        + _render_stat("상위 테마", _escape_html(top_topic) or "—", "", extra=topic_bar, small_value=True)
        + "</section>"
    )


def _render_stat(label: str, value: str, note: str, *, extra: str = "", small_value: bool = False) -> str:
    value_class = "stat__value stat__value--sm" if small_value else "stat__value"
    note_html = f'<span class="stat__note">{_escape_html(note)}</span>' if note else ""
    return (f'<div class="stat"><span class="stat__label">{_escape_html(label)}</span>'
            f'<span class="{value_class}">{value}</span>{note_html}{extra}</div>')


def _topic_summary(stories: tuple[Story, ...]) -> tuple[str, str]:
    counts: dict[str, int] = {}
    for story in stories:
        counts[_select_primary_topic(story)] = counts.get(_select_primary_topic(story), 0) + 1
    if not counts:
        return "", ""
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    colors = _topic_colors(stories)
    bar = _render_bar([(n, colors[topic]) for topic, n in ordered])
    return ordered[0][0], bar


def _render_bar(segments: list[tuple[int, str]]) -> str:
    parts = "".join(f'<span style="flex:{max(n, 0)};background:{color}"></span>'
                    for n, color in segments if n > 0)
    return f'<div class="distro" aria-hidden="true">{parts}</div>' if parts else ""


def _render_tabs(stories: tuple[Story, ...]) -> str:
    c = _counts(stories)
    buttons = []
    for index, region in enumerate(REGIONS):   # kr first, then intl
        active = "true" if index == 0 else "false"
        buttons.append(
            f'<button class="tab" data-region="{region}" role="tab" '
            f'aria-selected="{active}" type="button">{_escape_html(region_label(region))}'
            f'<span class="tab__count">{c[region]}</span></button>')
    return f'<div class="tabs" id="tabs" role="tablist">{"".join(buttons)}</div>'


def _render_topic_filter(stories: tuple[Story, ...], colors: dict[str, str]) -> str:
    seen: list[str] = []
    for story in stories:
        if _select_primary_topic(story) not in seen:
            seen.append(_select_primary_topic(story))
    chips = [f'<button class="chip" data-topic="{_ALL_TOPICS}" aria-pressed="true" type="button">'
             f'전체 <span class="chip__count">{len(stories)}</span></button>']
    for topic in seen:
        n = sum(1 for s in stories if _select_primary_topic(s) == topic)
        chips.append(
            f'<button class="chip" data-topic="{_escape_html(topic)}" aria-pressed="false" type="button">'
            f'<span class="dot" style="--c:{colors[topic]}"></span>{_escape_html(topic)} '
            f'<span class="chip__count">{n}</span></button>')
    return f'<nav class="filter" id="filter" aria-label="토픽 필터">{"".join(chips)}</nav>'


def _render_story_feed(stories: tuple[Story, ...], colors: dict[str, str]) -> str:
    if not stories:
        return '<main class="feed"><p class="empty" style="display:block">이 기간에 수집된 스토리가 없습니다.</p></main>'
    cards = "".join(_render_story_card(story, colors, index) for index, story in enumerate(stories))
    return (f'<main class="feed" id="feed">{cards}'
            '<p class="empty" id="empty">이 조건에 해당하는 스토리가 없습니다.</p></main>')


def _render_story_card(story: Story, colors: dict[str, str], index: int) -> str:
    lead = story.lead
    topic = _select_primary_topic(story)
    color = colors[topic]
    date = _format_short_date(lead.published)
    date_html = f"<time>{_escape_html(date)}</time>" if date else ""
    also = story.also_reported_by
    if also:
        chips = "".join(f'<span class="outlet-chip">{_escape_html(name)}</span>' for name in also)
        also_html = (f'<span class="also">외 {len(also)}개 매체</span>{chips}')
    else:
        also_html = ""
    link = _safe_href(lead.link)
    return (
        f'<article class="story" data-region="{_resolve_story_region(story)}" data-topic="{_escape_html(topic)}" '
        f'style="--c:{color};--i:{index}">'
        '<div class="story__rail"></div><div class="story__body">'
        f'<div class="story__eyebrow"><span class="tag"><span class="dot"></span>'
        f"{_escape_html(topic)}</span>{date_html}</div>"
        f'<h3 class="story__head"><a class="story__link"{link} target="_blank" '
        f'rel="noopener">{_escape_html(lead.title)}</a></h3>'
        f'<p class="story__sum">{_escape_html(lead.summary)}</p>'
        f'<div class="story__foot"><span class="outlet">{_escape_html(lead.source_name)}</span>'
        f"{also_html}</div>"
        "</div></article>"
    )


def _footer(period_label: str) -> str:
    return (
        "<footer>"
        f"{_escape_html(period_label)} 동안 수집·중복 병합·요약한 스토리입니다. 대표 기사 한 건에 "
        '"외 N개 매체"로 교차 출처를 묶어 보여주며, 요약은 newswatcher가 쓴 원문이 아닌 '
        "자체 요약입니다."
        "</footer>"
    )


_CSS = """
  :root {
    --ground:#eef1f4; --surface:#fff; --surface-2:#f6f8fa; --ink:#171b22; --muted:#5a6472;
    --faint:#8a93a1; --line:#e1e5ea; --line-strong:#cfd5dd; --accent:#0e7a82;
    --accent-ink:#0b5f66; --pos:#1f7a4d; --warn:#a9741a;
    --dot-kr:#0e7a82; --dot-intl:#7d6cab;
    --shadow:0 1px 2px rgba(23,27,34,.04),0 8px 24px -16px rgba(23,27,34,.22);
    --font-sans:system-ui,-apple-system,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR","Segoe UI",Roboto,sans-serif;
    --font-serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  }
  @media (prefers-color-scheme:dark){:root{
    --ground:#0e1116; --surface:#161b22; --surface-2:#1b212a; --ink:#e6e9ed; --muted:#9aa4b2;
    --faint:#6f7a89; --line:#262d38; --line-strong:#333c49; --accent:#2aa7b0;
    --accent-ink:#4fc2ca; --pos:#52b083; --warn:#d0a24e; --dot-kr:#2aa7b0; --dot-intl:#9b8bd0;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px -18px rgba(0,0,0,.7);
  }}
  :root[data-theme="light"]{--ground:#eef1f4;--surface:#fff;--surface-2:#f6f8fa;--ink:#171b22;--muted:#5a6472;--faint:#8a93a1;--line:#e1e5ea;--line-strong:#cfd5dd;--accent:#0e7a82;--accent-ink:#0b5f66;--pos:#1f7a4d;--warn:#a9741a;--dot-kr:#0e7a82;--dot-intl:#7d6cab;--shadow:0 1px 2px rgba(23,27,34,.04),0 8px 24px -16px rgba(23,27,34,.22);}
  :root[data-theme="dark"]{--ground:#0e1116;--surface:#161b22;--surface-2:#1b212a;--ink:#e6e9ed;--muted:#9aa4b2;--faint:#6f7a89;--line:#262d38;--line-strong:#333c49;--accent:#2aa7b0;--accent-ink:#4fc2ca;--pos:#52b083;--warn:#d0a24e;--dot-kr:#2aa7b0;--dot-intl:#9b8bd0;--shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px -18px rgba(0,0,0,.7);}
  *{box-sizing:border-box;}
  body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--font-sans);line-height:1.6;-webkit-font-smoothing:antialiased;}
  .wrap{max-width:1040px;margin:0 auto;padding:0 24px 80px;}
  .topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px 24px;background:color-mix(in srgb,var(--ground) 86%,transparent);backdrop-filter:saturate(1.4) blur(10px);border-bottom:1px solid var(--line);}
  .brand{display:flex;align-items:baseline;gap:9px;}
  .brand__mark{font-family:var(--font-serif);font-weight:600;font-style:italic;font-size:1.12rem;color:var(--accent-ink);}
  .brand__sub{font-size:.72rem;text-transform:uppercase;letter-spacing:.14em;color:var(--faint);}
  .theme-btn{appearance:none;cursor:pointer;font:inherit;font-size:.8rem;color:var(--muted);background:var(--surface);border:1px solid var(--line-strong);border-radius:8px;padding:5px 11px;line-height:1;}
  .theme-btn:hover{color:var(--ink);border-color:var(--accent);}
  .theme-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
  .masthead{padding:42px 0 26px;border-bottom:1px solid var(--line);}
  .eyebrow{font-size:.76rem;text-transform:uppercase;letter-spacing:.16em;color:var(--accent-ink);margin:0 0 13px;font-weight:600;}
  .masthead h1{font-size:clamp(1.8rem,4vw,2.8rem);line-height:1.1;margin:0;letter-spacing:-.02em;font-weight:800;text-wrap:balance;}
  .masthead__meta{margin:16px 0 0;color:var(--muted);font-size:.96rem;max-width:64ch;text-wrap:pretty;}
  .masthead__meta b{color:var(--ink);font-weight:700;font-variant-numeric:tabular-nums;}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0 6px;}
  .stat{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:15px 16px 14px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:4px;min-width:0;}
  .stat__label{font-size:.72rem;text-transform:uppercase;letter-spacing:.09em;color:var(--faint);}
  .stat__value{font-size:1.7rem;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.1;}
  .stat__value--sm{font-size:1.15rem;line-height:1.3;}
  .stat__value small{font-size:.9rem;font-weight:700;color:var(--muted);}
  .stat__note{font-size:.8rem;color:var(--muted);font-variant-numeric:tabular-nums;}
  .distro{display:flex;height:7px;border-radius:999px;overflow:hidden;margin-top:8px;gap:2px;}
  .distro span{display:block;height:100%;border-radius:2px;min-width:3px;}
  .tabs{display:flex;gap:6px;margin:26px 0 0;border-bottom:1px solid var(--line);}
  .tab{appearance:none;cursor:pointer;font:inherit;font-size:.95rem;font-weight:700;color:var(--muted);background:none;border:0;border-bottom:2px solid transparent;padding:10px 4px 12px;margin-bottom:-1px;display:inline-flex;align-items:center;gap:8px;}
  .tab:hover{color:var(--ink);}
  .tab:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
  .tab[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent);}
  .tab__count{font-size:.78rem;font-weight:700;color:var(--faint);background:var(--surface-2);border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-variant-numeric:tabular-nums;}
  .tab[aria-selected="true"] .tab__count{color:var(--accent-ink);}
  .filter{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:16px 0 4px;}
  .chip{appearance:none;cursor:pointer;font:inherit;font-size:.82rem;display:inline-flex;align-items:center;gap:7px;color:var(--muted);background:var(--surface);border:1px solid var(--line-strong);border-radius:999px;padding:6px 13px;line-height:1;transition:color .15s,border-color .15s,background .15s;}
  .chip:hover{color:var(--ink);border-color:var(--accent);}
  .chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
  .chip[aria-pressed="true"]{color:#fff;background:var(--accent);border-color:var(--accent);}
  .chip .dot{width:8px;height:8px;border-radius:50%;background:var(--c,var(--faint));flex:none;}
  .chip[aria-pressed="true"] .dot{background:#fff;}
  .chip__count{color:var(--faint);font-variant-numeric:tabular-nums;font-size:.78rem;}
  .chip[aria-pressed="true"] .chip__count{color:rgba(255,255,255,.82);}
  .feed{display:flex;flex-direction:column;gap:13px;margin-top:18px;}
  .story{display:grid;grid-template-columns:auto 1fr;gap:16px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:19px 22px;box-shadow:var(--shadow);transition:border-color .18s,transform .18s;}
  .story:hover{border-color:var(--line-strong);transform:translateY(-2px);}
  .story__rail{width:3px;border-radius:3px;background:var(--c,var(--accent));align-self:stretch;}
  .story__eyebrow{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px;}
  .tag{display:inline-flex;align-items:center;gap:7px;font-size:.74rem;font-weight:700;color:var(--ink);}
  .tag .dot{width:8px;height:8px;border-radius:50%;background:var(--c,var(--faint));}
  .story time{font-size:.78rem;color:var(--faint);font-variant-numeric:tabular-nums;}
  .story__head{margin:0 0 8px;font-size:1.2rem;line-height:1.32;font-weight:800;letter-spacing:-.015em;text-wrap:balance;}
  .story__link{color:inherit;text-decoration:none;}
  .story__link:hover{color:var(--accent-ink);text-decoration:underline;text-underline-offset:3px;}
  .story__sum{margin:0;color:var(--muted);font-size:.95rem;max-width:66ch;text-wrap:pretty;}
  .story__foot{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-top:13px;padding-top:12px;border-top:1px dashed var(--line);}
  .outlet{font-size:.8rem;font-weight:700;color:var(--accent-ink);}
  .also{font-size:.8rem;color:var(--faint);}
  .outlet-chip{font-size:.74rem;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:2px 8px;background:var(--surface-2);}
  .empty{display:none;text-align:center;color:var(--faint);padding:44px 0;font-size:.95rem;}
  footer{margin-top:38px;padding-top:20px;border-top:1px solid var(--line);color:var(--faint);font-size:.82rem;line-height:1.7;}
  @media (prefers-reduced-motion:no-preference){.story,.stat{animation:rise .5s cubic-bezier(.2,.7,.2,1) both;animation-delay:calc(var(--i,0)*35ms);}@keyframes rise{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:none;}}}
  @media (max-width:720px){.stats{grid-template-columns:1fr 1fr;}.wrap{padding:0 16px 60px;}.topbar{padding:12px 16px;}}
  @media (max-width:440px){.stats{grid-template-columns:1fr;}.story{padding:16px;gap:12px;}}
"""

_SCRIPT = """
(function(){
  var region='kr', topic='__all__';
  var tabs=document.getElementById('tabs');
  var filter=document.getElementById('filter');
  var empty=document.getElementById('empty');
  var stories=Array.prototype.slice.call(document.querySelectorAll('.story'));
  function apply(){
    var shown=0;
    stories.forEach(function(s){
      var on=s.getAttribute('data-region')===region &&
             (topic==='__all__'||s.getAttribute('data-topic')===topic);
      s.style.display=on?'':'none';
      if(on)shown++;
    });
    if(empty)empty.style.display=shown?'none':'block';
  }
  if(tabs)tabs.addEventListener('click',function(e){
    var b=e.target.closest('.tab');if(!b)return;
    region=b.getAttribute('data-region');
    tabs.querySelectorAll('.tab').forEach(function(t){t.setAttribute('aria-selected',String(t===b));});
    apply();
  });
  if(filter)filter.addEventListener('click',function(e){
    var b=e.target.closest('.chip');if(!b)return;
    topic=b.getAttribute('data-topic');
    filter.querySelectorAll('.chip').forEach(function(c){c.setAttribute('aria-pressed',String(c===b));});
    apply();
  });
  apply();
  var btn=document.getElementById('themeBtn');
  if(btn)btn.addEventListener('click',function(){
    var root=document.documentElement,cur=root.getAttribute('data-theme');
    if(!cur)cur=window.matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';
    root.setAttribute('data-theme',cur==='dark'?'light':'dark');
  });
})();
"""
