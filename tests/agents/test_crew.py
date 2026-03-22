"""
Agent crew unit tests — no real LLM calls, tests routing and output parsing.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from agents.crew import AgentInput, AvantikaLanguageCrew, TaskType


MOCK_TRANSLATION_JSON = json.dumps({
    "primary_translation": "Bonjour",
    "literal_translation": "Good day",
    "pronunciation": "Bo-zhoor",
    "alternatives": ["Salut"],
    "vocabulary": [],
    "cultural_note": "Used any time of day in French",
    "usage_warning": None,
    "confidence_score": 0.97,
})


def test_agent_input_defaults():
    inp = AgentInput(task_type=TaskType.TRANSLATE, input_text="Hello")
    assert inp.source_language == "Hindi"
    assert inp.target_language == "English"
    assert inp.user_level == "beginner"


def test_task_type_routing():
    crew = AvantikaLanguageCrew()
    inp = AgentInput(
        task_type=TaskType.TRANSLATE,
        source_language="English",
        target_language="French",
        input_text="Hello",
    )
    # Just test routing doesn't raise (mocked kickoff)
    with patch("crewai.Crew.kickoff", return_value=MOCK_TRANSLATION_JSON):
        result = crew.run(inp)

    assert result.success is True
    assert result.task_type == "translate"
    assert result.data["primary_translation"] == "Bonjour"


def test_parse_output_handles_markdown_fences():
    raw = f"```json\n{MOCK_TRANSLATION_JSON}\n```"
    result = AvantikaLanguageCrew._parse_output(raw)
    assert result["primary_translation"] == "Bonjour"


def test_parse_output_handles_invalid_json():
    result = AvantikaLanguageCrew._parse_output("I cannot translate this right now.")
    assert "raw_output" in result


def test_run_handles_exception():
    crew = AvantikaLanguageCrew()
    inp = AgentInput(task_type=TaskType.TRANSLATE, input_text="Hello")
    with patch.object(crew, "_route", side_effect=RuntimeError("LLM unavailable")):
        result = crew.run(inp)
    assert result.success is False
    assert "LLM unavailable" in result.error
