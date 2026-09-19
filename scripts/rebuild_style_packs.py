#!/usr/bin/env python3
"""Rebuild categorized Style Library ZIP packs from the raw local MIDI corpus."""

from __future__ import annotations

import json

from local_server import build_style_packs


def main() -> None:
    report = build_style_packs()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
