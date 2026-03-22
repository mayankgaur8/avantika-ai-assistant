"""
Avantika Global Language AI — CrewAI Orchestration Layer
Production-grade, API-driven crew with modular task routing.

Production-safety improvements in this file:
  1. Task-specific Pydantic output schemas (TranslationOutput, LearnOutput, etc.)
     enforce structural contracts at the Python layer, not just via prompt.
  2. _REQUIRED_INPUTS registry validates caller-supplied fields *before* any LLM
     call is made, so missing inputs surface as clear ValueError rather than
     silent empty/hallucinated output.
  3. _fmt() inside both factories now raises ValueError on a missing template key
     instead of silently returning the un-substituted YAML text.
  4. extract_json() uses a three-strategy cascade (direct parse → fence strip →
     brace-scan regex) to recover valid JSON from imperfect LLM output.
  5. validate_output() validates the parsed dict against the task schema and, on
     failure, invokes one LLM repair pass before re-validating — giving the
     pipeline a single self-correction opportunity without infinite loops.
  6. _inject_metadata() always stamps task_type, version, generated_at,
     source_language, and target_language onto every output before validation,
     so the LLM never needs to get those fields right.
  7. All task output schemas share a TaskOutputBase metadata envelope ensuring
     every response is version-tagged and timestamped.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

import yaml
from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field, ValidationError


# ---------------------------------------------------------------------------
# Task type routing enum
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    TRANSLATE = "translate"
    LEARN = "learn"
    TRAVEL = "travel"
    COACH = "coach"
    CURRICULUM = "curriculum"
    CULTURE = "culture"


# ===========================================================================
# Shared sub-models
# ===========================================================================

class VocabItem(BaseModel):
    """Used in translation output: single vocabulary breakdown entry."""
    word: str
    meaning: str
    part_of_speech: str


class DialogueLine(BaseModel):
    """Generic dialogue exchange used in lesson output."""
    speaker: str
    text: str
    translation: str


# ===========================================================================
# Task-specific content schemas
# Each schema enforces the counts promised in tasks.yaml so validation catches
# LLMs that truncate lists.
# ===========================================================================

# ---- TRANSLATE ----

class TranslationContent(BaseModel):
    primary_translation: str
    literal_translation: str
    pronunciation: str
    # Exactly 2 alternatives — min_length and max_length enforce this at parse time
    alternatives: list[str] = Field(min_length=2, max_length=2)
    # 3–5 vocabulary items — mirrors tasks.yaml "exactly 3 to 5 words"
    vocabulary: list[VocabItem] = Field(min_length=3, max_length=5)
    cultural_note: str | None = None
    usage_warning: str | None = None
    # Score must be a valid probability
    confidence_score: float = Field(ge=0.0, le=1.0)


# ---- LEARN ----

class LearnVocabItem(BaseModel):
    word: str
    translation: str
    pronunciation: str
    example: str
    example_translation: str


class GrammarSection(BaseModel):
    rule: str
    explanation: str
    # Exactly 3 examples — mirrors tasks.yaml "exactly 3 example sentences"
    examples: list[str] = Field(min_length=3, max_length=3)


class Exercise(BaseModel):
    # Constrained to the two supported types
    type: Literal["multiple_choice", "fill_blank"]
    question: str
    options: list[str]
    answer: str


class LearnContent(BaseModel):
    lesson_title: str
    # Exactly 3 learning objectives — mirrors tasks.yaml
    objectives: list[str] = Field(min_length=3, max_length=3)
    # Exactly 10 vocabulary items — mirrors tasks.yaml
    vocabulary: list[LearnVocabItem] = Field(min_length=10, max_length=10)
    grammar: GrammarSection
    # 4–6 dialogue exchanges — mirrors tasks.yaml
    dialogue: list[DialogueLine] = Field(min_length=4, max_length=6)
    # Exactly 5 exercises — mirrors tasks.yaml
    exercises: list[Exercise] = Field(min_length=5, max_length=5)
    cultural_tip: str
    estimated_duration_minutes: int = Field(gt=0)


# ---- TRAVEL ----

class TravelPhrase(BaseModel):
    phrase: str
    translation: str
    pronunciation: str
    when_to_use: str


class TravelDialogueLine(BaseModel):
    # Only these two speaker values are valid
    speaker: Literal["traveler", "local"]
    text: str
    translation: str
    note: str | None = None


class TravelVocabItem(BaseModel):
    word: str
    translation: str
    pronunciation: str


class TravelContent(BaseModel):
    scenario_type: str
    scenario_description: str
    # Exactly 10 essential phrases — mirrors tasks.yaml
    essential_phrases: list[TravelPhrase] = Field(min_length=10, max_length=10)
    # 8–10 dialogue exchanges — mirrors tasks.yaml
    dialogue: list[TravelDialogueLine] = Field(min_length=8, max_length=10)
    # Exactly 8 vocabulary items — mirrors tasks.yaml
    vocabulary: list[TravelVocabItem] = Field(min_length=8, max_length=8)
    # At least 3 etiquette tips
    etiquette_tips: list[str] = Field(min_length=3)
    emergency_phrase: str
    # At least 3 common mistakes
    common_mistakes: list[str] = Field(min_length=3)


# ---- COACH ----

class ProfessionalVocabItem(BaseModel):
    term: str
    meaning: str
    example: str


class InterviewQA(BaseModel):
    question: str
    ideal_answer: str
    tips: str


class CoachAnalysis(BaseModel):
    strengths: list[str]
    improvements: list[str]


class CoachContent(BaseModel):
    coaching_type: str
    analysis: CoachAnalysis
    improved_version: str
    # Exactly 10 professional vocabulary items — mirrors tasks.yaml
    professional_vocabulary: list[ProfessionalVocabItem] = Field(
        min_length=10, max_length=10
    )
    tone_guidance: str
    # Exactly 3 interview Q&A pairs — mirrors tasks.yaml
    interview_qa: list[InterviewQA] = Field(min_length=3, max_length=3)
    # At least 3 common mistakes
    common_mistakes: list[str] = Field(min_length=3)
    # At least 3 confidence tips
    confidence_tips: list[str] = Field(min_length=3)


# ---- CURRICULUM ----

class WeekPlan(BaseModel):
    week: int = Field(ge=1)
    theme: str
    # At least 2 objectives — mirrors tasks.yaml
    objectives: list[str] = Field(min_length=2)
    vocabulary_count: int = Field(gt=0)
    # At least 1 grammar topic
    grammar_topics: list[str] = Field(min_length=1)
    # At least 1 scenario type
    scenario_types: list[str] = Field(min_length=1)
    study_hours: float = Field(gt=0)
    milestone: str | None = None


class CurriculumContent(BaseModel):
    curriculum_title: str
    total_weeks: int = Field(gt=0)
    target_level_end: str
    # At least 1 week; caller validates exact count against duration_weeks
    weeks: list[WeekPlan] = Field(min_length=1)


# ---- CULTURE ----

class DiningEtiquette(BaseModel):
    # At least 3 dos and 3 don'ts — mirrors tasks.yaml
    dos: list[str] = Field(min_length=3)
    donts: list[str] = Field(min_length=3)


class BusinessCulture(BaseModel):
    # At least 3 norms and 3 tips — mirrors tasks.yaml
    norms: list[str] = Field(min_length=3)
    tips: list[str] = Field(min_length=3)


class CultureContent(BaseModel):
    destination_country: str
    context: str
    greeting_norms: str
    dining_etiquette: DiningEtiquette
    business_culture: BusinessCulture
    # At least 4 taboo items — mirrors tasks.yaml
    taboos: list[str] = Field(min_length=4)
    dress_code: str
    religious_sensitivities: str | None = None
    # At least 3 common misunderstandings — mirrors tasks.yaml
    common_misunderstandings: list[str] = Field(min_length=3)


# ===========================================================================
# Top-level output wrappers — every task response includes standard metadata
# ===========================================================================

class TaskOutputBase(BaseModel):
    """
    Metadata envelope present on every task output.
    Fields are always populated by _inject_metadata() before schema validation
    so the LLM cannot omit them silently.
    """
    version: str = "1.0"
    generated_at: str          # ISO 8601 UTC string  e.g. "2024-01-15T10:30:00Z"
    source_language: str
    target_language: str


class TranslationOutput(TaskOutputBase):
    task_type: Literal["translate"] = "translate"
    content: TranslationContent


class LearnOutput(TaskOutputBase):
    task_type: Literal["learn"] = "learn"
    content: LearnContent


class TravelOutput(TaskOutputBase):
    task_type: Literal["travel"] = "travel"
    content: TravelContent


class CoachOutput(TaskOutputBase):
    task_type: Literal["coach"] = "coach"
    content: CoachContent


class CurriculumOutput(TaskOutputBase):
    task_type: Literal["curriculum"] = "curriculum"
    content: CurriculumContent


class CultureOutput(TaskOutputBase):
    task_type: Literal["culture"] = "culture"
    content: CultureContent


# Registry maps TaskType → its output schema class.
# Used by validate_output() to pick the right validator without a switch.
_TASK_OUTPUT_SCHEMAS: dict[TaskType, type[TaskOutputBase]] = {
    TaskType.TRANSLATE: TranslationOutput,
    TaskType.LEARN: LearnOutput,
    TaskType.TRAVEL: TravelOutput,
    TaskType.COACH: CoachOutput,
    TaskType.CURRICULUM: CurriculumOutput,
    TaskType.CULTURE: CultureOutput,
}


# ===========================================================================
# Required-input registry
# Validated before any agent/task is created — fail fast on bad caller inputs.
# ===========================================================================

# Each entry lists input dict keys whose values must be truthy for that task.
_REQUIRED_INPUTS: dict[TaskType, list[str]] = {
    TaskType.TRANSLATE: ["input_text"],
    TaskType.LEARN: ["lesson_topic"],
    TaskType.TRAVEL: ["destination_country", "scenario_type"],
    TaskType.COACH: ["job_field", "coaching_type"],
    TaskType.CURRICULUM: ["learning_goal"],
    TaskType.CULTURE: ["source_country", "destination_country", "etiquette_context"],
}


def validate_required_inputs(task_type: TaskType, inputs: dict) -> None:
    """
    Raise ValueError listing every missing required field for `task_type`.

    Called before task construction so callers receive a clear, actionable
    error rather than an LLM response with hallucinated placeholder values.
    """
    required = _REQUIRED_INPUTS.get(task_type, [])
    # A field is "missing" if absent or empty-string (safe_inputs replaces None → "")
    missing = [f for f in required if not inputs.get(f)]
    if missing:
        raise ValueError(
            f"Task '{task_type.value}' missing required input fields: {missing}. "
            f"Provide these fields in AgentInput before calling run()."
        )


# ---------------------------------------------------------------------------
# Input / Output contracts (shared with backend)
# ---------------------------------------------------------------------------

class AgentInput(BaseModel):
    task_type: TaskType
    source_language: str = "Hindi"
    target_language: str = "English"
    user_level: str = "beginner"           # beginner | intermediate | advanced
    destination_country: str | None = None
    job_field: str | None = None
    input_text: str | None = None
    lesson_topic: str | None = None
    session_number: int = 1
    previous_topics: list[str] = Field(default_factory=list)
    scenario_type: str | None = None
    coaching_type: str | None = None
    user_draft: str | None = None
    context_tone: str = "neutral"
    formality_level: str = "neutral"       # formal | neutral | casual
    learning_goal: str | None = None
    duration_weeks: int = 4
    source_country: str | None = None
    etiquette_context: str | None = None
    user_id: str | None = None
    session_id: str | None = None


class AgentOutput(BaseModel):
    task_type: str
    success: bool
    data: dict[str, Any]
    error: str | None = None
    model_used: str | None = None
    tokens_used: int | None = None


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_yaml(filename: str) -> dict:
    config_dir = os.path.join(os.path.dirname(__file__), "config")
    with open(os.path.join(config_dir, filename), "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Model router — cheap vs premium
# ---------------------------------------------------------------------------

def _resolve_model(agent_model: str) -> str:
    """
    Route to the shared AI platform model based on cost tier.
    Override via environment variables for Ollama / local models.
    """
    use_local = os.getenv("USE_LOCAL_MODEL", "false").lower() == "true"
    if use_local:
        return os.getenv("LOCAL_MODEL", "ollama/llama3")

    cheap_model = os.getenv("CHEAP_MODEL", "gpt-4o-mini")
    premium_model = os.getenv("PREMIUM_MODEL", "gpt-4o")
    if agent_model in ("gpt-4o",):
        return premium_model
    return cheap_model


# ===========================================================================
# JSON extraction helper
# Recovers valid JSON from imperfect LLM output without silently dropping data.
# ===========================================================================

def extract_json(text: str) -> dict:
    """
    Attempt to extract a valid JSON object from LLM output using three strategies:

    Strategy 1 — Direct parse:
        The LLM obeyed the prompt exactly and returned bare JSON.

    Strategy 2 — Markdown fence strip:
        The LLM wrapped the JSON in ```json ... ``` or ``` ... ``` despite
        being instructed not to. Strip the fence and parse the inner content.

    Strategy 3 — Brace-scan regex:
        The LLM included prose before/after the JSON block. Find the outermost
        { ... } span in the text and parse it.

    Raises ValueError if all three strategies fail, including a snippet of the
    raw output so the caller can log a meaningful error.
    """
    text = text.strip()

    # Strategy 1: direct parse (ideal path — prompt was obeyed)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip ```json ... ``` or ``` ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: find the outermost { ... } block (handles leading/trailing prose)
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not extract valid JSON from LLM output after three strategies. "
        f"First 400 chars of raw output: {text[:400]!r}"
    )


# ===========================================================================
# Metadata injection
# Always called before schema validation so the LLM never needs to produce
# these fields correctly — they are filled in from the known caller context.
# ===========================================================================

def _inject_metadata(data: dict, task_type: TaskType, inputs: dict) -> None:
    """
    Stamp standard metadata fields onto `data` in-place if they are absent.

    This means even if the LLM omits task_type, version, generated_at,
    source_language, or target_language the downstream schema will still
    validate successfully.  Values are never overwritten so an LLM that does
    produce correct metadata is not penalised.
    """
    data.setdefault("task_type", task_type.value)
    data.setdefault("version", "1.0")
    data.setdefault(
        "generated_at",
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    data.setdefault("source_language", inputs.get("source_language", ""))
    data.setdefault("target_language", inputs.get("target_language", ""))


# ===========================================================================
# One-shot LLM repair pass
# ===========================================================================

def _repair_json(
    raw_data: dict,
    schema_cls: type[TaskOutputBase],
    validation_error: str,
) -> dict:
    """
    Ask the cheap LLM model to fix a JSON object that failed schema validation.

    Sends the broken JSON, the full Pydantic JSON schema, and the exact
    validation error to the model so it can make a targeted correction.

    Uses litellm (already a CrewAI dependency) for the repair call.
    Raises RuntimeError if litellm is not available.
    Raises ValueError if the repair response cannot be parsed as JSON.
    """
    try:
        import litellm
    except ImportError as exc:
        raise RuntimeError(
            "litellm is required for the JSON repair pass but is not installed. "
            "Install it with: pip install litellm"
        ) from exc

    model = os.getenv("CHEAP_MODEL", "gpt-4o-mini")
    schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)

    repair_prompt = (
        "The following JSON object failed schema validation.\n\n"
        f"Validation error:\n{validation_error}\n\n"
        f"Required JSON schema:\n{schema_json}\n\n"
        f"Broken JSON:\n{json.dumps(raw_data, indent=2)}\n\n"
        "Fix the JSON so it exactly matches the schema. "
        "Return ONLY the corrected JSON object. "
        "Do not wrap in markdown code fences. "
        "Do not include any explanation before or after the JSON."
    )

    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": repair_prompt}],
        max_tokens=4096,
    )
    raw_text = response.choices[0].message.content
    # extract_json handles any residual fences the repair model might add
    return extract_json(raw_text)


# ===========================================================================
# Output validation + repair orchestrator
# ===========================================================================

def validate_output(
    data: dict,
    task_type: TaskType,
    inputs: dict,
) -> dict:
    """
    Validate `data` against the task-specific Pydantic schema.

    Flow:
      1. _inject_metadata() stamps known-good metadata fields so the validator
         never fails on fields the caller already knows.
      2. model_validate() checks the full schema.
      3. On ValidationError: one LLM repair pass via _repair_json(), then
         re-validate.  If the second validation fails the exception propagates
         to the caller — there is no silent swallowing of bad output.

    Returns the validated dict from model_dump() so callers receive a
    canonical, fully-populated structure.
    """
    schema_cls = _TASK_OUTPUT_SCHEMAS[task_type]

    # Stamp metadata before first validation attempt
    _inject_metadata(data, task_type, inputs)

    try:
        return schema_cls.model_validate(data).model_dump()
    except ValidationError as first_error:
        # One repair attempt — repair pass also gets metadata injected
        repaired = _repair_json(
            raw_data=data,
            schema_cls=schema_cls,
            validation_error=str(first_error),
        )
        _inject_metadata(repaired, task_type, inputs)
        # Let any ValidationError from the second attempt propagate as a hard error
        return schema_cls.model_validate(repaired).model_dump()


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

class AvantikaAgentFactory:
    def __init__(self):
        self._agents_config = _load_yaml("agents.yaml")
        self._search_tool = SerperDevTool() if os.getenv("SERPER_API_KEY") else None

    def _make_agent(self, key: str, inputs: dict) -> Agent:
        cfg = self._agents_config[key]

        def _fmt(text: str) -> str:
            try:
                return text.format(**inputs)
            except KeyError as exc:
                # Production safety: fail fast rather than silently passing
                # un-substituted template text to the LLM.
                raise ValueError(
                    f"Agent config '{key}' references template variable {exc} "
                    f"which is absent from inputs. "
                    f"Available keys: {sorted(inputs.keys())}"
                ) from exc

        tools = [self._search_tool] if self._search_tool and key in (
            "travel_assistant", "professional_communication_coach"
        ) else []

        return Agent(
            role=_fmt(cfg["role"]),
            goal=_fmt(cfg["goal"]),
            backstory=_fmt(cfg["backstory"]),
            verbose=cfg.get("verbose", False),
            allow_delegation=cfg.get("allow_delegation", False),
            tools=tools,
            llm=_resolve_model(cfg.get("model", "gpt-4o-mini")),
        )

    def get_translator(self, inputs: dict) -> Agent:
        return self._make_agent("real_time_translator", inputs)

    def get_teacher(self, inputs: dict) -> Agent:
        return self._make_agent("language_teacher", inputs)

    def get_travel_assistant(self, inputs: dict) -> Agent:
        return self._make_agent("travel_assistant", inputs)

    def get_coach(self, inputs: dict) -> Agent:
        return self._make_agent("professional_communication_coach", inputs)

    def get_curriculum_planner(self, inputs: dict) -> Agent:
        return self._make_agent("curriculum_planner", inputs)

    def get_culture_coach(self, inputs: dict) -> Agent:
        return self._make_agent("cultural_etiquette_coach", inputs)


# ---------------------------------------------------------------------------
# Task factory
# ---------------------------------------------------------------------------

class AvantikaTaskFactory:
    def __init__(self):
        self._tasks_config = _load_yaml("tasks.yaml")

    def _make_task(self, key: str, agent: Agent, inputs: dict) -> Task:
        cfg = self._tasks_config[key]

        def _fmt(text: str) -> str:
            try:
                return text.format(**inputs)
            except KeyError as exc:
                # Production safety: fail fast rather than silently passing
                # un-substituted template text to the LLM.
                raise ValueError(
                    f"Task config '{key}' references template variable {exc} "
                    f"which is absent from inputs. "
                    f"Available keys: {sorted(inputs.keys())}"
                ) from exc

        return Task(
            description=_fmt(cfg["description"]),
            expected_output=cfg["expected_output"],
            agent=agent,
            async_execution=cfg.get("async_execution", False),
        )

    def translation_task(self, agent: Agent, inputs: dict) -> Task:
        return self._make_task("real_time_translation", agent, inputs)

    def lesson_task(self, agent: Agent, inputs: dict) -> Task:
        return self._make_task("structured_language_lesson", agent, inputs)

    def travel_task(self, agent: Agent, inputs: dict) -> Task:
        return self._make_task("travel_scenario_simulation", agent, inputs)

    def coaching_task(self, agent: Agent, inputs: dict) -> Task:
        return self._make_task("professional_communication_coaching", agent, inputs)

    def curriculum_task(self, agent: Agent, inputs: dict) -> Task:
        return self._make_task("curriculum_planning", agent, inputs)

    def culture_task(self, agent: Agent, inputs: dict) -> Task:
        return self._make_task("cultural_etiquette_briefing", agent, inputs)


# ---------------------------------------------------------------------------
# Main Crew runner
# ---------------------------------------------------------------------------

class AvantikaLanguageCrew:
    """
    Main orchestrator. Accepts an AgentInput, routes to the correct
    agent + task, runs the crew, and returns a structured AgentOutput.

    Run pipeline per request:
      1. validate_required_inputs() — fail fast before touching any LLM
      2. _route()                   — build agent + task objects
      3. crew.kickoff()             — invoke the LLM
      4. extract_json()             — recover JSON from (potentially messy) output
      5. validate_output()          — enforce schema; one repair pass if needed
    """

    def __init__(self):
        self._agent_factory = AvantikaAgentFactory()
        self._task_factory = AvantikaTaskFactory()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        inputs_dict = agent_input.model_dump(exclude_none=False)
        # Replace None with "" so YAML .format() never raises KeyError on optional fields
        safe_inputs = {k: (v if v is not None else "") for k, v in inputs_dict.items()}

        try:
            # Step 1: validate required fields before any LLM cost is incurred
            validate_required_inputs(agent_input.task_type, safe_inputs)

            # Step 2: build agent and task
            agent, task = self._route(agent_input.task_type, safe_inputs)

            # Step 3: run the crew
            crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )
            raw_result = crew.kickoff(inputs=safe_inputs)

            # Step 4: extract JSON from (potentially imperfect) LLM text output
            parsed = extract_json(str(raw_result))

            # Step 5: validate against schema; one repair pass on failure
            validated = validate_output(parsed, agent_input.task_type, safe_inputs)

            return AgentOutput(
                task_type=agent_input.task_type.value,
                success=True,
                data=validated,
            )

        except Exception as exc:
            return AgentOutput(
                task_type=agent_input.task_type.value,
                success=False,
                data={},
                error=str(exc),
            )

    def _route(self, task_type: TaskType, inputs: dict) -> tuple[Agent, Task]:
        match task_type:
            case TaskType.TRANSLATE:
                agent = self._agent_factory.get_translator(inputs)
                task = self._task_factory.translation_task(agent, inputs)
            case TaskType.LEARN:
                agent = self._agent_factory.get_teacher(inputs)
                task = self._task_factory.lesson_task(agent, inputs)
            case TaskType.TRAVEL:
                agent = self._agent_factory.get_travel_assistant(inputs)
                task = self._task_factory.travel_task(agent, inputs)
            case TaskType.COACH:
                agent = self._agent_factory.get_coach(inputs)
                task = self._task_factory.coaching_task(agent, inputs)
            case TaskType.CURRICULUM:
                agent = self._agent_factory.get_curriculum_planner(inputs)
                task = self._task_factory.curriculum_task(agent, inputs)
            case TaskType.CULTURE:
                agent = self._agent_factory.get_culture_coach(inputs)
                task = self._task_factory.culture_task(agent, inputs)
            case _:
                raise ValueError(f"Unknown task type: {task_type}")
        return agent, task
