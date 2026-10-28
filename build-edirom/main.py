#!/usr/bin/env python3
"""
Prepare Edirom Content dynamically from frbr-tree.xml.

This script is the main entry point for the Edirom content build pipeline.
It processes XML source files and generates the Edirom edition files
(edirom.xml and works.xml) that can be packaged into XAR files for deployment.

Usage:
    python main.py

Required input files (in project root):
    - frbr-tree.xml: Main work overview and structure
    - nav.xml or [edition-slug]-nav.xml: Navigation structures
    - kb_sources.xml: Source metadata (in Quellenuebersicht/)
    - tka_*.xml: Text-critical annotations (in Textkritische-Anmerkungen/)
    - source XML files (in Quellen/)

Output:
    - frbr.json: Intermediate JSON representation
    - build-xar/edirom.xml: Edirom edition file
    - build-xar/works.xml: Works file
    - build-xar/*.xar: Final Edirom edition package

Environment:
    The script uses global_variables.py for path configuration.
    Set LOCAL_PATHS in global_variables.py to match your project structure.
"""
import global_variables as vars
from parse_frbr import write_frbr_to_json
from sources import prepare_sources
from edirom_file import build_edirom
from works_file import build_works_file


def main():
    """
    Execute the Edirom content build pipeline in four steps:

    1. Parse frbr-tree.xml and convert to JSON
    2. Prepare and process all sources
    3. Build the edirom.xml file
    4. Build the works.xml file
    """
    print("=" * 70)
    print("1. Step: Preparation of frbr-tree.xml")
    print("=" * 70)

    # Parse the frbr-tree.xml and convert it to JSON format
    frbr_json = write_frbr_to_json(vars.LOCAL_PATHS['frbr'])

    with open('./frbr.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(frbr_json, f, ensure_ascii=False, indent=4)

    print(f"\n\t[OK] Found {len(frbr_json['work_list'])} work(s) to process\n")

    print("=" * 70)
    print("2. Step: Preparation of sources")
    print("=" * 70)

    prepare_sources(frbr_json['manifestation_list'])

    print("=" * 70)
    print("3. Step: Build edirom.xml file")
    print("=" * 70)

    build_edirom(frbr_json)

    print("=" * 70)
    print("4. Step: Build works.xml file")
    print("=" * 70)

    build_works_file(frbr_json)


if __name__ == "__main__":
    main()