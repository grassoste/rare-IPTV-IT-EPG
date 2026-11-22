"""Every channel source. Add a module here and its programmes land in epg.xml."""

from . import camera, iuniortv, raiitalia, senato, telefriuli

SOURCES = [telefriuli, iuniortv, camera, senato, raiitalia]
