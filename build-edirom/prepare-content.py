#!/usr/bin/env python3
"""
Prepare Edirom Content dynamically from frbr-tree.xml
Needed files: frbr-tree.xml, nav.xml, 
"""

from lxml import etree
from pathlib import Path
from copy import deepcopy
import subprocess
import sys

# XML namespaces
NAMESPACES = {
    'mei': 'http://www.music-encoding.org/ns/mei',
    'xml': 'http://www.w3.org/XML/1998/namespace',
    'edirom': 'http://www.edirom.de/ns/1.3',
    'xlink': 'http://www.w3.org/1999/xlink'
}

LOCAL_PATHS = {
    'frbr': Path('frbr-tree.xml'),
    'edirom-config': Path('Edirom-Config'),
    '_edirom': Path('Edirom'),
    'conc': Path('Konkordanzen'),
    'criticalRemarks': Path('Textkritische-Anmerkungen'),
    'kbSources': Path('Quellenuebersicht'),
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
        edition_name = root.xpath('/mei:mei/mei:meiHead/mei:fileDesc/mei:titleStmt/mei:title[@type="volume"]/text()', namespaces=NAMESPACES)
        vol_slug = root.xpath('/mei:mei/mei:meiHead/mei:fileDesc/mei:pubStmt/mei:identifier[@type="volSlug"]/text()', namespaces=NAMESPACES)
        return works, edition_name[0] if edition_name else 'Untitled Edition', vol_slug[0] if vol_slug else 'untitled_volume'
    except Exception as e:
        print(f"Error parsing {frbr_path}: {e}", file=sys.stderr)
        return [], 'Untitled Edition', 'untitled_volume'
    
def get_second_level_works(work: etree._Element) -> set:
    """ Get second-level works if the first-level work is a collection """
    if work.xpath('./@type', namespaces=NAMESPACES)[0] == 'collection':
        return work.xpath('./mei:componentList//mei:work[@type="singleton"]', namespaces=NAMESPACES)
    return []

def get_component_expressions(expression: etree._Element) -> list:
    """ Get component expressions if the expression has a componentList (e.g., for different editions like full-score, short-score) """
    component_list = expression.xpath('./mei:componentList', namespaces=NAMESPACES)
    if component_list:
        return expression.xpath('./mei:componentList/mei:expression', namespaces=NAMESPACES)
    return []

def get_concordances(work: etree._Element) -> str:
    """ Get correct concordance.csv for first-level work and return as JSON string """
    import json
    results = []
    if work.xpath('./@type', namespaces=NAMESPACES)[0] == 'collection':
        for sub_work in get_second_level_works(work):
            sub_div = sub_work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES)[0] if sub_work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES) else ""
            title_de = sub_work.xpath('./mei:title[@xml:lang="de"]/text()', namespaces=NAMESPACES)
            title_en = sub_work.xpath('./mei:title[@xml:lang="en"]/text()', namespaces=NAMESPACES)
            file = _get_rel_file(sub_div, LOCAL_PATHS['conc'], '*.csv', 'by_filename')
            if file:
                results.append({
                    "title_de": title_de[0] if title_de else "", 
                    "title_en": title_en[0] if title_en else "", 
                    "file": (LOCAL_PATHS['conc'] / file).resolve().as_uri()
                })
    else:
        for mdiv in work.xpath('.//mei:contentItem[@type="mdiv"]', namespaces=NAMESPACES):
            sub_div = mdiv.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES)[0] if mdiv.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES) else ""
            title_de = mdiv.xpath('.//mei:title[@xml:lang="de"]/text()', namespaces=NAMESPACES)[0]
            title_en = mdiv.xpath('.//mei:title[@xml:lang="en"]/text()', namespaces=NAMESPACES)[0]

            file = _get_rel_file(sub_div, LOCAL_PATHS['conc'], '*.csv', 'by_filename')
            if file:
                results.append({
                    "title_de": title_de if title_de else "", 
                    "title_en": title_en if title_en else "", 
                    "file": (LOCAL_PATHS['conc'] / file).resolve().as_uri()
                })
    return json.dumps(results) if results else None

def _get_rel_file(search_string, path, file_type, search_type: str) -> str:
    """ Helper function to find related files (nav, cnl, etc.) based on file name or ID. Searches recursively in subdirectories. """
    result = None
    if search_type == 'by_id':
        parser = etree.XMLParser(resolve_entities=False)
        for file in path.rglob(file_type):
            tree = etree.parse(file, parser)
            root = tree.getroot()
            # Check root element first
            root_id = root.xpath('./@xml:id', namespaces=NAMESPACES)
            if root_id and root_id[0] == search_string:
                return str(file.relative_to(path))  # ← Return relative path from base path
            else:
                nav = root.xpath('//*[@xml:id=$search_string]', namespaces=NAMESPACES, search_string=search_string)
                if nav:
                    return str(file.relative_to(path))  # ← Return relative path from base path
        return None
    elif search_type == 'by_filename':
        for file in path.rglob(file_type):
            if search_string in file.name:
                result = str(file.relative_to(path))  # ← Return relative path from base path
    if result:
        return result
    else:
        print(f"    |   |   [WARN] [W2] No file with '{search_string}' in name found in {path}", file=sys.stderr)
        return None

