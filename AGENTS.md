# AGENTS.md

## What this project is

Generates XMLTV guides for **rare Italian TV channels** that publish no EPG feed — regional and
niche broadcasters whose schedule exists only as hand-typed HTML. One `epg.xml` serves all of
them, for Dispatcharr.

Each channel is a module in `sources/`; `build_epg.py` merges them and writes the file.

## Rules

- **Standard library only.** `urllib` + `re` + `xml.sax.saxutils` + `zoneinfo` are enough.
  A dependency needs a reason the stdlib cannot meet.
- **One module per channel, one shared writer.** A source module exposes
  `CHANNEL = {"id", "name", "icon"}` and `collect(today, days) -> [(start, stop, title)]`.
  Only `epg.py` builds XML. Never let a source assemble XML itself.
- **Channel ids match iptv-org** (`Telefriuli.it`, `IuniorTV.it`) so playlists match without
  remapping; icons come from iptv-org's logo list too.
- **Timezones are explicit.** Times are Europe/Rome; XMLTV carries a numeric offset
  (`+0100` / `+0200`). Never emit naive local times.
- **Per-source failure is contained, a total failure is fatal.** `build_epg.py` warns and skips a
  source that raises; if no source produced programmes it exits non-zero. An empty published
  guide is worse than a failed cron job.
- **Fixture-driven tests.** Save the fetched page under `tests/fixtures/` and test the parser
  against it, never against the live site. `python3 -m unittest discover -s tests -t .`
- **Commit every change.** Small, coherent commits. Never commit `tvit/` (separate upstream
  clone) or `__pycache__`. `epg.xml` **is** committed: it is the published guide that Dispatcharr
  reads from the raw URL, and the Action refreshes it daily.

## Layout

```
build_epg.py            # entry point: every source -> one epg.xml
epg.py                  # shared fetch/text/date/XMLTV plumbing
sources/telefriuli.py   # Telefriuli.it
sources/iuniortv.py     # IuniorTV.it
tests/                  # unittest + one HTML fixture per source
.github/workflows/epg.yml  # daily 06:30 UTC build + commit of epg.xml
PLAN.md                 # source analysis and plan
tvit/                   # git-ignored clone of github.com/leicaflorian/tvit (reference / PR work)
```

## Source facts

### Telefriuli (`Telefriuli.it`) — verified 2026-11

- Two sources merged: the weekly page and the live playout log.
- Weekly page: `GET https://www.telefriuli.it/wp-json/wp/v2/pages/494` → `content.rendered`
  (the same markup as `/palinsesto/`, which sits behind a URL-keyed cache that can serve last
  week). Elementor tabs, ids `elementor-tab-content-8271` … `8277` (Mon → Sun), one
  `<p class="MsoNormal">` per row: `06.20` + nbsp padding + title.
- **Heading dates drift by weeks** (e.g. Wed 28/10/26 next to Sat 07/11/26); only the weekday is
  trusted and each day is re-projected onto the coming week.
- Live playout log: `https://www.telefriuli.it/streaming/` → `<h3>Domenica 8 Novembre 2026</h3>`
  + `<ul class="programme-day">` with `.time` / `.title`. Minute-accurate real broadcast names
  (`FOCUS ALLUVIONE FORNI AVOLTRI`), covers today + part of tomorrow, and wins for those days.
  A live day with fewer than 10 rows is ignored.
- The weekly page sometimes lists a row out of order (Thursday `11.15` then `10.45`); rows are
  sorted before durations are computed, or one stray row shifts the day by 24 hours.
- Rows are emitted whole as `<title>`; no `<sub-title>` (Dispatcharr concatenates them without a
  separator and the source wording is kept as published).

### Iunior TV (`IuniorTV.it`) — verified 2026-11

- The blog is **one ever-green post**: `https://iuniortv.blogspot.com/`. No pages, no other posts.
- The guide starts after a line containing `PALINSESTO` and `=`
  (`============= PALINSESTO ============`), then weekday blocks `LUNEDI` … `DOMENICA`
  (unaccented, uppercase), each row `ore 07,00 - TITLE`. **Times use a comma**, not a colon.
- No dates anywhere: each block is projected onto the next occurrence of its weekday.
- A block runs past midnight (`ore 00,00`, `ore 00,30`, `ore 01,00` at the end); those rows are
  the **next calendar day**, so a broadcast day starts at 07,00.
- Counts at last check: 262 rows, 30–43 per day. Fewer than 150 rows means the markup moved.
- Trailing page furniture (`Home page`, cookie script) appears after the guide but never matches
  a row, so it is ignored.
- `www.iuniortv.it` is a meta-refresh to the blog; `www.iuniortv.es` is a bare Clappr player.
  Neither carries a schedule.

## Upstream

`tvit/` (github.com/leicaflorian/tvit) is a Laravel IPTV/EPG app for Italian channels; it does
not cover either channel here. Its scrapers dispatch by `ChannelGroup.scrapper` →
`app/Jobs/Scrappers/<Name>Scrapper.php`. Kept as reference for a possible upstream contribution.
