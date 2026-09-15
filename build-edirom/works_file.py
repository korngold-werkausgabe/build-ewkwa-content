import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from lxml import etree

import global_variables as vars
import utils


MEI_NS = vars.NAMESPACES["mei"]

def _title_text(title_obj: dict) -> str:
    if not isinstance(title_obj, dict):
        return ""
    return title_obj.get("de") or title_obj.get("en") or ""


def extract_expression_struct(work: dict) -> dict:
    """Collect expression metadata needed to build works.xml from JSON."""
    output = {
        "type": work.get("type", ""),
        "has_expression_components": False,
        "main_expression": None,
        "expression_ids": [],
        "component_expression_ids": [],
    }

    expression_list = work.get("expression_list", [])
    if expression_list:
        output["main_expression"] = expression_list[0]

    if work.get("type") == "singleton":
        for expression in expression_list:
            expr_id = expression.get("id")
            if expr_id:
                output["expression_ids"].append(expr_id)

            component_expressions = expression.get("component_list", [])
            if component_expressions:
                output["has_expression_components"] = True
                for component in component_expressions:
                    comp_id = component.get("id")
                    if comp_id:
                        output["component_expression_ids"].append(comp_id)
                        output["expression_ids"].append(comp_id)

    elif work.get("type") == "collection":
        for sub_work in work.get("component_list", []):
            for expression in sub_work.get("expression_list", []):
                expr_id = expression.get("id")
                if expr_id:
                    output["expression_ids"].append(expr_id)

    return output


def _get_cnl_ids_for_expression(work: dict, expression_id: str) -> list:
    if not expression_id:
        return []

    cnl_ids = []
    for relation in work.get("relation_list", []):
        rel_type = relation.get("rel", "")
        target = relation.get("targets", "").lstrip("#")
        if rel_type != "hasPart" or target != expression_id:
            continue

        for item in relation.get("plist", []):
            if "cnl" in item:
                cnl_ids.append(item.lstrip("#"))

    return cnl_ids


def _append_critical_remarks(notes_stmt: etree._Element, work: dict, expression_id: str, sub_div: str, vol_slug: str) -> None:
    cnl_ids = _get_cnl_ids_for_expression(work, expression_id)
    if not cnl_ids:
        return

    wrapper_annot = etree.Element("{%s}annot" % vars.NAMESPACES["mei"], type="criticalCommentary")

    for cnl_id in cnl_ids:
        cnl_xml = utils._get_xml_by_id(vars.LOCAL_PATHS["criticalRemarks"], cnl_id)
        if cnl_xml is None:
            continue

        critical_remarks_str = build_critical_remarks(
            etree.tostring(cnl_xml, encoding="unicode"),
            str(vars.LOCAL_PATHS["sources"]),
            sub_div,
            vol_slug,
        )
        if not critical_remarks_str:
            continue

        try:
            wrapped_str = f'<temp xmlns="{vars.NAMESPACES["mei"]}">{critical_remarks_str}</temp>'
            wrapper_elem = etree.fromstring(wrapped_str.encode("utf-8"))
            for annot in wrapper_elem:
                wrapper_annot.append(deepcopy(annot))
        except Exception as parse_error:
            print(f"\t[WARN] Failed to parse critical remarks for '{cnl_id}': {parse_error}", file=sys.stderr)

    if len(wrapper_annot) > 0:
        notes_stmt.append(wrapper_annot)


def _build_component_work_from_template(template_path: Path, sub_work: dict, index: int, parent_work: dict, sub_div: str, vol_slug: str) -> etree._Element:
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(template_path), parser)
    component_element = tree.getroot()

    component_element.set("{%s}id" % vars.NAMESPACES["xml"], sub_work.get("id", ""))
    component_element.set("n", str(index))

    title_elems = component_element.xpath("./mei:title", namespaces=vars.NAMESPACES)
    if title_elems:
        title_elems[0].text = _title_text(sub_work.get("title", {}))

    component_expr_lists = component_element.xpath("./mei:expressionList", namespaces=vars.NAMESPACES)
    if component_expr_lists:
        component_element.remove(component_expr_lists[0])

    notes_stmt = etree.Element("{%s}notesStmt" % vars.NAMESPACES["mei"])
    expr_list = sub_work.get("expression_list", [])
    expr_id = expr_list[0].get("id") if expr_list else ""
    print(f"\t[INFO] Component work {index}: work_id={sub_work.get('id', '')}, expression_id={expr_id}, sub_div={sub_div}")
    _append_critical_remarks(notes_stmt, parent_work, expr_id, sub_div, vol_slug)
    component_element.append(notes_stmt)

    return component_element


