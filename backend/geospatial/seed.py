"""Restore the small, reviewed demo layers needed by the public Geoportal.

Render's free filesystem is ephemeral.  The five Ecuador IGBP layers are kept
in the repository as deployment seed data and copied to the private runtime
store when it is empty.  User uploads and unseeded original rasters are never
overwritten or published by this helper.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from backend.geospatial.settings import GeoportalSettings, PROJECT_ROOT


def restore_seed_assets(settings: GeoportalSettings) -> int:
    """Copy absent seed files into the private runtime directory.

    Returns the number of restored files.  No work is performed in a local
    installation that does not include deployment seed data.
    """
    source_root = PROJECT_ROOT / 'data' / 'seed' / 'geoportal'
    if not source_root.is_dir():
        return 0

    destination_root = settings.storage_dir.resolve()
    restored = 0
    for source in source_root.rglob('*'):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        destination = (destination_root / relative).resolve()
        try:
            destination.relative_to(destination_root)
        except ValueError:
            continue
        if destination.is_file():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        restored += 1
    return restored
