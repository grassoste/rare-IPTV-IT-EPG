"""Every channel source. Add a module here and its programmes land in epg.xml."""

from . import camera, iuniortv, telefriuli

SOURCES = [telefriuli, iuniortv, camera]
