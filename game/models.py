"""Pydantic models for game state. Will be updated after Phase 0 API verification."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID, uuid4


class NPC(BaseModel):
    id: str
    name: str
    role: str
    public_persona: str
    secret: str
    alibi: str
    alibi_is_true: bool
    known_facts: list[str] = Field(default_factory=list)
    lies_about: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)  # npc_id → edge_type


class Clue(BaseModel):
    id: str
    description: str
    location: str
    reveals: str  # what fact this clue supports


class GameState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    current_room: str = "entrance_hall"
    player_learned_facts: list[str] = Field(default_factory=list)
    npc_standings: dict[str, str] = Field(default_factory=dict)  # npc_id → stance
    turn: int = 0
    accused: str | None = None
    game_over: bool = False
