"""
upload.py — Script file upload handler for Fountain, TXT, and DOCX files.
"""
import io
from .fountain import parse_fountain
from .models import Script, Scene, Line

try:
    import docx
except ImportError:
    docx = None


def parse_script_file(file_obj, filename: str) -> list[dict]:
    """
    Extract text or paragraphs from uploaded file object and parse into scene structure.
    Supports .fountain, .txt, and .docx.
    """
    ext = filename.lower().split(".")[-1]

    if ext == "docx":
        if not docx:
            raise ValueError("python-docx package is not installed.")
        doc = docx.Document(io.BytesIO(file_obj.read()))
        full_text = "\n".join([p.text for p in doc.paragraphs])
    else:
        # fountain or txt
        full_text = file_obj.read().decode("utf-8", errors="replace")

    if not full_text.strip():
        raise ValueError("Uploaded file is empty.")

    return parse_fountain(full_text)


def create_script_from_upload(user, title: str, file_obj, filename: str) -> Script:
    """
    Parse uploaded script file and create Script, Scene, and Line DB records.
    """
    scenes_data = parse_script_file(file_obj, filename)

    clean_title = title.strip() if title and title.strip() else filename.rsplit(".", 1)[0]
    script = Script.objects.create(title=clean_title, owner=user)

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
                )
                for l in lines_data
            ]
        )

    return script
