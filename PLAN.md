# Analysis & Plan — Rare italian TV EPG

## 1. Scope

One XMLTV file for Italian channels that publish **no EPG feed**, for Dispatcharr. Every channel
is a source module; `build_epg.py` merges them into a single `epg.xml`.

Shipped: **Telefriuli** (`Telefriuli.it`), **Iunior TV** (`IuniorTV.it`).
Adding a channel = one module in `sources/` + fixture + tests; the XMLTV writer never changes.

## 2. Why these channels have no EPG

Checked 2026-11: `iptv-org/epg` covers only `superguidatv.it`, `guidatv.sky.it`, `tivu.tv`,
`tv.blue.ch`, none of which lists either channel. `leicaflorian/tvit` covers Italian national
channels plus a single regional (Tele Norba). Dispatcharr/Threadfin ship no catalog entry.
Both channels exist in iptv-org's channel database, so ids and logos are reused from there.

## 3. Telefriuli

Two sources, merged.

| Fact | Detail |
|---|---|
| Weekly page | `GET /wp-json/wp/v2/pages/494` → `content.rendered`; 7 Elementor tabs (`elementor-tab-content-8271`…`8277`), one `<p class="MsoNormal">` per row, `06.20` + nbsp + title |
| Page cache | `/palinsesto/` is behind a URL-keyed cache that can serve **last week**; the REST endpoint does not |
| Dates | headings drift by weeks (Wed 28/10/26 next to Sat 07/11/26) → only the weekday is trusted, days are re-projected onto the coming week |
| Live log | `/streaming/` → `<h3>Domenica 8 Novembre 2026</h3>` + `programme-day` list, minute-accurate, real broadcast names, today + part of tomorrow; **wins** for the days it covers |
| Rows | 190/week, all match `^(\d{1,2})[.:](\d{2})\s+(.+)$`; one row is listed out of order (Thu `11.15` before `10.45`) → rows are sorted, never shifted by a day |
| Durations | derived from the next start; last of the day = 60 min |

## 4. Iunior TV

| Fact | Detail |
|---|---|
| Source | `https://iuniortv.blogspot.com/` — one ever-green post, no pages, no other posts |
| Guide | after `============= PALINSESTO ============`, weekday blocks `LUNEDI`…`DOMENICA`, rows `ore 07,00 - TITLE` (**comma** times) |
| Dates | none in the source → each block lands on the next occurrence of its weekday |
| Midnight | each block ends `00,00`, `00,30`, `01,00` → those rows belong to the **next calendar day** (broadcast day starts 07,00) |
| Volume | 262 rows, 30–43 per day; under 150 means the markup moved |
| Ignored | `www.iuniortv.it` (meta-refresh to the blog) and `www.iuniortv.es` (bare Clappr player) carry no schedule |

## 5. Architecture

```
build_epg.py            # CLI: runs every source, writes one epg.xml
epg.py                  # fetch, text extraction, weekday projection, XMLTV assembly
sources/<channel>.py    # CHANNEL = {id, name, icon}; collect(today, days) -> [(start, stop, title)]
sources/__init__.py     # SOURCES list
tests/                  # unittest per parser, one HTML fixture per source
```

- A source that raises is a warning; if every source fails the build exits non-zero.
- Times are Europe/Rome and always carry `+0100`/`+0200` in the output.
- One `<tv>` document: all `<channel>` elements, then all `<programme>` sorted by start.

## 6. Delivery

- GitHub Action daily at **06:30 UTC** (07:30 Rome in CET, 08:30 in CEST — GitHub cron is UTC
  only), which runs the tests, rebuilds `epg.xml` and commits it if it changed.
- Dispatcharr reads
  `https://raw.githubusercontent.com/grassoste/rare-IPTV-IT-EPG/main/epg.xml`.

## 7. Phases

| # | Step | State |
|---|---|---|
| 1 | Telefriuli weekly page + live log, single script | done |
| 2 | Publish `epg.xml` on GitHub, daily refresh | done |
| 3 | Multi-source architecture (`sources/`, `epg.py`, `build_epg.py`) | done |
| 4 | Iunior TV source + tests | done |
| 5 | Repo rename to `rare-IPTV-IT-EPG`, daily build at 07:30 Rome | done |
| 6 | Next channel: add a module, fixture, tests | pending |

## 8. Risks

- **Hand-typed sources.** Both are maintained by humans and lag behind reality; the guide shows
  the last published schedule. Telefriuli's live log mitigates this for today/tomorrow.
- **Markup is the contract.** Each parser keys on a specific shape (`PALINSESTO` line, Elementor
  tab ids) and fails loudly instead of publishing an empty guide.
- **No descriptions or genres** for either channel: the sources carry titles only.
- **Timezone drift in CI.** The workflow is UTC; during CEST the build runs at 08:30 local.