def build_nav(nav_path, vol_slug: str, sub_div: str) -> str:
    """ Call buildNav.xsl with volSlug and subDiv parameters """
    try:
        build_nav_xsl = LOCAL_PATHS['scripts'] / 'buildNav.xsl'
        nav_path_abs = Path(nav_path).resolve()  # Absolut path
        
        result = subprocess.run([
            'xsltproc',
            '--stringparam', 'volSlug', vol_slug,
            '--stringparam', 'subDiv', sub_div,
            str(build_nav_xsl),
            str(nav_path_abs)
        ], capture_output=True, text=True, check=True)
        print(f"    |   |   [OK] buildNav.xsl processed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"    |   |   [FAIL] [E1] buildNav.xsl failed: {e.stderr}", file=sys.stderr)
        return None
    
def build_concordances(conc_json: str, groups_titles: list, sources_path: str, sub_div: str, vol_slug: str) -> str:
    """ Call buildConnectionsByCSV.xql with concordance JSON and sources using basex """
    try:
        if not conc_json:
            print(f"    |   |   [FAIL] [E2] No concordance files provided", file=sys.stderr)
            return None
        
        build_concordances_xql = LOCAL_PATHS['scripts'] / 'buildConnectionsByCSV.xql'
        sources_path_abs = Path(sources_path).resolve()
        
        result = subprocess.run([
            'basex',
            f'-b csvPathsString={conc_json}',
            f'-b sourcesPath={sources_path_abs}',
            f'-b subDiv={sub_div}',
            f'-b volSlug={vol_slug}',
            f'-b propertiesPath={Path("properties.xml").resolve()}',
            f'-b groupsTitleDe={groups_titles["de"]}',
            f'-b groupsTitleEn={groups_titles["en"]}',
            str(build_concordances_xql)
        ], capture_output=True, text=True, check=True)
        print(f"    |   |   [OK] buildConnectionsByCSV.xql processed")
        return result.stdout
    except FileNotFoundError:
        print(f"    |   |   [WARN] [W6] basex not found - using empty fallback", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"    |   |   [FAIL] [E3] buildConnectionsByCSV.xql failed: {e.stderr}", file=sys.stderr)
        return None
    
def build_edirom_file(works: list, edition_name: str, vol_slug: str) -> bool:
    """ 
    Build Edirom file with dependency tracking using Early Return Pattern.
    Returns True if successful, False if any step fails.
    Handles both Collection and Singleton work types differently.
    """
    print(f"+-- Step 1: Build Edirom File")
    works_wrapper = etree.Element('{%s}works' % NAMESPACES['edirom'], nsmap={None: NAMESPACES['edirom']})

    for xid, work in enumerate(works):
        work_title = work.xpath('./mei:title/text()', namespaces=NAMESPACES)[0]
        print(f"    +-- Processing {xid + 1}/{len(works)}: '{work_title}'")
        work_type = work.xpath('./@type', namespaces=NAMESPACES)[0]
        edition_id = work.xpath('./mei:expressionList/mei:expression/@xml:id', namespaces=NAMESPACES)[0]
        sub_div = work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES)[0] if work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES) else ""
        tmp_path = LOCAL_PATHS['tmp'] / sub_div if sub_div else LOCAL_PATHS['tmp']
        tmp_path.mkdir(parents=True, exist_ok=True)
        # Create output directory for this edition
        output_path = LOCAL_PATHS['_edirom']
        output_path.mkdir(parents=True, exist_ok=True)
    
        # Step 1: Build Nav
        print(f"    |   +-- Step 1.1: Build Navigation ({sub_div})")
        nav_id = _get_rel_by_id(work, edition_id, type='nav')[0] if _get_rel_by_id(work, edition_id, type='nav') else None
        nav_file = _get_rel_file(nav_id, LOCAL_PATHS['edirom-config'], '*.xml', 'by_id') if nav_id else None
        if nav_file is None:
            print(f"    |   |   [WARN] [W4] No nav file found - using empty fallback", file=sys.stderr)
            nav_output = "<navigatorDefinition/>"
        else:
            nav_output = build_nav(LOCAL_PATHS['edirom-config'] / nav_file, vol_slug, sub_div)
            if not nav_output:
                print(f"    |   |   [WARN] [W4b] build_nav failed - using empty fallback", file=sys.stderr)
                nav_output = "<navigatorDefinition/>"
        
        # Save nav output to tmp file
        nav_path = tmp_path / f"{sub_div}_nav.xml" if sub_div else tmp_path / "nav.xml"
        create_file(nav_output, nav_path, format_xml=True)
        print(f"    |   |   [OK] Navigation complete")
        
        # Step 2: Build Concordances
        print(f"    |   +-- Step 1.2: Build Concordances ({sub_div})")
        conc_files = get_concordances(work)
        if not conc_files:
            print(f"    |   |   [WARN] [W5] No concordance files found - using empty fallback", file=sys.stderr)
            concordance_output = "<concordances/>"
        else:
            conc_count = len(eval(conc_files))
            
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
            
            concordance_output = build_concordances(conc_files, groups_titles, f"{LOCAL_PATHS['_edirom']}/{sub_div}/sources", sub_div, vol_slug)
            if not concordance_output:
                print(f"    |   |   [WARN] [W5b] build_concordances failed - using empty fallback", file=sys.stderr)
                concordance_output = "<concordances/>"
            
            # Save concordance output to tmp file
            conc_path = tmp_path / f"{sub_div}_concordance.xml" if sub_div else tmp_path / "concordance.xml"
            create_file(concordance_output, conc_path, format_xml=True)
            print(f"    |   |   [OK] Concordance complete")

        # Build work element in edirom namespace (outside if/else to ensure always created)
        work_xml_id = work.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        href = (f"xmldb:exist:///db/apps/edirom-content/{vol_slug}/{sub_div}/{sub_div}_works.xml"
                if sub_div else
                f"xmldb:exist:///db/apps/edirom-content/{vol_slug}/works.xml")

        work_element = etree.Element(
            '{%s}work' % NAMESPACES['edirom'], 
            attrib={
                '{%s}id' % NAMESPACES['xml']: work_xml_id,
                'sortNo': str(xid + 1),
                '{%s}href' % NAMESPACES['xlink']: href,
            },
            nsmap={'xlink': NAMESPACES['xlink']}  
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
            
    works_file_path = LOCAL_PATHS['tmp'] / "works_tmp.xml"
    create_file(etree.tostring(works_wrapper, encoding='unicode', pretty_print=True), works_file_path)

    # Step 3: Build Edirom File
    try:
        print(f"    +-- Step 1.3: Create Edirom File")
        build_edirom_file_xsl = LOCAL_PATHS['scripts'] / 'buildEdiromFile.xsl'
        edirom_file_template_path = (LOCAL_PATHS['templates'] / 'template_edirom-file.xml').resolve()
        edition_prefs_path = f"{vol_slug}/{sub_div}" if sub_div else f"{vol_slug}"

        result = subprocess.run([
            'xsltproc',
            '--stringparam', 'editionId', edition_id,
            '--stringparam', 'editionName', edition_name,
            '--stringparam', 'editionPrefsPath', edition_prefs_path,
            '--stringparam', 'editionWorksPath', str(works_file_path.resolve()),
            str(build_edirom_file_xsl),
            str(edirom_file_template_path),
        ], capture_output=True, text=True, check=True)
        print(f"    |   |   [OK] buildEdiromFile.xsl processed")
        # Save - xsltproc already outputs formatted XML with declaration
        create_file(result.stdout, output_path / "edition.xml", format_xml=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    |   |   [FAIL] [E1] buildEdiromFile.xsl failed: {e.stderr}", file=sys.stderr)
        return False
    
def prepare_sources(first_level_works: list, vol_slug: str) -> bool:
    """ Prepare source files for Edirom edition """

    print(f"+-- Step 2: Prepare Source Files")

    
    for work in first_level_works:
        work_id = work.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        root = work.getroottree().getroot()
        sub_div = work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES)[0] if work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES) else None
        ex_id = work.xpath('./mei:expressionList/mei:expression/@xml:id', namespaces=NAMESPACES)[0]

        kb_sources_ids = _get_rel_by_id(work, ex_id, type='srcs')
        
        for kb_sources_id in kb_sources_ids:
            listSources = _get_rel_xml(kb_sources_id, type='srcs')
            
            if listSources is None:
                print(f"    |   [WARN] [W7] No file found for '{kb_sources_id}' in {LOCAL_PATHS['kbSources']}", file=sys.stderr)
                continue
        
        for source in listSources.xpath('//source', namespaces=NAMESPACES):
            source_id = source.xpath('./@xml:id', namespaces=NAMESPACES)[0] if source.xpath('./@xml:id', namespaces=NAMESPACES) else None
            source_file_id = source.xpath('./@targets', namespaces=NAMESPACES)[0] if source.xpath('./@targets', namespaces=NAMESPACES) else source.xpath('./@xml:id', namespaces=NAMESPACES)[0]
            source_file_id = source_file_id.lstrip('#')  # Remove leading '#' if present
            source_title = source.xpath('./shortTitle/text()', namespaces=NAMESPACES)[0] if source.xpath('./shortTitle/text()', namespaces=NAMESPACES) else "No title found"
            source_siglum = source.xpath('./siglum/text()', namespaces=NAMESPACES)[0] if source.xpath('./siglum/text()', namespaces=NAMESPACES) else "Siglum not found"
            source_file = _get_rel_file(source_file_id, LOCAL_PATHS['sources'], '*.xml', 'by_id')
            
            if not source_file:
                print(f"    |   [WARN] [W8] Source file not found for '{source_file_id}' - skipping", file=sys.stderr)
                continue
            else: 
                print(f"    |   +-- Preparing source file '{source_file}' for '{source_title}' ({source_siglum})")

            manifestation = None
            item = None

            # Add identifier to manifestation
            identifier = etree.Element('{%s}identifier' % NAMESPACES['mei'])
            identifier.set('type', 'siglum')
            identifier.text = source_siglum

            relList = etree.Element('{%s}relationList' % NAMESPACES['mei'])
            rel = etree.Element('{%s}relation' % NAMESPACES['mei'])
            rel.set('rel', 'isEmbodimentOf')
            rel.set('target', f"xmldb:exist:///db/apps/edirom-content/{vol_slug}/{sub_div}/works.xml#{work_id}")
            relList.append(rel)

            # Get manifestation in frbr-tree
            if root.xpath(f'.//mei:manifestation[@target="#{source_id}"]', namespaces=NAMESPACES):
                manifestation = root.xpath(f'.//mei:manifestation[@target="#{source_id}"]', namespaces=NAMESPACES)[0] 
                del manifestation.attrib['target']
                manifestation.append(identifier)
                manifestation.append(relList)
            elif root.xpath(f'.//mei:item[@target="#{source_id}"]', namespaces=NAMESPACES):
                    item = root.xpath(f'.//mei:item[@target="#{source_id}"]', namespaces=NAMESPACES)[0]
                    del item.attrib['target']
                    manifestation = item.xpath('ancestor::mei:manifestation[1]', namespaces=NAMESPACES)[0]
                    manifestation.append(relList)
                    item.append(identifier)
            else:
                print(f"    |   [WARN] [W10] No manifestation or item found for source '{source_id}'", file=sys.stderr)
                continue

                    
            try:
                print(f"    +-- Step 2.2: Prepare and copy source file")
                prepare_sources_xsl = LOCAL_PATHS['scripts'] / 'prepareSources.xsl'
                source_file = (LOCAL_PATHS['sources'] / source_file).resolve()
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as tmp_manifestation_file:
                    manifestation_xml = etree.tostring(manifestation, encoding='unicode') if manifestation is not None else '<manifestation xmlns="http://www.music-encoding.org/ns/mei"/>'
                    tmp_manifestation_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    tmp_manifestation_file.write(manifestation_xml)
                    manifestation_file_uri = Path(tmp_manifestation_file.name).resolve().as_uri()

                try:
                    result = subprocess.run([
                        'xsltproc',
                        '--stringparam', 'title', source_title,
                        '--stringparam', 'manifestationFile', manifestation_file_uri,
                        str(prepare_sources_xsl),
                        str(source_file),
                    ], capture_output=True, text=True, check=True)
                finally:
                    Path(tmp_manifestation_file.name).unlink(missing_ok=True)
                print(f"    |   |   [OK] prepareSources.xsl processed")
                # Save - xsltproc already outputs formatted XML with declaration
                # Use original filename instead of source_file_id
                original_filename = source_file.name
                if sub_div:
                    source_output_path = LOCAL_PATHS['_edirom'] / sub_div / "sources" / original_filename
                else:
                    source_output_path = LOCAL_PATHS['_edirom'] / "sources" / original_filename
                source_output_path.parent.mkdir(parents=True, exist_ok=True)

                create_file(result.stdout, source_output_path, format_xml=True)
            except subprocess.CalledProcessError as e:
                print(f"    |   |   [FAIL] [E1] prepareSources.xsl failed: {e.stderr}", file=sys.stderr)
                continue
    
    print(f"    |   [OK] Source files complete")
    return True

