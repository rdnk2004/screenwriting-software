"""
serializers.py — Screenplay Studio DRF Serializers.

Provides serialization, nested representations, and validation for Scripts,
TitlePages, ScriptRevisions, Scenes, Lines, Characters, Relationships, and Beats.
"""
from rest_framework import serializers
from .models import (
    Script,
    TitlePage,
    ScriptRevision,
    Scene,
    Line,
    Character,
    Relationship,
    Beat,
    RevisionColor,
)
from .screenplay_terms import (
    normalize_character_name,
    is_valid_character_cue,
    extract_character_extension,
)


class LineSerializer(serializers.ModelSerializer):
    """
    Serializer for individual screenplay lines with dual dialogue flags.
    """
    class Meta:
        model = Line
        fields = [
            "id",
            "scene",
            "order",
            "type",
            "text",
            "extension",
            "is_dual_dialogue",
            "dual_pos",
        ]


class SceneSerializer(serializers.ModelSerializer):
    """
    Nested scene representation with ordered lines and production metadata.
    """
    lines = LineSerializer(many=True, read_only=True)

    class Meta:
        model = Scene
        fields = [
            "id",
            "script",
            "order",
            "scene_number",
            "heading",
            "location",
            "time_of_day",
            "pov_character",
            "synopsis",
            "notes",
            "lines",
        ]


class SceneWriteSerializer(serializers.ModelSerializer):
    """
    Used when creating or updating scene metadata without modifying nested lines.
    """
    class Meta:
        model = Scene
        fields = [
            "id",
            "script",
            "order",
            "scene_number",
            "heading",
            "location",
            "time_of_day",
            "pov_character",
            "synopsis",
            "notes",
        ]


class TitlePageSerializer(serializers.ModelSerializer):
    """
    Serializer for screenplay title page metadata.
    """
    class Meta:
        model = TitlePage
        fields = [
            "id",
            "script",
            "title",
            "credit",
            "author",
            "source",
            "notes",
            "draft_date",
            "contact",
            "copyright",
        ]


class ScriptRevisionSerializer(serializers.ModelSerializer):
    """
    Serializer for historical screenplay revision snapshots.
    """
    color_display = serializers.CharField(source="get_color_display", read_only=True)

    class Meta:
        model = ScriptRevision
        fields = [
            "id",
            "script",
            "color",
            "color_display",
            "name",
            "revision_date",
            "notes",
            "created_at",
        ]


class CharacterSerializer(serializers.ModelSerializer):
    """
    Character profile serializer with dynamically computed scene counts and dialogue stats.
    """
    scene_count = serializers.SerializerMethodField()
    dialogue_line_count = serializers.SerializerMethodField()
    first_appearance_scene = serializers.SerializerMethodField()
    last_appearance_scene = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = [
            "id",
            "script",
            "name",
            "bio",
            "motivation",
            "arc_notes",
            "voice_notes",
            "image_url",
            "pos_x",
            "pos_y",
            "scene_count",
            "dialogue_line_count",
            "first_appearance_scene",
            "last_appearance_scene",
        ]

    def _get_character_scenes_and_dialogue(self, obj):
        target_name = normalize_character_name(obj.name)
        if not target_name:
            return [], 0

        scenes = obj.script.scenes.prefetch_related("lines").all()
        appeared_scenes = []
        dialogue_count = 0

        for scene in sorted(scenes, key=lambda s: s.order):
            lines = sorted(scene.lines.all(), key=lambda l: l.order)
            in_scene = False
            is_target_character = False
            for line in lines:
                if line.type == Line.LineType.CHARACTER:
                    if not is_valid_character_cue(line.text):
                        is_target_character = False
                        continue
                    char_name = normalize_character_name(line.text)
                    if char_name == target_name:
                        in_scene = True
                        is_target_character = True
                    else:
                        is_target_character = False
                elif line.type == Line.LineType.DIALOGUE:
                    if is_target_character:
                        dialogue_count += 1
                else:
                    if line.type not in (Line.LineType.PARENTHETICAL, Line.LineType.DIALOGUE):
                        is_target_character = False

            if in_scene:
                appeared_scenes.append(scene)

        return appeared_scenes, dialogue_count

    def get_scene_count(self, obj) -> int:
        scenes, _ = self._get_character_scenes_and_dialogue(obj)
        return len(scenes)

    def get_dialogue_line_count(self, obj) -> int:
        _, dialogue_count = self._get_character_scenes_and_dialogue(obj)
        return dialogue_count

    def get_first_appearance_scene(self, obj) -> dict | None:
        scenes, _ = self._get_character_scenes_and_dialogue(obj)
        if not scenes:
            return None
        first = scenes[0]
        return {
            "id": first.id,
            "order": first.order,
            "heading": first.heading or f"Scene {first.order + 1}",
        }

    def get_last_appearance_scene(self, obj) -> dict | None:
        scenes, _ = self._get_character_scenes_and_dialogue(obj)
        if not scenes:
            return None
        last = scenes[-1]
        return {
            "id": last.id,
            "order": last.order,
            "heading": last.heading or f"Scene {last.order + 1}",
        }


