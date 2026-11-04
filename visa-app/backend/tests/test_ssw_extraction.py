"""Specified skilled worker extraction is separate from the engineer profile."""

from unittest.mock import MagicMock, patch

import pytest

from extractors.gemini import extract_all_scopes, extract_scoped
from extractors.gemini_pipeline import extract_documents
from extractors.prompt_template import build_scoped_prompt
from extractors.schema import to_response_json_schema
from extractors.ssw_profile import (
    SSW_EXTRACTION_SCOPES,
    SSW_REVIEW_SCHEMA,
    ssw_extraction_scopes,
    ssw_scope_schema,
)
from extractors.document_models import PreparedDocuments
from extractors.types import ExtractionResult


SSW_CASE = {
    "case_id": "case_ssw",
    "application_type": "extension_of_stay",
    "target_status": "specified_skilled_worker",
    "target_status_variant": "ssw_1",
}


def test_ssw_prompt_uses_own_review_rules_and_keeps_variant():
    prompt = build_scoped_prompt("review", SSW_CASE, [], {"applicant": {}})

    assert "ssw_1" in prompt
    assert "技能・日本語の根拠" in prompt
    assert "学歴と仕事内容の関連性" not in prompt


def test_ssw_second_variant_prompt_does_not_request_first_variant_support():
    second = {**SSW_CASE, "target_status_variant": "ssw_2"}

    status_prompt = build_scoped_prompt("ssw_status", second, [])
    review_prompt = build_scoped_prompt("review", second, [], {})

    assert "支援方法" not in status_prompt
    assert "登録支援機関" not in review_prompt


def _leaf_paths(schema: dict, prefix: str = "") -> set[str]:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return {prefix}
    paths = set()
    for name, child in properties.items():
        path = f"{prefix}.{name}" if prefix else name
        paths.update(_leaf_paths(child, path))
    return paths


@pytest.mark.parametrize(
    "application_type",
    ["certificate_of_eligibility", "change_of_status", "extension_of_stay"],
)
@pytest.mark.parametrize("variant", ["ssw_1", "ssw_2"])
def test_ssw_scopes_have_no_overlapping_leaf_paths(application_type, variant):
    case_meta = {
        **SSW_CASE,
        "application_type": application_type,
        "target_status_variant": variant,
    }
    schemas = [ssw_scope_schema(scope, case_meta) for scope in ssw_extraction_scopes(case_meta)]
    combined: set[str] = set()
    for schema in schemas:
        paths = _leaf_paths(schema)
        assert combined.isdisjoint(paths)
        combined.update(paths)
        assert "source_locations" in to_response_json_schema(schema)["properties"]

    status = ssw_scope_schema("ssw_status", case_meta)
    eligibility = ssw_scope_schema("ssw_eligibility", case_meta)
    facts = status["properties"]["specified_skilled_worker"]["properties"]
    eligibility_facts = eligibility["properties"]["specified_skilled_worker"]["properties"]
    assert "employment_type" in facts
    assert ("support_method" in facts) is (variant == "ssw_1")
    assert "guarantee_deposit_exists" not in eligibility_facts["eligibility"]["properties"]
    assert "test_location" in eligibility_facts["eligibility"]["properties"]["skill_tests"]["items"]["properties"]


def test_ssw_schema_only_requests_fields_for_the_procedure_and_variant():
    coe = ssw_scope_schema(
        "ssw_status",
        {**SSW_CASE, "application_type": "certificate_of_eligibility"},
    )
    renewal_second = ssw_scope_schema(
        "ssw_status", {**SSW_CASE, "target_status_variant": "ssw_2"}
    )

    assert "entry_plan" in coe["properties"]
    assert "applicant" not in coe["properties"]
    assert "requested_period_of_stay" not in coe["properties"]["specified_skilled_worker"]["properties"]
    assert "applicant" in renewal_second["properties"]
    assert "entry_plan" not in renewal_second["properties"]
    assert "support_method" not in renewal_second["properties"]["specified_skilled_worker"]["properties"]
    assert "ssw_support_organization" not in ssw_extraction_scopes(
        {**SSW_CASE, "target_status_variant": "ssw_2"}
    )
    assert "ssw_self_support" not in ssw_extraction_scopes(
        {**SSW_CASE, "target_status_variant": "ssw_2"}
    )


@patch("extractors.gemini._call_gemini")
def test_every_ssw_scope_uses_its_schema_and_prompt(mock_call):
    mock_call.return_value = {"case_data": {}}

    for scope in ssw_extraction_scopes(SSW_CASE):
        extract_scoped(scope, MagicMock(), [], SSW_CASE, [])
        assert mock_call.call_args.kwargs["schema"] == ssw_scope_schema(scope, SSW_CASE)
        assert "技人国向け" not in mock_call.call_args.args[2]


@patch("extractors.gemini._call_gemini")
@patch("extractors.gemini.extract_scoped")
def test_ssw_runs_only_identity_and_ssw_facts_then_review(mock_scoped, mock_call):
    mock_scoped.side_effect = lambda scope, *_args, **_kwargs: (
        {
            "case_data": {
                "applicant": {
                    "name_roman": {
                        "value": "SAMPLE PERSON",
                        "source_ref": {
                            "document_id": "doc_passport", "page": 1,
                            "text_quote": "SAMPLE PERSON", "confidence": 0.95,
                        },
                    },
                },
            },
        }
        if scope == "applicant_identity" else {"case_data": {}}
    )
    mock_call.return_value = {"missing_items": [], "findings": [], "validation_errors": []}

    extract_all_scopes(MagicMock(), [], SSW_CASE, [])

    assert {call.args[0] for call in mock_scoped.call_args_list} == set(ssw_extraction_scopes(SSW_CASE))
    assert mock_call.call_args.kwargs["schema"] is SSW_REVIEW_SCHEMA