def build_critical_remarks(cnl_xml: str, sources_path: str, sub_div: str, vol_slug: str) -> str:
    """ Call buildEdiromTkAs.xql to build critical remarks (annots) """   
    try:
        build_tk_as_xql = LOCAL_PATHS['scripts'] / 'buildEdiromTkAs.xql'
        sources_path_abs = Path(sources_path).resolve()
        collection_path_abs = (LOCAL_PATHS['tmp'] / sub_div).resolve() if sub_div else (LOCAL_PATHS['tmp']).resolve()
        
        # Write CNL XML to temp file instead of passing via command line to avoid arg length limit
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp_file:
            tmp_file.write(cnl_xml)
            tmp_cnl_file = tmp_file.name
        
        try:
            result = subprocess.run([
                'basex',
                f'-b cnListFile={tmp_cnl_file}',
                f'-b collectionPath={collection_path_abs}',
                f'-b sourcesPath={sources_path_abs}',
                f'-b subDiv={sub_div}',
                f'-b volumeName={vol_slug}',
                str(build_tk_as_xql)
            ], capture_output=True, text=True, check=True)
            print(f"    |   |   [OK] buildEdiromTkAs.xql processed")
            return result.stdout
        finally:
            # Clean up temp file
            Path(tmp_cnl_file).unlink(missing_ok=True)
    except FileNotFoundError:
        print(f"    |   |   [WARN] [W6] basex not found - using empty fallback", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"    |   |   [FAIL] [E3] buildEdiromTkAs.xql failed: {e.stderr}", file=sys.stderr)
        return None

