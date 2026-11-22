"""Every channel source. Add a module here and its programmes land in epg.xml."""

from . import iuniortv, telefriuli

SOURCES = [telefriuli, iuniortv]