class RelationshipSerializer(serializers.ModelSerializer):
    """
    Serializer for directed character relationship graphs.
    """
    character_a_name = serializers.ReadOnlyField(source="character_a.name")
    character_b_name = serializers.ReadOnlyField(source="character_b.name")

    class Meta:
        model = Relationship
        fields = [
            "id",
            "script",
            "character_a",
            "character_b",
            "character_a_name",
            "character_b_name",
            "label",
            "type",
            "notes",
        ]


class BeatSerializer(serializers.ModelSerializer):
    """
    Serializer for story beats, including Act categorization, emotional polarity, and scene link.
    """
    linked_scene_heading = serializers.ReadOnlyField(source="linked_scene.heading")
    linked_scene_order = serializers.ReadOnlyField(source="linked_scene.order")

    class Meta:
        model = Beat
        fields = [
            "id",
            "script",
            "name",
            "order",
            "act",
            "emotional_polarity",
            "synopsis",
            "color_tag",
            "target_page",
            "linked_scene",
            "linked_scene_heading",
            "linked_scene_order",
        ]


class ScriptListSerializer(serializers.ModelSerializer):
    """
    Lightweight script dashboard serializer with summary metrics and metadata.
    """
    scene_count = serializers.SerializerMethodField()
    estimated_pages = serializers.SerializerMethodField()
    character_count = serializers.SerializerMethodField()
    revision_color_display = serializers.CharField(
        source="get_current_revision_color_display",
        read_only=True,
    )

    class Meta:
        model = Script
        fields = [
            "id",
            "title",
            "logline",
            "genre",
            "current_revision_color",
            "revision_color_display",
            "created_at",
            "updated_at",
            "scene_count",
            "estimated_pages",
            "character_count",
        ]

    def get_scene_count(self, obj) -> int:
        return obj.scenes.count()

    def get_estimated_pages(self, obj) -> float:
        line_count = Line.objects.filter(scene__script=obj).count()
        return round(line_count / 54.0, 1) if line_count > 0 else 0.0

    def get_character_count(self, obj) -> int:
        return obj.characters.count()


class ScriptDetailSerializer(serializers.ModelSerializer):
    """
    Full hierarchical screenplay serializer including nested TitlePage, Revisions, and Scenes.
    """
    scenes = SceneSerializer(many=True, read_only=True)
    title_page = TitlePageSerializer(read_only=True)
    revisions = ScriptRevisionSerializer(many=True, read_only=True)
    revision_color_display = serializers.CharField(
        source="get_current_revision_color_display",
        read_only=True,
    )
    character_count = serializers.SerializerMethodField()
    beat_count = serializers.SerializerMethodField()

    class Meta:
        model = Script
        fields = [
            "id",
            "title",
            "logline",
            "genre",
            "current_revision_color",
            "revision_color_display",
            "created_at",
            "updated_at",
            "title_page",
            "revisions",
            "character_count",
            "beat_count",
            "scenes",
        ]

    def get_character_count(self, obj) -> int:
        return obj.characters.count()

    def get_beat_count(self, obj) -> int:
        return obj.beats.count()