def _get_rel_by_id(first_level_work: etree._Element, expression_id: str, type: str) -> list:
    """ Extract ALL cnl_ids from first_level_work's relationList """
    rel_ids = []
    rel_has_part = first_level_work.xpath(f'./mei:relationList/mei:relation[@rel="hasPart" and @target="#{expression_id}"]/@plist', namespaces=NAMESPACES)

    for plist in rel_has_part:
        for id_item in plist.split():
            id_clean = id_item.lstrip('#')
            if type in id_clean:
                rel_ids.append(id_clean)
    
    return rel_ids

def _get_rel_xml(cnl_id: str, subdirectory: str = None, type: str = None) -> etree._Element:
    """ 
    Get cnList element from criticalRemarks by cnl_id.
    If subdirectory is provided, search in criticalRemarks/subdirectory/ first.
    """
    try:
        cnl_file = None
        search_paths = []

        if type and type == 'cnl':
            # If subdirectory is provided, search there first
            if subdirectory:
                subdir_path = LOCAL_PATHS['criticalRemarks'] / subdirectory
                if subdir_path.exists():
                    search_paths.append(subdir_path)
            
            # Also search in root criticalRemarks directory
            search_paths.append(LOCAL_PATHS['criticalRemarks'])
        elif type and type == 'srcs':
            search_paths.append(LOCAL_PATHS['kbSources'])
        
        # Search for file in paths
        for search_path in search_paths:
            cnl_file = _get_rel_file(cnl_id, search_path, '*.xml', 'by_id')
            if cnl_file:
                tree = etree.parse(search_path / cnl_file, parser=etree.XMLParser(resolve_entities=False))
                root = tree.getroot()
                cnList = root.xpath(f'//*[@xml:id="{cnl_id}"]', namespaces=NAMESPACES)
                if cnList:
                    return cnList[0]
        
        print(f"    |   [WARN] [W9] No critical remarks found for id '{cnl_id}'", file=sys.stderr)
        return None
        
    except Exception as e:
        print(f"    |   [FAIL] Failed to parse cnl file: {e}", file=sys.stderr)
        return None