@patch("extractors.gemini._call_gemini")
@patch("extractors.gemini.extract_scoped")
def test_ssw_split_scopes_merge_into_the_existing_case_shape(mock_scoped, mock_call):
    def field(value):
        return {
            "value": value,
            "source_ref": {
                "document_id": "doc_sample", "page": 1,
                "text_quote": value, "confidence": 0.9,
            },
        }

    values = {
        "applicant_identity": {"applicant": {"nationality_region": field("SAMPLE COUNTRY")}},
        "ssw_status": {"specified_skilled_worker": {"employment_type": field("direct")}},
        "ssw_employer": {"employer": {"name": field("SAMPLE COMPANY")}},
        "ssw_contract": {"specified_skilled_worker": {"contract": {"start_date": field("")}}},
        "ssw_eligibility": {"specified_skilled_worker": {"eligibility": {"skill_level_assessment": field("")}}},
        "ssw_dispatch": {"specified_skilled_worker": {"dispatch_destination": {"name": field("")}}},
        "ssw_support_organization": {"specified_skilled_worker": {"support_organization": {"name": field("SAMPLE SUPPORT")}}},
        "ssw_recruitment": {"specified_skilled_worker": {"recruiter": {"name": field("")}}},
        "ssw_self_support": {"specified_skilled_worker": {"self_support": {"manager_name": field("")}}},
    }
    mock_scoped.side_effect = lambda scope, *_args, **_kwargs: {"case_data": values[scope]}
    mock_call.return_value = {"missing_items": [], "findings": [], "validation_errors": []}

    result = extract_all_scopes(MagicMock(), [], SSW_CASE, [])

    assert result.display_case_data["applicant"]["nationality_region"] == "SAMPLE COUNTRY"
    assert result.display_case_data["employer"]["name"] == "SAMPLE COMPANY"
    assert result.display_case_data["specified_skilled_worker"]["employment_type"] == "direct"
    assert result.display_case_data["specified_skilled_worker"]["support_organization"]["name"] == "SAMPLE SUPPORT"


@patch("extractors.gemini._call_gemini")
@patch("extractors.gemini.extract_scoped")
def test_ssw_returns_partial_result_and_names_failed_scope(mock_scoped, mock_call):
    def extract(scope, *_args, **_kwargs):
        if scope == "ssw_dispatch":
            raise RuntimeError("synthetic failure")
        if scope == "ssw_employer":
            return {
                "case_data": {
                    "employer": {
                        "name": {
                            "value": "SAMPLE COMPANY",
                            "source_ref": {
                                "document_id": "doc_sample",
                                "page": 1,
                                "text_quote": "SAMPLE COMPANY",
                                "confidence": 0.9,
                            },
                        }
                    }
                }
            }
        return {"case_data": {}}

    mock_scoped.side_effect = extract
    mock_call.return_value = {"missing_items": [], "findings": [], "validation_errors": []}

    result = extract_all_scopes(MagicMock(), [], SSW_CASE, [])

    assert result.display_case_data["employer"]["name"] == "SAMPLE COMPANY"
    assert any("ssw_dispatch" in error for error in result.review["validation_errors"])
    assert any("一部の抽出scopeが失敗" in finding for finding in result.review["findings"])


def test_ssw_legacy_extraction_is_rejected_before_using_engineer_prompt():
    with pytest.raises(ValueError, match="scope抽出のみ"):
        extract_documents(SSW_CASE, [], [], MagicMock(), scoped=False)


@patch("extractors.gemini_pipeline.extract_all_scopes")
@patch("extractors.gemini_pipeline._get_client")
def test_ssw_pipeline_prepares_only_its_scopes(mock_client, mock_extract):
    mock_extract.return_value = ExtractionResult(
        case_data={}, display_case_data={}, review={}, field_metadata={}
    )

    extract_documents(SSW_CASE, [], [], PreparedDocuments(), attach_source_refs=False)

    contents_by_scope = mock_extract.call_args.args[1]
    assert set(contents_by_scope) == {*ssw_extraction_scopes(SSW_CASE), "review"}


@patch("extractors.gemini_pipeline.extract_all_scopes")
@patch("extractors.gemini_pipeline._get_client")
def test_ssw_second_variant_pipeline_does_not_prepare_support_scope(mock_client, mock_extract):
    mock_extract.return_value = ExtractionResult(
        case_data={}, display_case_data={}, review={}, field_metadata={}
    )
    second = {**SSW_CASE, "target_status_variant": "ssw_2"}

    extract_documents(second, [], [], PreparedDocuments(), attach_source_refs=False)

    contents_by_scope = mock_extract.call_args.args[1]
    assert "ssw_support_organization" not in contents_by_scope
    assert "ssw_self_support" not in contents_by_scope
    assert set(contents_by_scope) == {*ssw_extraction_scopes(second), "review"}
