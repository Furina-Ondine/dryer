"""Use the shared compiler front end from the environment or a sibling checkout."""

from __future__ import annotations

import sys
from pathlib import Path


def _sibling_src() -> Path:
    return Path(__file__).resolve().parents[3] / "crapper" / "src"


def parse_document(source: str, language: str, path: str, project_root=None):
    try:
        import crapper
    except ImportError:
        sibling = _sibling_src()
        if not (sibling / "crapper").is_dir():
            raise ImportError(
                "C# analysis requires the matching Crapper compiler front end. "
                "Install Crapper in this environment or clone it next to Dryer."
            ) from None
        sys.path.insert(0, str(sibling))
        import crapper
    from crapper.frontend import parse_document as read

    return read(source, language, path, project_root)
