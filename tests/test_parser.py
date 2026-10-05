import os
import sys
import unittest

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fountain_parser import (
    Action,
    Boneyard,
    Character,
    Dialogue,
    PageBreak,
    Parenthetical,
    SceneHeading,
    SectionHeading,
    Synopsis,
    Transition,
    parse,
)


class TestFountainParser(unittest.TestCase):

    def test_title_page(self):
        text = """Title: Prevue Pilot
Author: Forest Taylor
Draft date: October 2026

EXT. CITY STREET - DAY
"""
        screenplay = parse(text)
        self.assertEqual(screenplay.title_page.get("Title"), ["Prevue Pilot"])
        self.assertEqual(screenplay.title_page.get("Author"), ["Forest Taylor"])
        self.assertEqual(screenplay.title_page.get("Draft Date"), ["October 2026"])
        self.assertEqual(len(screenplay.elements), 1)
        self.assertIsInstance(screenplay.elements[0], SceneHeading)
        self.assertEqual(screenplay.elements[0].text, "EXT. CITY STREET - DAY")

    def test_scenes_and_dialogue(self):
        text = """INT. DINER - NIGHT #1#

Jacob sits across from Violet, looking exhausted.

JACOB
(whispering)
Vi, I'm sorry.

VIOLET
(coldly)
You should be.

> FADE OUT.
"""
        screenplay = parse(text)
        scenes = screenplay.scenes
        self.assertEqual(len(scenes), 1)
        scene = scenes[0]

        # Check Heading
        self.assertIsNotNone(scene.heading)
        self.assertEqual(scene.heading.text, "INT. DINER - NIGHT")
        self.assertEqual(scene.heading.scene_number, "1")

        # Check Dialogue Blocks
        blocks = scene.dialogue_blocks
        self.assertEqual(len(blocks), 2)

        # Jacob's block
        self.assertEqual(blocks[0].character.name, "JACOB")
        self.assertEqual(blocks[0].spoken_text, "Vi, I'm sorry.")
        self.assertEqual(len(blocks[0].lines), 2)
        self.assertIsInstance(blocks[0].lines[0], Parenthetical)
        self.assertEqual(blocks[0].lines[0].text, "(whispering)")
        self.assertIsInstance(blocks[0].lines[1], Dialogue)

        # Violet's block
        self.assertEqual(blocks[1].character.name, "VIOLET")
        self.assertEqual(blocks[1].spoken_text, "You should be.")

    def test_forced_elements(self):
        text = """
.UNDERGROUND BUNKER

@GENERAL
Attack at dawn!

> FADE TO BLACK.
"""
        screenplay = parse(text)
        self.assertEqual(len(screenplay.elements), 4)

        self.assertIsInstance(screenplay.elements[0], SceneHeading)
        self.assertTrue(screenplay.elements[0].is_forced)
        self.assertEqual(screenplay.elements[0].text, "UNDERGROUND BUNKER")

        self.assertIsInstance(screenplay.elements[1], Character)
        self.assertEqual(screenplay.elements[1].name, "GENERAL")

        self.assertIsInstance(screenplay.elements[2], Dialogue)
        self.assertEqual(screenplay.elements[2].text, "Attack at dawn!")

        self.assertIsInstance(screenplay.elements[3], Transition)
        self.assertTrue(screenplay.elements[3].is_forced)
        self.assertEqual(screenplay.elements[3].text, "FADE TO BLACK.")

    def test_big_fish_real_world_sample(self):
        big_fish_path = os.path.join(os.path.dirname(__file__), "Big-Fish.fountain")
        self.assertTrue(os.path.exists(big_fish_path))

        with open(big_fish_path, "r", encoding="utf-8") as f:
            screenplay = parse(f.read())

        # Title Page
        self.assertEqual(screenplay.title_page.get("Title"), ["Big Fish"])
        self.assertEqual(screenplay.title_page.get("Author"), ["John August"])
        self.assertEqual(screenplay.title_page.get("Credit"), ["written by"])

        # Epigraph / Front Matter
        self.assertEqual(
            screenplay.epigraph,
            "This is a Southern story, full of lies and fabrications, but truer for their inclusion.",
        )

        # Scenes & Total Elements
        scenes = screenplay.scenes
        self.assertGreater(len(scenes), 150)
        self.assertGreater(len(screenplay.elements), 2000)

        # First Scene (opening sequence before first explicit scene heading)
        first_scene = scenes[0]
        self.assertIsNone(first_scene.heading)
        self.assertIsInstance(first_scene.elements[0], Transition)
        self.assertEqual(first_scene.elements[0].text, "**FADE IN:**")

        # Second Scene (Will's Bedroom)
        bedroom_scene = scenes[1]
        self.assertIsNotNone(bedroom_scene.heading)
        self.assertEqual(bedroom_scene.heading.text, "INT.  WILL'S BEDROOM - NIGHT (1973)")
        self.assertEqual(len(bedroom_scene.dialogue_blocks), 1)
        self.assertEqual(bedroom_scene.dialogue_blocks[0].character.name, "EDWARD")
        self.assertIn("trying to catch that fish", bedroom_scene.dialogue_blocks[0].spoken_text)


if __name__ == "__main__":
    unittest.main()
