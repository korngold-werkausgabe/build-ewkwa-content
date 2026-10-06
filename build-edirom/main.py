#!/usr/bin/env python3
"""
Prepare Edirom Content dynamically from frbr-tree.xml
Needed files: frbr-tree.xml, nav.xml, kb_sources.xml, Textkritische-Anmerkungen/*.xml, Quellen/*.xml
"""
import global_variables as vars
from parse_frbr import write_frbr_to_json
from sources import prepare_sources
from edirom_file import build_edirom
from works_file import build_works_file


def main():
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