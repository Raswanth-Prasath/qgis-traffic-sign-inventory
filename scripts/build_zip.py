#!/usr/bin/env python3
"""
Build a publishable zip bundle for plugins.qgis.org.

Produces ./dist/traffic_sign_inventory-<version>.zip from an explicit
allowlist of files. Runs on any platform with a stdlib Python 3.

Usage (from the plugin root):

    python scripts/build_zip.py
    python scripts/build_zip.py --check      # verify, don't write the zip
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "traffic_sign_inventory"

# Files that MUST ship. Missing anything here fails the build.
REQUIRED = [
    "__init__.py",
    "metadata.txt",
    "icon.png",
    "LICENSE",
    "README.md",
    "traffic_sign_inventory.py",
    "traffic_sign_inventory_dialog.py",
    "traffic_sign_inventory_dialog_base.ui",
    "mapillary_client.py",
    "mutcd_mapping.py",
    "settings_dialog.py",
    "tile_math.py",
    "mvt_decoder.py",
    "resources.py",
]

# Files that ship if they exist, silently skipped otherwise.
OPTIONAL = [
    # (no currently optional files, but reserved for future translations etc.)
]


def read_version() -> str:
    meta = (PLUGIN_ROOT / "metadata.txt").read_text(encoding="utf-8")
    match = re.search(r"^version\s*=\s*(\S+)", meta, re.MULTILINE)
    if not match:
        sys.exit("ERROR: could not find 'version=' in metadata.txt")
    return match.group(1)


def ensure_pyqt_resources_up_to_date() -> None:
    """Warn if resources.py looks older than resources.qrc (stale compile)."""
    qrc = PLUGIN_ROOT / "resources.qrc"
    py = PLUGIN_ROOT / "resources.py"
    if qrc.exists() and py.exists() and qrc.stat().st_mtime > py.stat().st_mtime:
        print(
            "WARNING: resources.qrc is newer than resources.py. "
            "Run 'pyrcc5 -o resources.py resources.qrc' before publishing.",
            file=sys.stderr,
        )


def collect_files() -> tuple[list[Path], list[str]]:
    included: list[Path] = []
    missing: list[str] = []

    for rel in REQUIRED:
        path = PLUGIN_ROOT / rel
        if path.exists():
            included.append(path)
        else:
            missing.append(rel)

    for rel in OPTIONAL:
        path = PLUGIN_ROOT / rel
        if path.exists():
            included.append(path)

    return included, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="verify the allowlist against the working tree; do not write the zip",
    )
    args = parser.parse_args()

    version = read_version()
    ensure_pyqt_resources_up_to_date()
    included, missing = collect_files()

    if missing:
        print("Missing required files:", file=sys.stderr)
        for rel in missing:
            print(f"  - {rel}", file=sys.stderr)
        sys.exit(1)

    dist_dir = PLUGIN_ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)
    zip_path = dist_dir / f"{PLUGIN_NAME}-{version}.zip"

    if args.check:
        print(f"Would write: {zip_path}")
        print(f"Files to include: {len(included)}")
        for src in included:
            print(f"  {PLUGIN_NAME}/{src.relative_to(PLUGIN_ROOT).as_posix()}")
        return

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src in included:
            arcname = f"{PLUGIN_NAME}/{src.relative_to(PLUGIN_ROOT).as_posix()}"
            zf.write(src, arcname)

    size = zip_path.stat().st_size
    print(f"Wrote {zip_path} ({size:,} bytes, {len(included)} files)")
    print("\nNext steps:")
    print("  1. Install the zip locally via Plugins > Manage and Install > Install from ZIP")
    print("  2. Run the plugin end-to-end with a real Mapillary token")
    print("  3. Upload at https://plugins.qgis.org/plugins/add/")


if __name__ == "__main__":
    main()
