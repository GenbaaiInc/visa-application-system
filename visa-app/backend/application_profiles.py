"""Resolve the application profile supported by downstream processing."""

import copy
from datetime import date, datetime
from typing import Any


SUPPORTED_APPLICATION_PROFILE_ID = "coe_engineer_humanities_international"
SSW_PROFILES = {
    "certificate_of_eligibility": "coe_specified_skilled_worker",
    "change_of_status": "change_specified_skilled_worker",
    "extension_of_stay": "renewal_specified_skilled_worker",
}
PROCEDURE_TITLES = {
    "certificate_of_eligibility": "在留資格認定証明書交付申請",
    "change_of_status": "在留資格変更許可申請",
    "extension_of_stay": "在留期間更新許可申請",
}

_LEGACY_CASE_KEYS = {"applicant", "employer", "employment", "entry_plan"}
_LEGACY_CASE_CUTOFF = date(2026, 6, 1)


def with_legacy_case_profile(case_doc: dict[str, Any]) -> dict[str, Any]:
    """Interpret known pre-profile engineer cases without migrating stored documents."""
    case_data = case_doc.get("case_data")
    if not isinstance(case_data, dict):
        return case_doc

    case = case_data.get("case")
    if isinstance(case, dict):
        if (
            case.get("application_type") == "coe"
            and case.get("target_status") == "engineer_humanities_international"
            and case.get("target_status_variant") is None
        ):
            normalized = copy.deepcopy(case_doc)
            normalized["case_data"]["case"]["application_type"] = "certificate_of_eligibility"
            return normalized
        return case_doc

    # The six observed May 2026 cases predate the case profile and contain only
    # these four sections. Do not infer a profile for newer or partial cases.
    created_at = case_doc.get("created_at")
    if "case" in case_data or set(case_data) != _LEGACY_CASE_KEYS or not isinstance(created_at, str):
        return case_doc
    if not all(isinstance(case_data[key], dict) for key in _LEGACY_CASE_KEYS):
        return case_doc
    if not isinstance(case_doc.get("case_id"), str) or not case_doc["case_id"]:
        return case_doc
    try:
        created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    except ValueError:
        return case_doc
    if created_date >= _LEGACY_CASE_CUTOFF:
        return case_doc

    normalized = copy.deepcopy(case_doc)
    normalized["case_data"]["case"] = {
        "case_id": case_doc["case_id"],
        "application_type": "certificate_of_eligibility",
        "target_status": "engineer_humanities_international",
        "workflow_state": case_doc.get("workflow_state") or "draft",
    }
    return normalized


def resolve_application_profile(case_data: dict[str, Any]) -> str:
    """Return the supported profile, or reject an unsupported case type."""
    case = case_data.get("case") or {}
    if (
        case.get("target_status") == "specified_skilled_worker"
        and case.get("target_status_variant") in {"ssw_1", "ssw_2"}
        and case.get("application_type") in SSW_PROFILES
    ):
        return SSW_PROFILES[case["application_type"]]
    if (
        case.get("application_type") == "certificate_of_eligibility"
        and case.get("target_status") == "engineer_humanities_international"
        and case.get("target_status_variant") is None
    ):
        return SUPPORTED_APPLICATION_PROFILE_ID

    raise ValueError(
        "この在留資格・申請種別のAI抽出・RASENS入力はまだ対応していません。"
        "技人国の認定申請、特定技能の認定・変更・更新に対応しています。"
    )


def application_form_profile(case_data: dict[str, Any]) -> dict[str, Any]:
    case = case_data["case"]
    return {
        "id": resolve_application_profile(case_data),
        "application_type": case["application_type"],
        "target_status": case["target_status"],
        "target_status_variant": case.get("target_status_variant"),
        "title": PROCEDURE_TITLES[case["application_type"]],
    }
