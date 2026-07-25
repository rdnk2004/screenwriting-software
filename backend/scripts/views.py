# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.http import HttpResponse
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
from rest_framework import viewsets, status
# pyrefly: ignore [missing-import]
from rest_framework.decorators import action
# pyrefly: ignore [missing-import]
from rest_framework.response import Response

from .models import Script, Scene, Line, Character, Relationship, Beat
from .serializers import (
    LineSerializer,
    SceneWriteSerializer,
    ScriptListSerializer,
    ScriptDetailSerializer,
    CharacterSerializer,
    RelationshipSerializer,
    BeatSerializer,
    normalize_character_name,
)
from .fountain import parse_fountain, serialize_to_fountain
from .exporter import export_script_to_pdf, export_script_to_word


from .upload import create_script_from_upload


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

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        """
        Upload a screenplay file (.fountain, .txt, .docx) to create a new Script.
        Form-data: 'file' (required), 'title' (optional)
        """
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"detail": "No file was uploaded in request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = request.data.get("title", "")
        try:
            script = create_script_from_upload(
                user=_get_default_user(),
                title=title,
                file_obj=uploaded_file,
                filename=uploaded_file.name,
            )
            serializer = ScriptDetailSerializer(script)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response(
                {"detail": f"Upload processing failed: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        # Store beat linkage mapping before scene replacement to preserve beats
        linked_beats = list(script.beats.filter(linked_scene__isnull=False))
        beat_scene_headings = {
            b.id: b.linked_scene.heading for b in linked_beats if b.linked_scene
        }

        # Atomic replacement: delete old scenes (cascades to lines), create new
        script.scenes.all().delete()

        new_scenes_by_heading = {}
        for scene_data in scenes_data:
            lines_data = scene_data.pop("lines", [])
            scene = Scene.objects.create(script=script, **scene_data)
            if scene.heading:
                new_scenes_by_heading[scene.heading] = scene
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

        # Re-link beats if new scene matching heading exists
        for beat in linked_beats:
            heading = beat_scene_headings.get(beat.id)
            if heading and heading in new_scenes_by_heading:
                beat.linked_scene = new_scenes_by_heading[heading]
                beat.save(update_fields=["linked_scene"])

        # Touch updated_at with timezone-aware timestamp
        Script.objects.filter(pk=script.pk).update(updated_at=timezone.now())
        script.save(update_fields=["updated_at"])

        serializer = ScriptDetailSerializer(script)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="export_fountain")
    def export_fountain(self, request, pk=None):
        """Return the script serialized as Fountain plaintext."""
        script = self.get_object()

        scenes_data = []
        for scene in script.scenes.prefetch_related("lines").all().order_by("order"):
            scenes_data.append(
                {
                    "order": scene.order,
                    "heading": scene.heading,
                    "location": scene.location,
                    "time_of_day": scene.time_of_day,
                    "pov_character": scene.pov_character,
                    "lines": [
                        {"order": l.order, "type": l.type, "text": l.text}
                        for l in scene.lines.all().order_by("order")
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

    @action(detail=True, methods=["get"], url_path="analysis")
    def analysis(self, request, pk=None):
        """
        Return script analysis statistics:
        - dialogue balance per character (% and line counts)
        - page/scene count per act / beat grouping
        - location list with scene counts
        - most and least active characters
        """
        script = self.get_object()
        scenes = script.scenes.all().order_by("order")
        total_scenes = scenes.count()

        all_lines = Line.objects.filter(scene__script=script)
        total_lines_count = all_lines.count()
        estimated_total_pages = round(total_lines_count / 54.0, 1) if total_lines_count > 0 else 0.0

        # 1. Dialogue balance per character
        dialogue_lines = all_lines.filter(type=Line.LineType.CHARACTER)
        dialogue_counts = {}
        total_dialogue_lines = 0
        for d_line in dialogue_lines:
            norm_name = normalize_character_name(d_line.text)
            if norm_name:
                dialogue_counts[norm_name] = dialogue_counts.get(norm_name, 0) + 1
                total_dialogue_lines += 1

        dialogue_balance = []
        for name, cnt in sorted(dialogue_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((cnt / total_dialogue_lines) * 100.0, 1) if total_dialogue_lines > 0 else 0.0
            dialogue_balance.append({
                "character": name.title(),
                "dialogue_lines": cnt,
                "percentage": pct
            })

        # 2. Location list with scene counts
        locations_map = {}
        for s in scenes:
            loc = (s.location or "").strip().upper() or "UNKNOWN"
            locations_map[loc] = locations_map.get(loc, 0) + 1

        location_list = [
            {"location": loc, "scene_count": cnt}
            for loc, cnt in sorted(locations_map.items(), key=lambda x: x[1], reverse=True)
        ]

        # 3. Beat / Act Structure Breakdown
        beats = script.beats.all().order_by("order")
        beat_breakdown = []
        scenes_list = list(scenes)
        scene_order_map = {s.order: i for i, s in enumerate(scenes_list)}

        beats_list = list(beats)
        for i, beat in enumerate(beats_list):
            linked_scene_idx = scene_order_map.get(beat.linked_scene.order) if beat.linked_scene else None
            
            next_linked_idx = None
            for next_beat in beats_list[i + 1:]:
                if next_beat.linked_scene and next_beat.linked_scene.order in scene_order_map:
                    next_linked_idx = scene_order_map[next_beat.linked_scene.order]
                    break

            if linked_scene_idx is not None:
                end_idx = next_linked_idx if next_linked_idx is not None else len(scenes_list)
                section_scenes = scenes_list[linked_scene_idx:end_idx]
                sec_scene_count = len(section_scenes)
                sec_lines = Line.objects.filter(scene__in=section_scenes).count()
                sec_pages = round(sec_lines / 54.0, 1)
            else:
                sec_scene_count = 0
                sec_pages = 0.0

            beat_breakdown.append({
                "id": beat.id,
                "name": beat.name,
                "order": beat.order,
                "linked_scene_id": beat.linked_scene.id if beat.linked_scene else None,
                "linked_scene_heading": beat.linked_scene.heading if beat.linked_scene else None,
                "scene_count": sec_scene_count,
                "estimated_pages": sec_pages
            })

        # 4. Most / Least active characters
        character_stats = []
        for char in script.characters.all():
            serializer = CharacterSerializer(char)
            character_stats.append({
                "id": char.id,
                "name": char.name,
                "scene_count": serializer.data["scene_count"],
                "dialogue_line_count": serializer.data["dialogue_line_count"]
            })

        sorted_by_activity = sorted(character_stats, key=lambda x: (x["scene_count"], x["dialogue_line_count"]), reverse=True)
        most_active = sorted_by_activity[:3]
        least_active = sorted_by_activity[-3:] if len(sorted_by_activity) > 3 else []

        return Response({
            "total_scenes": total_scenes,
            "total_dialogue_lines": total_dialogue_lines,
            "total_lines": total_lines_count,
            "estimated_total_pages": estimated_total_pages,
            "dialogue_balance": dialogue_balance,
            "beat_breakdown": beat_breakdown,
            "locations": location_list,
            "most_active_characters": most_active,
            "least_active_characters": least_active
        })

    @action(detail=True, methods=["get"], url_path="extraction")
    def extraction(self, request, pk=None):
        """
        Script Extraction Engine:
        Analyzes screenplay text to extract dialogue lines per character,
        character co-appearance in scenes, and dialogue exchange connections.
        """
        script = self.get_object()
        scenes = script.scenes.prefetch_related("lines").all().order_by("order")

        extracted_lines = []
        character_scene_map = {}  # char_norm -> set(scene_ids)
        character_dialogue_map = {}  # char_norm -> list of line dicts
        character_exchanges = {}  # (char_a, char_b) -> exchange_count

        for scene in scenes:
            scene_chars = set()
            last_speaker = None
            lines = list(scene.lines.all().order_by("order"))

            for i, line in enumerate(lines):
                if line.type == Line.LineType.CHARACTER:
                    speaker = normalize_character_name(line.text)
                    if speaker:
                        scene_chars.add(speaker)

                        # Look ahead for dialogue text
                        dialogue_text = ""
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j]
                            if next_line.type == Line.LineType.DIALOGUE:
                                dialogue_text += (" " if dialogue_text else "") + next_line.text.strip()
                            elif next_line.type == Line.LineType.PARENTHETICAL:
                                continue
                            else:
                                break

                        item = {
                            "scene_id": scene.id,
                            "scene_order": scene.order + 1,
                            "scene_heading": scene.heading or f"Scene {scene.order + 1}",
                            "character": speaker.title(),
                            "dialogue": dialogue_text,
                            "line_order": line.order,
                        }
                        extracted_lines.append(item)

                        if speaker not in character_dialogue_map:
                            character_dialogue_map[speaker] = []
                        character_dialogue_map[speaker].append(item)

                        # Track dialogue exchange connection with previous speaker
                        if last_speaker and last_speaker != speaker:
                            pair = tuple(sorted([last_speaker, speaker]))
                            character_exchanges[pair] = character_exchanges.get(pair, 0) + 1

                        last_speaker = speaker

            for speaker in scene_chars:
                if speaker not in character_scene_map:
                    character_scene_map[speaker] = set()
                character_scene_map[speaker].add(scene.id)

        # Build co-appearance & exchange matrix
        all_speakers = sorted(character_scene_map.keys())
        connections = []
        for i in range(len(all_speakers)):
            for j in range(i + 1, len(all_speakers)):
                char_a = all_speakers[i]
                char_b = all_speakers[j]
                shared_scenes = len(
                    character_scene_map[char_a].intersection(character_scene_map[char_b])
                )
                exchanges = character_exchanges.get(tuple(sorted([char_a, char_b])), 0)

                if shared_scenes > 0 or exchanges > 0:
                    connections.append({
                        "character_a": char_a.title(),
                        "character_b": char_b.title(),
                        "shared_scenes": shared_scenes,
                        "dialogue_exchanges": exchanges,
                    })

        return Response({
            "total_extracted_lines": len(extracted_lines),
            "total_characters": len(all_speakers),
            "connections": connections,
            "extracted_lines": extracted_lines,
        })


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


# ---------------------------------------------------------------------------
# Beat ViewSet
# ---------------------------------------------------------------------------

class BeatViewSet(viewsets.ModelViewSet):
    serializer_class = BeatSerializer

    def get_queryset(self):
        qs = Beat.objects.all()
        script_id = self.request.query_params.get("script")
        if script_id:
            qs = qs.filter(script_id=script_id)
        return qs.order_by("order")
