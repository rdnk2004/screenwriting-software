# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User


class Script(models.Model):
    title = models.CharField(max_length=255, default="Untitled Script")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="scripts"
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Scene(models.Model):
    script = models.ForeignKey(Script, on_delete=models.CASCADE, related_name="scenes")
    order = models.PositiveIntegerField(default=0)
    heading = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    time_of_day = models.CharField(max_length=64, blank=True)
    pov_character = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Scene {self.order}: {self.heading}"


class Line(models.Model):
    class LineType(models.TextChoices):
        SCENE_HEADING = "scene_heading", "Scene Heading"
        ACTION = "action", "Action"
        CHARACTER = "character", "Character"
        DIALOGUE = "dialogue", "Dialogue"
        PARENTHETICAL = "parenthetical", "Parenthetical"
        TRANSITION = "transition", "Transition"

    scene = models.ForeignKey(Scene, on_delete=models.CASCADE, related_name="lines")
    order = models.PositiveIntegerField(default=0)
    type = models.CharField(
        max_length=32, choices=LineType.choices, default=LineType.ACTION
    )
    text = models.TextField(blank=True)
    extension = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"[{self.type}] {self.text[:60]}"


class Character(models.Model):
    script = models.ForeignKey(
        Script, on_delete=models.CASCADE, related_name="characters"
    )
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    motivation = models.TextField(blank=True)
    arc_notes = models.TextField(blank=True)
    voice_notes = models.TextField(blank=True)
    image_url = models.CharField(max_length=512, blank=True)
    pos_x = models.FloatField(default=100.0)
    pos_y = models.FloatField(default=100.0)

    class Meta:
        ordering = ["name"]
        unique_together = ["script", "name"]

    def __str__(self):
        return f"{self.name} ({self.script.title})"


class Relationship(models.Model):
    class RelationshipType(models.TextChoices):
        ALLY = "ally", "Ally"
        RIVAL = "rival", "Rival"
        ROMANTIC = "romantic", "Romantic"
        FAMILY = "family", "Family"
        OTHER = "other", "Other"

    script = models.ForeignKey(
        Script, on_delete=models.CASCADE, related_name="relationships"
    )
    character_a = models.ForeignKey(
        Character, on_delete=models.CASCADE, related_name="relationships_as_a"
    )
    character_b = models.ForeignKey(
        Character, on_delete=models.CASCADE, related_name="relationships_as_b"
    )
    label = models.CharField(max_length=255, blank=True)
    type = models.CharField(
        max_length=32,
        choices=RelationshipType.choices,
        default=RelationshipType.OTHER,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.character_a.name} -> {self.character_b.name} ({self.label})"


class Beat(models.Model):
    script = models.ForeignKey(
        Script, on_delete=models.CASCADE, related_name="beats"
    )
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    linked_scene = models.ForeignKey(
        Scene, on_delete=models.SET_NULL, null=True, blank=True, related_name="beats"
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}. {self.name} ({self.script.title})"
