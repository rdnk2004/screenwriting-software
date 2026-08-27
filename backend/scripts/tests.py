# pyrefly: ignore [missing-import]
from django.urls import reverse
# pyrefly: ignore [missing-import]
from rest_framework import status
# pyrefly: ignore [missing-import]
from rest_framework.test import APITestCase
# pyrefly: ignore [missing-import]
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

    def test_beat_crud(self):
        from .models import Beat
        script = Script.objects.create(title="Beat Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="INT. COFFEE SHOP - DAY")

        url = reverse("beat-list")
        res = self.client.post(url, {
            "script": script.pk,
            "name": "Opening Image",
            "order": 1,
            "linked_scene": scene.pk
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Beat.objects.filter(script=script).count(), 1)

        beat = Beat.objects.first()
        self.assertEqual(beat.name, "Opening Image")
        self.assertEqual(beat.linked_scene, scene)

    def test_script_analysis(self):
        script = Script.objects.create(title="Analysis Test", owner=self.user)
        scene1 = Scene.objects.create(script=script, order=0, heading="INT. CAFE - DAY", location="CAFE")
        Line.objects.create(scene=scene1, order=0, type="scene_heading", text="INT. CAFE - DAY")
        Line.objects.create(scene=scene1, order=1, type="character", text="BOB")
        Line.objects.create(scene=scene1, order=2, type="dialogue", text="Hello Alice.")
        Line.objects.create(scene=scene1, order=3, type="character", text="ALICE")
        Line.objects.create(scene=scene1, order=4, type="dialogue", text="Hi Bob!")

        scene2 = Scene.objects.create(script=script, order=1, heading="EXT. PARK - DAY", location="PARK")
        Line.objects.create(scene=scene2, order=0, type="scene_heading", text="EXT. PARK - DAY")
        Line.objects.create(scene=scene2, order=1, type="character", text="BOB")
        Line.objects.create(scene=scene2, order=2, type="dialogue", text="Nice park.")

        url = reverse("script-analysis", kwargs={"pk": script.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        self.assertEqual(data["total_scenes"], 2)
        self.assertEqual(data["total_dialogue_lines"], 3)
        self.assertEqual(len(data["locations"]), 2)
        self.assertEqual(len(data["dialogue_balance"]), 2)

    def test_character_extraction_excludes_structural_terms(self):
        """
        Assert that structural terms (transitions, scene headings, etc.) are excluded from character extraction.
        """
        from .models import Character
        script = Script.objects.create(title="Structural Exclusions Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="INT. HOUSE - DAY")

        Line.objects.create(scene=scene, order=0, type="character", text="CUT TO:")
        Line.objects.create(scene=scene, order=1, type="character", text="FADE OUT.")
        Line.objects.create(scene=scene, order=2, type="character", text="INT. HOUSE - DAY")
        Line.objects.create(scene=scene, order=3, type="character", text="SARAH")
        Line.objects.create(scene=scene, order=4, type="dialogue", text="I am a real character.")

        url = reverse("script-extract-characters", kwargs={"pk": script.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        extracted = Character.objects.filter(script=script)
        extracted_names = [c.name.upper() for c in extracted]

        self.assertNotIn("CUT TO:", extracted_names)
        self.assertNotIn("CUT TO", extracted_names)
        self.assertNotIn("FADE OUT.", extracted_names)
        self.assertNotIn("FADE OUT", extracted_names)
        self.assertNotIn("INT. HOUSE - DAY", extracted_names)
        self.assertEqual(extracted.count(), 1)
        self.assertEqual(extracted.first().name, "Sarah")

    def test_character_extraction_merges_extensions(self):
        """
        Assert that 'JOHN' and 'JOHN (V.O.)' resolve to the same Character record.
        """
        from .models import Character
        script = Script.objects.create(title="Extension Merge Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="INT. ROOM - NIGHT")

        Line.objects.create(scene=scene, order=0, type="character", text="JOHN")
        Line.objects.create(scene=scene, order=1, type="dialogue", text="Speaking live.")
        Line.objects.create(scene=scene, order=2, type="character", text="JOHN (V.O.)")
        Line.objects.create(scene=scene, order=3, type="dialogue", text="Voice over now.")

        url = reverse("script-extract-characters", kwargs={"pk": script.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        extracted = Character.objects.filter(script=script)
        self.assertEqual(extracted.count(), 1)
        self.assertEqual(extracted.first().name, "John")

    def test_character_extraction_excludes_montage_and_close_on(self):
        """
        Assert that 'MONTAGE' and 'CLOSE ON' are excluded from character extraction.
        """
        from .models import Character
        script = Script.objects.create(title="Montage and Close On Test", owner=self.user)
        scene = Scene.objects.create(script=script, order=0, heading="EXT. STREET - DAY")

        Line.objects.create(scene=scene, order=0, type="character", text="MONTAGE")
        Line.objects.create(scene=scene, order=1, type="character", text="CLOSE ON")
        Line.objects.create(scene=scene, order=2, type="character", text="DAVID")
        Line.objects.create(scene=scene, order=3, type="dialogue", text="Hello.")

        url = reverse("script-extract-characters", kwargs={"pk": script.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        extracted = Character.objects.filter(script=script)
        extracted_names = [c.name.upper() for c in extracted]

        self.assertNotIn("MONTAGE", extracted_names)
        self.assertNotIn("CLOSE ON", extracted_names)
        self.assertEqual(extracted.count(), 1)
        self.assertEqual(extracted.first().name, "David")

    def test_title_page_crud(self):
        from .models import TitlePage
        script = Script.objects.create(title="Title Page Test", owner=self.user)
        
        # Create TitlePage via API
        url = reverse("title_page-list")
        data = {
            "script": script.pk,
            "title": "Chinatown",
            "credit": "written by",
            "author": "Robert Towne",
            "source": "Original Screenplay",
            "contact": "CAA Beverly Hills",
            "draft_date": "October 9, 1973",
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TitlePage.objects.filter(script=script).count(), 1)

        tp = TitlePage.objects.get(script=script)
        self.assertEqual(tp.title, "Chinatown")
        self.assertEqual(tp.author, "Robert Towne")

        # Retrieve Script Detail and verify nested title page
        script_url = reverse("script-detail", kwargs={"pk": script.pk})
        script_res = self.client.get(script_url)
        self.assertEqual(script_res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(script_res.json().get("title_page"))
        self.assertEqual(script_res.json()["title_page"]["author"], "Robert Towne")

    def test_script_revision_crud(self):
        from .models import ScriptRevision, RevisionColor
        script = Script.objects.create(title="Revision Test", owner=self.user)

        url = reverse("revision-list")
        data = {
            "script": script.pk,
            "color": RevisionColor.BLUE,
            "name": "Second Draft - Blue Pages",
            "notes": "Tightened Act II-B sequence.",
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ScriptRevision.objects.filter(script=script).count(), 1)

        rev = ScriptRevision.objects.get(script=script)
        self.assertEqual(rev.color, RevisionColor.BLUE)
        self.assertEqual(rev.get_color_display(), "Blue (Second Draft)")

        # Verify in script detail
        script_url = reverse("script-detail", kwargs={"pk": script.pk})
        script_res = self.client.get(script_url)
        self.assertEqual(len(script_res.json()["revisions"]), 1)
        self.assertEqual(script_res.json()["revisions"][0]["color_display"], "Blue (Second Draft)")

    def test_beat_act_and_polarity(self):
        from .models import Beat
        script = Script.objects.create(title="Beat Metadata Test", owner=self.user)

        url = reverse("beat-list")
        data = {
            "script": script.pk,
            "name": "Midpoint Climax",
            "order": 5,
            "act": "act_2a",
            "emotional_polarity": "+/-",
            "synopsis": "The protagonist gains the treasure but loses their mentor.",
            "color_tag": "#ff6b6b",
            "target_page": 55.0,
        }
        res = self.client.post(url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        beat = Beat.objects.get(script=script, name="Midpoint Climax")
        self.assertEqual(beat.act, "act_2a")
        self.assertEqual(beat.emotional_polarity, "+/-")
        self.assertEqual(beat.target_page, 55.0)

    def test_fountain_full_title_page_parsing(self):
        from .fountain import parse_fountain_document, serialize_to_fountain
        fountain_doc = (
            "Title: THE GODFATHER\n"
            "Credit: Screenplay by\n"
            "Author: Mario Puzo and Francis Ford Coppola\n"
            "Source: Based on the novel by Mario Puzo\n"
            "Draft date: March 29, 1971\n"
            "Contact:\n"
            "\tParamount Pictures\n"
            "\tHollywood, CA\n\n"
            "INT. DON CORLEONE'S OFFICE - DAY\n\n"
            "BONASERA\n"
            "I believe in America.\n"
        )
        parsed = parse_fountain_document(fountain_doc)
        tp = parsed["title_page"]
        self.assertEqual(tp["title"], "THE GODFATHER")
        self.assertEqual(tp["credit"], "Screenplay by")
        self.assertEqual(tp["author"], "Mario Puzo and Francis Ford Coppola")
        self.assertEqual(tp["source"], "Based on the novel by Mario Puzo")
        self.assertEqual(tp["draft_date"], "March 29, 1971")
        self.assertIn("Paramount Pictures", tp["contact"])

        # Check scene
        self.assertEqual(len(parsed["scenes"]), 1)
        self.assertEqual(parsed["scenes"][0]["heading"], "INT. DON CORLEONE'S OFFICE - DAY")

        # Check serialization roundtrip
        serialized = serialize_to_fountain(parsed["scenes"], parsed["title_page"])
        self.assertIn("Title: THE GODFATHER", serialized)
        self.assertIn("Author: Mario Puzo and Francis Ford Coppola", serialized)
        self.assertIn("INT. DON CORLEONE'S OFFICE - DAY", serialized)

    def test_fountain_dual_dialogue_parsing_and_serialization(self):
        from .fountain import parse_fountain_document, serialize_to_fountain
        fountain_text = (
            "INT. APARTMENT - NIGHT\n\n"
            "BRICK\n"
            "Stay out of my way!\n\n"
            "STEEL ^\n"
            "Make me, Brick!"
        )
        parsed = parse_fountain_document(fountain_text)
        scene = parsed["scenes"][0]
        lines = scene["lines"]
        
        # 1. scene_heading, 2. BRICK (left), 3. Dialogue (left), 4. STEEL (right), 5. Dialogue (right)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[1]["text"], "BRICK")
        self.assertTrue(lines[1]["is_dual_dialogue"])
        self.assertEqual(lines[1]["dual_pos"], "left")

        self.assertEqual(lines[2]["text"], "Stay out of my way!")
        self.assertTrue(lines[2]["is_dual_dialogue"])
        self.assertEqual(lines[2]["dual_pos"], "left")

        self.assertEqual(lines[3]["text"], "STEEL")
        self.assertTrue(lines[3]["is_dual_dialogue"])
        self.assertEqual(lines[3]["dual_pos"], "right")

        self.assertEqual(lines[4]["text"], "Make me, Brick!")
        self.assertTrue(lines[4]["is_dual_dialogue"])
        self.assertEqual(lines[4]["dual_pos"], "right")

        # Serializer should attach caret ^ to right character
        serialized = serialize_to_fountain(parsed["scenes"])
        self.assertIn("STEEL ^", serialized)

    def test_fountain_scene_numbers_and_synopsis(self):
        from .fountain import parse_fountain_document
        fountain_text = (
            "INT. WAREHOUSE - NIGHT #14A#\n"
            "= Jack searches for the contraband shipments.\n\n"
            "Jack kicks open a wooden crate.\n"
        )
        parsed = parse_fountain_document(fountain_text)
        scene = parsed["scenes"][0]
        self.assertEqual(scene["heading"], "INT. WAREHOUSE - NIGHT")
        self.assertEqual(scene["scene_number"], "14A")
        self.assertEqual(scene["synopsis"], "Jack searches for the contraband shipments.")
        self.assertEqual(len(scene["lines"]), 2) # heading, action

    def test_fountain_forced_elements(self):
        from .fountain import parse_fountain_document
        fountain_text = (
            ".TOP OF THE MOUNTAIN\n\n"
            "@CHOPPER\n"
            "Get to the chopper!\n\n"
            "!ALL CAPS ACTION LINE THAT SHOULD NOT BE A CHARACTER\n\n"
            "> SMASH CUT TO: <\n"
        )
        parsed = parse_fountain_document(fountain_text)
        scene = parsed["scenes"][0]
        self.assertEqual(scene["heading"], "TOP OF THE MOUNTAIN")
        line_types = [l["type"] for l in scene["lines"]]
        self.assertEqual(line_types, ["scene_heading", "character", "dialogue", "action", "action"])
        self.assertEqual(scene["lines"][1]["text"], "CHOPPER")

    def test_fountain_serialization_with_scene_numbers_and_notes(self):
        from .fountain import serialize_to_fountain
        scenes_data = [
            {
                "order": 0,
                "scene_number": "10B",
                "heading": "INT. SUBWAY CAR - NIGHT",
                "synopsis": "The train suddenly screeches to a halt.",
                "notes": "Ensure dim emergency red lighting.",
                "lines": [
                    {"order": 0, "type": "scene_heading", "text": "INT. SUBWAY CAR - NIGHT"},
                    {"order": 1, "type": "action", "text": "Passengers grip the handrails."},
                ]
            }
        ]
        serialized = serialize_to_fountain(scenes_data)
        self.assertIn("INT. SUBWAY CAR - NIGHT #10B#", serialized)
        self.assertIn("= The train suddenly screeches to a halt.", serialized)
        self.assertIn("[[ Ensure dim emergency red lighting. ]]", serialized)
        self.assertIn("Passengers grip the handrails.", serialized)



