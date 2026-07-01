"""
Custom Cognee DataPoint subclasses for Ravenwood Manor.

Node types  : CharacterNode, FactNode, LocationNode, ClueNode, EventNode
Edge types  : set via List[OtherNode] fields — Cognee uses the field name as the
              relationship label in the graph (e.g. `knows_fact` → KNOWS_FACT edge).

Import path confirmed in Phase 0:
  from cognee.infrastructure.engine import DataPoint
  from cognee.tasks.storage.add_data_points import add_data_points
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import SkipValidation
from cognee.infrastructure.engine import DataPoint


class FactNode(DataPoint):
    """A discrete piece of knowledge in the world."""
    name: str                       # fact_id — used as the lookup key
    statement: str                  # the actual fact text
    is_solution: bool = False       # True if this is part of motive/means/opportunity
    metadata: dict = {"index_fields": ["name", "statement"]}


class LocationNode(DataPoint):
    """A room or area in Ravenwood Manor."""
    name: str
    description: str
    metadata: dict = {"index_fields": ["name", "description"]}


class EventNode(DataPoint):
    """A timestamped event on the night's timeline."""
    name: str           # event_id
    description: str
    time: str
    metadata: dict = {"index_fields": ["name", "description", "time"]}


class ClueNode(DataPoint):
    """A physical clue the player can discover."""
    name: str           # clue_id
    description: str
    # typed edges set after construction
    located_in: SkipValidation[Any] = None      # → LocationNode
    supports_fact: SkipValidation[Any] = None   # → FactNode
    metadata: dict = {"index_fields": ["name", "description"]}


class CharacterNode(DataPoint):
    """An NPC — suspect, witness, or staff."""
    name: str
    character_id: str   # slug like "ashworth_gerald"
    role: str
    public_persona: str
    alibi: str
    alibi_is_true: bool
    # Character → Character relationships (SkipValidation avoids self-ref issues)
    knows: SkipValidation[Any] = None           # list[CharacterNode]
    allied_with: SkipValidation[Any] = None     # list[CharacterNode]
    resents: SkipValidation[Any] = None         # list[CharacterNode]
    family_of: SkipValidation[Any] = None       # list[CharacterNode]
    owes_debt_to: SkipValidation[Any] = None    # list[CharacterNode]
    blackmails: SkipValidation[Any] = None      # list[CharacterNode]
    # Character → Fact relationships
    knows_fact: SkipValidation[Any] = None      # list[FactNode]
    lies_about_fact: SkipValidation[Any] = None # list[FactNode]
    metadata: dict = {"index_fields": ["name", "role", "public_persona", "alibi"]}


class PlayerNode(DataPoint):
    """Runtime node tracking what the player has learned."""
    name: str = "Detective"
    # grows at runtime via remember()
    learned_fact: SkipValidation[Any] = None    # list[FactNode]
    standing: SkipValidation[Any] = None        # list[CharacterNode] with stance attr
    metadata: dict = {"index_fields": ["name"]}
