"""The child process of ``GmshMesher`` (Decision 43): reads one request on stdin, builds the mesh in the main
thread of this fresh interpreter, writes the cell count as JSON on stdout. A failure is a message on stderr
and a non-zero exit status; the parent turns it into a ``MeshError``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from wind_tunnel_model.mesh import MeshError, build_in_this_process, outline_from_data
from wind_tunnel_model.settings import _build as settings_from_data


def main() -> int:
    request = json.loads(sys.stdin.read())
    outline = outline_from_data(request["outline"])
    settings = settings_from_data(request["settings"])
    try:
        cells = build_in_this_process(outline, settings, Path(request["target"]))
    except MeshError as error:
        print(f"mesh error: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"cells": cells}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
