import unittest
import sys
import os

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fountain_parser import (
    parse,
    SceneHeading,
    Action,
    Character,
    Parenthetical,
    Dialogue,
    Transition,
    PageBreak,
    Boneyard,
    SectionHeading,
    Synopsis,
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

        # Forced scene
        self.assertIsInstance(screenplay.elements[0], SceneHeading)
        self.assertTrue(screenplay.elements[0].is_forced)
        self.assertEqual(screenplay.elements[0].text, "UNDERGROUND BUNKER")

        # Forced character
        self.assertIsInstance(screenplay.elements[1], Character)
        self.assertEqual(screenplay.elements[1].name, "GENERAL")

        # Dialogue
        self.assertIsInstance(screenplay.elements[2], Dialogue)
        self.assertEqual(screenplay.elements[2].text, "Attack at dawn!")

        # Forced transition
        self.assertIsInstance(screenplay.elements[3], Transition)
        self.assertTrue(screenplay.elements[3].is_forced)
        self.assertEqual(screenplay.elements[3].text, "FADE TO BLACK.")

    def test_boneyard_and_sections(self):
        text = """
# ACT I

/* This is a boneyard note */

= Introduce our heroes.

===
"""
        screenplay = parse(text)
        self.assertIsInstance(screenplay.elements[0], SectionHeading)
        self.assertEqual(screenplay.elements[0].text, "ACT I")
        self.assertEqual(screenplay.elements[0].level, 1)

        self.assertIsInstance(screenplay.elements[1], Boneyard)
        self.assertIn("This is a boneyard note", screenplay.elements[1].text)

        self.assertIsInstance(screenplay.elements[2], Synopsis)
        self.assertEqual(screenplay.elements[2].text, "Introduce our heroes.")

        self.assertIsInstance(screenplay.elements[3], PageBreak)


if __name__ == "__main__":
    unittest.main()
