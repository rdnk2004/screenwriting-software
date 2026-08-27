"""
fdx.py — Final Draft XML (.fdx) Parser and Serializer Service.

Specification: Final Draft 8-13 XML Interchange Format (<FinalDraft DocumentType="Script">).

Handles:
  - Hierarchical extraction of scenes, sluglines, scene numbers, and script lines
  - Paragraph type mapping: 'Scene Heading', 'Action', 'Character', 'Dialogue', 'Parenthetical', 'Transition', 'Shot'
  - Character extension parsing (e.g. 'JOHN (V.O.)')
  - Dual Dialogue extraction from <DualDialogue> tags and paragraph attributes
  - Title Page metadata extraction from <TitlePage> blocks
  - Defensive XML parsing with entity safety
"""
import re
import xml.etree.ElementTree as ET
from .screenplay_terms import (
    extract_character_extension,
    normalize_character_name,
    is_valid_character_cue,
)

# ---------------------------------------------------------------------------
# Paragraph Type Normalization Map
# ---------------------------------------------------------------------------

FDX_TYPE_MAP = {
    "scene heading": "scene_heading",
    "sceneheading": "scene_heading",
    "slugline": "scene_heading",
    "action": "action",
    "general": "action",
    "character": "character",
    "dialogue": "dialogue",
    "parenthetical": "parenthetical",
    "transition": "transition",
    "shot": "action",
    "cast list": "action",
}

_RE_HEADING_PARTS = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|INT\./EXT\.|I/E\.|I/E)?\s*(.+?)\s*[-–]\s*(.+?)$",
    re.IGNORECASE,
)


def _extract_text_from_element(elem: ET.Element) -> str:
    """
    Combines all nested <Text> nodes within a paragraph element into a single string.
    """
    text_parts = []
    # If element has direct text
    if elem.text:
        text_parts.append(elem.text)

    # Inspect all children (especially <Text> tags)
    for child in elem:
        if child.text:
            text_parts.append(child.text)
        if child.tail:
            text_parts.append(child.tail)

    return "".join(text_parts).strip()


_RE_PREFIX = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|INT\./EXT\.|I/E\.|I/E)\s+",
    re.IGNORECASE,
)


def _parse_heading_metadata(heading: str) -> tuple[str, str]:
    """
    Extracts location and time_of_day from scene heading text.
    Handles multiple dashes like 'EXT. LOS ANGELES - 2019 - NIGHT'.
    """
    raw = heading.strip()
    # Strip INT./EXT. prefix
    m_pref = _RE_PREFIX.match(raw)
    body = raw[m_pref.end():].strip() if m_pref else raw

    # Split on last dash
    if " - " in body:
        loc, tod = body.rsplit(" - ", 1)
        return loc.strip(), tod.strip()
    elif " – " in body:
        loc, tod = body.rsplit(" – ", 1)
        return loc.strip(), tod.strip()
    elif " — " in body:
        loc, tod = body.rsplit(" — ", 1)
        return loc.strip(), tod.strip()
    elif "-" in body:
        loc, tod = body.rsplit("-", 1)
        return loc.strip(), tod.strip()

    return body, ""


def _extract_title_page(root: ET.Element) -> dict:
    """
    Extracts title page metadata from <TitlePage> element if present in FDX.
    """
    title_page = {
        "title": "",
        "credit": "written by",
        "author": "",
        "source": "",
        "notes": "",
        "draft_date": "",
        "contact": "",
        "copyright": "",
    }

    tp_elem = root.find("TitlePage")
    if tp_elem is None:
        return title_page

    content = tp_elem.find("Content")
    if content is None:
        return title_page

    paragraphs = content.findall("Paragraph")
    collected_texts = []
    for p in paragraphs:
        t = _extract_text_from_element(p)
        if t:
            collected_texts.append(t)

    # Heuristic mapping for standard FDX Title Page layout:
    # 0: Title, 1: "written by" or Credit, 2: Author, 3: Source / Based On, remaining: Contact/Date
    if collected_texts:
        title_page["title"] = collected_texts[0]
        if len(collected_texts) > 1:
            if collected_texts[1].lower() in ("written by", "by", "screenplay by"):
                title_page["credit"] = collected_texts[1]
                if len(collected_texts) > 2:
                    title_page["author"] = collected_texts[2]
            else:
                title_page["author"] = collected_texts[1]

        # Look for contact / date indicators
        for text_item in collected_texts[3:]:
            if "contact" in text_item.lower() or "@" in text_item or "phone" in text_item.lower():
                title_page["contact"] = (
                    f"{title_page['contact']}\n{text_item}".strip()
                    if title_page["contact"]
                    else text_item
                )
            elif "draft" in text_item.lower() or any(
                year in text_item for year in ["19", "20"]
            ):
                title_page["draft_date"] = text_item
            else:
                title_page["notes"] = (
                    f"{title_page['notes']}\n{text_item}".strip()
                    if title_page["notes"]
                    else text_item
                )

    return title_page