def build_works_file(first_level_works: list, edition_name: str, vol_slug: str) -> bool:
    """ Build works.xml file for each first-level work (one file per work, with possible multiple expressions) """
    print(f"+-- Step 3: Build Works Files")

    works_by_sub_div: dict[str, list] = {}

    for first_level_work in first_level_works:
        # Get the main expression
        main_expression = first_level_work.xpath('./mei:expressionList/mei:expression', namespaces=NAMESPACES)[0]
        sub_div = main_expression.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES)[0] if main_expression.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES) else ''
        work_type = first_level_work.xpath('./@type', namespaces=NAMESPACES)[0]

        print(f"    +-- Building works.xml for '{sub_div}' ({work_type})")

        # Build single work element with main expression
        work_element = _build_work_element_with_components(first_level_work, sub_div, work_type, edition_name, vol_slug)
        if work_element is None:
            print(f"    |   [WARN] No work element created for {sub_div}", file=sys.stderr)
            continue

        # Check if there are component expressions (e.g., full-score, short-score)
        component_expressions = get_component_expressions(main_expression)

        if component_expressions:
            print(f"    |   [INFO] Found {len(component_expressions)} component expression(s)")
            # Add component expressions to a componentList within the main expression in the work element
            try:
                # Get the main expression in the work element
                work_expressions = work_element.xpath('./mei:expressionList/mei:expression', namespaces=NAMESPACES)
                if work_expressions:
                    main_expr_in_work = work_expressions[0]

                    # Check if componentList already exists, if not create it
                    component_lists = main_expr_in_work.xpath('./mei:componentList', namespaces=NAMESPACES)
                    if component_lists:
                        component_list = component_lists[0]
                    else:
                        # Create new componentList element
                        component_list = etree.Element('{%s}componentList' % NAMESPACES['mei'])
                        main_expr_in_work.append(component_list)

                    # Add component expressions to componentList with their critical remarks
                    for component_expr in component_expressions:
                        try:
                            component_expr_copy = deepcopy(component_expr)
                            component_slug = component_expr_copy.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES)[0] if component_expr_copy.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES) else "unknown"
                            component_expr_id = component_expr_copy.xpath('./@xml:id', namespaces=NAMESPACES)[0] if component_expr_copy.xpath('./@xml:id', namespaces=NAMESPACES) else None

                            # Add notesStmt with critical remarks to component expression
                            if component_expr_id:
                                cnl_ids = _get_rel_by_id(first_level_work, component_expr_id, type='cnl')
                                if cnl_ids:
                                    # Ensure component_expr_copy has notesStmt
                                    notes_stmts = component_expr_copy.xpath('./mei:notesStmt', namespaces=NAMESPACES)
                                    if not notes_stmts:
                                        notes_stmt = etree.Element('{%s}notesStmt' % NAMESPACES['mei'])
                                        component_expr_copy.append(notes_stmt)
                                        notes_stmts = [notes_stmt]

                                    # Create single criticalCommentary wrapper for all CNL files
                                    wrapper_annot = etree.Element('{%s}annot' % NAMESPACES['mei'], type='criticalCommentary')

                                    # Process each CNL file and collect all inner annots
                                    for cnl_id in cnl_ids:
                                        cnl_xml = _get_rel_xml(cnl_id, subdirectory=component_slug, type='cnl')
                                        if cnl_xml is not None:
                                            critical_remarks_str = build_critical_remarks(etree.tostring(cnl_xml, encoding='unicode'), LOCAL_PATHS['sources'], sub_div, vol_slug)
                                            if critical_remarks_str:
                                                try:
                                                    parser = etree.XMLParser(remove_blank_text=True)
                                                    # Parse the response - it now contains multiple annot elements without wrapper
                                                    # Wrap them temporarily for parsing
                                                    wrapped_str = f'<temp xmlns="http://www.music-encoding.org/ns/mei">{critical_remarks_str}</temp>'
                                                    wrapper_elem = etree.fromstring(wrapped_str.encode('utf-8'), parser)
                                                    # Extract all annot children and add to our criticalCommentary wrapper
                                                    for annot in wrapper_elem:
                                                        wrapper_annot.append(deepcopy(annot))
                                                    print(f"    |   [OK] Added {len(wrapper_elem)} critical remarks from '{cnl_id}' to component '{component_slug}'")
                                                except Exception as cr_e:
                                                    print(f"    |   [WARN] Could not parse critical remarks from '{cnl_id}': {cr_e}", file=sys.stderr)
                                            else:
                                                print(f"    |   [WARN] No critical remarks generated for CNL '{cnl_id}'", file=sys.stderr)
                                        else:
                                            print(f"    |   [WARN] No CNL XML found for '{cnl_id}'", file=sys.stderr)

                                    # Add wrapper with all collected annots to notesStmt
                                    if len(wrapper_annot) > 0:
                                        notes_stmts[0].append(wrapper_annot)

                            component_list.append(component_expr_copy)
                            print(f"    |   [OK] Added component expression '{component_slug}' to componentList")
                        except Exception as e:
                            component_slug = component_expr.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES)[0] if component_expr.xpath('./mei:identifier[@type="subDiv"]/text()', namespaces=NAMESPACES) else "unknown"
                            print(f"    |   [WARN] Failed to add component expression '{component_slug}': {e}", file=sys.stderr)
            except Exception as e:
                print(f"    |   [WARN] Failed to process component expressions: {e}", file=sys.stderr)

        works_by_sub_div.setdefault(sub_div, []).append(work_element)

    for output_sub_div, collected_work_elements in works_by_sub_div.items():
        print(f"    +-- Writing final works.xml for '{output_sub_div}' ({len(collected_work_elements)} work(s))")
        if _assemble_works_xml(collected_work_elements, output_sub_div, edition_name, vol_slug):
            print(f"    |   [OK] works.xml created")
        else:
            print(f"    |   [FAIL] Failed to assemble works.xml for {output_sub_div}", file=sys.stderr)

    print(f"    [OK] Step 3 complete")
    return True

