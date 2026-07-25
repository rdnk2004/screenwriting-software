# pyrefly: ignore [missing-import]
from rest_framework import serializers
import re
from .models import Script, Scene, Line, Character, Relationship, Beat


def normalize_character_name(text: str) -> str:
    """
    Normalizes a character line cue text by stripping extensions like (V.O.), (O.S.), (CONT'D)
    and extra whitespace, returning uppercase string.
    Example: 'JOHN (V.O.)' -> 'JOHN'
    """
    if not text:
        return ""
    cleaned = re.sub(r"\s*\([^)]*\)", "", text)
    return cleaned.strip().upper()


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = ["id", "order", "type", "text"]


class SceneSerializer(serializers.ModelSerializer):
    lines = LineSerializer(many=True, read_only=True)

    class Meta:
        model = Scene
        fields = [
            "id",
            "order",
            "heading",
            "location",
            "time_of_day",
            "pov_character",
            "lines",
        ]


class SceneWriteSerializer(serializers.ModelSerializer):
    """Used when creating/updating a scene without nested lines."""

    class Meta:
        model = Scene
        fields = [
            "id",
            "script",
            "order",
            "heading",
            "location",
            "time_of_day",
            "pov_character",
        ]


class CharacterSerializer(serializers.ModelSerializer):
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
        """
        Helper method to compute statistics by inspecting Script -> Scene -> Line.
        Returns (appeared_scenes_list, dialogue_count).
        """
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
                if line.type == "character":
                    char_name = normalize_character_name(line.text)
                    if char_name == target_name:
                        in_scene = True
                        is_target_character = True
                    else:
                        is_target_character = False
                elif line.type == "dialogue":
                    if is_target_character:
                        dialogue_count += 1
                else:
                    if line.type not in ("parenthetical", "dialogue"):
                        is_target_character = False

            if in_scene:
                appeared_scenes.append(scene)

        return appeared_scenes, dialogue_count

    def get_scene_count(self, obj):
        scenes, _ = self._get_character_scenes_and_dialogue(obj)
        return len(scenes)

    def get_dialogue_line_count(self, obj):
        _, dialogue_count = self._get_character_scenes_and_dialogue(obj)
        return dialogue_count

    def get_first_appearance_scene(self, obj):
        scenes, _ = self._get_character_scenes_and_dialogue(obj)
        if not scenes:
            return None
        first = scenes[0]
        return {
            "id": first.id,
            "order": first.order,
            "heading": first.heading or f"Scene {first.order + 1}",
        }

    def get_last_appearance_scene(self, obj):
        scenes, _ = self._get_character_scenes_and_dialogue(obj)
        if not scenes:
            return None
        last = scenes[-1]
        return {
            "id": last.id,
            "order": last.order,
            "heading": last.heading or f"Scene {last.order + 1}",
        }


class ScriptListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the script list with statistics."""

    scene_count = serializers.SerializerMethodField()
    estimated_pages = serializers.SerializerMethodField()
    character_count = serializers.SerializerMethodField()

    class Meta:
        model = Script
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
            "scene_count",
            "estimated_pages",
            "character_count",
        ]

    def get_scene_count(self, obj):
        return obj.scenes.count()

    def get_estimated_pages(self, obj):
        line_count = Line.objects.filter(scene__script=obj).count()
        return round(line_count / 54.0, 1) if line_count > 0 else 0.0

    def get_character_count(self, obj):
        return obj.characters.count()


class ScriptDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested scenes and lines."""

    scenes = SceneSerializer(many=True, read_only=True)

    class Meta:
        model = Script
        fields = ["id", "title", "created_at", "updated_at", "scenes"]


class RelationshipSerializer(serializers.ModelSerializer):
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
    linked_scene_heading = serializers.ReadOnlyField(source="linked_scene.heading")
    linked_scene_order = serializers.ReadOnlyField(source="linked_scene.order")

    class Meta:
        model = Beat
        fields = [
            "id",
            "script",
            "name",
            "order",
            "linked_scene",
            "linked_scene_heading",
            "linked_scene_order",
        ]