def _build_work_element(work: dict, vol_slug: str) -> tuple[etree._Element, str]:
    template_path = vars.TEMPLATES["template_work"]
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(template_path), parser)
    work_element = tree.getroot()

    expression_struct = extract_expression_struct(work)
    main_expression = expression_struct.get("main_expression") or {}
    sub_div = main_expression.get("edition_slug", "")
    print(
        "\t[INFO] Build work: "
        f"work_id={work.get('id', '')}, "
        f"type={work.get('type', '')}, "
        f"title={_title_text(work.get('title', {}))}, "
        f"main_expression_id={main_expression.get('id', '')}, "
        f"sub_div={sub_div}"
    )

    work_element.set("{%s}id" % vars.NAMESPACES["xml"], work.get("id", ""))
    work_element.set("n", work.get("n", "1") or "1")

    title_elems = work_element.xpath("./mei:title", namespaces=vars.NAMESPACES)
    if title_elems:
        title_elems[0].text = _title_text(work.get("title", {}))

    expr_nodes = work_element.xpath("./mei:expressionList/mei:expression", namespaces=vars.NAMESPACES)
    if expr_nodes:
        expr_node = expr_nodes[0]
        if main_expression.get("id"):
            expr_node.set("{%s}id" % vars.NAMESPACES["xml"], main_expression["id"])
        if main_expression.get("n"):
            expr_node.set("n", main_expression["n"])

        expr_title = expr_node.xpath("./mei:title", namespaces=vars.NAMESPACES)
        if expr_title:
            expr_title[0].text = _title_text(main_expression.get("title", {}))

        if work.get("type") == "singleton" and expression_struct.get("has_expression_components"):
            component_list = etree.Element("{%s}componentList" % vars.NAMESPACES["mei"])
            for component_expression in main_expression.get("component_list", []):
                print(
                    "\t[INFO]  Add component expression: "
                    f"expression_id={component_expression.get('id', '')}, "
                    f"identifier={component_expression.get('identifier', '')}, "
                    f"title={_title_text(component_expression.get('title', {}))}"
                )
                comp_expr = etree.Element("{%s}expression" % vars.NAMESPACES["mei"])
                if component_expression.get("id"):
                    comp_expr.set("{%s}id" % vars.NAMESPACES["xml"], component_expression["id"])

                comp_title = etree.Element("{%s}title" % vars.NAMESPACES["mei"])
                comp_title.text = _title_text(component_expression.get("title", {}))
                comp_expr.append(comp_title)

                identifier_value = component_expression.get("identifier", "")
                if identifier_value:
                    identifier_elem = etree.Element("{%s}identifier" % vars.NAMESPACES["mei"], type="subDiv")
                    identifier_elem.text = identifier_value
                    comp_expr.append(identifier_elem)

                notes_stmt = etree.Element("{%s}notesStmt" % vars.NAMESPACES["mei"])
                _append_critical_remarks(notes_stmt, work, component_expression.get("id", ""), sub_div, vol_slug)
                comp_expr.append(notes_stmt)

                component_list.append(comp_expr)

            expr_node.append(component_list)

        elif work.get("type") == "singleton":
            print(f"\t[INFO]  Add singleton notes for expression_id={main_expression.get('id', '')}")
            notes_stmt = etree.Element("{%s}notesStmt" % vars.NAMESPACES["mei"])
            _append_critical_remarks(notes_stmt, work, main_expression.get("id", ""), sub_div, vol_slug)
            expr_node.append(notes_stmt)

    if work.get("type") == "collection":
        print(f"\t[INFO]  Build collection components: count={len(work.get('component_list', []))}")
        component_list = etree.Element("{%s}componentList" % vars.NAMESPACES["mei"])
        for idx, sub_work in enumerate(work.get("component_list", []), 1):
            component_element = _build_component_work_from_template(template_path, sub_work, idx, work, sub_div, vol_slug)
            component_list.append(component_element)
        work_element.append(component_list)

    return work_element, sub_div


