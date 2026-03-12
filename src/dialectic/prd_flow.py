"""
Main flow with automatic retry until quality_score >= 9.0
Implements the dialectic: Thesis → Antithesis → Synthesis → Validation → Loop
Uses CrewAI Flow API with persistent state

Uses native CrewAI features:
- output_pydantic: structured output from the Validator (PRDSchema)
- Task guardrails: automatic output validation
- Flow pattern: @start, @listen, @router for retry
"""

import json
import os
import logging
from datetime import datetime
from importlib import import_module
from typing import Any

from crewai.flow import Flow, listen, or_, router, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist

from dialectic.app_logging import bind_log_context, log_context
from dialectic.config import get_export_config
from dialectic.export import PRDExporter, prd_to_markdown
from dialectic.flow_persistence import build_sqlite_flow_persistence
from dialectic.hooks import HookScope
from dialectic.metrics import emit as emit_metric
from dialectic.prd_guardrails import (
    _build_retry_feedback_context,
    _extract_prd_from_result,
    _materialize_plain_data,
    _prd_guardrail,
)
from dialectic.prd_runtime import build_prd_crew
from dialectic.state import DialecticState, MAX_RETRIES
from dialectic.vision import VisionContext
from schemas import PRDSchema

try:
    CrewAIFile = getattr(import_module("crewai_files"), "File")

    _HAS_FILES = True
except (ImportError, AttributeError):
    CrewAIFile = None
    _HAS_FILES = False

logger = logging.getLogger(__name__)

OUTPUT_DIR = "prd_output"


