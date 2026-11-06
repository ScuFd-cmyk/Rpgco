"""Request schemas (validated input from the browser)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

NAME_PATTERN = r"^[A-Za-z][A-Za-z '\-]{1,22}[A-Za-z]$"


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_\-]+$")
    passphrase: str = Field(min_length=6, max_length=128)


class CharacterCreate(BaseModel):
    name: str = Field(pattern=NAME_PATTERN, description="3-24 letters, spaces, ' or -")
    class_id: Literal["sentinel", "arcanist", "ranger"]


class TravelRequest(BaseModel):
    location_id: str = Field(max_length=64)
    expected_version: int | None = None


class WorldAction(BaseModel):
    character_id: int
    action: Literal["fortify"]
    expected_version: int | None = Field(
        default=None, description="If set, the action fails with 409 when the world changed since you loaded it.")
