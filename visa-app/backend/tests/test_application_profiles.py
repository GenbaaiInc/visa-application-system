"""Application profile resolution tests."""

import pytest

from main import _merge_extracted_case_data
from application_profiles import resolve_application_profile, with_legacy_case_profile


def test_resolve_application_profile_supports_coe_engineer_humanities_international():
    case_data = {
        "case": {
            "application_type": "certificate_of_eligibility",
            "target_status": "engineer_humanities_international",
        }
    }

    assert resolve_application_profile(case_data) == "coe_engineer_humanities_international"


@pytest.mark.parametrize(
    "case_data",
    [
        {
            "case": {
                "application_type": "certificate_of_eligibility",
                "target_status": "specified_skilled_worker",
                "target_status_variant": "",
            }
        },
        {
            "case": {
                "application_type": "change_of_status",
                "target_status": "engineer_humanities_international",
            }
        },
        {
            "case": {
                "application_type": "certificate_of_eligibility",
                "target_status": "engineer_humanities_international",
                "target_status_variant": "ssw_2",
            }
        },
    ],
)
def test_resolve_application_profile_rejects_unsupported_profiles(case_data):
    with pytest.raises(ValueError, match="まだ対応していません"):
        resolve_application_profile(case_data)


@pytest.mark.parametrize("procedure,prefix", [
    ("certificate_of_eligibility", "coe"),
    ("change_of_status", "change"),
    ("extension_of_stay", "renewal"),
])
@pytest.mark.parametrize("variant", ["ssw_1", "ssw_2"])
def test_ssw_profiles(procedure, prefix, variant):
    assert resolve_application_profile({"case": {
        "application_type": procedure, "target_status": "specified_skilled_worker",
        "target_status_variant": variant,
    }}) == f"{prefix}_specified_skilled_worker"


def test_legacy_case_without_profile_is_interpreted_without_mutating_source():
    stored = {
        "case_id": "case_old",
        "created_at": "2026-05-20T01:02:03+00:00",
        "workflow_state": "extracted",
        "case_data": {key: {} for key in ("applicant", "employer", "employment", "entry_plan")},
    }

    normalized = with_legacy_case_profile(stored)

    assert "case" not in stored["case_data"]
    assert normalized["case_data"]["case"] == {
        "case_id": "case_old",
        "application_type": "certificate_of_eligibility",
        "target_status": "engineer_humanities_international",
        "workflow_state": "extracted",
    }
    assert resolve_application_profile(normalized["case_data"]) == "coe_engineer_humanities_international"


def test_legacy_coe_alias_is_interpreted_only_for_known_engineer_profile():
    stored = {"case_data": {"case": {
        "application_type": "coe", "target_status": "engineer_humanities_international",
    }}}

    normalized = with_legacy_case_profile(stored)

    assert stored["case_data"]["case"]["application_type"] == "coe"
    assert normalized["case_data"]["case"]["application_type"] == "certificate_of_eligibility"


@pytest.mark.parametrize("legacy_case_data", [
    {key: {} for key in ("applicant", "employer", "employment", "entry_plan")},
    {"case": {"application_type": "coe", "target_status": "engineer_humanities_international"}},
])
def test_reextraction_cannot_replace_legacy_case_profile(legacy_case_data):
    stored = {
        "case_id": "case_old",
        "created_at": "2026-05-20T00:00:00+00:00",
        "case_data": legacy_case_data,
    }
    existing = with_legacy_case_profile(stored)["case_data"]

    merged = _merge_extracted_case_data(existing, {"case": {
        "application_type": "change_of_status",
        "target_status": "specified_skilled_worker",
        "target_status_variant": "ssw_1",
    }})

    assert resolve_application_profile(merged) == "coe_engineer_humanities_international"
    assert merged["case"] == existing["case"]


@pytest.mark.parametrize("stored", [
    {"case_id": "case_new", "created_at": "2026-09-01T00:00:00+00:00", "case_data": {
        key: {} for key in ("applicant", "employer", "employment", "entry_plan")
    }},
    {"case_id": "case_partial", "created_at": "2026-05-20T00:00:00+00:00", "case_data": {
        "applicant": {}, "employer": {}, "employment": {},
    }},
    {"case_id": "case_ssw", "created_at": "2026-05-20T00:00:00+00:00", "case_data": {
        **{key: {} for key in ("applicant", "employer", "employment", "entry_plan")},
        "specified_skilled_worker": {},
    }},
    {"case_id": "case_incomplete_ssw", "case_data": {"case": {
        "application_type": "coe", "target_status": "specified_skilled_worker",
    }}},
    {"case_id": "case_explicit_change", "case_data": {"case": {
        "application_type": "change_of_status", "target_status": "engineer_humanities_international",
    }}},
])
def test_unknown_or_incomplete_case_is_not_interpreted_as_legacy_engineer(stored):
    assert with_legacy_case_profile(stored) is stored