# ---------------------------------------------------------------------------
# Public FDX Parser API
# ---------------------------------------------------------------------------

def parse_fdx(xml_content: str | bytes) -> dict:
    """
    Parses Final Draft XML string/bytes into structured screenplay dictionary.

    Returns:
        {
            "title_page": { ... },
            "scenes": [
                {
                    "order": 0,
                    "scene_number": "1A",
                    "heading": "INT. COFFEE SHOP - DAY",
                    "location": "COFFEE SHOP",
                    "time_of_day": "DAY",
                    "pov_character": None,
                    "synopsis": "",
                    "notes": "",
                    "lines": [
                        {
                            "order": 0,
                            "type": "scene_heading",
                            "text": "INT. COFFEE SHOP - DAY",
                            "extension": "",
                            "is_dual_dialogue": False,
                            "dual_pos": "",
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Malformed Final Draft XML (.fdx): {exc}") from exc

    if root.tag != "FinalDraft":
        raise ValueError("Invalid FDX document: root tag is not <FinalDraft>.")

    # 1. Title page
    title_page_data = _extract_title_page(root)

    content_elem = root.find("Content")
    if content_elem is None:
        return {"title_page": title_page_data, "scenes": []}

    scenes = []
    current_scene = None
    scene_order = 0
    line_order = 0

    def start_scene(heading_text: str, scene_number: str = "") -> dict:
        nonlocal scene_order, line_order
        location, time_of_day = _parse_heading_metadata(heading_text)
        s = {
            "order": scene_order,
            "scene_number": scene_number,
            "heading": heading_text,
            "location": location,
            "time_of_day": time_of_day,
            "pov_character": None,
            "synopsis": "",
            "notes": "",
            "lines": [],
        }
        scene_order += 1
        line_order = 0
        return s

    def add_line(
        ltype: str,
        ltext: str,
        is_dual: bool = False,
        dual_pos: str = "",
    ):
        nonlocal line_order
        if current_scene is None:
            return
        ext = extract_character_extension(ltext) if ltype == "character" else ""
        current_scene["lines"].append(
            {
                "order": line_order,
                "type": ltype,
                "text": ltext,
                "extension": ext,
                "is_dual_dialogue": is_dual,
                "dual_pos": dual_pos,
            }
        )
        line_order += 1

    current_scene = start_scene("")

    def process_paragraph(
        p_elem: ET.Element,
        forced_dual: bool = False,
        dual_position: str = "",
    ):
        nonlocal current_scene
        raw_type = p_elem.get("Type", "Action").strip().lower()
        ltype = FDX_TYPE_MAP.get(raw_type, "action")
        text = _extract_text_from_element(p_elem)

        if not text:
            return

        # Check for Scene Heading
        if ltype == "scene_heading":
            scene_num = p_elem.get("Number", "").strip()
            # Also check nested <SceneProperties><SceneNumber>
            props = p_elem.find("SceneProperties")
            if props is not None:
                num_elem = props.find("SceneNumber")
                if num_elem is not None and num_elem.text:
                    scene_num = num_elem.text.strip()

            if current_scene["lines"] or current_scene["heading"]:
                scenes.append(current_scene)

            current_scene = start_scene(text.upper(), scene_number=scene_num)
            add_line("scene_heading", current_scene["heading"])
            return

        # Check Dual Dialogue attributes on paragraph or parent
        is_dual = forced_dual or p_elem.get("DualDialogue", "").lower() in ("yes", "left", "right")
        pos = dual_position
        if not pos and is_dual:
            pos = "right" if p_elem.get("DualDialogue", "").lower() == "right" else "left"

        add_line(ltype, text, is_dual=is_dual, dual_pos=pos)

    # Traverse <Content> children: <Paragraph> or <DualDialogue>
    for child in content_elem:
        if child.tag == "Paragraph":
            process_paragraph(child)
        elif child.tag == "DualDialogue":
            # Nested left and right blocks in Final Draft
            sub_paragraphs = child.findall("Paragraph")
            # First half is left speaker, second half is right speaker
            midpoint = len(sub_paragraphs) // 2
            for i, sub_p in enumerate(sub_paragraphs):
                position = "left" if i < midpoint else "right"
                process_paragraph(sub_p, forced_dual=True, dual_position=position)

    if current_scene:
        scenes.append(current_scene)

    # Filter empty preamble
    scenes = [s for s in scenes if s["heading"] or s["lines"]]

    # Re-index
    for i, s in enumerate(scenes):
        s["order"] = i

    return {
        "title_page": title_page_data,
        "scenes": scenes,
    }


# ---------------------------------------------------------------------------
# Public FDX Serializer API
# ---------------------------------------------------------------------------

def serialize_to_fdx(scenes_data: list[dict], title_page_data: dict | None = None) -> str:
    """
    Serializes structured screenplay scenes and title page metadata into Final Draft XML (.fdx).
    """
    root = ET.Element("FinalDraft", {"DocumentType": "Script", "Template": "No", "Version": "1"})

    # 1. Build Title Page
    if title_page_data and any(title_page_data.values()):
        tp_elem = ET.SubElement(root, "TitlePage")
        ET.SubElement(tp_elem, "Header")
        tp_content = ET.SubElement(tp_elem, "Content")

        title = title_page_data.get("title", "").strip()
        if title:
            p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Center"})
            t = ET.SubElement(p, "Text", {"Bold": "Yes"})
            t.text = title

        credit = title_page_data.get("credit", "written by").strip()
        if credit:
            p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Center"})
            t = ET.SubElement(p, "Text")
            t.text = credit

        author = title_page_data.get("author", "").strip()
        if author:
            p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Center"})
            t = ET.SubElement(p, "Text")
            t.text = author

        source = title_page_data.get("source", "").strip()
        if source:
            p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Center"})
            t = ET.SubElement(p, "Text")
            t.text = source

        draft_date = title_page_data.get("draft_date", "").strip()
        if draft_date:
            p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Left"})
            t = ET.SubElement(p, "Text")
            t.text = f"Draft Date: {draft_date}"

        contact = title_page_data.get("contact", "").strip()
        if contact:
            for line in contact.splitlines():
                if line.strip():
                    p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Left"})
                    t = ET.SubElement(p, "Text")
                    t.text = line.strip()

        notes = title_page_data.get("notes", "").strip()
        if notes:
            for line in notes.splitlines():
                if line.strip():
                    p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Left"})
                    t = ET.SubElement(p, "Text")
                    t.text = line.strip()

        copyright_text = title_page_data.get("copyright", "").strip()
        if copyright_text:
            p = ET.SubElement(tp_content, "Paragraph", {"Alignment": "Left"})
            t = ET.SubElement(p, "Text")
            t.text = copyright_text

    # 2. Build Content
    content_elem = ET.SubElement(root, "Content")

    for scene in sorted(scenes_data, key=lambda s: s.get("order", 0)):
        scene_num = scene.get("scene_number", "").strip()
        lines = sorted(scene.get("lines", []), key=lambda l: l.get("order", 0))

        idx = 0
        while idx < len(lines):
            line = lines[idx]
            ltype = line.get("type", "action")
            text = line.get("text", "").strip()
            is_dual = line.get("is_dual_dialogue", False)
            dual_pos = line.get("dual_pos", "")

            # Check if this starts a dual dialogue block
            if is_dual and dual_pos == "left":
                dual_elem = ET.SubElement(content_elem, "DualDialogue")
                # Collect all left lines, then all right lines
                while idx < len(lines) and lines[idx].get("is_dual_dialogue", False):
                    cur_line = lines[idx]
                    ptype = _get_fdx_paragraph_type(cur_line.get("type", "action"))
                    p = ET.SubElement(
                        dual_elem,
                        "Paragraph",
                        {"Type": ptype, "DualDialogue": cur_line.get("dual_pos", "left").capitalize()},
                    )
                    t = ET.SubElement(p, "Text")
                    t.text = cur_line.get("text", "")
                    idx += 1
                continue

            # Standard paragraph
            ptype = _get_fdx_paragraph_type(ltype)
            p_attrs = {"Type": ptype}

            if ltype == "scene_heading":
                if scene_num:
                    p_attrs["Number"] = scene_num
                p = ET.SubElement(content_elem, "Paragraph", p_attrs)
                if scene_num:
                    sp = ET.SubElement(p, "SceneProperties")
                    sn = ET.SubElement(sp, "SceneNumber")
                    sn.text = scene_num
                t = ET.SubElement(p, "Text")
                t.text = text.upper()
            elif ltype == "transition":
                p_attrs["Alignment"] = "Right"
                p = ET.SubElement(content_elem, "Paragraph", p_attrs)
                t = ET.SubElement(p, "Text")
                t.text = text.upper()
            elif ltype == "character":
                p = ET.SubElement(content_elem, "Paragraph", p_attrs)
                t = ET.SubElement(p, "Text")
                t.text = text.upper()
            else:
                p = ET.SubElement(content_elem, "Paragraph", p_attrs)
                t = ET.SubElement(p, "Text")
                t.text = text

            idx += 1

    # Format XML with indent
    ET.indent(root, space="  ", level=0)
    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
    return xml_str


def _get_fdx_paragraph_type(internal_type: str) -> str:
    """Maps internal LineType to official Final Draft paragraph type string."""
    mapping = {
        "scene_heading": "Scene Heading",
        "action": "Action",
        "character": "Character",
        "dialogue": "Dialogue",
        "parenthetical": "Parenthetical",
        "transition": "Transition",
    }
    return mapping.get(internal_type, "Action")

