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
    'xml': 'http://www.w3.org/XML/1998/namespace',
    'edirom': 'http://www.edirom.de/ns/1.3',
}

LOCAL_PATHS = {
    'frbr': Path('frbr-tree.xml'),
    'edirom-config': Path('Edirom-Config'),
    'conc': Path('Konkordanzen'),
    'tmp': Path('tmp'),
    'scripts': Path(__file__).parent,
    'sources': Path('Quellen'),
    'templates': Path('build-ewkwa-content') / 'build-edirom' / 'templates'
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

def get_concordances(work: etree._Element) -> str:
    """ Get correct concordance.csv for first-level work and return as JSON string """
    import json
    results = []
    if work.xpath('./@type', namespaces=NAMESPACES)[0] == 'collection':
        for sub_work in get_second_level_works(work):
            edition_slug = sub_work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
            title_de = sub_work.xpath('./mei:title[@xml:lang="de"]/text()', namespaces=NAMESPACES)
            title_en = sub_work.xpath('./mei:title[@xml:lang="en"]/text()', namespaces=NAMESPACES)
            file = get_related_file(edition_slug, LOCAL_PATHS['conc'], '*.csv', 'by_filename')
            if file:
                results.append({
                    "title_de": title_de[0] if title_de else "", 
                    "title_en": title_en[0] if title_en else "", 
                    "file": (LOCAL_PATHS['conc'] / file).resolve().as_uri()
                })
    else:
        for mdiv in work.xpath('.//mei:contentItem[@type="mdiv"]', namespaces=NAMESPACES):
            edition_slug = mdiv.xpath('./mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
            title_de = mdiv.xpath('.//mei:title[@xml:lang="de"]/text()', namespaces=NAMESPACES)[0]
            title_en = mdiv.xpath('.//mei:title[@xml:lang="en"]/text()', namespaces=NAMESPACES)[0]

            file = get_related_file(edition_slug, LOCAL_PATHS['conc'], '*.csv', 'by_filename')
            if file:
                results.append({
                    "title_de": title_de if title_de else "", 
                    "title_en": title_en if title_en else "", 
                    "file": (LOCAL_PATHS['conc'] / file).resolve().as_uri()
                })
    return json.dumps(results) if results else None

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
        print(f"      [OK] buildNav.xsl processed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"      [FAIL] [E1] buildNav.xsl failed: {e.stderr}", file=sys.stderr)
        return None
    
def build_concordances(conc_json: str, groups_titles: list, sources_path: str, edition_slug: str) -> str:
    """ Call buildConnectionsByCSV.xql with concordance JSON and sources using basex """
    try:
        if not conc_json:
            print(f"      [FAIL] [E2] No concordance files provided", file=sys.stderr)
            return None
        
        build_concordances_xql = LOCAL_PATHS['scripts'] / 'buildConnectionsByCSV.xql'
        sources_path_abs = Path(sources_path).resolve()
        
        result = subprocess.run([
            'basex',
            f'-b csvPathsString={conc_json}',
            f'-b sourcesPath={sources_path_abs}',
            f'-b editionSlug={edition_slug}',
            f'-b propertiesPath={Path("properties.xml").resolve()}',
            f'-b groupsTitleDe={groups_titles["de"]}',
            f'-b groupsTitleEn={groups_titles["en"]}',
            str(build_concordances_xql)
        ], capture_output=True, text=True, check=True)
        print(f"      [OK] buildConnectionsByCSV.xql processed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"      [FAIL] [E3] buildConnectionsByCSV.xql failed: {e.stderr}", file=sys.stderr)
        return None
    
def build_edirom_file(works: list) -> bool:
    """ 
    Build Edirom file with dependency tracking using Early Return Pattern.
    Returns True if successful, False if any step fails.
    Handles both Collection and Singleton work types differently.
    """
    works_wrapper = etree.Element('{%s}works' % NAMESPACES['edirom'], nsmap={None: NAMESPACES['edirom']})

    for xid, work in enumerate(works):
        work_type = work.xpath('./@type', namespaces=NAMESPACES)[0]
        edition_slug = work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
        edition_name = work.xpath('./mei:expressionList/mei:expression/mei:title/text()', namespaces=NAMESPACES)[0]
        edition_id = work.xpath('./mei:expressionList/mei:expression/@xml:id', namespaces=NAMESPACES)[0]
        # Create tmp directory for this edition
        tmp_path = LOCAL_PATHS['tmp'] / edition_slug
        tmp_path.mkdir(parents=True, exist_ok=True)
    
        # Step 1: Build Nav
        print(f"  +-- Step 1: Build Navigation ({work_type})")
        nav_file = get_nav(work)
        if not nav_file:
            print(f"  |   [WARN] [W4] No nav file found - using empty fallback", file=sys.stderr)
            nav_output = "<navigatorDefinition/>"
        else:
            print(f"      Found: {nav_file}")
            nav_output = build_nav(LOCAL_PATHS['edirom-config'] / nav_file, edition_slug)
            if not nav_output:
                print(f"  |   [WARN] [W4b] build_nav failed - using empty fallback", file=sys.stderr)
                nav_output = "<navigatorDefinition/>"
        
        # Save nav output to tmp file
        nav_path = tmp_path / f"{edition_slug}_nav.xml"
        create_file(nav_output, nav_path)
        print(f"      [OK] Navigation complete\n")
        
        # Step 2: Build Concordances
        print(f"  +-- Step 2: Build Concordances ({work_type})")
        conc_files = get_concordances(work)
        if not conc_files:
            print(f"  |   [WARN] [W5] No concordance files found - using empty fallback", file=sys.stderr)
            concordance_output = "<concordances/>"
        else:
            conc_count = len(eval(conc_files))
            print(f"      Found: {conc_count} concordance file(s)")
            
            # Get group titles based on work type
            if work_type == 'collection':
                title_de = work.xpath('./mei:title[@xml:lang="de"]/text()', namespaces=NAMESPACES)
                title_en = work.xpath('./mei:title[@xml:lang="en"]/text()', namespaces=NAMESPACES)
            else:
                # Singleton: titles come from contentItem
                title_de = work.xpath('./mei:contentItem[@type="mdiv"]/mei:title[@xml:lang="de"]/text()', namespaces=NAMESPACES)
                title_en = work.xpath('./mei:contentItem[@type="mdiv"]/mei:title[@xml:lang="en"]/text()', namespaces=NAMESPACES)
            
            groups_titles = {
                'de': title_de[0] if title_de else '',
                'en': title_en[0] if title_en else ''
            }
            
            concordance_output = build_concordances(conc_files, groups_titles, LOCAL_PATHS['sources'], edition_slug)
            if not concordance_output:
                print(f"  |   [WARN] [W5b] build_concordances failed - using empty fallback", file=sys.stderr)
                concordance_output = "<concordances/>"
            
            # Save concordance output to tmp file
            conc_path = tmp_path / f"{edition_slug}_concordance.xml"
            create_file(concordance_output, conc_path)
            print(f"      [OK] Concordance complete\n")

        # Build work element in edirom namespace (outside if/else to ensure always created)
        work_xml_id = work.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        work_element = etree.Element(
            '{%s}work' % NAMESPACES['edirom'], 
            attrib={
                '{%s}id' % NAMESPACES['xml']: work_xml_id, 
                'sortNo': str(xid + 1)
            }
        )

        # Add navigation (guaranteed to have valid XML from fallback)
        nav_element = etree.fromstring(nav_output)
        work_element.append(nav_element)
        
        work_element.append(etree.Element('{%s}searchWindowConfig' % NAMESPACES['edirom']))
        
        # Add concordances (guaranteed to have valid XML from fallback)
        concordances_element = etree.Element('{%s}concordances' % NAMESPACES['edirom'])
        conc_element = etree.fromstring(concordance_output)
        concordances_element.append(conc_element)
        
        work_element.append(concordances_element)
        works_wrapper.append(work_element)
            
    works_file_path = LOCAL_PATHS['tmp'] / "works.xml"
    create_file(etree.tostring(works_wrapper, encoding='unicode', pretty_print=True), works_file_path)

    # Step 3: Build Edirom File
    try:
        build_edirom_file_xsl = LOCAL_PATHS['scripts'] / 'buildEdiromFile.xsl'
        edirom_file_template_path = (LOCAL_PATHS['templates'] / 'template_edirom-file.xml').resolve()

        result = subprocess.run([
            'xsltproc',
            '--stringparam', 'editionId', edition_id,
            '--stringparam', 'editionName', edition_name,
            '--stringparam', 'editionPrefsPath', edition_slug,
            '--stringparam', 'editionWorksPath', str(works_file_path.resolve()),
            str(build_edirom_file_xsl),
            str(edirom_file_template_path),
        ], capture_output=True, text=True, check=True)
        print(f"      [OK] buildEdiromFile.xsl processed")
        # Save with XML formatting
        create_file(result.stdout, LOCAL_PATHS['tmp'] / "edition.xml", format_xml=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"      [FAIL] [E1] buildEdiromFile.xsl failed: {e.stderr}", file=sys.stderr)
        return False

def create_file(content: str, output_path: Path, format_xml: bool = False):
    """ Helper function to create output files """
    try:
        # Format XML if requested
        if format_xml:
            tree = etree.fromstring(content.encode('utf-8'))
            content = etree.tostring(tree, encoding='unicode', pretty_print=True, xml_declaration=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"      [OK] Saved: {output_path.name}")
    except Exception as e:
        sys.exit(1)

def main():
    print("=" * 70)
    print("Preparation of Edirom Content from frbr-tree.xml")
    print("=" * 70)

    first_level_works = get_first_level_works_from_frbr(LOCAL_PATHS['frbr'])
    print(f"\nFound {len(first_level_works)} work(s) to process\n")

    # Build all dependencies with early return on failure
    if build_edirom_file(first_level_works):
        print(f"  [OK] READY: Edition prepared for next steps\n")
    else:
        print(f"  [FAIL] FAILED: Edition skipped due to dependency errors\n")

if __name__ == "__main__":
    main()