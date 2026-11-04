"""Synthetic SSW integration tests; no applicant information is stored here."""

import pytest

from application_data import build_application_data, build_display_case_data, visible
from application_profiles import resolve_application_profile
from rasens_definitions import load_profile_definitions


def case_data(procedure="certificate_of_eligibility", variant="ssw_1", employment="direct", support="entrusted"):
    return {
        "case": {"application_type": procedure, "target_status": "specified_skilled_worker", "target_status_variant": variant},
        "specified_skilled_worker": {"employment_type": employment, "support_method": support},
    }


def application(data, metadata=None, settings=None):
    mapping, definitions = load_profile_definitions(resolve_application_profile(data))
    return build_application_data(
        {"case_data": data, "workflow_state": "extracted", "field_metadata": metadata or {}},
        mapping, definitions, settings=settings or {},
    )


@pytest.mark.parametrize("procedure", ["certificate_of_eligibility", "change_of_status", "extension_of_stay"])
@pytest.mark.parametrize("variant", ["ssw_1", "ssw_2"])
def test_empty_required_fields_are_reviewable_and_block_filling(procedure, variant):
    result = application(case_data(procedure, variant))
    assert result["fillable"] is False
    missing = {item["canonical_path"] for item in result["missing_required_fields"]}
    editable = {item["canonical_path"] for item in result["review_fields"]}
    assert "applicant.name_roman" in missing & editable
    assert "applicant.birth_date" in missing & editable
    assert not any(row["canonical_path"] == "entry_plan.main_activity_category" for row in result["rows"])


def test_missing_condition_selectors_do_not_crash():
    data = case_data()
    data.pop("specified_skilled_worker")
    paths = {item["canonical_path"] for item in application(data)["missing_required_fields"]}
    assert "specified_skilled_worker.employment_type" in paths
    assert "specified_skilled_worker.support_method" in paths


def test_gijinkoku_defaults_are_not_added_to_ssw():
    display = build_display_case_data(case_data())
    assert not display.get("entry_plan", {}).get("planned_period_years")
    assert not display.get("entry_plan", {}).get("planned_port")
    assert display.get("applicant", {}).get("criminal_record") is None


@pytest.mark.parametrize("procedure", ["certificate_of_eligibility", "change_of_status", "extension_of_stay"])
def test_conditions_exclude_stale_support_and_dispatch_values(procedure):
    data = case_data(procedure, "ssw_2")
    data["specified_skilled_worker"].update({
        "support_organization": {"name": "STALE SUPPORT"},
        "self_support": {"manager_name": "STALE MANAGER"},
        "dispatch_destination": {"name": "STALE DISPATCH"},
    })
    result = application(data)
    paths = [item["canonical_path"] for item in result["review_fields"] + result["rows"]]
    assert not any(path.startswith(("specified_skilled_worker.support_organization.", "specified_skilled_worker.self_support.", "specified_skilled_worker.support_plan.", "specified_skilled_worker.dispatch_destination.")) for path in paths)


def test_dispatch_destination_is_separate_from_employer():
    data = case_data(employment="dispatch")
    data["employer"] = {"name": "SYNTHETIC EMPLOYER"}
    data["specified_skilled_worker"]["dispatch_destination"] = {"name": "SYNTHETIC DESTINATION"}
    rows = application(data)["rows"]
    values = {item["canonical_path"]: item["display_value"] for item in rows}
    assert values["employer.name"] == "SYNTHETIC EMPLOYER"
    assert values["specified_skilled_worker.dispatch_destination.name"] == "SYNTHETIC DESTINATION"


def test_manual_only_fields_never_enter_autofill_rows():
    data = case_data()
    mapping, _ = load_profile_definitions(resolve_application_profile(data))
    manual_ids = {item["field_id"] for item in mapping["mappings"] if item.get("manual_only")}
    assert manual_ids
    assert not manual_ids.intersection(item["field_id"] for item in application(data)["rows"])


def test_mappings_have_conditions_for_dispatch_details():
    data = case_data()
    mapping, _ = load_profile_definitions(resolve_application_profile(data))
    dispatch = [item for item in mapping["mappings"] if item.get("value_path", "").startswith("specified_skilled_worker.dispatch_destination.")]
    assert dispatch
    assert all(not visible(data, item) for item in dispatch)


def test_review_options_use_meaningful_values_not_dom_numbers():
    fields = {item["canonical_path"]: item for item in application(case_data())["review_fields"]}
    assert {option["value"] for option in fields["applicant.sex"]["options"]} == {"male", "female"}
    assert all(option["value"] == option["text"] for option in fields["applicant.nationality_region"]["options"])
    assert all("選択してください" not in option["text"] for option in fields["applicant.nationality_region"]["options"])


@pytest.mark.parametrize("value", ["NOT A REAL OPTION", "2"])
def test_unknown_select_value_is_not_considered_ready(value):
    data = case_data()
    data["applicant"] = {"nationality_region": value}
    missing = {item["canonical_path"]: item for item in application(data)["missing_required_fields"]}
    assert "選択肢" in missing["applicant.nationality_region"]["reason"]