@persist()
class DialecticFlow(Flow[DialecticState]):
    """Dialectic flow with automatic retry and state persistence"""

    @start()
    def iniciar_dialetica(self):
        bind_log_context(
            flow_id=self.flow_id,
            phase="start",
            vision_context=self.state.vision_context,
        )
        logger.info("PRD dialectic flow started")
        phase = self.state.current_phase
        print(f"\n{'='*60}")
        print("STARTING DIALECTIC FLOW")
        print(f"{'='*60}")
        print(f"Flow ID: {self.flow_id}")
        print(f"Feature: {self.state.feature_objective}")
        print(f"Max retries: {self.state.max_retries}")
        print(f"{'='*60}\n")

        if phase == "evaluate":
            return "avaliar"
        if phase in {"save", "completed"}:
            return "aprovar"

        self.state.current_phase = "dialectic"
        return "rodar_rodada"

    # Router outputs remain string labels because CrewAI emits route names here,
    # not method references.
    @listen("retry")
    def fazer_retry(self):
        self.state.current_phase = "dialectic"
        return "rodar_rodada"

    @listen(or_(iniciar_dialetica, fazer_retry))
    def rodar_rodada_dialetica(self):
        with log_context(
            flow_id=self.flow_id,
            phase="dialectic",
            vision_context=self.state.vision_context,
        ):
            self.state.current_phase = "dialectic"
            print(f"\nROUND {self.state.retry_count + 1}/{self.state.max_retries}\n")
            logger.info("Running PRD dialectic round", extra={"retry": self.state.retry_count})

            vision_context = VisionContext(self.state.vision_context)
            retry_feedback = (self.state.final_validation_notes or "").strip()
            retry_feedback_block, retry_feedback_sources = _build_retry_feedback_context(
                retry_feedback,
                self.state.retry_count,
            )

            crew = build_prd_crew(
                feature_objective=self.state.feature_objective,
                vision_context=vision_context,
                retry_feedback_block=retry_feedback_block,
                retry_feedback_sources=retry_feedback_sources,
            )

            kickoff_kwargs: dict[str, Any] = {
                "inputs": {
                    "feature_objective": self.state.feature_objective,
                },
            }

            if _HAS_FILES and self.state.file_paths:
                input_files = {}
                for i, path in enumerate(self.state.file_paths):
                    if os.path.exists(path):
                        key = os.path.splitext(os.path.basename(path))[0] or f"file_{i}"
                        if CrewAIFile is not None:
                            input_files[key] = CrewAIFile(source=path)
                if input_files:
                    kickoff_kwargs["input_files"] = input_files

            feature_label = self.state.feature_objective[:60].replace(" ", "_")
            with HookScope(
                token_budget=0,
                label=f"prd/{feature_label}",
            ):
                resultado = crew.kickoff(**kickoff_kwargs)

        # Extract PRD using the same helper used by the guardrail so the flow
        # stores the exact validated representation rather than reparsing a
        # different raw payload later.
        prd: PRDSchema | None = _extract_prd_from_result(resultado)
        if prd is None:
            tasks_out = getattr(resultado, "tasks_output", None) or []
            for task_output in reversed(tasks_out):
                prd = _extract_prd_from_result(task_output)
                if prd is not None:
                    break

        if prd is not None:
            self.state.prd_data = prd.model_dump()
            self.state.quality_score = prd.quality_score
            self.state.consensus_reached = prd.consensus_reached
            self.state.final_validation_notes = prd.final_validation_notes
        else:
            # Fallback: parse raw text (should rarely trigger with output_pydantic)
            raw_text = getattr(resultado, "raw", None) or str(resultado)
            tasks_out = getattr(resultado, "tasks_output", None) or []
            if tasks_out:
                last_raw = getattr(tasks_out[-1], "raw", None)
                if last_raw and isinstance(last_raw, str) and last_raw.strip():
                    raw_text = last_raw
            try:
                import re
                matches = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
                json_str = matches[-1].strip() if matches else raw_text
                start_idx = json_str.find("{")
                if start_idx >= 0:
                    json_str = json_str[start_idx:]
                prd_dict = json.loads(json_str)
                prd = PRDSchema.model_validate(prd_dict)
                self.state.prd_data = prd.model_dump()
                self.state.quality_score = prd.quality_score
                self.state.consensus_reached = prd.consensus_reached
                self.state.final_validation_notes = prd.final_validation_notes
            except Exception:
                self.state.prd_data = {"_parse_failed": True, "raw": raw_text[:5000]}
                self.state.quality_score = 0.0
                self.state.consensus_reached = False
                self.state.final_validation_notes = (
                    "PARSE FAILURE: The output could not be parsed as PRDSchema JSON. "
                    "On retry, the Validator MUST return ONLY valid JSON matching PRDSchema "
                    "with all required fields."
                )
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                debug_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_path = os.path.join(OUTPUT_DIR, f"debug_crew_output_{debug_ts}.txt")
                try:
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write("# Raw crew output (parse failed)\n\n")
                        f.write(raw_text if isinstance(raw_text, str) else str(raw_text))
                    logger.warning("Parse failed; raw output saved to %s", debug_path)
                except OSError:
                    pass

        print(f"\n{'='*60}")
        print(f"QUALITY SCORE: {self.state.quality_score}/10.0")
        print(f"{'='*60}")
        self.state.current_phase = "evaluate"
        return "avaliar"

    @router(rodar_rodada_dialetica)
    def avaliar(self):
        bind_log_context(flow_id=self.flow_id, phase="evaluate")
        logger.info("Evaluating PRD dialectic round", extra={"retry": self.state.retry_count})
        if self.state.quality_score >= 9.0:
            self.state.current_phase = "save"
            print(f"APPROVED! Quality score: {self.state.quality_score}")
            return "aprovar"
        elif self.state.retry_count >= self.state.max_retries:
            self.state.current_phase = "save"
            print(f"Max retries reached. Finishing with score: {self.state.quality_score}")
            return "aprovar"
        else:
            self.state.retry_count += 1
            self.state.current_phase = "dialectic"
            print(f"Rejected. Retry #{self.state.retry_count}")
            notes = self.state.final_validation_notes
            notes_str = notes[:200] if isinstance(notes, str) else str(notes)[:200]
            print(f"   What is missing: {notes_str}...")
            return "retry"

    # Router outputs remain string labels because CrewAI emits route names here,
    # not method references.
    @listen("aprovar")
    def salvar_prd_final(self):
        bind_log_context(flow_id=self.flow_id, phase="save")
        if self.state.current_phase == "completed" and (self.state.prd_path_json or self.state.prd_path_md):
            print(f"\nPRD already exported for flow {self.flow_id}.")
            if self.state.prd_path_json:
                print(f"Saved to: {self.state.prd_path_json}")
            if self.state.prd_path_md:
                print(f"Markdown: {self.state.prd_path_md}")
            data = _materialize_plain_data(self.state.prd_data)
            try:
                return PRDSchema.model_validate(data)
            except Exception:
                return None

        self.state.current_phase = "save"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        emit_metric(
            "prd_score",
            self.state.quality_score,
            feature=self.state.feature_objective[:120],
            vision_context=self.state.vision_context,
        )
        emit_metric(
            "prd_retry_count",
            float(self.state.retry_count),
            feature=self.state.feature_objective[:120],
            vision_context=self.state.vision_context,
        )

        data = _materialize_plain_data(self.state.prd_data)
        if not isinstance(data, dict):
            data = {}

        if data.get("_parse_failed"):
            self.state.prd_path_json = ""
            self.state.prd_path_md = ""
            print("\nPRD generation FAILED: could not extract structured output.")
            print(f"Score: {self.state.quality_score}/10.0")
            print("No PRD artifact saved. Check debug files in prd_output/.")
            return None

        try:
            prd = PRDSchema.model_validate(data)
        except Exception as exc:
            self.state.prd_path_json = ""
            self.state.prd_path_md = ""
            logger.error(
                "Failed to validate prd_data as PRDSchema (%s): %s",
                data.keys(),
                exc,
            )
            print("\nPRD generation FAILED: state data is not a valid PRDSchema.")
            print(f"Score: {self.state.quality_score}/10.0")
            return None

        prd.quality_score = self.state.quality_score
        prd.consensus_reached = self.state.consensus_reached
        prd.final_validation_notes = self.state.final_validation_notes

        if float(self.state.quality_score) >= 9.0:
            try:
                config = get_export_config()
                exporter = PRDExporter()
                created_paths = exporter.export(prd, config)
                created_path_strings = [str(path) for path in created_paths]
                json_path = next((p for p in created_path_strings if p.endswith(".json")), "")
                md_path = next((p for p in created_path_strings if p.endswith(".md")), "")
                self.state.prd_path_json = json_path
                self.state.prd_path_md = md_path
                logger.info("PRD exported via PRDExporter: %s", created_path_strings)
                print(f"\nPRD APPROVED with score {self.state.quality_score}!")
                for p in created_path_strings:
                    print(f"Saved to: {p}")
                self.state.current_phase = "completed"
                return prd
            except Exception as e:
                logger.exception("Failed to export PRD via PRDExporter: %s", e)
                print("Failed to export PRD via PRDExporter; falling back to local save.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{OUTPUT_DIR}/PRD_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(prd.model_dump(), f, indent=2, ensure_ascii=False)

        filename_md = filename.replace(".json", ".md")
        with open(filename_md, "w", encoding="utf-8") as f:
            f.write(prd_to_markdown(prd))

        self.state.prd_path_json = filename
        self.state.prd_path_md = filename_md

        print(f"\nPRD APPROVED with score {self.state.quality_score}!")
        print(f"Saved to: {filename}")
        print(f"Markdown: {filename_md}")
        self.state.current_phase = "completed"
        return prd


_persistence: SQLiteFlowPersistence | None = None


def _get_persistence() -> SQLiteFlowPersistence:
    global _persistence
    if _persistence is None:
        _persistence = build_sqlite_flow_persistence()
    return _persistence


def get_prd_resume_state(flow_id: str) -> dict[str, Any] | None:
    """Return persisted PRD flow state for the provided flow ID, if it exists."""
    return _get_persistence().load_state(flow_id)


def run_dialectic_flow(
    feature_request: str | None,
    *,
    file_paths: list[str] | None = None,
    vision_context: VisionContext = VisionContext.PROJECT,
    resume_id: str | None = None,
) -> dict:
    if not resume_id and not feature_request:
        raise ValueError("feature_request is required when not resuming a persisted PRD flow")

    flow = DialecticFlow(persistence=_get_persistence())
    kickoff_inputs: dict[str, Any] = {
        "feature_objective": feature_request or "",
        "max_retries": MAX_RETRIES,
        "vision_context": vision_context.value,
    }
    if file_paths:
        kickoff_inputs["file_paths"] = file_paths
    if resume_id:
        kickoff_inputs["id"] = resume_id
    flow.kickoff(inputs=kickoff_inputs)
    s = flow.state
    return {
        "flow_id": flow.flow_id,
        "success": s.consensus_reached or s.quality_score >= 9.0,
        "quality_score": s.quality_score,
        "iterations": s.retry_count + 1,
        "prd": s.prd_data,
        "prd_path_json": s.prd_path_json,
        "prd_path_md": s.prd_path_md,
        "consensus_reached": s.consensus_reached,
        "validation": s.final_validation_notes,
    }


__all__ = [
    "DialecticFlow",
    "OUTPUT_DIR",
    "_prd_guardrail",
    "get_prd_resume_state",
    "run_dialectic_flow",
]
