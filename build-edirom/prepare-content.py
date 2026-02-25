#!/usr/bin/env python3
"""
Prepare Edirom Content dynamically from frbr-tree.xml
Needed files: frbr-tree.xml, nav.xml, 
"""

from lxml import etree
from pathlib import Path
import subprocess
import sys

# XML namespaces
NAMESPACES = {
    'mei': 'http://www.music-encoding.org/ns/mei',
    'xml': 'http://www.w3.org/XML/1998/namespace'
}

LOCAL_PATHS = {
    'frbr': Path('frbr-tree.xml'),
    'edirom-config': Path('Edirom-Config'),
    'conc': Path('Konkordanzen'),
    'tmp': Path('tmp'),
    'scripts': Path(__file__).parent,
    'sources': Path('Quellen')
}

def get_first_level_works_from_frbr(frbr_path: str) -> tuple:
    """ Extract first-level works from frbr-tree.xml """
    try:
        tree = etree.parse(frbr_path)
        root = tree.getroot()
        works = root.xpath('/mei:mei/mei:meiHead/mei:workList/mei:work', namespaces=NAMESPACES)
        return works
    except Exception as e:
        print(f"Error parsing {frbr_path}: {e}", file=sys.stderr)
        return []
    
def get_second_level_works(work: etree._Element) -> set:
    """ Get second-level works if the first-level work is a collection """
    if work.xpath('./@type', namespaces=NAMESPACES)[0] == 'collection':
        return work.xpath('./mei:componentList//mei:work[@type="singleton"]', namespaces=NAMESPACES)
    return []
    
def get_nav(work: etree._Element) -> str:
    """ Get filename of nav.xml for a given first-level work """
    rel_has_part = work.xpath('./mei:relationList/mei:relation[@rel="hasPart"]/@plist', namespaces=NAMESPACES)
    nav_id = None

    for id in rel_has_part:
        id_clean = id.lstrip('#')
        if 'nav' in id_clean:
            nav_id = id_clean
            break

    return get_related_file(nav_id, LOCAL_PATHS['edirom-config'], '*.xml', 'by_id') if nav_id else None

def get_concordances(work: etree._Element) -> list:
    """ Get correct concordance.csv for first-level work """
    results = []
    if work.xpath('./@type', namespaces=NAMESPACES)[0] == 'collection':
        for sub_work in get_second_level_works(work):
            edition_slug = sub_work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
            file = get_related_file(edition_slug, LOCAL_PATHS['conc'], '*.csv', 'by_filename')
            if file:
                results.append(file)
    else:
        edition_slug = work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
        file = get_related_file(edition_slug, LOCAL_PATHS['conc'], '*.csv', 'by_filename')
        if file:
            results.append(file)
    return results

def get_related_file(search_string, path, file_type, search_type: str) -> str:
    """ Helper function to find related files (nav, cnl, etc.) based on file name or ID """
    if search_type == 'by_id':
        for file in path.glob(file_type):
            tree = etree.parse(file)
            root = tree.getroot()
            nav = root.xpath('//navigatorDefinition[@xml:id=$search_string]', namespaces=NAMESPACES, search_string=search_string)
            if nav:
                print(f"  Preparing {file.name} for '{search_string}'")
                return file.name
    elif search_type == 'by_filename':
        for file in path.glob(file_type):
            if search_string in file.name:
                print(f"  Preparing {file.name} for '{search_string}'")
                return file.name
            
def build_nav(nav_path, edition_slug: str) -> str:
    """ Call buildNav.xsl with editionSlug parameter """
    try:
        build_nav_xsl = LOCAL_PATHS['scripts'] / 'buildNav.xsl'
        nav_path_abs = Path(nav_path).resolve()  # Absolut path
        
        result = subprocess.run([
            'xsltproc',
            '--stringparam', 'editionSlug', edition_slug,
            str(build_nav_xsl),
            str(nav_path_abs)
        ], capture_output=True, text=True, check=True)
        print(f"  buildNav.xsl processed for '{edition_slug}'")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running buildNav.xsl: {e.stderr}", file=sys.stderr)
        return None
    
def build_concordances(conc_files, groups_titles: list, sources_path: str, edition_slug: str) -> str:
    """ Call buildConnectionsByCSV.xql with concordance files and sources using basex """
    try:
        if not conc_files:
            print(f"  No concordance files provided for '{edition_slug}'")
            return None
        
        build_concordances_xql = LOCAL_PATHS['scripts'] / 'buildConnectionsByCSV.xql'
        csv_paths = ';'.join([str(LOCAL_PATHS['conc'] / file) for file in conc_files])
        sources_path_abs = Path(sources_path).resolve()
        
        result = subprocess.run([
            'basex',
            f'-b csvPathsString={csv_paths}',
            f'-b sourcesPath={sources_path_abs}',
            f'-b editionHandle={edition_slug}',
            f'-b propertiesPath={Path("properties.xml").resolve()}',
            f'-b groupTitles=<titles><title xml:lang="de">{groups_titles["de"]}</title><title xml:lang="en">{groups_titles["en"]}</title></titles>',
            str(build_concordances_xql)
        ], capture_output=True, text=True, check=True)
        print(f"  buildConnectionsByCSV.xql processed for '{edition_slug}'")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running buildConnectionsByCSV.xql: {e.stderr}", file=sys.stderr)
        return None

def create_file(content: str, output_path: Path):
    """ Helper function to create output files """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  File created at {output_path}")
    except Exception as e:
        print(f"Error creating file {output_path}: {e}", file=sys.stderr)

def main():
    if not LOCAL_PATHS['frbr'].exists():
        print(f"Error: {LOCAL_PATHS['frbr']} not found", file=sys.stderr)
        sys.exit(1)
    
    print("Preparation of Edirom content from frbr-tree.xml")
    print("=" * 60)

    first_level_works = get_first_level_works_from_frbr(LOCAL_PATHS['frbr'])

    for work in first_level_works:
        print(f"\nProcessing work {work.xpath('./@xml:id', namespaces=NAMESPACES)[0]}")

        edition_slug = work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
        nav_file = get_nav(work)
        conc_files = get_concordances(work)

        tmp_path = LOCAL_PATHS['tmp'] / edition_slug if edition_slug else None
        if tmp_path:
            tmp_path.mkdir(parents=True, exist_ok=True)
            print(f"  Created tmp directory {tmp_path} for edition '{edition_slug}'")

        if nav_file:
            nav_output = build_nav(LOCAL_PATHS['edirom-config'] / nav_file, edition_slug)
            if nav_output:
                output_path = tmp_path / f"{edition_slug}_nav.xml"
                create_file(nav_output, output_path)
            else:
                print(f"  WARNING: No output from buildNav.xsl for {nav_file}")

        if conc_files:
            title_de = work.xpath('./mei:titleStmt/mei:title[@xml:lang="de"]/text()', namespaces=NAMESPACES)
            title_en = work.xpath('./mei:titleStmt/mei:title[@xml:lang="en"]/text()', namespaces=NAMESPACES)
            groups_titles = {
                'de': title_de,
                'en': title_en
            }   
            concordance_output = build_concordances(conc_files, groups_titles, LOCAL_PATHS['sources'], edition_slug)
            if concordance_output:
                output_path = tmp_path / f"{edition_slug}_concordance.xml"
                create_file(concordance_output, output_path)
            else:
                print(f"  WARNING: No output from buildConnectionsByCSV.xql")

if __name__ == "__main__":
    main()