def _build_work_element_from_component(component_expr: etree._Element, component_slug: str, work_type: str, first_level_work: etree._Element) -> etree._Element:
    """ 
    Helper: Build a work element from a component expression (e.g., full-score, short-score).
    Component expressions are sub-expressions in a componentList, each with their own CNL files in subdirectories.
    """
    
    work_template_path = (LOCAL_PATHS['templates'] / 'template_work.xml').resolve()
    
    try:
        # Create work element from template
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(work_template_path, parser)
        work_element = tree.getroot()
        
        # Set attributes for component work
        component_id = component_expr.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        component_title_list = component_expr.xpath('./mei:title/text()', namespaces=NAMESPACES)
        component_title = component_title_list[0] if component_title_list else component_slug
        
        work_element.set('{%s}id' % NAMESPACES['xml'], component_id)
        work_element.set('n', '1')
        
        # Set title for component work
        title_elems = work_element.xpath('./mei:title', namespaces=NAMESPACES)
        if title_elems:
            title_elems[0].text = component_title
        
        # Set title for component expression
        expression_list = work_element.xpath('./mei:expressionList', namespaces=NAMESPACES)
        expression = expression_list[0].xpath('./mei:expression', namespaces=NAMESPACES) if expression_list else []
        if expression:
            # Remove expression title element if present
            expr_title = expression[0].xpath('./mei:title', namespaces=NAMESPACES)
            if expr_title:
                expression[0].remove(expr_title[0])
        
        # Add critical remarks for component expression
        component_expr_id = component_expr.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        cnl_id = _get_rel_by_id(first_level_work, component_expr_id, type='cnl')
        cnl_xml = _get_rel_xml(cnl_id, subdirectory=component_slug, type='cnl') if cnl_id else None
        
        notes_stmts = work_element.xpath('.//mei:notesStmt')
        if notes_stmts:
            if cnl_xml is not None:
                critical_remarks_str = build_critical_remarks(etree.tostring(cnl_xml, encoding='unicode'), LOCAL_PATHS['sources'], component_slug, vol_slug)
                if critical_remarks_str:
                    try:
                        parser = etree.XMLParser(remove_blank_text=True)
                        cr_elem = etree.fromstring(critical_remarks_str.encode('utf-8'), parser)
                        notes_stmts[0].append(cr_elem)
                    except Exception as cr_e:
                        print(f"    |   |   [WARN] Could not parse critical remarks: {cr_e}", file=sys.stderr)
                        empty_annot = etree.Element('annot')
                        notes_stmts[0].append(empty_annot)
                else:
                    empty_annot = etree.Element('annot')
                    notes_stmts[0].append(empty_annot)
            else:
                print(f"    |   |   [WARN] [W14] No critical remarks file reference found for {component_slug}", file=sys.stderr)
                empty_annot = etree.Element('annot')
                notes_stmts[0].append(empty_annot)
        
        return work_element
        
    except Exception as e:
        print(f"    |   |   [WARN] Failed to build work element for component: {e}", file=sys.stderr)
        return None

