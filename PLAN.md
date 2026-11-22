# Analysis & Plan — Rare italian TV EPG

## 1. Scope

One XMLTV file for Italian channels that publish **no usable EPG feed**, for Dispatcharr. Every
channel is a source module; `build_epg.py` merges them into a single `epg.xml`.

| Channel | `tvg-id` | Type |
|---|---|---|
| Telefriuli | `Telefriuli.it` | 7-day grid + live playout log |
| Iunior TV | `Iuniortv.it` | 7-day weekly template |
| Camera dei Deputati | `CameradeiDeputati.it` | event list |
| Senato TV | `SenatoTV.it` | event list |
| Rai Italia | `RaiItalia.it` | full-day grid, exact durations |

Two of them are event channels: they air sittings, press conferences and events, never a 24/7
grid. Gaps are the truth.

## 2. Why these channels have no EPG

`iptv-org/epg` covers only `superguidatv.it`, `guidatv.sky.it`, `tivu.tv`, `tv.blue.ch`, none of
which lists any of these channels. `leicaflorian/tvit` covers national channels plus Tele Norba.
Dispatcharr/Threadfin ship no catalog entry. All five exist in iptv-org's channel database, so
ids and logos are reused from there.

## 3. Telefriuli

| Fact | Detail |
|---|---|
| Weekly page | `GET /wp-json/wp/v2/pages/494` → `content.rendered`; 7 Elementor tabs, `06.20` + title |
| Page cache | `/palinsesto/` is behind a URL-keyed cache that can serve last week |
| Dates | headings drift by weeks; only the weekday is trusted, days are re-projected |
| Live log | `/streaming/` — dated, minute-accurate, real broadcast names, today + part of tomorrow; wins for its days |
| Rows | 190/week; one row listed out of order → rows are sorted, never shifted by a day |

## 4. Iunior TV

One ever-green Blogger post; guide after `============= PALINSESTO ============`, weekday blocks
`LUNEDI`…`DOMENICA`, rows `ore 07,00 - TITLE` (comma times). No dates: each block lands on the
next occurrence of its weekday. Blocks end at `01,00` of the following calendar day (broadcast
day starts 07,00). 262 rows.

## 5. Camera dei Deputati

`/palinsesto-webtv?data=YYYY-MM-DD`, server-rendered, ISO date only, range today+90 days. One
`.caption` per event (`.ora` + `.titolo`). Empty days say "Nessun evento in questa data". No end
times → next event, last of the day 60 min. The satellite PDF is a different schedule and is not
used.

## 6. Senato TV

`/api/palimpsest` JSON with an explicit one-day window plus a cache-buster. Each `nid` appears
twice → dedupe. `field_date` is `HH:MM`; the date comes from `field_vevent_id`. No end times.

## 7. Rai Italia

`raiplay.it/palinsesto/raiitalia/<feed>/<dd-mm-yyyy>.json`, exact UTC starts and durations.
Feeds published: Africa, America, Asia, Australia — **no Europa** (302), so the Africa feed is
used. Window ≈ D-24…D+7 then HTTP 559. A day file holds two near-duplicate grids (≈49 h in 24 h),
so overlaps are dropped to keep the day linear.

## 8. Architecture

```
build_epg.py            # CLI: runs every source, writes one epg.xml
epg.py                  # fetch (retry on 429/5xx), text, weekday projection, XMLTV assembly
sources/<channel>.py    # CHANNEL = {id, name, icon}; collect(today, days) -> [(start, stop, title)]
sources/__init__.py     # SOURCES list
tests/                  # unittest per parser, one fixture per source
```

- A source that raises is a warning and **carries over its programmes from the published file**
  instead of vanishing; if nothing at all is produced, the build exits non-zero.
- All times are Europe/Rome with an explicit `+0100`/`+0200` offset.
- One `<tv>` document: all `<channel>` elements, then all programmes sorted by start.
- Minimum programme length is 5 minutes, since some sources list two events at the same minute.

## 9. Delivery

GitHub Action every 6 hours (`30 */6 * * *` = 07:30/13:30/19:30/01:30 Rome in CET; 08:30-based
during CEST, as GitHub cron is UTC only). It runs the tests, rebuilds `epg.xml` and commits it
when it changed. Dispatcharr reads
`https://raw.githubusercontent.com/grassoste/rare-IPTV-IT-EPG/main/epg.xml`.

## 10. Phases

| # | Step | State |
|---|---|---|
| 1 | Telefriuli weekly page + live log | done |
| 2 | Publish `epg.xml`, daily refresh | done |
| 3 | Multi-source architecture | done |
| 4 | Iunior TV | done |
| 5 | Repo rename, 6-hourly build | done |
| 6 | Camera dei Deputati | done |
| 7 | Senato TV | done |
| 8 | Rai Italia (Africa feed) | done |
| 9 | Next channel | pending |

## 11. Risks

- **Hand-typed or event-only sources.** The guide is only as complete as the broadcaster's own
  publication; Camera and Senato are empty on non-sitting days, by design.
- **Markup/API is the contract.** Each parser keys on a specific shape and fails loudly rather
  than publishing an empty guide.
- **Rai Italia feed mismatch.** If the Europe/Africa satellite leg does not follow the Africa
  feed, `FEED` in `sources/raiitalia.py` is the one line to change.
- **CEST drift.** During summer the 6-hourly runs sit one hour later in Rome.