@pytest.mark.parametrize("procedure", ["certificate_of_eligibility", "change_of_status", "extension_of_stay"])
def test_document_terms_use_exact_rasens_choices(procedure):
    data = case_data(procedure)
    data["specified_skilled_worker"]["contract"] = {
        "industry": ["農業分野"], "business_category": ["耕種農業全般"]
    }
    if procedure != "certificate_of_eligibility":
        data["applicant"] = {"current_period_of_stay": "1年"}
    result = application(data)
    rows = {row["canonical_path"]: row for row in result["rows"]}
    assert rows["specified_skilled_worker.contract.industry.0"]["fill_value"] == "農業分野 Agriculture"
    assert rows["specified_skilled_worker.contract.business_category.0"]["fill_value"] == "耕種農業（農業分野） General crop farming（Agriculture）"
    missing = {field["canonical_path"] for field in result["missing_required_fields"]}
    assert "specified_skilled_worker.contract.industry.0" not in missing
    assert "specified_skilled_worker.contract.business_category.0" not in missing
    if procedure != "certificate_of_eligibility":
        assert rows["applicant.current_period_of_stay"]["fill_value"] == "１年"
        assert "applicant.current_period_of_stay" not in missing


@pytest.mark.parametrize("procedure", ["certificate_of_eligibility", "change_of_status", "extension_of_stay"])
def test_payment_job_and_company_industry_cannot_autofill_before_human_review(procedure):
    data = case_data(procedure)
    data["specified_skilled_worker"]["contract"] = {"payment_method": "口座振込"}
    data["employment"] = {"job_category_primary": "農業"}
    data["employer"] = {"industry_primary": "農業"}
    result = application(data)
    rows = {row["canonical_path"]: row for row in result["rows"]}
    missing = {field["canonical_path"]: field["reason"] for field in result["missing_required_fields"]}
    payment = "specified_skilled_worker.contract.payment_method"
    job = "employment.job_category_primary"
    industry = "employer.industry_primary"
    assert rows[payment]["fill_value"] == "口座振込み Paid into a bank account"
    assert "担当者" in missing[payment]
    assert "選択肢" in missing[job]
    assert "選択肢" in missing[industry]
    assert result["fillable"] is False

    # Even an exact RASENS choice stays blocked until a person confirms it.
    data["specified_skilled_worker"]["contract"]["payment_method"] = "通貨払"
    data["employment"]["job_category_primary"] = "農林漁業従事者 Agriculture, forestry and fishery workers"
    data["employer"]["industry_primary"] = "農林業 Agriculture"
    confirmed_values = application(data)
    unconfirmed = {field["canonical_path"]: field["reason"] for field in confirmed_values["missing_required_fields"]}
    assert all("担当者" in unconfirmed[path] for path in (payment, job, industry))
    confirmed = application(data, {path: {"human_edited": True} for path in (payment, job, industry)})
    confirmed_missing = {field["canonical_path"] for field in confirmed["missing_required_fields"]}
    assert not confirmed_missing.intersection({payment, job, industry})


@pytest.mark.parametrize("variant,other", [("ssw_1", "ssw_2"), ("ssw_2", "ssw_1")])
def test_renewal_period_choices_match_selected_variant(variant, other):
    data = case_data("extension_of_stay", variant)
    path = "specified_skilled_worker.requested_period_of_stay"
    own_field = next(item for item in application(data)["review_fields"] if item["canonical_path"] == path)
    other_field = next(item for item in application(case_data("extension_of_stay", other))["review_fields"] if item["canonical_path"] == path)
    assert own_field["options"] and other_field["options"]
    assert {item["value"] for item in own_field["options"]}.isdisjoint(item["value"] for item in other_field["options"])
    data["specified_skilled_worker"]["requested_period_of_stay"] = other_field["options"][0]["value"]
    missing = {item["canonical_path"]: item for item in application(data)["missing_required_fields"]}
    assert "選択肢" in missing[path]["reason"]


def test_human_declaration_requires_confirmation_even_if_ai_provided_value():
    data = case_data()
    mapping, definitions = load_profile_definitions(resolve_application_profile(data))
    item = next(item for item in mapping["mappings"] if item.get("manual_required") and item.get("value_map") and visible(data, item))
    path = item["value_path"]
    current = data
    for part in path.split(".")[:-1]:
        current = current.setdefault(part, {})
    current[path.split(".")[-1]] = next(iter(item["value_map"]))
    assert path in {item["canonical_path"] for item in application(data)["missing_required_fields"]}
    confirmed = application(data, {path: {"human_edited": True}})
    assert path not in {item["canonical_path"] for item in confirmed["missing_required_fields"]}


@pytest.mark.parametrize("procedure", ["certificate_of_eligibility", "change_of_status", "extension_of_stay"])
@pytest.mark.parametrize("variant,employment,support", [
    ("ssw_1", "direct", "entrusted"), ("ssw_1", "direct", "self"),
    ("ssw_1", "dispatch", "entrusted"), ("ssw_1", "dispatch", "self"),
    ("ssw_2", "direct", "entrusted"), ("ssw_2", "dispatch", "entrusted"),
])
def test_complete_synthetic_review_can_become_fillable(procedure, variant, employment, support):
    # Contract test only: dummy values are never sent to RASENS or to an AI API.
    from main import _set_value_at_path

    data = case_data(procedure, variant, employment, support)
    metadata = {}
    settings = {
        "intermediary": {key: "SYNTHETIC" for key in ("name", "postal_code", "address", "organization", "phone")},
        "receiving_method": {"notification_email": "test@example.invalid"},
    }
    for _ in range(6):
        result = application(data, metadata, settings)
        if not result["missing_required_fields"]:
            break
        for field in result["missing_required_fields"]:
            path = field["canonical_path"]
            assert not path.startswith("settings."), (path, field["reason"])
            options = field.get("options", [])
            value = options[0]["value"] if options else "20260101"
            _set_value_at_path(data, path, value)
            metadata[path] = {"human_edited": True}
    assert result["missing_required_fields"] == []
    assert result["fillable"] is True
    assert result["pending_manual_fields"]  # Prefill ready does not mean application complete.
