#!/usr/bin/env python3
"""
Prepare Edirom Content dynamically from frbr-tree.xml
Uses lxml for robust XPath support with namespaces
"""
from lxml import etree
import subprocess
from pathlib import Path
import sys

# Namespace constants
NAMESPACES = {
    'mei': 'http://www.music-encoding.org/ns/mei',
    'xml': 'http://www.w3.org/XML/1998/namespace'
}

def get_works_from_frbr(frbr_path: str) -> tuple:
    """Extract all works and manifestations from frbr-tree.xml"""
    try:
        tree = etree.parse(frbr_path)
        root = tree.getroot()
        # Get all works - both collections and standalone singletons
        works = root.xpath('.//mei:work', namespaces=NAMESPACES)
        # Get all manifestations for source lookup
        manifestations = root.xpath('.//mei:manifestation', namespaces=NAMESPACES)
        return works, manifestations, tree
    except Exception as e:
        print(f"Error parsing {frbr_path}: {e}", file=sys.stderr)
        return [], [], None

def get_sources_for_expression(work: etree._Element, expr_id: str, manifestations: list) -> set:
    """Get all ewk-source IDs for a given expression"""
    sources = set()
    
    # Find relation with matching expression ID
    relations = work.xpath('./mei:relationList/mei:relation[@rel="hasRealization"]', namespaces=NAMESPACES)
    
    for relation in relations:
        target = relation.get('target', '')
        if target == f'#{expr_id}':
            # Get manifestation IDs from plist
            plist = relation.get('plist', '').split()
            
            for man_id in plist:
                man_id_clean = man_id.lstrip('#')
                
                # Find the manifestation with this ID
                for manifestation in manifestations:
                    if manifestation.get(f'{{{NAMESPACES["xml"]}}}id') == man_id_clean:
                        # Get sources from manifestation target attribute
                        man_target = manifestation.get('target', '')
                        if man_target:
                            sources.update(man_target.split())
                        
                        # Also check items within manifestation
                        items = manifestation.xpath('./mei:itemList/mei:item', namespaces=NAMESPACES)
                        for item in items:
                            item_target = item.get('target', '')
                            if item_target:
                                sources.update(item_target.split())
    
    return sources

def get_related_files_for_expression(work: etree._Element, expr_id: str) -> dict:
    """Get all related files (nav, cnl, etc.) for a given expression via hasPart relations"""
    related_files = {
        'nav': [],
        'cnl': [],
        'other': []
    }
    
    # Find all hasPart relations for this expression
    relations = work.xpath('./mei:relationList/mei:relation[@rel="hasPart"]', namespaces=NAMESPACES)
    
    for relation in relations:
        target = relation.get('target', '')
        if target == f'#{expr_id}':
            # Get IDs from plist
            plist = relation.get('plist', '').split()
            
            for file_id in plist:
                file_id_clean = file_id.lstrip('#')
                
                # Categorize by prefix
                if 'nav' in file_id_clean:
                    related_files['nav'].append(file_id_clean)
                elif 'cnl' in file_id_clean:
                    related_files['cnl'].append(file_id_clean)
                else:
                    related_files['other'].append(file_id_clean)
    
    return related_files

def select_work_workflow(work: etree._Element, manifestations: list, processed_works: set):
    """Prepare content for a specific work (collection or singleton)"""
    work_id = work.get(f'{{{NAMESPACES["xml"]}}}id')
    
    # Skip if already processed as component
    if work_id in processed_works:
        return
    
    work_type = work.get('type', 'unknown')
    work_n = work.get('n')
    identifier_elem = work.find('mei:identifier', NAMESPACES)
    identifier = identifier_elem.text if identifier_elem is not None else 'unknown'
    
    print(f"Processing Work @type={work_type}: {identifier} (n={work_n})")
    
    if work_type == 'collection':
        # Get component works (singletons within collection)
        components = work.xpath('./mei:componentList/mei:work', namespaces=NAMESPACES)
        
        for component in components:
            # Mark component as processed
            component_id = component.get(f'{{{NAMESPACES["xml"]}}}id')
            processed_works.add(component_id)
            
            # Pass parent work for relationList lookup
            process_single_work(component, manifestations, parent_work=work)
    
    elif work_type == 'singleton':
        # Process standalone singleton work (only if not already processed)
        process_single_work(work, manifestations)

def process_single_work(work: etree._Element, manifestations: list, parent_work: etree._Element = None):
    """Process a single work (component or standalone singleton)"""
    work_n = work.get('n')
    comp_id = work.get(f'{{{NAMESPACES["xml"]}}}id')
    comp_identifier = work.find('mei:identifier', NAMESPACES)
    comp_id_text = comp_identifier.text if comp_identifier is not None else 'unknown'
    comp_title_main = work.find('mei:title[@type="main"]', NAMESPACES)
    comp_title_main_text = comp_title_main.text if comp_title_main is not None else 'unknown'

    print(f"  - Work {work_n}: {comp_id_text} (xml:id={comp_id})")
    
    # Get expressions
    expressions = work.xpath('./mei:expressionList/mei:expression', namespaces=NAMESPACES)
    for expr in expressions:
        expr_id = expr.get(f'{{{NAMESPACES["xml"]}}}id')
        
        # For components, search in parent work's relationList
        # For standalone singletons, search in own relationList
        search_work = parent_work if parent_work is not None else work
        
        # Get sources for this expression
        sources = get_sources_for_expression(search_work, expr_id, manifestations)
        sources_str = ', '.join(sorted(sources)) if sources else 'none'
        
        # Get related files (nav, cnl, etc.)
        related_files = get_related_files_for_expression(search_work, expr_id)
        
        print(f"    Title: {comp_title_main_text} (xml:id={expr_id})")
        print(f"    Sources: {sources_str}")
        
        # Show related files if any
        if related_files['nav'] or related_files['cnl'] or related_files['other']:
            if related_files['nav']:
                print(f"    Navigation: {', '.join(related_files['nav'])}")
            if related_files['cnl']:
                print(f"    Connections: {', '.join(related_files['cnl'])}")
            if related_files['other']:
                print(f"    Other files: {', '.join(related_files['other'])}")

def main():
    """Main execution"""
    frbr_path = "../../frbr-tree.xml"
    
    if not Path(frbr_path).exists():
        print(f"Error: {frbr_path} not found", file=sys.stderr)
        sys.exit(1)
    
    print("Preparation of Edirom content from frbr-tree.xml")
    print("=" * 60)
    
    works, manifestations, tree = get_works_from_frbr(frbr_path)
    
    if not works:
        print("No works found", file=sys.stderr)
        sys.exit(1)
    
    # Track which works have been processed as components
    processed_works = set()
    
    for work in works:
        select_work_workflow(work, manifestations, processed_works)
    
    print("=" * 60)
    print("Done!")

if __name__ == "__main__":
    main()