def _assemble_works_xml(work_elements: list, sub_div: str, edition_name: str) -> bool:
    try:
        template_path = vars.TEMPLATES["template_edirom-works"]
        tree = etree.parse(str(template_path))
        root = tree.getroot()

        work_list = root.xpath(".//mei:workList", namespaces=vars.NAMESPACES)
        if not work_list:
            print("\t[FAIL] template_edirom-works.xml has no workList", file=sys.stderr)
            return False

        edition_stmt = root.xpath(".//mei:editionStmt", namespaces=vars.NAMESPACES)
        if edition_stmt:
            edition_elem = etree.Element("edition")
            edition_elem.text = edition_name
            edition_stmt[0].clear()
            edition_stmt[0].append(edition_elem)

        for element in work_elements:
            work_list[0].append(element)

        if sub_div:
            target_dir = vars.LOCAL_PATHS["_edirom"] / sub_div
            target_file = target_dir / f"{sub_div}_works.xml"
        else:
            target_dir = vars.LOCAL_PATHS["_edirom"]
            target_file = target_dir / "works.xml"

        target_dir.mkdir(parents=True, exist_ok=True)
        xml_output = etree.tostring(root, encoding="unicode", pretty_print=True)
        utils._create_file(xml_output, target_file, format_xml=True)
        return True
    except Exception as error:
        print(f"\t[FAIL] Could not assemble works.xml: {error}", file=sys.stderr)
        return False


def build_critical_remarks(cnl_xml: str, sources_path: str, sub_div: str, vol_slug: str) -> str:
    """Call buildEdiromTkAs.xql and return generated annot fragments."""
    try:
        build_tkas_xql = vars.SCRIPTS["build_tkas"]
        sources_path_abs = Path(sources_path).resolve()
        collection_path_abs = (vars.LOCAL_PATHS["tmp"] / sub_div).resolve() if sub_div else vars.LOCAL_PATHS["tmp"].resolve()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write(cnl_xml)
            tmp_cnl_file = tmp_file.name

        try:
            result = subprocess.run([
                "basex",
                f"-b cnListFile={tmp_cnl_file}",
                f"-b collectionPath={collection_path_abs}",
                f"-b sourcesPath={sources_path_abs}",
                f"-b subDiv={sub_div}",
                f"-b volumeName={vol_slug}",
                str(build_tkas_xql),
            ], capture_output=True, text=True, check=True)
            return result.stdout
        finally:
            Path(tmp_cnl_file).unlink(missing_ok=True)
    except FileNotFoundError:
        print("\t[WARN] basex not found, no critical remarks generated", file=sys.stderr)
        return ""
    except subprocess.CalledProcessError as error:
        print(f"\t[WARN] buildEdiromTkAs.xql failed: {error.stderr}", file=sys.stderr)
        return ""


def build_works_file(frbr_json: dict) -> None:
    """Build per-subDiv works.xml files from FRBR JSON."""
    work_list = frbr_json.get("work_list", [])
    edition_name = frbr_json.get("edition_name", "")
    vol_slug = frbr_json.get("vol_slug", "")
    print(f"[INFO] Build works.xml: works={len(work_list)}, edition='{edition_name}', vol_slug='{vol_slug}'")

    grouped_work_elements = {}

    for work in work_list:
        work_element, sub_div = _build_work_element(work, vol_slug)
        grouped_work_elements.setdefault(sub_div, []).append(work_element)

    for sub_div, elements in grouped_work_elements.items():
        print(f"[INFO] Assemble works.xml for sub_div='{sub_div}' with {len(elements)} work element(s)")
        if not _assemble_works_xml(elements, sub_div, edition_name):

