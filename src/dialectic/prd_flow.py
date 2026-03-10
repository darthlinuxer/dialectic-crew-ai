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
from datetime import datetime
import logging
from typing import Any

from crewai.flow import Flow, start, listen, router, or_
from crewai.flow.persistence import SQLiteFlowPersistence
from crewai import Task, Crew

from dialectic.agents import (
    _vision_label,
    create_visionario,
    create_critico_socratico,
    create_sintetizador,
    create_validador_macro,
    llm_planning,
    vision_knowledge,
)
from dialectic.state import DialecticState, MAX_RETRIES
from dialectic.vision import VisionContext
from dialectic.export import prd_to_markdown, PRDExporter
from dialectic.config import get_export_config
from dialectic.hooks import HookScope
from dialectic.metrics import emit as emit_metric
from schemas import PRDSchema

try:
    from crewai_files import File
    _HAS_FILES = True
except ImportError:
    _HAS_FILES = False

logger = logging.getLogger(__name__)

OUTPUT_DIR = "prd_output"


# ---------------------------------------------------------------------------
# Guardrail: validates PRDSchema output from Validador
# ---------------------------------------------------------------------------

def _prd_guardrail(result) -> tuple[bool, Any]:
    """Ensures validation task returns a valid PRDSchema."""
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, PRDSchema):
        if pydantic_obj.user_stories and len(pydantic_obj.user_stories) >= 1:
            return (True, result)
        emit_metric("guardrail_reject", 1.0, guardrail="prd", reason="no_user_stories")
        return (False, "PRD must include at least one user story")
    emit_metric("guardrail_reject", 1.0, guardrail="prd", reason="invalid_schema")
    return (
        False,
        "Output must be a valid PRDSchema JSON. Include all required fields: "
        "feature_name, objective, macro_impact, user_stories (min 1), "
        "anti_drift_questions (min 5), quality_score, consensus_reached, "
        "final_validation_notes. Use English values for risk_level "
        "(LOW/MEDIUM/HIGH) and effort (XS/S/M/L/XL). Return ONLY the JSON.",
    )


