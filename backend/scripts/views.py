from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Script, Scene, Line, Character, Relationship
from .serializers import (
    LineSerializer,
    SceneWriteSerializer,
    ScriptListSerializer,
    ScriptDetailSerializer,
    CharacterSerializer,
    RelationshipSerializer,
    normalize_character_name,
)
from .fountain import parse_fountain, serialize_to_fountain
from .exporter import export_script_to_pdf, export_script_to_word


def _get_default_user():
    """Return (or create) the single default admin user."""
    user, _ = User.objects.get_or_create(
        username="admin",
        defaults={"is_staff": True, "is_superuser": False},
    )
    return user


# ---------------------------------------------------------------------------
# Script ViewSet
# ---------------------------------------------------------------------------

class ScriptViewSet(viewsets.ModelViewSet):
    queryset = Script.objects.all()

    def get_serializer_class(self):
        if self.action in ("list", "create", "update", "partial_update"):
            return ScriptListSerializer
        return ScriptDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=_get_default_user())

    # ------------------------------------------------------------------
    # Extra actions: Fountain import / export
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="import_fountain")
    def import_fountain(self, request, pk=None):
        """
        Replace all scenes/lines in a script from raw Fountain text.

        Body: plain text (Content-Type: text/plain) or JSON {"text": "..."}
        """
        script = self.get_object()

        # Accept both plain-text body and JSON {"text": "..."}
        content_type = request.content_type or ""
        if "application/json" in content_type:
            fountain_text = request.data.get("text", "")
        else:
            fountain_text = request.body.decode("utf-8", errors="replace")

        if not fountain_text.strip():
            return Response(
                {"detail": "Empty Fountain text."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Parse
        try:
            scenes_data = parse_fountain(fountain_text)
        except Exception as exc:
            return Response(
                {"detail": f"Parse error: {exc}"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Atomic replacement: delete old scenes (cascades to lines), create new
        script.scenes.all().delete()

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

        # Touch updated_at
        Script.objects.filter(pk=script.pk).update(
            updated_at=script.updated_at.__class__.now()
            if hasattr(script.updated_at, "__class__")
            else None
        )
        script.save(update_fields=["updated_at"])

        serializer = ScriptDetailSerializer(script)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="export_fountain")
    def export_fountain(self, request, pk=None):
        """Return the script serialized as Fountain plaintext."""
        script = self.get_object()

        scenes_data = []
        for scene in script.scenes.prefetch_related("lines").all():
            scenes_data.append(
                {
                    "order": scene.order,
                    "heading": scene.heading,
                    "location": scene.location,
                    "time_of_day": scene.time_of_day,
                    "pov_character": scene.pov_character,
                    "lines": [
                        {"order": l.order, "type": l.type, "text": l.text}
                        for l in scene.lines.all()
                    ],
                }
            )

        fountain_text = serialize_to_fountain(scenes_data)
        return HttpResponse(fountain_text, content_type="text/plain; charset=utf-8")

    @action(detail=True, methods=["get"], url_path="export_pdf")
    def export_pdf(self, request, pk=None):
        """Return the script exported as a screenplay-formatted PDF."""
        script = self.get_object()
        pdf_bytes = export_script_to_pdf(script)
        filename = f"{script.title.replace(' ', '_')}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"], url_path="export_word")
    def export_word(self, request, pk=None):
        """Return the script exported as a screenplay-formatted Word document (.docx)."""
        script = self.get_object()
        docx_bytes = export_script_to_word(script)
        filename = f"{script.title.replace(' ', '_')}.docx"
        response = HttpResponse(
            docx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"], url_path="extract_characters")
    def extract_characters(self, request, pk=None):
        """
        Auto-extract unique character names from screenplay lines of type 'character'
        and seed Character model entries for this script if they don't already exist.
        """
        script = self.get_object()
        character_lines = Line.objects.filter(
            scene__script=script, type=Line.LineType.CHARACTER
        ).values_list("text", flat=True)

        existing_names = set(
            script.characters.values_list("name", flat=True)
        )
        existing_normalized = {n.upper() for n in existing_names}

        created = []
        for raw_name in character_lines:
            norm = normalize_character_name(raw_name)
            if norm and norm not in existing_normalized:
                # Use title-cased name for display or normalized uppercase
                display_name = norm.title()
                char = Character.objects.create(script=script, name=display_name)
                created.append(char)
                existing_normalized.add(norm)

        characters = script.characters.all()
        serializer = CharacterSerializer(characters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Scene ViewSet
# ---------------------------------------------------------------------------

class SceneViewSet(viewsets.ModelViewSet):
    serializer_class = SceneWriteSerializer

    def get_queryset(self):
        qs = Scene.objects.all()
        script_id = self.request.query_params.get("script")
        if script_id:
            qs = qs.filter(script_id=script_id)
        return qs


# ---------------------------------------------------------------------------
# Line ViewSet
# ---------------------------------------------------------------------------

class LineViewSet(viewsets.ModelViewSet):
    serializer_class = LineSerializer

    def get_queryset(self):
        qs = Line.objects.all()
        scene_id = self.request.query_params.get("scene")
        if scene_id:
            qs = qs.filter(scene_id=scene_id)
        return qs


# ---------------------------------------------------------------------------
# Character ViewSet
# ---------------------------------------------------------------------------

class CharacterViewSet(viewsets.ModelViewSet):
    serializer_class = CharacterSerializer

    def get_queryset(self):
        qs = Character.objects.all()
        script_id = self.request.query_params.get("script")
        if script_id:
            qs = qs.filter(script_id=script_id)
        return qs


# ---------------------------------------------------------------------------
# Relationship ViewSet
# ---------------------------------------------------------------------------

class RelationshipViewSet(viewsets.ModelViewSet):
    serializer_class = RelationshipSerializer

    def get_queryset(self):
        qs = Relationship.objects.all()
        script_id = self.request.query_params.get("script")
        if script_id:
            qs = qs.filter(script_id=script_id)
        return qs
