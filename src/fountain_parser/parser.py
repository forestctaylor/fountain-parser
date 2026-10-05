import re
from typing import Dict, List, Optional, Tuple

from fountain_parser.ast import (
    Action,
    Boneyard,
    Character,
    Dialogue,
    PageBreak,
    Parenthetical,
    SceneHeading,
    Screenplay,
    ScreenplayElement,
    SectionHeading,
    Synopsis,
    Transition,
)

# Regex Patterns for Fountain Specification
RE_SCENE_PREFIX = re.compile(
    r"^(INT\.|EXT\.|INT/EXT\.|INT / EXT\.|I/E\.|EST\.)", re.IGNORECASE
)
RE_SCENE_NUMBER = re.compile(r"#([^#]+)#\s*$")
RE_TRANSITION_SUFFIX = re.compile(r"TO:\s*$", re.IGNORECASE)
RE_CHARACTER_EXTENSION = re.compile(r"\s*(\([^\)]+\))\s*$")
RE_PAGE_BREAK = re.compile(r"^={3,}\s*$")
RE_SECTION = re.compile(r"^(#+)\s*(.*)")
RE_SYNOPSIS = re.compile(r"^=\s*(.*)")


class FountainParser:
    """Parses Fountain screenplay text into a typed Abstract Syntax Tree (AST)."""

    def __init__(self, strict: bool = False):
        self.strict = strict

    def parse(self, text: str) -> Screenplay:
        """Parses a full Fountain screenplay string into a Screenplay AST."""
        # Normalize newlines
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 1. Parse Title Page (if present at the top)
        title_page, script_text = self._extract_title_page(normalized_text)

        # 2. Extract and handle elements
        elements = self._parse_elements(script_text)

        return Screenplay(title_page=title_page, elements=elements)

    def _extract_title_page(self, text: str) -> Tuple[Dict[str, List[str]], str]:
        """Extracts title page key-values according to Fountain spec."""
        lines = text.split("\n")
        title_page: Dict[str, List[str]] = {}
        current_key: Optional[str] = None
        index = 0

        # Title page must start on the first non-empty line
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                if current_key is not None:
                    # An empty line after title page fields terminates the title page
                    index = i + 1
                    break
                continue

            # Title page keys: e.g. "Title: The Big Movie" or "Draft date:"
            if ":" in line and not line.startswith("..") and not stripped.isupper():
                parts = line.split(":", 1)
                potential_key = parts[0].strip().title()
                val = parts[1].strip()
                current_key = potential_key
                title_page.setdefault(current_key, [])
                if val:
                    title_page[current_key].append(val)
            elif current_key and (line.startswith("   ") or line.startswith("\t")):
                # Indented continuation line for current title page key
                title_page[current_key].append(stripped)
            else:
                # First non-title line encountered before an empty line
                if not title_page:
                    return {}, text
                index = i
                break

        remaining_text = "\n".join(lines[index:])
        return title_page, remaining_text

    def _parse_elements(self, text: str) -> List[ScreenplayElement]:
        """Tokenizes script text into typed ScreenplayElement instances."""
        elements: List[ScreenplayElement] = []
        raw_lines = text.split("\n")
        total_lines = len(raw_lines)
        i = 0

        in_boneyard = False
        boneyard_buffer: List[str] = []

        while i < total_lines:
            line = raw_lines[i]
            stripped = line.strip()

            # Handle Boneyard comments (/* ... */)
            if in_boneyard:
                if "*/" in line:
                    b_part, _, remaining = line.partition("*/")
                    boneyard_buffer.append(b_part)
                    elements.append(Boneyard(text="\n".join(boneyard_buffer)))
                    boneyard_buffer = []
                    in_boneyard = False
                    raw_lines[i] = remaining
                    continue
                else:
                    boneyard_buffer.append(line)
                    i += 1
                    continue

            if "/*" in line:
                before, _, b_part = line.partition("/*")
                if before.strip():
                    raw_lines[i] = before
                    in_boneyard = True
                    boneyard_buffer.append(b_part)
                    continue
                else:
                    in_boneyard = True
                    if "*/" in b_part:
                        b_text, _, rem = b_part.partition("*/")
                        elements.append(Boneyard(text=b_text))
                        in_boneyard = False
                        raw_lines[i] = rem
                        continue
                    else:
                        boneyard_buffer.append(b_part)
                        i += 1
                        continue

            if not stripped:
                i += 1
                continue

            # Page Break (=== or ====)
            if RE_PAGE_BREAK.match(stripped):
                elements.append(PageBreak())
                i += 1
                continue

            # Section Heading (# Act I)
            sec_match = RE_SECTION.match(stripped)
            if sec_match:
                level = len(sec_match.group(1))
                sec_text = sec_match.group(2).strip()
                elements.append(SectionHeading(text=sec_text, level=level))
                i += 1
                continue

            # Synopsis (= Synopsis text)
            syn_match = RE_SYNOPSIS.match(stripped)
            if syn_match:
                elements.append(Synopsis(text=syn_match.group(1).strip()))
                i += 1
                continue

            # Scene Heading (Forced or Unforced)
            is_forced_scene = stripped.startswith(".") and not stripped.startswith("..")
            is_unforced_scene = bool(RE_SCENE_PREFIX.match(stripped))

            if is_forced_scene or is_unforced_scene:
                heading_raw = stripped[1:].strip() if is_forced_scene else stripped
                scene_num = None
                num_match = RE_SCENE_NUMBER.search(heading_raw)
                if num_match:
                    scene_num = num_match.group(1)
                    heading_raw = heading_raw[: num_match.start()].strip()

                elements.append(
                    SceneHeading(
                        text=heading_raw,
                        scene_number=scene_num,
                        is_forced=is_forced_scene,
                    )
                )
                i += 1
                continue

            # Transitions (Forced: '> ...' or Unforced: '... TO:', 'FADE IN:', 'FADE OUT.')
            clean_for_trans = stripped.strip("*_").strip()
            is_forced_transition = stripped.startswith(">") and not stripped.endswith("<")
            is_unforced_transition = (
                clean_for_trans.isupper()
                and (
                    bool(RE_TRANSITION_SUFFIX.search(clean_for_trans))
                    or clean_for_trans in ("FADE IN:", "FADE OUT.", "FADE TO BLACK.")
                )
            )

            if is_forced_transition:
                elements.append(Transition(text=stripped[1:].strip(), is_forced=True))
                i += 1
                continue
            elif is_unforced_transition:
                elements.append(Transition(text=stripped, is_forced=False))
                i += 1
                continue

            # Character Cue Check
            is_forced_char = stripped.startswith("@")
            is_potential_char = False

            if is_forced_char:
                is_potential_char = True
            elif self._is_character_line(stripped):
                # Must be followed by dialogue or parenthetical on next non-empty line
                next_non_empty = self._find_next_non_empty(raw_lines, i + 1)
                if next_non_empty is not None:
                    next_str = raw_lines[next_non_empty].strip()
                    if next_str and not RE_PAGE_BREAK.match(next_str):
                        is_potential_char = True

            if is_potential_char:
                char_text = stripped[1:].strip() if is_forced_char else stripped
                is_dual = char_text.endswith("^")
                if is_dual:
                    char_text = char_text[:-1].strip()

                # Extract all character extensions (V.O., O.S., CONT'D, etc.)
                extensions: List[str] = []
                while True:
                    ext_match = RE_CHARACTER_EXTENSION.search(char_text)
                    if ext_match:
                        extensions.append(ext_match.group(1).strip("()"))
                        char_text = char_text[: ext_match.start()].strip()
                    else:
                        break
                extensions.reverse()

                elements.append(
                    Character(name=char_text, extensions=extensions, is_dual=is_dual)
                )
                i += 1

                # Parse subsequent dialogue & parenthetical lines for this character
                while i < total_lines:
                    diag_line = raw_lines[i].strip()
                    if not diag_line:
                        # Empty line marks end of this dialogue block
                        i += 1
                        break

                    if diag_line.startswith("(") and diag_line.endswith(")"):
                        elements.append(Parenthetical(text=diag_line))
                    else:
                        elements.append(Dialogue(text=diag_line))
                    i += 1
                continue

            # Action / General Description paragraph
            action_lines = [stripped]
            i += 1
            while i < total_lines:
                next_line = raw_lines[i]
                next_stripped = next_line.strip()
                if not next_stripped:
                    i += 1
                    break
                # If next line starts a new element type, break action block
                clean_next_trans = next_stripped.strip("*_").strip()
                if (
                    next_stripped.startswith(".")
                    or next_stripped.startswith("@")
                    or next_stripped.startswith("#")
                    or next_stripped.startswith("=")
                    or RE_SCENE_PREFIX.match(next_stripped)
                    or self._is_character_line(next_stripped)
                    or RE_PAGE_BREAK.match(next_stripped)
                    or clean_next_trans in ("FADE IN:", "FADE OUT.", "FADE TO BLACK.")
                    or bool(RE_TRANSITION_SUFFIX.search(clean_next_trans))
                ):
                    break
                action_lines.append(next_stripped)
                i += 1

            elements.append(Action(text=" ".join(action_lines)))

        return elements

    def _is_character_line(self, line: str) -> bool:
        """Determines if a line conforms to Fountain unforced character cue syntax."""
        if not line:
            return False
        clean = line.strip("*_").strip()
        # Characters cannot end in colons (that's a transition)
        if clean.endswith(":"):
            return False
        if clean.endswith("^"):
            clean = clean[:-1].strip()

        # Strip all trailing parentheticals
        while True:
            ext_match = RE_CHARACTER_EXTENSION.search(clean)
            if ext_match:
                clean = clean[: ext_match.start()].strip()
            else:
                break

        return (
            bool(clean)
            and clean.isupper()
            and not clean.endswith(".")
            and not bool(RE_SCENE_PREFIX.match(clean))
        )

    def _find_next_non_empty(self, lines: List[str], start_idx: int) -> Optional[int]:
        for idx in range(start_idx, len(lines)):
            if lines[idx].strip():
                return idx
        return None


def parse(text: str) -> Screenplay:
    """Convenience function to parse a Fountain string into an AST."""
    return FountainParser().parse(text)
