from lxml import etree
from pathlib import Path
import sys

### MODULE IMPORTS ###
import global_variables as vars

def _get_matching_entry(plist: list, substring: str) -> str:
    return next((item for item in plist if substring in item), '')


def _get_xml_by_id(folder_path: Path, element_id: str) -> etree._Element:
    try:
        parser = etree.XMLParser(resolve_entities=False)
        for file in folder_path.rglob('*.xml'):
            tree = etree.parse(file, parser)
            root = tree.getroot()
            # Check root element first
            root_id = root.xpath('./@xml:id', namespaces=vars.NAMESPACES)
            if root_id and root_id[0] == element_id:
                return root
            else:
                elements = root.xpath('.//*[@xml:id = $element_id]', namespaces=vars.NAMESPACES, element_id=element_id)
                if len(elements) > 0:
                    element = elements[0]
                    return element
    except Exception as e:
        print(f"\t[ERROR] Error searching for element with ID {element_id} in {folder_path}: {e}")
    return None

def _get_file(folder_path: Path, search_string: str, search_type: str ='by_id', return_full_path: bool = True) -> Path:
    result = Path('')
    if search_type == 'by_id':
        parser = etree.XMLParser(resolve_entities=False)
        for file in folder_path.rglob('*.xml'):
            tree = etree.parse(file, parser)
            root = tree.getroot()
            # Check root element first
            root_id = root.xpath('./@xml:id', namespaces=vars.NAMESPACES)
            if root_id and root_id[0] == search_string:
                result = file if return_full_path else file.name
            else:
                nav = root.xpath('//*[@xml:id=$search_string]', namespaces=vars.NAMESPACES, search_string=search_string)
                if nav:
                    result = file if return_full_path else file.name

    elif search_type == 'by_filename':
        for file in folder_path.rglob('*.xml'):
            if search_string in file.name:
                result = file if return_full_path else file.name

    if result == Path(''):
        print(f"\t[WARN] No file found for search string '{search_string}' in {folder_path}", file=sys.stderr)
    return result

def _create_file(content: str, file_path: Path, format_xml: bool = False) -> None:
    try:
        if format_xml:
            parser = etree.XMLParser(resolve_entities=False)
            tree = etree.fromstring(content, parser)
            content = etree.tostring(tree, pretty_print=True, encoding='unicode')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"\t[ERROR] Failed to save file {file_path}: {e}", file=sys.stderr)