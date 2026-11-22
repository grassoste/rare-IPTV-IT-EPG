# Rare italian TV EPG — EPG Rari per TV italiana

XMLTV guides for small Italian TV channels that publish **no EPG feed** — regional and niche
broadcasters whose schedule exists only as something hand-typed on a website.

Built for [Dispatcharr](https://github.com/Dispatcharr/Dispatcharr), which reads one XMLTV file:
every channel source contributes programmes to the same `epg.xml`.

## Published guide

Regenerated daily by a GitHub Action (07:30 Rome):

```
https://raw.githubusercontent.com/grassoste/rare-IPTV-IT-EPG/main/epg.xml
```

## Channels

| Channel | `tvg-id` | Source | Coverage |
|---|---|---|---|
| Telefriuli | `Telefriuli.it` | [palinsesto](https://www.telefriuli.it/palinsesto/) + [live playout log](https://www.telefriuli.it/streaming/) | 7 days, today/tomorrow minute-accurate |
| Iunior TV | `IuniorTV.it` | [iuniortv.blogspot.com](https://iuniortv.blogspot.com/) PALINSESTO section | 7 days, weekly template |

Ids follow [iptv-org](https://github.com/iptv-org/database) so a playlist built from it matches
without remapping. Icons come from iptv-org too.

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
tests/                  # unittest + HTML fixtures
PLAN.md                 # source analysis and plan
tvit/                   # git-ignored clone of github.com/leicaflorian/tvit (reference)
```

## Adding a channel

Write `sources/<channel>.py` exposing `CHANNEL = {"id", "name", "icon"}` and
`collect(today, days) -> [(start, stop, title)]`, add it to `SOURCES` in `sources/__init__.py`,
save a fixture, and test the parser offline. Nothing else changes: the XMLTV assembly is shared.
