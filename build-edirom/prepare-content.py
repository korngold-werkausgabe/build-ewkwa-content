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
    result = None
    if search_type == 'by_id':
        parser = etree.XMLParser(resolve_entities=False)
        for file in path.glob(file_type):
            tree = etree.parse(file, parser)
            root = tree.getroot()
            # Check root element first
            root_id = root.xpath('./@xml:id', namespaces=NAMESPACES)
            if root_id and root_id[0] == search_string:
                return file.name  # ← Return filename, not Element
            else:
                nav = root.xpath('//*[@xml:id=$search_string]', namespaces=NAMESPACES, search_string=search_string)
                if nav:
                    return file.name  # ← Return filename, not Element
        return None
    elif search_type == 'by_filename':
        for file in path.glob(file_type):
            if search_string in file.name:
                result = file.name
    if result:
        return result
    else:
        print(f"    |   |   [WARN] [W2] No file with '{search_string}' in name found in {path}", file=sys.stderr)
        return None

def build_nav(nav_path, vol_slug: str, edition_slug: str) -> str:
    """ Call buildNav.xsl with volSlug and editionSlug parameters """
    try:
        build_nav_xsl = LOCAL_PATHS['scripts'] / 'buildNav.xsl'
        nav_path_abs = Path(nav_path).resolve()  # Absolut path
        
        result = subprocess.run([
            'xsltproc',
            '--stringparam', 'volSlug', vol_slug,
            '--stringparam', 'editionSlug', edition_slug,
            str(build_nav_xsl),
            str(nav_path_abs)
        ], capture_output=True, text=True, check=True)
        print(f"    |   |   [OK] buildNav.xsl processed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"    |   |   [FAIL] [E1] buildNav.xsl failed: {e.stderr}", file=sys.stderr)
        return None
    
def build_concordances(conc_json: str, groups_titles: list, sources_path: str, edition_slug: str, vol_slug: str) -> str:
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
            f'-b editionSlug={edition_slug}',
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
        edition_slug = work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]     # Create tmp directory for this edition
        tmp_path = LOCAL_PATHS['tmp'] / edition_slug
        tmp_path.mkdir(parents=True, exist_ok=True)
        # Create output directory for this edition
        output_path = LOCAL_PATHS['_edirom']
        output_path.mkdir(parents=True, exist_ok=True)
    
        # Step 1: Build Nav
        print(f"    |   +-- Step 1.1: Build Navigation ({edition_slug})")
        nav_file = get_nav(work)
        if not nav_file:
            print(f"    |   |   [WARN] [W4] No nav file found - using empty fallback", file=sys.stderr)
            nav_output = "<navigatorDefinition/>"
        else:
            nav_output = build_nav(LOCAL_PATHS['edirom-config'] / nav_file, vol_slug, edition_slug)
            if not nav_output:
                print(f"    |   |   [WARN] [W4b] build_nav failed - using empty fallback", file=sys.stderr)
                nav_output = "<navigatorDefinition/>"
        
        # Save nav output to tmp file
        nav_path = tmp_path / f"{edition_slug}_nav.xml"
        create_file(nav_output, nav_path, format_xml=True)
        print(f"    |   |   [OK] Navigation complete")
        
        # Step 2: Build Concordances
        print(f"    |   +-- Step 1.2: Build Concordances ({edition_slug})")
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
            
            concordance_output = build_concordances(conc_files, groups_titles, f"{LOCAL_PATHS['_edirom']}/{edition_slug}/sources", edition_slug, vol_slug)
            if not concordance_output:
                print(f"    |   |   [WARN] [W5b] build_concordances failed - using empty fallback", file=sys.stderr)
                concordance_output = "<concordances/>"
            
            # Save concordance output to tmp file
            conc_path = tmp_path / f"{edition_slug}_concordance.xml"
            create_file(concordance_output, conc_path, format_xml=True)
            print(f"    |   |   [OK] Concordance complete")

        # Build work element in edirom namespace (outside if/else to ensure always created)
        work_xml_id = work.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        work_element = etree.Element(
            '{%s}work' % NAMESPACES['edirom'], 
            attrib={
                '{%s}id' % NAMESPACES['xml']: work_xml_id, 
                'sortNo': str(xid + 1),
                '{%s}href' % NAMESPACES['xlink']: f"xmldb:exist:///db/apps/edirom-content/{vol_slug}/{edition_slug}/{edition_slug}_works.xml"
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

        result = subprocess.run([
            'xsltproc',
            '--stringparam', 'editionId', edition_id,
            '--stringparam', 'editionName', edition_name,
            '--stringparam', 'editionPrefsPath', f"{vol_slug}/{edition_slug}",
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
    
def prepare_sources(first_level_works: list) -> bool:
    """ Prepare source files for Edirom edition """

    print(f"+-- Step 2: Prepare Source Files")
    
    for work in first_level_works:
        work_type = work.xpath('./@type', namespaces=NAMESPACES)[0]
        edition_slug = work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]

        print(f"    +-- Processing sources for '{edition_slug}'")
        
        # Collect all search strings from sub-works
        search_strings = []
        if work_type == 'collection':
            for sub_work in get_second_level_works(work):
                search_string = sub_work.xpath('./mei:expressionList/mei:expression/mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
                search_strings.append(search_string)
        else:
            search_strings = [edition_slug]
        
        # Process each search string to find and process its kb_sources file
        for search_string in search_strings:
            kb_sources_files = list(LOCAL_PATHS['kbSources'].glob('kb_sources*.xml'))
            kb_sources_paths = []
            
            for kb_file in kb_sources_files:
                if search_string == "":
                    kb_sources_paths.append(LOCAL_PATHS['kbSources'] / kb_file.name)
                    break
                elif search_string in kb_file.name:
                    kb_sources_paths.append(LOCAL_PATHS['kbSources'] / kb_file.name)
                    break
            
            # Fallback: if no matching file found, use default kb_sources.xml for singletons
            if not kb_sources_paths and work_type != 'collection':
                default_kb_sources = LOCAL_PATHS['kbSources'] / 'kb_sources.xml'
                if default_kb_sources.exists():
                    kb_sources_paths.append(default_kb_sources)
            
            if not kb_sources_paths:
                print(f"    |   [WARN] [W7] No kb_sources file found for '{search_string}' in {LOCAL_PATHS['kbSources']}", file=sys.stderr)
                continue
            
            for kb_file in kb_sources_paths:
                kb_file_parsed = etree.parse(kb_file)
                kb_file_root = kb_file_parsed.getroot()
                sources = kb_file_root.xpath('//source', namespaces=NAMESPACES)
                
                for source in sources:
                    source_file_id = source.xpath('./@target', namespaces=NAMESPACES)[0] if source.xpath('./@target', namespaces=NAMESPACES) else source.xpath('./@xml:id', namespaces=NAMESPACES)[0]
                    source_title = source.xpath('./shortTitle/text()', namespaces=NAMESPACES)[0] if source.xpath('./shortTitle/text()', namespaces=NAMESPACES) else "No title found"
                    source_siglum = source.xpath('./siglum/text()', namespaces=NAMESPACES)[0] if source.xpath('./siglum/text()', namespaces=NAMESPACES) else "Siglum not found"
                    source_file = get_related_file(source_file_id, LOCAL_PATHS['sources'], '*.xml', 'by_id')
                    
                    if not source_file:
                        print(f"    |   [WARN] [W8] Source file not found for '{source_file_id}' - skipping", file=sys.stderr)
                        continue
                    
                    try:
                        print(f"    +-- Step 2.2: Prepare and copy source file")
                        prepare_sources_xsl = LOCAL_PATHS['scripts'] / 'prepareSources.xsl'
                        source_file = (LOCAL_PATHS['sources'] / source_file).resolve()

                        result = subprocess.run([
                            'xsltproc',
                            '--stringparam', 'title', source_title,
                            '--stringparam', 'siglum', source_siglum,
                            str(prepare_sources_xsl),
                            str(source_file),
                        ], capture_output=True, text=True, check=True)
                        print(f"    |   |   [OK] prepareSources.xsl processed")
                        # Save - xsltproc already outputs formatted XML with declaration
                        # Use original filename instead of source_file_id
                        original_filename = source_file.name
                        source_output_path = LOCAL_PATHS['_edirom'] / edition_slug / "sources" / original_filename
                        source_output_path.parent.mkdir(parents=True, exist_ok=True)
                        create_file(result.stdout, source_output_path, format_xml=True)
                    except subprocess.CalledProcessError as e:
                        print(f"    |   |   [FAIL] [E1] prepareSources.xsl failed: {e.stderr}", file=sys.stderr)
                        continue
    
    print(f"    |   [OK] Source files complete")
    return True
    return True

def build_critical_remarks(cnl_xml: str, sources_path: str, edition_slug: str, vol_slug: str) -> str:
    """ Call buildEdiromTkAs.xql to build critical remarks (annots) """   
    try:
        build_tk_as_xql = LOCAL_PATHS['scripts'] / 'buildEdiromTkAs.xql'
        sources_path_abs = Path(sources_path).resolve()
        collection_path_abs = (LOCAL_PATHS['tmp'] / edition_slug).resolve()
        
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
                f'-b editionHandle={edition_slug}',
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

def _get_cnl_id(first_level_work: etree._Element, expression_id: str) -> list:
    """ Extract ALL cnl_ids from first_level_work's relationList """
    cnl_ids = []
    rel_has_part = first_level_work.xpath(f'./mei:relationList/mei:relation[@rel="hasPart" and @target="#{expression_id}"]/@plist', namespaces=NAMESPACES)
    
    for plist in rel_has_part:
        for id_item in plist.split():
            id_clean = id_item.lstrip('#')
            if 'cnl' in id_clean:
                cnl_ids.append(id_clean)
    
    return cnl_ids

def _get_cnl_xml(cnl_id: str, subdirectory: str = None) -> etree._Element:
    """ 
    Get cnList element from criticalRemarks by cnl_id.
    If subdirectory is provided, search in criticalRemarks/subdirectory/ first.
    """
    try:
        cnl_file = None
        search_paths = []
        
        # If subdirectory is provided, search there first
        if subdirectory:
            subdir_path = LOCAL_PATHS['criticalRemarks'] / subdirectory
            if subdir_path.exists():
                search_paths.append(subdir_path)
        
        # Also search in root criticalRemarks directory
        search_paths.append(LOCAL_PATHS['criticalRemarks'])
        
        # Search for file in paths
        for search_path in search_paths:
            cnl_file = get_related_file(cnl_id, search_path, '*.xml', 'by_id')
            if cnl_file:
                tree = etree.parse(search_path / cnl_file, parser=etree.XMLParser(resolve_entities=False))
                root = tree.getroot()
                cnList = root.xpath(f'//*[@xml:id="{cnl_id}"]', namespaces=NAMESPACES)
                if cnList:
                    return cnList[0]
        
        # If we get here, file not found
        if subdirectory:
            print(f"    |   [WARN] [W9] No critical remarks found for cnl_id '{cnl_id}' in {LOCAL_PATHS['criticalRemarks']}/{subdirectory} or root", file=sys.stderr)
        else:
            print(f"    |   [WARN] [W9] No critical remarks found for cnl_id '{cnl_id}'", file=sys.stderr)
        return None
        
    except Exception as e:
        print(f"    |   [FAIL] Failed to parse cnl file: {e}", file=sys.stderr)
        return None

def build_works_file(first_level_works: list, edition_name: str, vol_slug: str) -> bool:
    """ Build works.xml file for each first-level work (one file per work, with possible multiple expressions) """
    print(f"+-- Step 3: Build Works Files")
    
    for first_level_work in first_level_works:
        # Get the main expression
        main_expression = first_level_work.xpath('./mei:expressionList/mei:expression', namespaces=NAMESPACES)[0]
        edition_slug = main_expression.xpath('./mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0]
        work_type = first_level_work.xpath('./@type', namespaces=NAMESPACES)[0]
        
        print(f"    +-- Building works.xml for '{edition_slug}' ({work_type})")
        
        # Build single work element with main expression
        work_element = _build_work_element_with_components(first_level_work, edition_slug, work_type, edition_name, vol_slug)
        if work_element is None:
            print(f"    |   [WARN] No work element created for {edition_slug}", file=sys.stderr)
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
                            component_slug = component_expr_copy.xpath('./mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0] if component_expr_copy.xpath('./mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES) else "unknown"
                            component_expr_id = component_expr_copy.xpath('./@xml:id', namespaces=NAMESPACES)[0] if component_expr_copy.xpath('./@xml:id', namespaces=NAMESPACES) else None
                            
                            # Add notesStmt with critical remarks to component expression
                            if component_expr_id:
                                cnl_ids = _get_cnl_id(first_level_work, component_expr_id)
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
                                        cnl_xml = _get_cnl_xml(cnl_id, subdirectory=component_slug)
                                        if cnl_xml is not None:
                                            critical_remarks_str = build_critical_remarks(etree.tostring(cnl_xml, encoding='unicode'), LOCAL_PATHS['sources'], edition_slug, vol_slug)
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
                            component_slug = component_expr.xpath('./mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES)[0] if component_expr.xpath('./mei:identifier[@type="editionSlug"]/text()', namespaces=NAMESPACES) else "unknown"
                            print(f"    |   [WARN] Failed to add component expression '{component_slug}': {e}", file=sys.stderr)
            except Exception as e:
                print(f"    |   [WARN] Failed to process component expressions: {e}", file=sys.stderr)
        
        # Assemble final works.xml with the single work element (containing main + components in componentList)
        if _assemble_works_xml([work_element], edition_slug, edition_name):
            print(f"    |   [OK] works.xml created")
        else:
            print(f"    |   [FAIL] Failed to assemble works.xml for {edition_slug}", file=sys.stderr)
            continue
    
    print(f"    [OK] Step 3 complete")
    return True

def _build_work_element_from_component(component_expr: etree._Element, component_slug: str, work_type: str, first_level_work: etree._Element) -> etree._Element:
    """ 
    Helper: Build a work element from a component expression (e.g., full-score, short-score).
    Component expressions are sub-expressions in a componentList, each with their own CNL files in subdirectories.
    """
    termList_elements = _get_termlists()
    
    if not termList_elements:
        print(f"    |   |   [WARN] No termList elements found - expressions won't have classifications", file=sys.stderr)
        return None
    
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
        
        # Add termLists to expression
        expression_list = work_element.xpath('./mei:expressionList', namespaces=NAMESPACES)
        expression = expression_list[0].xpath('./mei:expression', namespaces=NAMESPACES) if expression_list else []
        if expression:
            # Remove expression title element if present
            expr_title = expression[0].xpath('./mei:title', namespaces=NAMESPACES)
            if expr_title:
                expression[0].remove(expr_title[0])
            
            # Replace classification element with termLists
            classification = expression[0].xpath('./mei:classification', namespaces=NAMESPACES)
            if classification:
                expression[0].remove(classification[0])
                if termList_elements:
                    for termList in termList_elements:
                        try:
                            expression[0].append(deepcopy(termList))
                        except Exception as tl_e:
                            print(f"    |   |   [WARN] [W15] Failed to append termList: {tl_e}", file=sys.stderr)
                            continue
        
        # Add critical remarks for component expression
        component_expr_id = component_expr.xpath('./@xml:id', namespaces=NAMESPACES)[0]
        cnl_id = _get_cnl_id(first_level_work, component_expr_id)
        cnl_xml = _get_cnl_xml(cnl_id, subdirectory=component_slug) if cnl_id else None
        
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

def _build_work_element_with_components(first_level_work: etree._Element, edition_slug: str, work_type: str, edition_name: str, vol_slug: str) -> etree._Element:
    """ 
    Helper: Build a single work element with nested components if it's a collection.
    For collections: Creates a first-level work with a componentList containing second-level works.
    For singletons: Creates a single work element.
    """
    termList_elements = _get_termlists()
    
    if not termList_elements:
        print(f"    |   [WARN] No termList elements found - expressions won't have classifications", file=sys.stderr)
        return None
    
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
            
            # Replace classification element with termLists
            classification = expression[0].xpath('./mei:classification', namespaces=NAMESPACES)
            if classification:
                expression[0].remove(classification[0])
                # Add termLists after title
                if termList_elements:
                    insert_index = 1 if expr_title_elems else 0
                    for i, termList in enumerate(termList_elements):
                        try:
                            expression[0].insert(insert_index + i, deepcopy(termList))
                            print(f"    |   [OK] Added termList to expression")
                        except Exception as tl_e:
                            print(f"    |   [WARN] [W15] Failed to append termList: {tl_e}", file=sys.stderr)
                            continue
        
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
                cnl_id = _get_cnl_id(first_level_work, second_level_work_expression_id) if second_level_work_expression_id else None
                cnl_xml = _get_cnl_xml(cnl_id) if cnl_id else None
                
                component_notes_stmts = component_element.xpath('.//mei:notesStmt', namespaces=NAMESPACES)
                if component_notes_stmts:
                    if cnl_xml is not None:
                        critical_remarks_str = build_critical_remarks(etree.tostring(cnl_xml, encoding='unicode'), LOCAL_PATHS['sources'], edition_slug, vol_slug)
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
            cnl_id = _get_cnl_id(first_level_work, expression_id) if expression_id else None
            cnl_xml = _get_cnl_xml(cnl_id) if cnl_id else None
            
            notes_stmts = work_element.xpath('.//mei:notesStmt', namespaces=NAMESPACES)
            if notes_stmts:
                if cnl_xml is not None:
                    critical_remarks_str = build_critical_remarks(etree.tostring(cnl_xml, encoding='unicode'), LOCAL_PATHS['sources'], edition_slug, vol_slug)
                    if critical_remarks_str:
                        try:
                            # Parse with proper namespace handling
                            parser = etree.XMLParser(remove_blank_text=True)
                            cr_elem = etree.fromstring(critical_remarks_str.encode('utf-8'), parser)
                            notes_stmts[0].append(cr_elem)
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

def _get_termlists() -> list:
    """ Helper: Get termList elements from template """
    try:
        termList_template_path = (LOCAL_PATHS['templates'] / 'template_termList.xml').resolve()
        tree = etree.parse(termList_template_path)
        root = tree.getroot()
        # termList elements have no namespace (not in MEI namespace)
        termList_elements = root.xpath('.//termList')
        if not termList_elements:
            print(f"    |   [WARN] No termList elements found in template", file=sys.stderr)
        return termList_elements
    except Exception as e:
        print(f"    |   [FAIL] Failed to parse termList template: {e}", file=sys.stderr)
        return []

def _assemble_works_xml(work_elements: list, edition_slug: str, edition_name: str) -> bool:
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
        tmp_path = LOCAL_PATHS['_edirom'] / edition_slug
        tmp_path.mkdir(parents=True, exist_ok=True)
        works_xml_path = tmp_path / f"{edition_slug}_works.xml"
        
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
    if prepare_sources(first_level_works):
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