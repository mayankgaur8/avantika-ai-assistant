"""
Backend mirror contracts for agent service outputs.

Purpose:
  The agent service (crew.py) validates its own output against strict Pydantic
  schemas before returning.  This module provides a *second*, independent
  validation layer inside the backend API.

Why two layers?
  - The agent service and backend are separate processes.  Schema drift between
    them can go unnoticed.  Validating here catches any mismatch before broken
    data reaches the database.
  - These contracts are intentionally *looser* than the agent-side schemas.
    They verify only the fields the backend actually reads or writes to DB
    columns.  Strict list-length enforcement lives in crew.py; here we only
    guard correctness.

Usage:
  from app.schemas.agent_outputs import validate_agent_response

  # Raises pydantic.ValidationError on failure.
  validate_agent_response("translate", result_data)
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Content contracts — minimum required fields per task type
# ---------------------------------------------------------------------------

class TranslationContentContract(BaseModel):
    """
    Minimum fields the backend needs from a translate response.
    The backend saves primary_translation as a quick-access column and
    stores the full output in output_data (JSON).
    """
    primary_translation: str = Field(min_length=1)
    pronunciation: str = Field(min_length=1)
    alternatives: list[str] = Field(min_length=1)
    vocabulary: list[dict[str, Any]] = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)


class LearnContentContract(BaseModel):
    """
    Minimum fields the backend needs from a learn response.
    lesson_title and vocabulary are stored as indexed lesson metadata.
    exercises are required to exist before saving (they drive progress tracking).
    """
    lesson_title: str = Field(min_length=1)
    vocabulary: list[dict[str, Any]] = Field(min_length=1)
    exercises: list[dict[str, Any]] = Field(min_length=1)
    grammar: dict[str, Any]
    cultural_tip: str = Field(min_length=1)

    @field_validator("exercises")
    @classmethod
    def exercises_have_answers(cls, v: list[dict]) -> list[dict]:
        # Every exercise must carry an answer — otherwise progress tracking
        # cannot score the session server-side.
        for i, ex in enumerate(v):
            if "answer" not in ex:
                raise ValueError(f"Exercise at index {i} is missing the 'answer' field")
        return v


class TravelContentContract(BaseModel):
    """
    Minimum fields the backend needs from a travel response.
    essential_phrases and emergency_phrase are the safety-critical outputs.
    """
    scenario_type: str = Field(min_length=1)
    essential_phrases: list[dict[str, Any]] = Field(min_length=1)
    emergency_phrase: str = Field(min_length=1)
    dialogue: list[dict[str, Any]] = Field(min_length=1)

    @field_validator("essential_phrases")
    @classmethod
    def phrases_have_translation(cls, v: list[dict]) -> list[dict]:
        for i, phrase in enumerate(v):
            if "phrase" not in phrase or "translation" not in phrase:
                raise ValueError(
                    f"essential_phrases[{i}] missing 'phrase' or 'translation'"
                )
        return v


class CoachContentContract(BaseModel):
    """
    Minimum fields the backend needs from a coach response.
    improved_version is always stored; professional_vocabulary drives the
    vocabulary-chip display in the frontend.
    """
    coaching_type: str = Field(min_length=1)
    improved_version: str = Field(min_length=1)
    professional_vocabulary: list[dict[str, Any]] = Field(min_length=1)
    confidence_tips: list[str] = Field(min_length=1)

    @field_validator("professional_vocabulary")
    @classmethod
    def vocab_has_term(cls, v: list[dict]) -> list[dict]:
        for i, item in enumerate(v):
            if "term" not in item:
                raise ValueError(f"professional_vocabulary[{i}] missing 'term'")
        return v


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Maps task_type string → its content contract class.
# curriculum and culture are not included because the backend saves their
# full output as-is without field-level reads; basic non-empty check is enough.
_CONTENT_CONTRACTS: dict[str, type[BaseModel]] = {
    "translate": TranslationContentContract,
    "learn": LearnContentContract,
    "travel": TravelContentContract,
    "coach": CoachContentContract,
}


# ---------------------------------------------------------------------------
# Public validator
# ---------------------------------------------------------------------------

def validate_agent_response(task_type: str, data: dict[str, Any]) -> None:
    """
    Validate the agent response dict against the task-specific content contract.

    Accepts both response shapes:
      - Metadata envelope:  {"task_type": "...", "content": {...}, ...}
      - Flat (legacy):      {"primary_translation": "...", ...}

    When a "content" key is present, only the content sub-dict is validated.
    This matches the shape produced by the updated crew.py.

    Raises pydantic.ValidationError if required fields are missing or invalid.
    No-ops for task types without a registered contract (curriculum, culture).
    """
    contract_cls = _CONTENT_CONTRACTS.get(task_type)
    if contract_cls is None:
        # No contract registered — accept as-is.  curriculum and culture
        # outputs are saved wholesale without field inspection.
        return

    # Prefer the content sub-object when the metadata envelope is present.
    payload = data.get("content") if "content" in data else data

    if not isinstance(payload, dict) or not payload:
        from pydantic import ValidationError as PydanticValidationError
        raise ValueError(
            f"Agent response for task_type='{task_type}' has an empty or "
            f"non-dict content payload.  Raw keys: {list(data.keys())}"
        )

    # model_validate raises pydantic.ValidationError on failure — callers
    # catch this and return HTTP 502.
    contract_cls.model_validate(payload)
