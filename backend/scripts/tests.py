from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from .models import Script, Scene, Line


class ScreenwriterAPITests(APITestCase):
    def setUp(self):
        # The admin user is automatically fetched/created in views.py, but we can verify it here too.
        self.user, _ = User.objects.get_or_create(username="admin")

    def test_create_script(self):
        url = reverse("script-list")
        data = {"title": "My First Screenplay"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Script.objects.count(), 1)
        self.assertEqual(Script.objects.get().title, "My First Screenplay")

    def test_import_fountain(self):
        script = Script.objects.create(title="Fountain Test", owner=self.user)
        url = reverse("script-import-fountain", kwargs={"pk": script.pk})
        
        fountain_text = (
            "INT. HOUSE - DAY\n\n"
            "JOHN\n"
            "Hello there.\n\n"
            "MARY\n"
            "(smiling)\n"
            "Hi John."
        )
        
        response = self.client.post(url, fountain_text, content_type="text/plain")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify database records
        scenes = Scene.objects.filter(script=script)
        self.assertEqual(scenes.count(), 1)
        scene = scenes.first()
        self.assertEqual(scene.heading, "INT. HOUSE - DAY")
        
        lines = Line.objects.filter(scene=scene)
        self.assertEqual(lines.count(), 6) # scene_heading, action/blank line is skipped? 
        # Let's count them: 
        # 1. scene_heading ("INT. HOUSE - DAY")
        # 2. character ("JOHN")
        # 3. dialogue ("Hello there.")
        # 4. character ("MARY")
        # 5. parenthetical ("(smiling)")
        # 6. dialogue ("Hi John.")
        
        line_types = [l.type for l in lines]
        self.assertEqual(line_types, ["scene_heading", "character", "dialogue", "character", "parenthetical", "dialogue"])
        
        line_texts = [l.text for l in lines]
        self.assertEqual(line_texts, [
            "INT. HOUSE - DAY",
            "JOHN",
            "Hello there.",
            "MARY",
            "(smiling)",
            "Hi John."
        ])

    def test_export_fountain(self):
        script = Script.objects.create(title="Export Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="EXT. STREET - NIGHT", location="STREET", time_of_day="NIGHT")
        Line.objects.create(scene=scene, order=0, type="scene_heading", text="EXT. STREET - NIGHT")
        Line.objects.create(scene=scene, order=1, type="character", text="BOB")
        Line.objects.create(scene=scene, order=2, type="dialogue", text="Where are you going?")
        
        url = reverse("script-export-fountain", kwargs={"pk": script.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        
        expected_content = "\nEXT. STREET - NIGHT\n\nBOB\nWhere are you going?\n"
        self.assertEqual(response.content.decode("utf-8").strip(), expected_content.strip())

    def test_export_pdf(self):
        script = Script.objects.create(title="PDF Export Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="INT. OFFICE - DAY")
        Line.objects.create(scene=scene, order=0, type="scene_heading", text="INT. OFFICE - DAY")
        Line.objects.create(scene=scene, order=1, type="action", text="Sitting at the desk.")

        url = reverse("script-export-pdf", kwargs={"pk": script.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(len(response.content) > 0)
        # Check PDF header bytes %PDF-
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_export_word(self):
        script = Script.objects.create(title="Word Export Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="INT. OFFICE - DAY")
        Line.objects.create(scene=scene, order=0, type="scene_heading", text="INT. OFFICE - DAY")
        Line.objects.create(scene=scene, order=1, type="action", text="Sitting at the desk.")

        url = reverse("script-export-word", kwargs={"pk": script.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertTrue(len(response.content) > 0)
        # Check docx zip magic header PK
        self.assertTrue(response.content.startswith(b"PK"))

    def test_character_stats(self):
        from .models import Character
        script = Script.objects.create(title="Character Stats Test", owner=self.user)

        # Scene 1
        scene1 = Scene.objects.create(script=script, order=0, heading="INT. COFFEE SHOP - DAY")
        Line.objects.create(scene=scene1, order=0, type="scene_heading", text="INT. COFFEE SHOP - DAY")
        Line.objects.create(scene=scene1, order=1, type="character", text="BOB (V.O.)")
        Line.objects.create(scene=scene1, order=2, type="dialogue", text="I like coffee.")
        Line.objects.create(scene=scene1, order=3, type="character", text="ALICE")
        Line.objects.create(scene=scene1, order=4, type="dialogue", text="Me too.")

        # Scene 2
        scene2 = Scene.objects.create(script=script, order=1, heading="EXT. PARK - DAY")
        Line.objects.create(scene=scene2, order=0, type="scene_heading", text="EXT. PARK - DAY")
        Line.objects.create(scene=scene2, order=1, type="character", text="BOB")
        Line.objects.create(scene=scene2, order=2, type="dialogue", text="Nice weather today.")

        char_bob = Character.objects.create(
            script=script,
            name="Bob",
            bio="A coffee lover.",
            motivation="Wants coffee.",
        )

        url = reverse("character-detail", kwargs={"pk": char_bob.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["name"], "Bob")
        self.assertEqual(data["scene_count"], 2)
        self.assertEqual(data["dialogue_line_count"], 2)
        self.assertEqual(data["first_appearance_scene"]["heading"], "INT. COFFEE SHOP - DAY")
        self.assertEqual(data["last_appearance_scene"]["heading"], "EXT. PARK - DAY")

    def test_extract_characters(self):
        from .models import Character
        script = Script.objects.create(title="Extract Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="INT. ROOM - DAY")
        Line.objects.create(scene=scene, order=0, type="character", text="CHARLIE (CONT'D)")

        url = reverse("script-extract-characters", kwargs={"pk": script.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Character.objects.filter(script=script).count(), 1)
        self.assertEqual(Character.objects.filter(script=script).first().name, "Charlie")

    def test_character_position_and_relationship(self):
        from .models import Character, Relationship
        script = Script.objects.create(title="Relationship Test", owner=self.user)
        char1 = Character.objects.create(script=script, name="Alice", pos_x=50.0, pos_y=50.0)
        char2 = Character.objects.create(script=script, name="Bob", pos_x=200.0, pos_y=200.0)

        # Update character position
        char_url = reverse("character-detail", kwargs={"pk": char1.pk})
        patch_res = self.client.patch(char_url, {"pos_x": 350.5, "pos_y": 420.0}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        char1.refresh_from_db()
        self.assertEqual(char1.pos_x, 350.5)
        self.assertEqual(char1.pos_y, 420.0)

        # Create relationship
        rel_url = reverse("relationship-list")
        rel_data = {
            "script": script.pk,
            "character_a": char1.pk,
            "character_b": char2.pk,
            "label": "Rivals",
            "type": "rival",
            "notes": "Bitter feud over market share."
        }
        res = self.client.post(rel_url, rel_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Relationship.objects.filter(script=script).count(), 1)
        rel = Relationship.objects.first()
        self.assertEqual(rel.label, "Rivals")
        self.assertEqual(rel.type, "rival")
