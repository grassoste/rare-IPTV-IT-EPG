"""Every channel source. Add a module here and its programmes land in epg.xml."""

from . import camera, iuniortv, raiitalia, senato, telefriuli, tv12

SOURCES = [telefriuli, iuniortv, camera, senato, raiitalia, tv12]
