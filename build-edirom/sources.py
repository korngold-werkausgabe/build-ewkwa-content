import global_variables as vars
import utils
from lxml import etree
import subprocess
import tempfile
from pathlib import Path
import os

### MODULE IMPORTS ###
from parse_frbr import _return_manifestation_xml_by_id

def _generate_source_maps(manifestation_list: dict) -> list:
    """
    Prepares the sources for processing.
    [
        {
            'manifestation_id': 'manifestation_id in frbr-tree',
            'source_id': 'source_id in kb_sources',
            'source_title': 'source title in kb_sources'
        }
    ]
    """
    source_maps = []
    for manifestation in manifestation_list:
        # Determine items to process: manifestation itself if singleton, else item_list
        items_to_process = [manifestation] if manifestation['singleton'] == 'true' else manifestation.get('item_list', [])
        
        for item in items_to_process:
            source_ids = item['targets'].strip('#').split(' ')
            
            if len(source_ids) < 1:
                print(f"\t[WARN] No source IDs found for {item['id']} in frbr-tree.xml.")
            
            for source_id in source_ids:
                for source_id in source_ids:
                    try:
                        source_title, source_sigle, targets = _get_source_info(source_id)
                        source_title, source_sigle, targets = _get_source_info(source_id)
                        source_maps.append({
                            'source_id': source_id,
                            'source_title': source_title,
                            'source_sigle': source_sigle,
                            'manifestation_id': manifestation['id'],
                            'targets': targets
                        })
                    except ValueError as e:
                        print(f"\t[WARN] Invalid source metadata for '{source_id}': {e}. Skipping.")
                        continue

                    if not source_title:
                        continue
                
    
    return source_maps

def _get_source_info(source_id: str) -> tuple:
    source_xml = utils._get_xml_by_id(vars.LOCAL_PATHS['kbSources'], source_id)
    if source_xml is None:
        print(f"\t[WARN] Source ID \"{source_id}\" not found in kb_sources.xml.")
        return '', '', []

    source_title = source_xml.xpath('./shortTitle/text()')[0] if source_xml.xpath('./shortTitle/text()') else ''
    source_sigle = source_xml.xpath('./siglum/text()')[0] if source_xml.xpath('./siglum/text()') else ''
    tmp_targets = source_xml.xpath('./@targets') if source_xml.xpath('./@targets') else []
    if len(tmp_targets) < 1:
        targets = []
        print(f"\t[WARN] No targets found for {source_id} in kb_sources.xml.")
    else:
        targets = tmp_targets[0].strip('#').split(' ')

    return source_title, source_sigle, targets

def prepare_sources(manifestation_list: dict) -> list:
    source_maps = _generate_source_maps(manifestation_list)

    for entry in source_maps:
        for target in entry['targets']:
            if target == "":
                print(f"\t[WARN] Empty target found for source {entry['source_id']}.")
                continue

            print(f"\t[INFO] Processing target: {target}")
            source_file = utils._get_file(
                vars.LOCAL_PATHS['sources'],
                target,
                search_type='by_id',
                return_full_path=True
            )

            if not source_file or source_file == Path('') or not source_file.exists():
                print(f"\t[WARN] No source file found for target '{target}'. Skipping.")
                continue

            try:
                manifestation_xml = _return_manifestation_xml_by_id(entry['manifestation_id'])
                if manifestation_xml is None:
                    print(f"\t[WARN] No manifestation found for {entry['manifestation_id']}. Skipping.")
                    continue

                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp:
                    tmp.write(etree.tostring(manifestation_xml, encoding='unicode', pretty_print=True))
                    manifestation_file = tmp.name

                result = subprocess.run([
                    'xsltproc',
                    '--stringparam', 'title', entry['source_title'],
                    '--stringparam', 'sigle', entry['source_sigle'],
                    '--param', 'manifestationFile', f"'file://{manifestation_file}'",
                    str(vars.SCRIPTS['prepare_sources']),
                    str(source_file),
                ], capture_output=True, text=True, check=True)

            except subprocess.CalledProcessError as e:
                print(f"\t[ERROR] Source transformation failed: {e.stderr}")
            except FileNotFoundError:
                print(f"\t[WARN] xsltproc not found. Skipping.")
            finally:
                try:
                    os.unlink(manifestation_file)
                except Exception:
                    pass

        return source_maps
                