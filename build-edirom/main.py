#!/usr/bin/env python3
"""
Prepare Edirom Content dynamically from frbr-tree.xml
Needed files: frbr-tree.xml, nav.xml, kb_sources.xml, Textkritische-Anmerkungen/*.xml, Quellen/*.xml
"""
from pprint import pprint
import parse_frbr
import sources
import global_variables as vars

def main():
    print("=" * 70)
    print("1. Step: Preparation of frbr-tree.xml")
    print("=" * 70)

    # Parse the frbr-tree.xml and convert it to JSON format
    #frbr = parse_frbr.write_frbr_to_json("/Users/diginaut/Repositories/Gitlab/Korngold/editions/series-c/c7_robin-hood/frbr-tree.xml")
    frbr_json = parse_frbr.write_frbr_to_json(vars.LOCAL_PATHS['frbr'])

    with open("file.json", "a", encoding="utf-8") as f:
        f.write(str(frbr_json))

    print(f"\n\t[OK] Found {len(frbr_json['work_list'])} work(s) to process\n")
        
    sources.prepare_sources(frbr_json['manifestation_list'])

if __name__ == "__main__":
    main()