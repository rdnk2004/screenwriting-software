from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Script",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(default="Untitled Script", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scripts",
                        to="auth.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="Scene",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                ("heading", models.CharField(blank=True, max_length=255)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("time_of_day", models.CharField(blank=True, max_length=64)),
                (
                    "pov_character",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "script",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scenes",
                        to="scripts.script",
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="Line",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("scene_heading", "Scene Heading"),
                            ("action", "Action"),
                            ("character", "Character"),
                            ("dialogue", "Dialogue"),
                            ("parenthetical", "Parenthetical"),
                            ("transition", "Transition"),
                        ],
                        default="action",
                        max_length=32,
                    ),
                ),
                ("text", models.TextField(blank=True)),
                (
                    "scene",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="scripts.scene",
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
            },
        ),
    ]