class DialecticFlow(Flow[DialecticState]):
    """Dialectic flow with automatic retry and state persistence"""

    @start()
    def iniciar_dialetica(self):
        print(f"\n{'='*60}")
        print(f"STARTING DIALECTIC FLOW")
        print(f"{'='*60}")
        print(f"Feature: {self.state.feature_objective}")
        print(f"Max retries: {self.state.max_retries}")
        print(f"{'='*60}\n")
        return "rodar_rodada"

    @listen(or_("iniciar_dialetica", "fazer_retry"))
    def rodar_rodada_dialetica(self):
        print(f"\nROUND {self.state.retry_count + 1}/{self.state.max_retries}\n")

        vision_context = VisionContext(self.state.vision_context)
        vision_label = _vision_label(vision_context)

        # region agent log
        try:
            import time

            log_path = "/home/darthlinuxer/dialectic-crew-ai/.cursor/debug-5709be.log"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(
                    json.dumps(
                        {
                            "sessionId": "5709be",
                            "runId": "pre-fix",
                            "hypothesisId": "H1",
                            "location": "src/dialectic/prd_flow.py:rodar_rodada_dialetica",
                            "message": "Computed vision_label before crew kickoff",
                            "data": {
                                "vision_context": self.state.vision_context,
                                "vision_label": vision_label,
                            },
                            "timestamp": time.time(),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # endregion

        vis = create_visionario(vision_context)
        crit = create_critico_socratico(vision_context)
        sint = create_sintetizador(vision_context)
        val = create_validador_macro(vision_context)

        task_vision = Task(
            description=f"""
Objective: {self.state.feature_objective}

Consult the system's macro vision ({vision_label} is available via your knowledge sources).
Generate the complete initial thesis (PRD proposal) including:
1. Feature name
2. Clear objective
3. Affected modules
4. User stories (minimum 3)
5. Non-functional requirements
6. Identified risks
7. Macro impact
""",
            expected_output="Complete initial proposal in structured PRD format",
            agent=vis,
        )

        task_critica = Task(
            description=f"""
Apply the full Socratic method.

Consult the system's macro vision ({vision_label} is available via your knowledge sources).
Analyze the Visionary's proposal (in context) and list ALL:
1. Flaws and weak points
2. Contradictions with the macro vision
3. Drift risks
4. Overscope and technical debt
5. Forgotten non-functional requirements
6. Weak or incomplete user stories

Be relentless. Each critique must be specific and actionable.
""",
            expected_output="Detailed critique with list of issues and score",
            agent=crit,
            context=[task_vision],
        )

        task_sintese = Task(
            description=f"""
Produce the final synthesis incorporating ALL critiques (thesis and antithesis are in context).

Consult the system's macro vision ({vision_label} is available via your knowledge sources).
The synthesis must:
1. Preserve what was good in the thesis
2. Incorporate ALL critiques from the antithesis
3. Eliminate ALL identified weaknesses
4. Be better than both individual proposals
5. Be aligned with the macro vision

Output: Complete PRD with corrected user stories, in structured format (objective, macro_impact, user_stories, anti_drift_questions). Use risk_level in English (LOW/MEDIUM/HIGH) and effort in English (XS/S/M/L/XL) for schema compatibility.
""",
            expected_output="Final refined version of the PRD",
            agent=sint,
            context=[task_vision, task_critica],
        )

        task_validacao = Task(
            description=f"""
Evaluate the FINAL SYNTHESIS (output from the Synthesizer in context) and produce the final PRD.

Consult the system's macro vision ({vision_label} is available via your knowledge sources).

            The PRD must follow exactly the PRDSchema structure:
            - feature_name, version, objective
            - macro_impact: {{ modules_affected, risk_level, performance_impact, security_impact }}
            - user_stories: [ {{ id, title, description, acceptance_criteria, effort, dependencies }} ]
            - anti_drift_questions: [ {{ question, answer }} ]
- quality_score: float (one decimal place, 0-10)
- consensus_reached: true or false
- final_validation_notes: string

Use the synthesis content to fill in the fields. If score < 9.0, explain in final_validation_notes what is missing.

Checklist for score: (1) Feature aligned with macro vision? (2) Affected modules? (3) Risks mitigated? (4) NFRs covered? (5) Consistent user stories? (6) 5+ anti-drift?

MANDATORY - use EXACTLY these English values (never in Portuguese):
- risk_level: only "LOW", "MEDIUM" or "HIGH"
- effort: only "XS", "S", "M", "L" or "XL"
""",
            expected_output="Valid PRDSchema with quality_score and consensus_reached",
            agent=val,
            output_pydantic=PRDSchema,
            guardrail=_prd_guardrail,
            guardrail_max_retries=2,
            context=[task_vision, task_critica, task_sintese],
        )

        crew = Crew(
            agents=[vis, crit, sint, val],
            tasks=[task_vision, task_critica, task_sintese, task_validacao],
            process="sequential",
            verbose=True,
            memory=True,
            planning=True,
            planning_llm=llm_planning,
            knowledge_sources=[vision_knowledge(vision_context)],
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
                    input_files[key] = File(source=path)
            if input_files:
                kickoff_kwargs["input_files"] = input_files

        feature_label = self.state.feature_objective[:60].replace(" ", "_")
        with HookScope(
            token_budget=0,
            label=f"prd/{feature_label}",
        ):
            resultado = crew.kickoff(**kickoff_kwargs)

        # Extract PRD via output_pydantic (native CrewAI structured output)
        prd: PRDSchema | None = None
        pydantic_result = getattr(resultado, "pydantic", None)
        if isinstance(pydantic_result, PRDSchema):
            prd = pydantic_result
        else:
            tasks_out = getattr(resultado, "tasks_output", None) or []
            if tasks_out:
                last_pydantic = getattr(tasks_out[-1], "pydantic", None)
                if isinstance(last_pydantic, PRDSchema):
                    prd = last_pydantic

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
        return "avaliar"

    @router(rodar_rodada_dialetica)
    def avaliar(self):
        if self.state.quality_score >= 9.0:
            print(f"APPROVED! Quality score: {self.state.quality_score}")
            return "aprovar"
        elif self.state.retry_count >= self.state.max_retries:
            print(f"Max retries reached. Finishing with score: {self.state.quality_score}")
            return "aprovar"
        else:
            self.state.retry_count += 1
            print(f"Rejected. Retry #{self.state.retry_count}")
            notes = self.state.final_validation_notes
            notes_str = notes[:200] if isinstance(notes, str) else str(notes)[:200]
            print(f"   What is missing: {notes_str}...")
            return "retry"

    @listen("retry")
    def fazer_retry(self):
        return "rodar_rodada"

    @listen("aprovar")
    def salvar_prd_final(self):
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

        data = self.state.prd_data if isinstance(self.state.prd_data, dict) else {}

        if data.get("_parse_failed"):
            self.state.prd_path_json = ""
            self.state.prd_path_md = ""
            print(f"\nPRD generation FAILED: could not extract structured output.")
            print(f"Score: {self.state.quality_score}/10.0")
            print("No PRD artifact saved. Check debug files in prd_output/.")
            return None

        try:
            prd = PRDSchema.model_validate(data)
        except Exception:
            self.state.prd_path_json = ""
            self.state.prd_path_md = ""
            logger.error("Failed to validate prd_data as PRDSchema: %s", data.keys())
            print(f"\nPRD generation FAILED: state data is not a valid PRDSchema.")
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
                json_path = next((p for p in created_paths if p.endswith(".json")), "")
                md_path = next((p for p in created_paths if p.endswith(".md")), "")
                self.state.prd_path_json = json_path
                self.state.prd_path_md = md_path
                logger.info("PRD exported via PRDExporter: %s", created_paths)
                print(f"\nPRD APPROVED with score {self.state.quality_score}!")
                for p in created_paths:
                    print(f"Saved to: {p}")
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
        return prd


_persistence: SQLiteFlowPersistence | None = None


def _get_persistence() -> SQLiteFlowPersistence:
    global _persistence
    if _persistence is None:
        _persistence = SQLiteFlowPersistence()
    return _persistence


def run_dialectic_flow(feature_request: str) -> dict:
    flow = DialecticFlow(persistence=_get_persistence())
    flow.state.feature_objective = feature_request
    flow.state.max_retries = MAX_RETRIES
    flow.kickoff()
    s = flow.state
    return {
        "success": s.consensus_reached or s.quality_score >= 9.0,
        "quality_score": s.quality_score,
        "iterations": s.retry_count + 1,
        "prd": s.prd_data,
        "prd_path_json": s.prd_path_json,
        "prd_path_md": s.prd_path_md,
        "consensus_reached": s.consensus_reached,
        "validation": s.final_validation_notes,
    }
