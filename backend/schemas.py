from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,40}$")


class SignupPayload(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    institution_name: str = Field(min_length=2, max_length=180)
    department: str | None = Field(default=None, max_length=120)
    designation: str | None = Field(default=None, max_length=120)
    signup_reason: str | None = Field(default=None, max_length=1200)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("Use 3-40 letters, numbers, dots, underscores, or hyphens")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginPayload(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class ReviewPayload(BaseModel):
    decision: Literal["approved", "denied"]
    admin_note: str | None = Field(default=None, max_length=1200)


class EntityPayload(BaseModel):
    payload: Any


class ConstraintUpdate(BaseModel):
    constraint_key: str
    enabled: bool
    mode: Literal["hard", "soft", "off"]
    weight: float = Field(default=1.0, ge=0, le=10)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ConstraintUpdatePayload(BaseModel):
    constraints: list[ConstraintUpdate]


class DatasetImportPayload(BaseModel):
    dataset: dict[str, Any]
    replace: bool = True
