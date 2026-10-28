from lxml import etree
from pathlib import Path
import sys

### MODULE IMPORTS ###
import global_variables as vars


def _get_matching_entry(plist: list, substring: str) -> str:
    """
    Find the first item in the list that contains the given substring.

    Args:
        plist: List of strings to search through
        substring: Substring to search for

    Returns:
        The first matching item, or empty string if no match found
    """
    return next((item for item in plist if substring in item), '')


def _get_matching_entries(plist: list, substring: str) -> list:
    """
    Find all items in the list that contain the given substring.

    Args:
        plist: List of strings to search through
        substring: Substring to search for

    Returns:
        List of all matching items
    """
    return [item for item in plist if substring in item]


def _get_rels_by_id(rels: list, search_id: str, rel_type: str) -> list:
    """
    Extract all relations of a specific type that reference the given ID.

    Args:
        rels: List of relation dictionaries with 'rel' and 'targets' keys
        search_id: ID to search for in relation targets
        rel_type: Type of relation to filter by (e.g., 'hasPart')

    Returns:
        List of matching relation dictionaries
    """
    rels_output = []
    for rel in rels:
        if rel["rel"] == rel_type and rel["targets"].strip("#") == search_id:            
            rels_output.append(rel)

    return rels_output


def _get_xml_by_id(folder_path: Path, element_id: str) -> etree._Element:
    """
    Search for an XML element with a specific ID in all XML files in a folder.

    Args:
        folder_path: Path to directory containing XML files
        element_id: The xml:id to search for

    Returns:
        The matching XML element, or None if not found
    """
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
    """
    Search for an XML file containing an element with a specific ID or filename.

    Args:
        folder_path: Path to directory containing XML files
        search_string: ID to search for (by_id) or filename substring (by_filename)
        search_type: 'by_id' to search xml:id attributes, 'by_filename' to match filenames
        return_full_path: If True, return full Path; if False, return filename only

    Returns:
        Path to the matching file, or empty Path if not found
    """
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
    """
    Write content to a file, optionally formatting as XML.

    Args:
        content: String content to write to the file
        file_path: Path where the file should be created
        format_xml: If True, parse and pretty-print as XML
    """
    try:
        if format_xml:
            parser = etree.XMLParser(resolve_entities=False)
            tree = etree.fromstring(content, parser)
            content = etree.tostring(tree, pretty_print=True, encoding='unicode')
        with open(file_path, 'w+', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"\t[ERROR] Failed to save file {file_path}: {e}", file=sys.stderr)