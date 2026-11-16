"""Make a case folder for the circle (rendered and meshed by the adapter's own functions), without running it.

usage: explore.py FOLDER     then run the container by hand on FOLDER. Exploration only (task 14.4 (c)).
"""

import sys
from pathlib import Path

from wind_tunnel_model.casegen import render_case
from wind_tunnel_model.geometry import outline
from wind_tunnel_model.mesh import GmshMesher
from wind_tunnel_model.settings import Settings

knobs = {"aspect": 1.0, "corner": 1.0, "splitter": 0.0, "angle": 0.0}
settings = Settings.load()
case = Path(sys.argv[1])
case.mkdir(parents=True)
body = outline(settings=settings, **knobs)
render_case(knobs, settings, case)
GmshMesher().build(body, settings, case)
print(sorted(p.name for p in case.iterdir()))