def _build_work_element_with_components(first_level_work: etree._Element, sub_div: str, work_type: str, edition_name: str, vol_slug: str) -> etree._Element:
    """ 
    Helper: Build a single work element with nested components if it's a collection.
    For collections: Creates a first-level work with a componentList containing second-level works.
    For singletons: Creates a single work element.
    """
    
    work_template_path = (LOCAL_PATHS['templates'] / 'template_work.xml').resolve()
    
    try:
        # Create or copy template for first-level work
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(work_template_path, parser)
        work_element = tree.getroot()
        
        # Set attributes for first-level work
        work_id = first_level_work.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        # Try to get title with type="main", fall back to any title
        work_title_list = first_level_work.xpath('./mei:title[@type="main"]/text()', namespaces=NAMESPACES)
        if not work_title_list:
            work_title_list = first_level_work.xpath('./mei:title/text()', namespaces=NAMESPACES)
        work_title = work_title_list[0] if work_title_list else 'Untitled'
        
        work_element.set('{%s}id' % NAMESPACES['xml'], work_id)
        work_element.set('n', '1')
        
        # Set title for first-level work
        title_elems = work_element.xpath('./mei:title', namespaces=NAMESPACES)
        if title_elems:
            title_elems[0].text = work_title
            print(f"    |   [OK] Set work title: {work_title}")
        
        # Get main expression from first_level_work to copy its metadata
        main_expression_source = first_level_work.xpath('./mei:expressionList/mei:expression', namespaces=NAMESPACES)[0] if first_level_work.xpath('./mei:expressionList/mei:expression', namespaces=NAMESPACES) else None
        
        # Add termLists to expression
        expression_list = work_element.xpath('./mei:expressionList', namespaces=NAMESPACES)
        expression = expression_list[0].xpath('./mei:expression', namespaces=NAMESPACES) if expression_list else []
        if len(expression) > 0 and main_expression_source is not None:
            # Set expression title from source
            expr_title_elems = expression[0].xpath('./mei:title', namespaces=NAMESPACES)
            expr_title_source = main_expression_source.xpath('./mei:title/text()', namespaces=NAMESPACES)
            if expr_title_elems and expr_title_source:
                expr_title_elems[0].text = expr_title_source[0]
                print(f"    |   [OK] Set expression title: {expr_title_source[0]}")
            else:
                # If title doesn't exist in source, still try to set empty/create one
                if expr_title_elems and not expr_title_source:
                    pass  # Leave empty or could remove
                elif not expr_title_elems:
                    # Create title element if missing
                    title_elem = etree.Element('{%s}title' % NAMESPACES['mei'])
                    if expr_title_source:
                        title_elem.text = expr_title_source[0]
                    expression[0].insert(0, title_elem)
        
        # For collections: Add componentList with second-level works
        if work_type == 'collection':
            second_level_works = get_second_level_works(first_level_work)
            
            # Create componentList element
            component_list = etree.Element('{%s}componentList' % NAMESPACES['mei'])
            
            for counter, second_level_work in enumerate(second_level_works, 1):
                # Parse template for each second-level work
                tree_component = etree.parse(work_template_path)
                component_element = tree_component.getroot()
                
                # Set component attributes
                component_id = second_level_work.xpath('./@xml:id', namespaces=NAMESPACES)[0]
                component_title_list = second_level_work.xpath('./mei:title/text()', namespaces=NAMESPACES)
                component_title = component_title_list[0] if component_title_list else 'Untitled'
                
                component_element.set('{%s}id' % NAMESPACES['xml'], component_id)
                component_element.set('n', str(counter))
                
                # Set component title
                component_title_elems = component_element.xpath('./mei:title', namespaces=NAMESPACES)
                if component_title_elems:
                    component_title_elems[0].text = component_title
                
                # Remove expressionList from component works
                component_expression_list = component_element.xpath('./mei:expressionList', namespaces=NAMESPACES)
                if component_expression_list:
                    component_element.remove(component_expression_list[0])
                
                # Add critical remarks to component notesStmt
                second_level_work_expression_id = second_level_work.xpath('./mei:expressionList/mei:expression/@xml:id', namespaces=NAMESPACES)[0] if second_level_work.xpath('./mei:expressionList/mei:expression/@xml:id', namespaces=NAMESPACES) else None
                cnl_id = _get_rel_by_id(first_level_work, second_level_work_expression_id, type='cnl') if second_level_work_expression_id else None
                cnl_xml = _get_rel_xml(cnl_id, type='cnl') if cnl_id else None
                
                component_notes_stmts = component_element.xpath('.//mei:notesStmt', namespaces=NAMESPACES)
                if component_notes_stmts:
                    if cnl_xml is not None:
                        critical_remarks_str = build_critical_remarks(etree.tostring(cnl_xml, encoding='unicode'), LOCAL_PATHS['sources'], sub_div, vol_slug)
                        if critical_remarks_str:
                            try:
                                # Parse with proper namespace handling
                                parser = etree.XMLParser(remove_blank_text=True)
                                cr_elem = etree.fromstring(critical_remarks_str.encode('utf-8'), parser)
                                component_notes_stmts[0].append(cr_elem)
                            except Exception as cr_e:
                                print(f"    |   [WARN] Could not parse critical remarks: {cr_e}", file=sys.stderr)
                                empty_annot = etree.Element('annot')
                                component_notes_stmts[0].append(empty_annot)
                        else:
                            empty_annot = etree.Element('annot')
                            component_notes_stmts[0].append(empty_annot)
                    else:
                        print(f"    |   |   [WARN] [W14] No critical remarks file reference found for {component_id}", file=sys.stderr)
                        empty_annot = etree.Element('annot')
                        component_notes_stmts[0].append(empty_annot)
                
                component_list.append(component_element)
                print(f"    |   Component element {counter}/{len(second_level_works)} created")
            
            # Add componentList to the first-level work
            work_element.append(component_list)
        
        else:  # singleton work
            # For singletons, add critical remarks directly to the first-level work
            expression_id = first_level_work.xpath('./mei:expressionList/mei:expression/@xml:id', namespaces=NAMESPACES)[0] if first_level_work.xpath('./mei:expressionList/mei:expression/@xml:id', namespaces=NAMESPACES) else None
            cnl_id = _get_rel_by_id(first_level_work, expression_id, type='cnl') if expression_id else None
            for id in cnl_id:
                cnl_xml = _get_rel_xml(id, type='cnl') if cnl_id else None
                notes_stmts = work_element.xpath('.//mei:notesStmt', namespaces=NAMESPACES)
                if notes_stmts:
                    if cnl_xml is not None:
                        critical_remarks_str = build_critical_remarks(etree.tostring(cnl_xml, encoding='unicode'), LOCAL_PATHS['sources'], sub_div, vol_slug)
                        if critical_remarks_str:
                            try:
                                # Parse with proper namespace handling
                                parser = etree.XMLParser(remove_blank_text=True)
                                cr_elem = etree.fromstring(critical_remarks_str.encode('utf-8'), parser)
                                cr_elem_list = cr_elem.findall('*')
                                for elem in cr_elem_list:
                                    notes_stmts[0].append(elem)
                            except Exception as cr_e:
                                print(f"    |   [WARN] Could not parse critical remarks: {cr_e}", file=sys.stderr)
                                empty_annot = etree.Element('annot')
                                notes_stmts[0].append(empty_annot)
                        else:
                            empty_annot = etree.Element('annot')
                            notes_stmts[0].append(empty_annot)
                    else:
                        print(f"    |   |   [WARN] [W14] No critical remarks file reference found for {work_id}", file=sys.stderr)
                        empty_annot = etree.Element('annot')
                        notes_stmts[0].append(empty_annot)
        
        return work_element
        
    except Exception as e:
        print(f"    |   [WARN] Failed to build work element: {e}", file=sys.stderr)
        return None

