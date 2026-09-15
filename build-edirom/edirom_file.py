import sys
from pathlib import Path
import subprocess
from lxml import etree

### MODULE IMPORTS ###
import global_variables as vars
import utils
def _build_nav(nav_id: str, vol_slug: str, sub_div: str) -> etree.Element:
    tmp_path = vars.LOCAL_PATHS['tmp'] / sub_div if sub_div != "" else vars.LOCAL_PATHS['tmp']
    tmp_path.mkdir(parents=True, exist_ok=True)

    nav_file = utils._get_file(
        vars.LOCAL_PATHS['edirom-config'],
        nav_id,
        search_type='by_id',
        return_full_path=True
    )

    if not nav_file or nav_file == Path('') or not nav_file.exists():
        print(f"\t[WARN] No nav file found - using empty fallback", file=sys.stderr)
    else:
        try:
            nav_path_abs = Path(nav_file).resolve()
            result = subprocess.run([
                'xsltproc',
                '--stringparam', 'volSlug', vol_slug,
                '--stringparam', 'subDiv', sub_div,
                str(vars.SCRIPTS['build_nav']),
                str(nav_path_abs)
            ], capture_output=True, text=True, check=True)
            print(f"\t[OK] buildNav.xsl processed")
            nav_output = etree.fromstring(result.stdout)
        except FileNotFoundError:
            print(f"\t[WARN] xsltproc not found - using empty fallback", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"\t[FAIL] buildNav.xsl failed: {e.stderr}", file=sys.stderr)

    """ nav_path = tmp_path / f"{sub_div}_nav.xml" if sub_div != "" else tmp_path / "nav.xml"
    utils._create_file(nav_output, nav_path, format_xml=True) """
    print(f"\t[OK] Navigation complete")
    return nav_output

def build_concordances(conc_ids: list, sub_div: str, vol_slug: str) -> etree.Element:
    """ Call buildConnectionsByXML.xql with concordance JSON and sources using basex """
    tmp_path = vars.LOCAL_PATHS['tmp'] / sub_div if sub_div != "" else vars.LOCAL_PATHS['tmp']
    tmp_path.mkdir(parents=True, exist_ok=True)
    try:
        conc_path = Path(vars.LOCAL_PATHS["conc"]).resolve().as_uri()
        result = subprocess.run([
            'basex',
            f'-b concIds={",".join(conc_ids)}',
            f'-b concPath={conc_path}',
            f'-b subDiv={sub_div}',
            f'-b volSlug={vol_slug}',
            f'-b propertiesPath={Path("properties.xml").resolve()}',
            str(vars.SCRIPTS['build_conc'])
        ], capture_output=True, text=True, check=True)
        conc_output = result.stdout
        print(f"\t[OK] buildConnectionsByXML.xql processed")
        conc_path = tmp_path / f"{sub_div}_nav.xml" if sub_div != "" else tmp_path / "conc.xml"
        utils._create_file(result.stdout, conc_path, format_xml=True)
    except FileNotFoundError:
        print(f"\t[WARN] basex not found - using empty fallback", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"\t[FAIL] buildConnectionsByXML.xql failed: {e.stderr}", file=sys.stderr)

    """ conc_path = tmp_path / f"{sub_div}_conc.xml" if sub_div != "" else tmp_path / "conc.xml"
    utils._create_file(conc_output, conc_path, format_xml=True) """
    print(f"\t[OK] Navigation complete")
    return conc_output

def build_edirom(frbr_json: dict):
    edition_name = frbr_json['edition_name']
    vol_slug = frbr_json['vol_slug']

    works_wrapper = etree.Element('{%s}works' % vars.NAMESPACES['edirom'], nsmap={None: vars.NAMESPACES['edirom']})
    
    for xid, work in enumerate(frbr_json['work_list']):

        sub_div = ""
        if work["type"] == "collection":
            sub_div = work["expression_list"][0]["edition_slug"]
            

        relation_list = work.get('relation_list', [])
        
        if not relation_list:
            continue

        for relation in relation_list:
            targets = relation['targets'].split(' ')
            targets = [t.strip('#') for t in targets]
            for target in targets:
                if relation['rel'] == 'hasPart' and target == work['expression_list'][0]['id']:
                    ## NAV ##
                    nav_id = utils._get_matching_entry(relation['plist'], 'nav')

                    if nav_id != '':
                        print(f"\t[INFO] Found nav_id: {nav_id}")
                        nav_id = nav_id.strip('#')
                        nav_output = _build_nav(nav_id, sub_div,  work['expression_list'][0]['edition_slug'])

                    ## CONC ##
                    conc_ids = []
                    conc_ids.append(utils._get_matching_entry(relation['plist'], 'conc'))
                    if len(conc_ids) > 0:
                        print(f"\t[INFO] Found conc_ids: {conc_ids}")
                        conc_ids = [c.strip('#') for c in conc_ids if c]
                        conc_output = build_concordances(conc_ids, sub_div, work['expression_list'][0]['edition_slug'])


        # Build edirom work element
        href = (f"xmldb:exist:///db/apps/edirom-content/{vol_slug}/{sub_div}/{sub_div}_works.xml"
                        if sub_div != "" else
                        f"xmldb:exist:///db/apps/edirom-content/{vol_slug}/works.xml")
        work_element = etree.Element(
                    '{%s}work' % vars.NAMESPACES['edirom'], 
                    attrib={
                        '{%s}id' % vars.NAMESPACES['xml']: work["id"],
                        'sortNo': str(xid + 1),
                        '{%s}href' % vars.NAMESPACES['xlink']: href,
                    },
                    nsmap={'xlink': vars.NAMESPACES['xlink']}  
        )
        work_element.append(nav_output)
        
        work_element.append(etree.Element('{%s}searchWindowConfig' % vars.NAMESPACES['edirom']))
        concordances_element = etree.Element('{%s}concordances' % vars.NAMESPACES['edirom'])
        
        conc_element = etree.fromstring(conc_output)
        concordances_element.append(conc_element)
        
        work_element.append(concordances_element)
        works_wrapper.append(work_element)

    works_file_path = vars.LOCAL_PATHS['tmp'] / "works_tmp.xml"
    utils._create_file(etree.tostring(works_wrapper, encoding='unicode', pretty_print=True), works_file_path)

    # Step 3: Build Edirom File
    try:
        print(f"    +-- Step 1.3: Create Edirom File")
        build_edirom_file_xsl = vars.SCRIPTS['build_edirom_file']
        edirom_file_template_path = vars.TEMPLATES['template_edirom_file'].resolve()
        edition_prefs_path = f"{vol_slug}/{sub_div}" if sub_div != "" else f"{vol_slug}"

        result = subprocess.run([
            'xsltproc',
            '--stringparam', 'editionId', f"ewk_{vol_slug}",
            '--stringparam', 'editionName', edition_name,
            '--stringparam', 'editionPrefsPath', edition_prefs_path,
            '--stringparam', 'editionWorksPath', str(works_file_path.resolve()),
            str(build_edirom_file_xsl),
            str(edirom_file_template_path),
        ], capture_output=True, text=True, check=True)
        print(f"    |   |   [OK] buildEdiromFile.xsl processed")
        # Save - xsltproc already outputs formatted XML with declaration
        utils._create_file(result.stdout, vars.LOCAL_PATHS["_edirom"] / "edition.xml", format_xml=True)
        
    except subprocess.CalledProcessError as e:
        print(f"    |   |   [FAIL] [E1] buildEdiromFile.xsl failed: {e.stderr}", file=sys.stderr)
