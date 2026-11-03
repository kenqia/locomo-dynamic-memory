"""Allowlisted output diagnostics. Never serialize Pydantic input, ctx or msg."""

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticCustomError


DOMAIN_ERRORS = {
    "extraction_time_anchor_cited": "Time anchor must be one of the cited sources",
    "extraction_time_expression_required": "Original time expression must occur in the cited anchor text",
    "answer_nonblank_required": "Answer cannot be blank",
    "answer_evidence_status_required": "Answer must preserve evidence uncertainty",
    "answer_citations_required": "Evidence-backed answer needs citations",
    "answer_raw_citation_scope_required": "Raw citation outside delivered sources",
    "answer_memory_citation_scope_required": "Citation outside delivered effective evidence",
    "answer_conflict_sides_required": "Cite both unresolved conflict sides",
    "resolution_explanation_required": "Resolution explanation cannot be blank",
    "resolution_reason_required": "Evidence applicability explanation cannot be blank",
    "resolution_raw_scope_required": "Raw evidence outside supplied scope",
    "resolution_unique_supplied_ids_required": "Effective evidence must use unique supplied IDs",
    "resolution_every_candidate_required": "Explain every candidate exactly once",
    "resolution_selection_agreement_required": "Selection and decisions disagree",
    "resolution_sufficient_evidence_required": "Sufficient answer requires evidence",
    "resolution_conflict_sides_required": "Conflict requires both evidence sides",
    "resolution_incomplete_relation_required": "Missing relation endpoints require uncertain applicability",
    "resolution_supplemental_endpoints_required": "Supplemental endpoints outside candidates",
    "update_stage_evidence_required": "UPDATE requires source-supported evidence of both stages",
    "update_real_stage_required": "UPDATE requires the same process and a real stage change",
    "update_endpoint_stage_required": "Stage quotation must be verbatim evidence from its own endpoint",
    "applicability_range_reversed": "Applicability range reversed",
    "applicability_time_evidence_required": "Applicability dates need source anchor, original expression and basis",
    "condition_evidence_required": "Satisfied condition requires source evidence",
    "explicit_condition_required": "Condition status requires an explicit condition",
    "reason_and_unique_evidence_required": "A relation needs a reason and unique evidence",
    "nonblank_reason_required": "A relation needs a nonblank reason",
    "unique_evidence_required": "A relation needs unique evidence IDs",
    "comparison_endpoints_required": "Relation endpoints must belong to the supplied historical comparison",
    "same_endpoint_scope_required": "Relation endpoints cross version, conversation or entity scope",
    "known_source_required": "Relation cites an unknown source",
    "endpoint_evidence_required": "Relation evidence must belong to its two endpoints",
    "both_endpoints_evidence_required": "Relation evidence must support both endpoints",
    "same_state_dimension_required": "This judgment requires the same state dimension",
    "factual_states_required": "Only factual states can supersede factual states; preserve events and plans",
    "factual_resolution_required": "A plan or uncertain claim cannot resolve an established factual state",
    "verbatim_support_required": "A determined judgment requires a verbatim supporting source quote",
    "relation_time_anchor_required": "Applicability anchor must be a relation source",
    "source_time_expression_required": "Applicability expression absent from source",
    "relation_condition_evidence_required": "Condition proof is not among relation evidence",
    "every_candidate_required": "Each supplied historical memory requires one judgment, including undetermined",
}


def domain_error(code: str) -> PydanticCustomError:
    return PydanticCustomError(code, DOMAIN_ERRORS[code])


def schema_path(schema: type[BaseModel], location: tuple) -> str | None:
    """Keep only a verified schema path prefix; extra field names are untrusted."""
    root = schema.model_json_schema()
    node = root
    path = ""
    for part in location:
        while "$ref" in node:
            node = root["$defs"][node["$ref"].rsplit("/", 1)[1]]
        if "anyOf" in node:
            node = next((item for item in node["anyOf"] if item.get("type") != "null"), {})
            while "$ref" in node:
                node = root["$defs"][node["$ref"].rsplit("/", 1)[1]]
        if type(part) is int and part >= 0 and "items" in node:
            path += f"[{part}]"
            node = node["items"]
        elif isinstance(part, str) and part in node.get("properties", {}):
            path += ("." if path else "") + part
            node = node["properties"][part]
        else:
            break
    return path or None


def validation_diagnostics(error: ValidationError, schema: type[BaseModel]) -> list[dict]:
    result = []
    codes = {"json_invalid": "invalid_json", "missing": "missing_field",
             "extra_forbidden": "extra_field", "literal_error": "invalid_enum"}
    for item in error.errors(include_url=False, include_input=False, include_context=False):
        kind = item["type"]
        if kind in DOMAIN_ERRORS or kind in {"value_error", "assertion_error"}:
            stage = "domain_validation"
            code = kind if kind in DOMAIN_ERRORS else "domain_constraint_failed"
        elif kind == "json_invalid":
            stage, code = "json_parsing", "invalid_json"
        else:
            stage, code = "schema_validation", codes.get(kind, "schema_constraint_failed")
        result.append({"failure_stage": stage, "error_code": code,
                       "field_path": schema_path(schema, item["loc"])})
    return result
