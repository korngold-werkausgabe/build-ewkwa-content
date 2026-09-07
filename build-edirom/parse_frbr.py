import global_variables as vars
from lxml import etree
from typing import Optional, Union
import sys

"""
This module provides functions to parse and extract information from a FRBR tree
represented in an MEI XML document. It includes utilities to collect titles, identifiers,
content items, component expressions, manifestations, and relations from the XML structure.
"""


def _first_text(node, xpath_expr: str) -> str:
    """
    Extracts the first text value from the given XML node based on the provided XPath expression.

    Args:
        node: The XML node to search within.
        xpath_expr: The XPath expression to locate the desired text.

    Returns:
        The first text value found, or an empty string if none is found.
    """
    values = node.xpath(xpath_expr, namespaces=vars.NAMESPACES)
    return values[0] if values else ""


def _collect_title_obj(node, title_xpath: str = './mei:title') -> dict:
    """
    Collects the title information from the given XML node and returns it as a dictionary with language keys.

    Args:
        node: The XML node containing the title information.
        title_xpath: The XPath expression to locate the title elements (default is './mei:title').

    Returns:
        A dictionary with 'de' and 'en' keys containing the respective title values.
    """
    title_map = {}
    for title in node.xpath(title_xpath, namespaces=vars.NAMESPACES):
        lang = title.attrib.get('{http://www.w3.org/XML/1998/namespace}lang', 'de')
        value = (title.text or '').strip()
        if value:
            title_map[lang] = value

    if not title_map:
        text = (node.xpath(title_xpath + '/text()', namespaces=vars.NAMESPACES) or [''])[0].strip()
        if text:
            title_map['de'] = text
            return {'de': text, 'en': text}

    if 'de' not in title_map and 'en' in title_map:
        title_map['de'] = title_map['en']
    elif 'en' not in title_map and 'de' in title_map:
        title_map['en'] = title_map['de']

    return {
        'de': title_map.get('de', ''),
        'en': title_map.get('en', '')
    }


def _collect_identifiers(node, identifier_type: Optional[str] = None) -> Union[dict, str]:
    """
    Collects the identifier information from the given XML node and returns it as a dictionary or a specific identifier value.

    Args:
        node: The XML node containing the identifier information.
        identifier_type: The specific type of identifier to retrieve (default is None, which returns all identifiers).

    Returns:
        A dictionary of all identifiers if identifier_type is None, otherwise the value of the specified identifier type.
    """
    identifiers = {}
    for identifier in node.xpath('./mei:identifier', namespaces=vars.NAMESPACES):
        key = (identifier.attrib.get('type') or '').strip()
        value = (identifier.text or '').strip()
        if key and value:
            identifiers[key] = value

    if identifier_type is None:
        return identifiers

    return identifiers.get(identifier_type, '')


def _collect_content_items(expression) -> list:
    """
    Collects the content items from the given expression node.

    Args:
        expression: The XML node representing the expression.

    Returns:
        A list of dictionaries, each containing information about a content item.
    """
    content_items = []
    for item in expression.xpath('./mei:contents/mei:contentItem', namespaces=vars.NAMESPACES):
        content_items.append({
            "type": item.attrib.get('type', ''),
            "identifier": _first_text(item, './mei:identifier[@type="subDiv"]/text()'),
            "num": _first_text(item, './mei:num/text()'),
            "title": _collect_title_obj(item),
        })
    return content_items


def _collect_component_expressions(expression) -> list:
    """
    Collects the component expressions from the given expression node.

    Args:
        expression: The XML node representing the expression.

    Returns:
        A list of dictionaries, each containing information about a component expression.
    """
    components = []
    for component in expression.xpath('./mei:componentList/mei:expression', namespaces=vars.NAMESPACES):
        components.append({
            "id": _first_text(component, './@xml:id'),
            "identifier": _first_text(component, './mei:identifier[@type="subDiv"]/text()'),
            "title": _collect_title_obj(component),
        })
    return components


def _collect_items(manifestation) -> list:
    """
    Collects the items from the given manifestation node.

    Args:
        manifestation: The XML node representing the manifestation.

    Returns:
        A list of dictionaries, each containing information about an item.
    """
    items = []
    for item in manifestation.xpath('./mei:itemList/mei:item', namespaces=vars.NAMESPACES):
        items.append({
            "id": _first_text(item, './@xml:id'),
            "targets": item.attrib.get('targets', ''),
            "title": _collect_title_obj(item, './mei:titleStmt/mei:title'),
            "identifier": _collect_identifiers(item),
        })
    return items


def _collect_manifestations(root) -> list:
    """
    Collects the manifestations from the given root node.

    Args:
        root: The XML root node containing the manifestation information.

    Returns:
        A list of dictionaries, each containing information about a manifestation.
    """
    manifestations = []
    for manifestation in root.xpath('/mei:mei/mei:meiHead/mei:manifestationList/mei:manifestation', namespaces=vars.NAMESPACES):
        manifestation_entry = {
            "id": _first_text(manifestation, './@xml:id'),
            "singleton": manifestation.attrib.get('singleton', ''),
            "targets": manifestation.attrib.get('targets', ''),
            "title": _collect_title_obj(manifestation, './mei:titleStmt/mei:title'),
            "identifier": _collect_identifiers(manifestation),
        }
        items = _collect_items(manifestation)
        if items:
            manifestation_entry["item_list"] = items
        manifestations.append(manifestation_entry)
    return manifestations


