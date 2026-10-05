from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union


class ElementType(str, Enum):
    SCENE_HEADING = "scene_heading"
    ACTION = "action"
    CHARACTER = "character"
    PARENTHETICAL = "parenthetical"
    DIALOGUE = "dialogue"
    TRANSITION = "transition"
    SECTION_HEADING = "section_heading"
    SYNOPSIS = "synopsis"
    PAGE_BREAK = "page_break"
    BONEYARD = "boneyard"


@dataclass(frozen=True)
class SceneHeading:
    text: str
    scene_number: Optional[str] = None
    is_forced: bool = False
    element_type: ElementType = ElementType.SCENE_HEADING


@dataclass(frozen=True)
class Action:
    text: str
    element_type: ElementType = ElementType.ACTION


@dataclass(frozen=True)
class Character:
    name: str
    extensions: List[str] = field(default_factory=list)  # e.g., ["V.O.", "CONT'D"]
    is_dual: bool = False                                 # Dual dialogue indicated by trailing ^
    element_type: ElementType = ElementType.CHARACTER

    @property
    def extension(self) -> Optional[str]:
        """Convenience property returning all extensions joined, or None if empty."""
        return " ".join(self.extensions) if self.extensions else None


@dataclass(frozen=True)
class Parenthetical:
    text: str
    element_type: ElementType = ElementType.PARENTHETICAL


@dataclass(frozen=True)
class Dialogue:
    text: str
    element_type: ElementType = ElementType.DIALOGUE


@dataclass(frozen=True)
class Transition:
    text: str
    is_forced: bool = False
    element_type: ElementType = ElementType.TRANSITION


@dataclass(frozen=True)
class SectionHeading:
    text: str
    level: int = 1
    element_type: ElementType = ElementType.SECTION_HEADING


@dataclass(frozen=True)
class Synopsis:
    text: str
    element_type: ElementType = ElementType.SYNOPSIS


@dataclass(frozen=True)
class PageBreak:
    element_type: ElementType = ElementType.PAGE_BREAK


@dataclass(frozen=True)
class Boneyard:
    text: str
    element_type: ElementType = ElementType.BONEYARD


ScreenplayElement = Union[
    SceneHeading,
    Action,
    Character,
    Parenthetical,
    Dialogue,
    Transition,
    SectionHeading,
    Synopsis,
    PageBreak,
    Boneyard,
]


@dataclass
class DialogueBlock:
    """Grouped character speech block: character cue followed by parentheticals/dialogue lines."""
    character: Character
    lines: List[Union[Parenthetical, Dialogue]] = field(default_factory=list)

    @property
    def spoken_text(self) -> str:
        """Returns the joined spoken dialogue text, excluding parentheticals."""
        return " ".join(line.text for line in self.lines if isinstance(line, Dialogue))


@dataclass
class Scene:
    """Convenience structure grouping elements under a scene heading."""
    heading: SceneHeading
    elements: List[ScreenplayElement] = field(default_factory=list)

    @property
    def dialogue_blocks(self) -> List[DialogueBlock]:
        """Extracts dialogue blocks within this scene."""
        blocks: List[DialogueBlock] = []
        current_block: Optional[DialogueBlock] = None

        for element in self.elements:
            if isinstance(element, Character):
                if current_block:
                    blocks.append(current_block)
                current_block = DialogueBlock(character=element)
            elif isinstance(element, (Dialogue, Parenthetical)):
                if current_block:
                    current_block.lines.append(element)
            else:
                if current_block:
                    blocks.append(current_block)
                    current_block = None

        if current_block:
            blocks.append(current_block)

        return blocks


@dataclass
class Screenplay:
    """The root AST node representing a complete parsed Fountain screenplay."""
    title_page: Dict[str, List[str]] = field(default_factory=dict)
    elements: List[ScreenplayElement] = field(default_factory=list)

    @property
    def scenes(self) -> List[Scene]:
        """Groups screenplay elements by SceneHeading, creating a PROLOGUE if scenes begin before a heading."""
        scene_list: List[Scene] = []
        current_scene: Optional[Scene] = None

        for elem in self.elements:
            if isinstance(elem, SceneHeading):
                if current_scene:
                    scene_list.append(current_scene)
                current_scene = Scene(heading=elem)
            else:
                if current_scene is None:
                    current_scene = Scene(heading=SceneHeading(text="PROLOGUE"))
                current_scene.elements.append(elem)

        if current_scene:
            scene_list.append(current_scene)

        return scene_list
