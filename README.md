# Rare italian TV EPG — EPG Rari per TV italiana

XMLTV guides for small Italian TV channels that publish **no EPG feed** — regional and niche
broadcasters whose schedule exists only as something hand-typed on a website.

Built for [Dispatcharr](https://github.com/Dispatcharr/Dispatcharr), which reads one XMLTV file:
every channel source contributes programmes to the same `epg.xml`.

## Published guide

Rebuilt every 6 hours by a GitHub Action (`30 */6 * * *`, so 07:30/13:30/19:30/01:30 Rome in
CET) and committed only when it changed:

```
https://raw.githubusercontent.com/grassoste/rare-IPTV-IT-EPG/main/epg.xml
```

## Channels

| Channel | `tvg-id` | Source | Shape |
|---|---|---|---|
| Telefriuli | `Telefriuli.it` | [palinsesto](https://www.telefriuli.it/palinsesto/) + [live playout log](https://www.telefriuli.it/streaming/) | 7-day grid, today/tomorrow minute-accurate |
| Iunior TV | `IuniorTV.it` | [iuniortv.blogspot.com](https://iuniortv.blogspot.com/) PALINSESTO section | 7-day weekly grid |
| Camera dei Deputati | `CameradeiDeputati.it` | [palinsesto-webtv?data=…](https://comunicazione.camera.it/palinsesto-webtv) | event list, gaps when not sitting |
| Senato TV | `SenatoTV.it` | [palimpsest JSON](https://webtv.senato.it/api/palimpsest) | event list, gaps when not sitting |
| Rai Italia | `RaiItalia.it` | [raiplay palinsesto JSON](https://www.raiplay.it/palinsesto/raiitalia/Rai-Italia-Africa/) | full-day grid, exact durations |
| TV12 Medianordest | `TV12.it` | [programmazione](https://tv12.medianordest.it/programmazione/) | today's table (05:00 → 04:00), with descriptions |

Ids follow [iptv-org](https://github.com/iptv-org/database) so a playlist built from it matches
without remapping. Icons come from iptv-org too.

Two of these are event channels: Camera and Senato publish only the sittings, press conferences
and events they air, never a 24/7 grid. Gaps in the guide are the truth, not a bug.

Rai Italia publishes guides per feed (Africa, America, Asia, Australia). There is **no Europa
file** — `Rai-Italia-Europa*.json` answers 302 — so the Africa feed is used, with `FEED` in
`sources/raiitalia.py` as the single place to change it.

## Usage

```bash
python3 build_epg.py -o epg.xml              # every source, 7 days
python3 build_epg.py --days 3                # shorter window
python3 build_epg.py --only IuniorTV.it      # one channel, for debugging
```

Then point Dispatcharr at the file (or at a static HTTP URL serving it).

A source that fails is a warning: the other channels still produce a guide. If **no** source
produces anything, the build exits non-zero so a cron job fails loudly instead of publishing
an empty guide.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

Every parser is tested against a saved fixture in `tests/fixtures/`, never against the live site.

## Layout

```
build_epg.py            # entry point: run every source, write one epg.xml
epg.py                  # shared: fetch, text, date projection, XMLTV assembly
sources/telefriuli.py   # Telefriuli
sources/iuniortv.py     # Iunior TV
sources/camera.py       # Camera dei Deputati
sources/senato.py       # Senato TV
sources/raiitalia.py    # Rai Italia
sources/tv12.py         # TV12 Medianordest
tests/                  # unittest + HTML/JSON fixtures
PLAN.md                 # source analysis and plan
tvit/                   # git-ignored clone of github.com/leicaflorian/tvit (reference)
```

## Adding a channel

Write `sources/<channel>.py` exposing `CHANNEL = {"id", "name", "icon"}` and
`collect(today, days) -> [(start, stop, title[, description])]`, add it to `SOURCES` in `sources/__init__.py`,
save a fixture, and test the parser offline. Nothing else changes: the XMLTV assembly is shared.
