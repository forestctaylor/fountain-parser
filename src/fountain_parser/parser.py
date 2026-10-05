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

        # 1. Parse Title Page and Front Matter (epigraph)
        title_page, epigraph, script_text = self._extract_title_page_and_epigraph(normalized_text)

        # 2. Extract and handle body elements
        elements = self._parse_elements(script_text)

        return Screenplay(title_page=title_page, epigraph=epigraph, elements=elements)

    def _extract_title_page_and_epigraph(
        self, text: str
    ) -> Tuple[Dict[str, List[str]], Optional[str], str]:
        """Extracts title page key-values and optional front-matter epigraph."""
        lines = text.split("\n")
        title_page: Dict[str, List[str]] = {}
        current_key: Optional[str] = None
        idx = 0
        total_lines = len(lines)

        # Phase 1: Extract Title Page Key-Value pairs
        while idx < total_lines:
            line = lines[idx]
            stripped = line.strip()

            if not stripped:
                if current_key is not None:
                    # An empty line after keys marks end of the key-value block
                    idx += 1
                    break
                idx += 1
                continue

            if ":" in line and not line.startswith("..") and not stripped.isupper():
                parts = line.split(":", 1)
                potential_key = parts[0].strip().title()
                val = parts[1].strip()
                current_key = potential_key
                title_page.setdefault(current_key, [])
                if val:
                    title_page[current_key].append(val)
            elif current_key and (line.startswith("   ") or line.startswith("\t")):
                # Indented continuation line
                title_page[current_key].append(stripped)
            else:
                # First non-title line encountered
                if not title_page:
                    return {}, None, text
                break
            idx += 1

        if not title_page:
            return {}, None, text

        # Phase 2: Check for Front-Matter / Epigraph before the first page break
        epigraph_lines: List[str] = []
        epigraph_found = False
        remaining_idx = idx

        for i in range(idx, total_lines):
            line = lines[i]
            stripped = line.strip()

            if RE_PAGE_BREAK.match(stripped):
                # Page break marks end of title/front-matter sequence
                epigraph_found = bool(epigraph_lines)
                remaining_idx = i + 1
                break
            elif stripped.startswith(".") or RE_SCENE_PREFIX.match(stripped) or stripped.startswith(">") or stripped.endswith("TO:"):
                # Hit actual screenplay elements before any page break
                break
            elif stripped:
                epigraph_lines.append(stripped)

        epigraph = "\n".join(epigraph_lines) if epigraph_found else None
        if not epigraph_found:
            # No epigraph with page-break; script body continues from after title keys
            remaining_idx = idx

        remaining_text = "\n".join(lines[remaining_idx:])
        return title_page, epigraph, remaining_text

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

            # Centered Text (> ... <)
            if stripped.startswith(">") and stripped.endswith("<"):
                elements.append(Action(text=stripped[1:-1].strip(), is_centered=True))
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
                # Fountain Spec Invariant: A character cue MUST be followed immediately
                # on the VERY NEXT LINE (no blank lines) by dialogue or parentheticals.
                if i + 1 < total_lines:
                    next_line_stripped = raw_lines[i + 1].strip()
                    if next_line_stripped and not RE_PAGE_BREAK.match(next_line_stripped):
                        # Ensure next line is not another heading, transition, etc.
                        clean_next = next_line_stripped.strip("*_").strip()
                        if (
                            not clean_next.endswith("TO:")
                            and clean_next not in ("FADE IN:", "FADE OUT.", "FADE TO BLACK.")
                            and not RE_SCENE_PREFIX.match(next_line_stripped)
                            and not next_line_stripped.startswith(".")
                        ):
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
                    or (next_stripped.startswith(">") and next_stripped.endswith("<"))
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
        # Characters cannot start with > or end in colons/angles
        if clean.startswith(">") or clean.endswith("<") or clean.endswith(":"):
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


def parse(text: str) -> Screenplay:
    """Convenience function to parse a Fountain string into an AST."""
    return FountainParser().parse(text)