def _assemble_works_xml(work_elements: list, sub_div: str, edition_name: str, vol_slug: str) -> bool:
    """ Helper: Assemble final works.xml with work elements """
    try:
        edirom_works_template = (LOCAL_PATHS['templates'] / 'template_edirom-works.xml').resolve()
        tree = etree.parse(edirom_works_template)
        root = tree.getroot()
        
        workList = root.xpath('.//mei:workList', namespaces=NAMESPACES)
        if not workList:
            print(f"    |   [WARN] No workList in template", file=sys.stderr)
            return False
        
        # Fill in editionStmt with edition element
        edition_stmts = root.xpath('.//mei:editionStmt', namespaces=NAMESPACES)
        if edition_stmts:
            edition_elem = etree.Element('edition')
            edition_elem.text = edition_name
            # Clear existing content and add edition
            edition_stmts[0].clear()
            edition_stmts[0].append(edition_elem)
        
        # Add work elements to workList
        for work_element in work_elements:
            workList[0].append(work_element)
        
        # Clean up whitespace-only text nodes for proper formatting
        def remove_blank_text(element):
            """Recursively remove whitespace-only text nodes"""
            if element.text and element.text.strip() == '':
                element.text = None
            if element.tail and element.tail.strip() == '':
                element.tail = None
            for child in element:
                remove_blank_text(child)
        
        remove_blank_text(root)
        
        # Save file with proper formatting
        if sub_div:
            tmp_path = LOCAL_PATHS['_edirom'] / sub_div
        else:
            tmp_path = LOCAL_PATHS['_edirom']
        tmp_path.mkdir(parents=True, exist_ok=True)
        works_xml_path = tmp_path / f"{sub_div}_works.xml" if sub_div else tmp_path / f"works.xml"
        
        # Format XML with proper pretty-printing
        xml_str = etree.tostring(root, encoding='unicode', pretty_print=True)
        
        create_file(
            xml_str,
            works_xml_path,
            format_xml=True
        )
        return True
        
    except Exception as e:
        print(f"    |   [FAIL] Failed to assemble works.xml: {e}", file=sys.stderr)
        return False

def create_file(content: str, output_path: Path, format_xml: bool = False):
    """ Helper function to create output files """
    try:
        # Format XML if requested
        if format_xml and content.strip():
            # Check if content already has XML declaration
            has_declaration = content.strip().startswith('<?xml')
            
            # If it has a declaration, remove it temporarily for parsing
            if has_declaration:
                # Find the end of the declaration
                decl_end = content.find('?>') + 2
                declaration = content[:decl_end]
                content_without_decl = content[decl_end:].strip()
                tree = etree.fromstring(content_without_decl.encode('utf-8'))
                # Format without adding another declaration
                formatted = etree.tostring(tree, encoding='unicode', pretty_print=True)
                content = declaration + '\n' + formatted
            else:
                tree = etree.fromstring(content.encode('utf-8'))
                # Format and add declaration manually
                formatted = etree.tostring(tree, encoding='unicode', pretty_print=True)
                content = '<?xml version="1.0" encoding="UTF-8"?>\n' + formatted
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"    |   |   [OK] Saved: {output_path.name}")
    except Exception as e:
        print(f"    |   |   [FAIL] [E5] Failed to create file {output_path.name}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    print("=" * 70)
    print("Preparation of Edirom Content from frbr-tree.xml")
    print("=" * 70)

    first_level_works, edition_name, vol_slug = get_first_level_works_from_frbr(LOCAL_PATHS['frbr'])
    print(f"\nFound {len(first_level_works)} work(s) to process\n")

    # Prepare sources
    if prepare_sources(first_level_works, vol_slug):
        print(f"  [OK] READY: Edition prepared for next steps\n")
    else:
        print(f"  [FAIL] FAILED: Edition skipped due to dependency errors\n")
    
    # Build edirom file
    if build_edirom_file(first_level_works, edition_name, vol_slug):
        print(f"  [OK] READY: Edition prepared for next steps\n")
    else:
        print(f"  [FAIL] FAILED: Edition skipped due to dependency errors\n")

    # Build works file
    if build_works_file(first_level_works, edition_name, vol_slug):
        print(f"  [OK] READY: Edition prepared for next steps\n")
    else:
        print(f"  [FAIL] FAILED: Edition skipped due to dependency errors\n")

if __name__ == "__main__":
    main()