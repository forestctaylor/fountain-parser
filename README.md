# fountain-parser

A fast, lightweight, zero-dependency, typed AST parser for the [Fountain](https://fountain.io) screenplay format in Python.

Built with Python standard library `@dataclass` models and strict adherence to the Fountain 1.1 specification.

## Features

- **Zero Third-Party Dependencies:** Pure Python standard library (`dataclasses`, `enum`, `typing`, `re`).
- **Fully Typed:** Complete type hinting for all AST nodes.
- **Spec-Compliant:** Supports Title Pages, Scene Headings (forced & unforced), Characters, Extensions (V.O., O.S.), Dual Dialogue (`^`), Parentheticals, Dialogue, Transitions, Actions, Sections, Synopses, Page Breaks, and Boneyards.
- **Scene-Level Grouping:** Convenience `.scenes` and `.dialogue_blocks` properties for instant pipeline consumption.

## Installation

```bash
pip install fountain-parser
```

*(Or for local development: `pip install -e .`)*

## Quick Start

```python
from fountain_parser import parse

script = """
Title: The Diner
Author: Forest Taylor

INT. DINER - NIGHT #1#

Jacob sits across from Violet.

JACOB
(whispering)
Vi, I'm sorry.

VIOLET
(coldly)
You should be.
"""

screenplay = parse(script)

# Title page metadata
print(screenplay.title_page["Title"])  # ['The Diner']

# Access grouped scenes
for scene in screenplay.scenes:
    print(scene.heading.text)  # "INT. DINER - NIGHT"
    print(scene.heading.scene_number)  # "1"

    # Iterate over dialogue blocks
    for block in scene.dialogue_blocks:
        print(f"{block.character.name}: {block.spoken_text}")
        # JACOB: Vi, I'm sorry.
        # VIOLET: You should be.
```
