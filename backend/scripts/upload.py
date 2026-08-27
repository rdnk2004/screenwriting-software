"""
upload.py — Script file upload handler for Fountain, TXT, and DOCX files.
"""
import io
from .fountain import parse_fountain_document
from .fdx import parse_fdx
from .models import Script, Scene, Line, TitlePage

try:
    import docx
except ImportError:
    docx = None


def parse_script_file(file_obj, filename: str) -> dict:
    """
    Extract text or paragraphs from uploaded file object and parse into document structure.
    Supports .fountain, .txt, .docx, and .fdx (Final Draft XML).
    """
    ext = filename.lower().split(".")[-1]

    if ext == "fdx":
        xml_content = file_obj.read()
        return parse_fdx(xml_content)
    elif ext == "docx":
        if not docx:
            raise ValueError("python-docx package is not installed.")
        doc = docx.Document(io.BytesIO(file_obj.read()))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        if not full_text.strip():
            raise ValueError("Uploaded file is empty.")
        return parse_fountain_document(full_text)
    else:
        # fountain or txt
        full_text = file_obj.read().decode("utf-8", errors="replace")
        if not full_text.strip():
            raise ValueError("Uploaded file is empty.")
        return parse_fountain_document(full_text)


def create_script_from_upload(user, title: str, file_obj, filename: str) -> Script:
    """
    Parse uploaded script file and create Script, TitlePage, Scene, and Line DB records.
    """
    doc_data = parse_script_file(file_obj, filename)
    scenes_data = doc_data.get("scenes", [])
    title_page_data = doc_data.get("title_page", {})

    fallback_title = filename.rsplit(".", 1)[0]
    extracted_title = title_page_data.get("title", "").strip() if title_page_data else ""
    clean_title = title.strip() if title and title.strip() else (extracted_title or fallback_title)

    script = Script.objects.create(title=clean_title, owner=user)

    if title_page_data and any(title_page_data.values()):
        TitlePage.objects.create(
            script=script,
            title=title_page_data.get("title") or clean_title,
            credit=title_page_data.get("credit", "written by"),
            author=title_page_data.get("author", ""),
            source=title_page_data.get("source", ""),
            notes=title_page_data.get("notes", ""),
            draft_date=title_page_data.get("draft_date", ""),
            contact=title_page_data.get("contact", ""),
            copyright=title_page_data.get("copyright", ""),
        )

    for scene_data in scenes_data:
        lines_data = scene_data.pop("lines", [])
        scene = Scene.objects.create(script=script, **scene_data)
        Line.objects.bulk_create(
            [
                Line(
                    scene=scene,
                    order=l["order"],
                    type=l["type"],
                    text=l["text"],
                    extension=l.get("extension", ""),
                    is_dual_dialogue=l.get("is_dual_dialogue", False),
                    dual_pos=l.get("dual_pos", ""),
                )
                for l in lines_data
            ]
        )

    return script