def _collect_relations(node) -> list:
    """
    Collects the relations from the given XML node.

    Args:
        node: The XML node containing the relation information.

    Returns:
        A list of dictionaries, each containing information about a relation.
    """
    relations = []
    for relation in node.xpath('./mei:relationList/mei:relation', namespaces=vars.NAMESPACES):
        plist_value = (relation.attrib.get('plist') or '').strip()
        relations.append({
            "rel": relation.attrib.get('rel', ''),
            "targets": relation.attrib.get('targets', ''),
            "plist": plist_value.split() if plist_value else [],
        })
    return relations


def _build_expression_entry(expression) -> dict:
    """
    Builds a dictionary entry for the given expression node.

    Args:
        expression: The XML node representing the expression.

    Returns:
        A dictionary containing information about the expression, including its ID, title, content items, component expressions, and relations.
    """
    title_obj = _collect_title_obj(expression)
    content_items = _collect_content_items(expression)
    component_list = _collect_component_expressions(expression)
    relations = _collect_relations(expression)

    expr = {
        "id": _first_text(expression, './@xml:id'),
        "n": _first_text(expression, './@n'),
        "title": title_obj,
        "edition_slug": _collect_identifiers(expression, 'editionSlug'),
    }

    if content_items:
        expr["content_items"] = content_items

    if component_list:
        expr["component_list"] = component_list

    if relations:
        expr["relation_list"] = relations

    return expr


def _build_work_entry(work) -> dict:
    """
    Builds a dictionary entry for the given work node.

    Args:
        work: The XML node representing the work.

    Returns:
        A dictionary containing information about the work, including its ID, title, direct expressions, child works, and relations.
    """
    title_obj = _collect_title_obj(work)
    direct_expressions = [
        _build_expression_entry(expression)
        for expression in work.xpath('./mei:expressionList/mei:expression', namespaces=vars.NAMESPACES)
    ]
    child_works = [
        _build_work_entry(child)
        for child in work.xpath('./mei:componentList/mei:work', namespaces=vars.NAMESPACES)
    ]
    relations = _collect_relations(work)

    work_entry = {
        "id": _first_text(work, './@xml:id'),
        "n": _first_text(work, './@n'),
        "type": _first_text(work, './@type'),
        "title": title_obj,
        "expression_list": direct_expressions,
    }

    if child_works:
        work_entry["component_list"] = child_works

    if relations:
        work_entry["relation_list"] = relations

    return work_entry


def _collect_works_in_order(works) -> list:
    """
    Collects the work entries in the order they appear in the XML.

    Args:
        works: A list of XML nodes representing the works.

    Returns:
        A list of dictionaries, each containing information about a work.
    """
    return [_build_work_entry(work) for work in works]

def _return_manifestation_xml_by_id(manifestation_id: str) -> etree._Element:
    try:
        tree = etree.parse(vars.LOCAL_PATHS['frbr'])
        root = tree.getroot()
        manifestation = root.xpath(f'//mei:manifestation[@xml:id="{manifestation_id}"]', namespaces=vars.NAMESPACES)
        if manifestation:
            return manifestation[0]
        return etree.Element("empty")
    except Exception as e:
        print(f"\t[ERROR] Failed to retrieve manifestation with ID {manifestation_id}: {e}")
        return etree.Element("empty")


def write_frbr_to_json(frbr_path: str) -> dict:
    """
    Parses the FRBR XML file and converts it into a JSON-compatible dictionary.

    Args:
        frbr_path: The file path to the FRBR XML file.

    Returns:
        A dictionary containing the FRBR data, including volume slug, edition name, work list, and manifestation list.
    """

    frbr_map = {
        "vol_slug": "",
        "edition_name": "",
        "work_list": [],
        "manifestation_list": []
    }

    try:
        tree = etree.parse(frbr_path)
        root = tree.getroot()

        frbr_map["vol_slug"] = _first_text(root, '/mei:mei/mei:meiHead/mei:fileDesc/mei:pubStmt/mei:identifier[@type="volSlug"]/text()')
        frbr_map["edition_name"] = _first_text(root, '/mei:mei/mei:meiHead/mei:fileDesc/mei:titleStmt/mei:title[@type="volume"]/text()')

        top_level_works = root.xpath('/mei:mei/mei:meiHead/mei:workList/mei:work', namespaces=vars.NAMESPACES)
        frbr_map["work_list"] = _collect_works_in_order(top_level_works)

        frbr_map["manifestation_list"] = _collect_manifestations(root)

    except Exception as e:
        print(f"\n\t[FAILED]: Error parsing FRBR file {frbr_path}: {e}")
        sys.exit(1)

    return frbr_map