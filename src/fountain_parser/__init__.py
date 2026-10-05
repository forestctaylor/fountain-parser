"""fountain-parser: A lightweight, zero-dependency, typed AST parser for Fountain."""

from fountain_parser.ast import (
    Action,
    Boneyard,
    Character,
    Dialogue,
    DialogueBlock,
    ElementType,
    PageBreak,
    Parenthetical,
    Scene,
    SceneHeading,
    Screenplay,
    ScreenplayElement,
    SectionHeading,
    Synopsis,
    Transition,
)
from fountain_parser.parser import FountainParser, parse

__version__ = "0.1.0"

__all__ = [
    "FountainParser",
    "parse",
    "Screenplay",
    "Scene",
    "DialogueBlock",
    "ScreenplayElement",
    "ElementType",
    "SceneHeading",
    "Action",
    "Character",
    "Parenthetical",
    "Dialogue",
    "Transition",
    "SectionHeading",
    "Synopsis",
    "PageBreak",
    "Boneyard",
]
