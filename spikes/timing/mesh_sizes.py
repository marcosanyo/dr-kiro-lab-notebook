"""Smallest cell edge of the mesh against the shortest piece of the outline (task 14.4 stage 2, measure only).
The mesh is made by the model's own GmshMesher with the settings unchanged, in a temporary folder.
usage: uv run --project wind-tunnel/adapter python spikes/timing/mesh_sizes.py
"""

import math
import tempfile
from pathlib import Path

import gmsh
import numpy as np
from wind_tunnel_model.geometry import Arc, outline
from wind_tunnel_model.mesh import GmshMesher
from wind_tunnel_model.settings import Settings

CASES = [
    (1.75, k)
    for k in (
        0.001,
        0.005,
        0.01,
        0.02,
        0.03,
        0.05,
        0.5,
        0.95,
        0.98,
        0.99,
        0.995,
        0.998,
        0.999,
    )
]
CASES += [(0.5, 0.02), (3.0, 0.02), (0.5, 0.98), (3.0, 0.98)]


def main() -> None:
    settings = Settings.load()
    print("aspect corner shortest_piece cells min_edge_of_cells")
    for aspect, corner in CASES:
        body = outline(aspect, corner, 1.5, 15.0, settings)
        pieces = [math.dist(p.p, p.q) if not isinstance(p, Arc) else None for p in body]
        shortest = min(x if x is not None else math.inf for x in pieces)
        for p in body:
            if isinstance(p, Arc):
                r = math.dist(p.p, p.centre)
                a0 = math.atan2(p.p[1] - p.centre[1], p.p[0] - p.centre[0])
                a1 = math.atan2(p.q[1] - p.centre[1], p.q[0] - p.centre[0])
                shortest = min(shortest, r * ((a1 - a0) % (2 * math.pi)))
        with tempfile.TemporaryDirectory() as tmp:
            mesher = GmshMesher()
            mesher.build(body, settings, Path(tmp))
            gmsh.initialize()
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.open(str(Path(tmp) / "case.msh"))
            tags, coords, _ = gmsh.model.mesh.getNodes()
            xyz = dict(
                zip(tags.tolist(), np.asarray(coords).reshape(-1, 3), strict=True)
            )
            smallest = math.inf
            for etype, _etags, nodes in zip(
                *gmsh.model.mesh.getElements(2), strict=True
            ):
                if etype != 2:
                    continue
                tri = np.asarray(nodes).reshape(-1, 3)
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    d = np.array(
                        [
                            np.linalg.norm(xyz[i][:2] - xyz[j][:2])
                            for i, j in zip(tri[:, a], tri[:, b], strict=True)
                        ]
                    )
                    smallest = min(smallest, float(d.min()))
            gmsh.finalize()
        print(
            f"{aspect:g} {corner:g} {shortest:.5f} {mesher.cells} {smallest:.5f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
