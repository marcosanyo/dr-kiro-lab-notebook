"""Export of the told set (wind-tunnel Requirement 2, design 1).

`wind-tunnel-told-set --out PATH` writes the text that the bench front end puts into the tool descriptions,
built from the adapter's declaration, with a final newline and nothing else.
"""

import argparse
from pathlib import Path

from bench.frontend.describe import declaration_text

from wind_tunnel.declaration import scan_adapter


def told_set_text() -> str:
    return declaration_text(scan_adapter().declaration()) + "\n"


def write_told_set(path: Path) -> None:
    path.write_bytes(told_set_text().encode("utf-8"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="wind-tunnel-told-set", description="Write the told set of the wind tunnel to a file."
    )
    parser.add_argument("--out", required=True, type=Path, help="the file to write")
    args = parser.parse_args(argv)
    write_told_set(args.out)


if __name__ == "__main__":
    main()
