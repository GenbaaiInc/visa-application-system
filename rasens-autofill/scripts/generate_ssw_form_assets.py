"""Build PII-free specified-skilled-worker form assets from saved RASENS pages.

The MHTML files are local evidence, not distributable fixtures.  Only labels,
control identifiers, options, and blank-form requirement markers are emitted.
Install ``rasens-autofill/scripts/requirements.txt`` in the local generation
environment, then run
``python rasens-autofill/scripts/generate_ssw_form_assets.py`` from the root. Verify with
``python -m unittest rasens-autofill/scripts/test_generate_ssw_form_assets.py``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "rasens-autofill/reference/rasens-ssw-2026-09-13"
OUTPUTS = (
    ROOT / "rasens-autofill/data",
    ROOT / "visa-app/backend/data",
)
SOURCES = {
    "coe_specified_skilled_worker": REFERENCE / "ssw_coe_2026-09-02.mhtml",
    "change_specified_skilled_worker": REFERENCE / "ssw_change_2026-09-13.mhtml",
    "renewal_specified_skilled_worker": REFERENCE / "ssw_renewal_2026-09-13.mhtml",
}

CONTRACT = {
    1: "start_date", 2: "end_date", 3: "industry", 4: "business_category",
    5: "job_category_primary", 6: "job_category_other", 7: "weekly_hours",
    8: "monthly_hours", 9: "hours_equivalent_to_regular_worker",
    10: "monthly_salary", 11: "hourly_base_pay", 12: "comparable_japanese_salary",
    13: "salary_at_least_japanese", 14: "payment_method", 15: "different_treatment",
    16: "home_leave_available", 17: "employment_standard_met",
    18: "return_travel_cost_covered", 19: "health_and_life_support",
    20: "industry_specific_standard_met", 21: "name", 22: "corporate_number",
    23: "employment_insurance_office_number", 24: "postal_code", 25: "address",
    26: "phone", 27: "representative_name", 28: "dispatch_start_date",
    29: "dispatch_end_date", 30: "name", 31: "corporate_number",
    32: "employment_insurance_office_number", 33: "postal_code", 34: "address",
    35: "phone", 36: "permit_number", 37: "permit_accepted_date",
    38: "name", 39: "country_region", 40: "postal_code", 41: "address", 42: "phone",
}
ORGANIZATION = {
    1: "name", 2: "corporate_number", 3: "employment_insurance_office_number",
    4: "industry_primary", 5: "industry_other", 6: "industry_secondary",
    7: "industry_secondary_other", 8: "postal_code", 9: "address", 10: "phone",
    11: "capital_jpy", 12: "annual_sales_jpy", 13: "employee_count",
    14: "representative_name", 15: "name", 16: "postal_code", 17: "address",
    18: "health_and_pension_covered", 19: "workers_comp_and_employment_covered",
    20: "labor_insurance_number", 21: "labor_social_tax_violation",
    22: "involuntary_dismissal", 23: "missing_worker_due_to_employer",
    24: "officers_criminal_conviction", 25: "officers_mental_incapacity",
    26: "officers_unrehabilitated_bankruptcy", 27: "technical_intern_approval_revoked",
    28: "officers_at_revoked_technical_intern_organization",
    29: "immigration_law_misconduct", 30: "organized_crime_member",
    31: "legal_representative_disqualified", 32: "organized_crime_control",
    33: "activity_records_retained", 34: "guarantee_deposit_contract_known",
    35: "employment_contract_penalty", 36: "no_support_cost_charged_to_worker",
    37: "dispatch_qualifying_condition", 38: "dispatch_condition_details",
    39: "dispatch_destination_qualifies", 40: "workers_comp_measures",
    41: "contract_performance_capacity", 42: "traceable_salary_payment",
    43: "industry_specific_compliance", 44: "manager_name", 45: "manager_position",
    46: "manager_is_officer_or_employee", 47: "staff_name", 48: "staff_position",
    49: "staff_assigned_per_workplace", 50: "support_qualifying_condition",
    51: "support_condition_details", 52: "multilingual_support_capacity",
    53: "support_records_retained", 54: "support_staff_independence",
    55: "prior_support_plan_failure", 56: "regular_interview_capacity",
    57: "support_plan_compliance",
}
SUPPORT_PLAN_BY_TEXT = (
    ("特定技能雇用契約の内容等", "contract_explanation_in_understood_language"),
    ("対面又はテレビ電話", "explanation_in_person_or_video"),
    ("出入国時に港", "airport_pickup"),
    ("適切な住居", "housing_assistance"),
    ("金融機関", "daily_contract_assistance"),
    ("生活一般", "life_orientation"),
    ("関係機関への同行", "administrative_procedure_accompaniment"),
    ("日本語を学習", "japanese_learning_opportunity"),
    ("相談又は苦情", "consultation_in_understood_language"),
    ("日本人の交流", "community_exchange"),
    ("転職支援", "job_change_support"),
    ("定期面談", "regular_interview_and_reporting"),
    ("写しを交付", "plan_copy_provided"),
    ("特定産業分野", "industry_specific_plan_items"),
    ("適切に実施", "appropriate_support_delivery"),
    ("基準に適合", "support_plan_standard_met"),
)
SUPPORT_ORGANIZATION = {
    1: "name", 2: "corporate_number", 3: "employment_insurance_office_number",
    4: "postal_code", 5: "address", 6: "phone", 7: "representative_name",
    8: "registration_number", 9: "registration_date", 10: "office_name",
    11: "office_postal_code", 12: "office_address", 13: "support_manager_name",
    14: "support_staff_name", 15: "available_languages", 16: "monthly_fee",
}


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("\u3000", " ").strip()


def read_html(path: Path) -> str:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    part = next(part for part in message.walk() if part.get_content_type() == "text/html")
    return part.get_payload(decode=True).decode("utf-8")


def controls_of(dl) -> list[dict]:
    controls = []
    for element in dl.find_all(["input", "select", "textarea"]):
        name = element.get("name", "")
        field_id = element.get("id", "")
        if not name and not field_id:
            continue
        kind = element.get("type", "") if element.name == "input" else element.name
        if kind in {"button", "hidden", "submit", "reset"}:
            continue
        options = []
        if element.name == "select":
            options = [
                {"value": option.get("value", ""), "text": option.get_text(" ", strip=True)}
                for option in element.find_all("option")
            ]
        elif kind in {"radio", "checkbox"}:
            label = element.find_parent("label") or dl.find("label", attrs={"for": field_id})
            if label:
                options = [{"value": element.get("value", ""), "text": label.get_text(" ", strip=True)}]
        controls.append({
            "field_id": field_id,
            "field_name": name,
            "input_type": kind,
            "options": options,
        })
    # RASENS renders each radio option as a separate input/id. The backend
    # resolves metadata by the mapped input id, so each member needs the
    # complete set of choices for that one field_name.
    radio_options: dict[str, list[dict]] = {}
    for control in controls:
        if control["input_type"] == "radio":
            radio_options.setdefault(control["field_name"], []).extend(control["options"])
    for control in controls:
        if control["input_type"] == "radio":
            control["options"] = radio_options[control["field_name"]]
    return controls


def parse_fields(path: Path) -> list[dict]:
    soup = BeautifulSoup(read_html(path), "html.parser")
    fields = []
    in_ssw_contract = False
    after_ssw = False
    for dl in soup.select("dl.c-input"):
        title = dl.select_one("dt.c-input__title")
        if not title:
            continue
        title_text = title.get_text(" ", strip=True)
        label = re.sub(r"\s*必須\s*$", "", title_text).strip()
        ascii_label = normalized(label)
        if ascii_label.startswith("2.1") and "特定技能雇用契約" in ascii_label:
            in_ssw_contract = True
        if ascii_label.startswith("3.1") and in_ssw_contract:
            in_ssw_contract = False
        if ascii_label.startswith("5.16") and "登録支援機関" in ascii_label:
            after_ssw = True
        # Other status-specific forms are retained in RASENS's hidden DOM.
        # They are not part of the selected SSW form and must not become rows.
        if after_ssw and "display: none" in (dl.get("style") or ""):
            continue
        controls = controls_of(dl)
        if not controls:
            continue
        note = dl.select_one("dd.c-input__note, .c-input__note")
        fields.append({
            "key": f"{dl.get('id', '')}:{label}",
            "section": "特定技能雇用契約" if in_ssw_contract else section_of(label),
            "sequence": dl.get("id", "").removeprefix("tr_"),
            "html_id": dl.get("id", ""),
            "no": code_of(label) or "",
            "label": label,
            "title": label,
            "required": "必須" in title_text,
            "conditional": "display: none" in (dl.get("style") or ""),
            "depends_on": "",
            "repeat_index": "",
            "controls": controls,
            "notes": note.get_text(" ", strip=True) if note else "",
        })
    return fields


def code_of(label: str) -> str | None:
    text = normalized(label)
    match = re.match(r"(\d+)(?:\.(\d+))?", text)
    return f"{match.group(1)}.{match.group(2)}" if match and match.group(2) else match.group(1) if match else None


def section_of(label: str) -> str:
    text = normalized(label)
    if re.match(r"2\.\d+", text) and "特定技能雇用契約" in text:
        return "特定技能雇用契約"
    if re.match(r"3\.\d+", text):
        return "特定技能所属機関・支援"
    if re.match(r"4\.\d+", text):
        return "1号特定技能外国人支援計画"
    if re.match(r"5\.\d+", text):
        return "登録支援機関"
    if "取次者" in text:
        return "取次者"
    if "受領方法" in text or "通知送信用" in text:
        return "受領方法"
    return "申請人・その他"


def repeated_index(text: str) -> int | None:
    match = re.search(r"(0[1-9]|[1-9][0-9])\s*$", text)
    return int(match.group(1)) - 1 if match else None


def field_path(field: dict, profile: str) -> tuple[str, list[dict], bool] | None:
    """Return semantic path, visibility conditions, and human-only flag."""
    label = normalized(field["label"])
    code = code_of(label)
    conditions: list[dict] = []
    if code and code.startswith("2.") and field["section"] == "特定技能雇用契約":
        number = int(code.split(".")[1])
        if number not in CONTRACT:
            return None
        key = CONTRACT[number]
        if 21 <= number <= 29:
            root = "specified_skilled_worker.dispatch_destination"
            conditions.append({"path": "specified_skilled_worker.employment_type", "value": "dispatch"})
        elif 30 <= number <= 37:
            root = "specified_skilled_worker.recruiter"
        elif 38 <= number <= 42:
            root = "specified_skilled_worker.overseas_intermediary"
        else:
            root = "specified_skilled_worker.contract"
        if number in {22, 31}:
            key = "has_corporate_number" if "有無" in label else "corporate_number"
            if key == "corporate_number":
                conditions.append({"path": f"{root}.has_corporate_number", "value": True})
        if number in {3, 4, 6}:
            index = repeated_index(label)
            if index is not None:
                key = f"{key}.{index}"
        if number == 10:
            return "employment.monthly_salary", conditions, False
        if number == 5:
            return "employment.job_category_primary", conditions, False
        return f"{root}.{key}", conditions, False
    if code and code.startswith("3.") and int(code.split(".")[1]) in ORGANIZATION:
        number = int(code.split(".")[1])
        key = ORGANIZATION[number]
        if number <= 14:
            root = "employer"
        elif number <= 20:
            root = "specified_skilled_worker.workplace"
        elif 37 <= number <= 39:
            root = "specified_skilled_worker.organization.compliance"
            conditions.append({"path": "specified_skilled_worker.employment_type", "value": "dispatch"})
        elif 44 <= number <= 57:
            root = "specified_skilled_worker.self_support"
            conditions += [
                {"path": "case.target_status_variant", "value": "ssw_1"},
                {"path": "specified_skilled_worker.support_method", "value": "self"},
            ]
        else:
            root = "specified_skilled_worker.organization.compliance"
        if number == 2:
            key = "has_corporate_number" if "有無" in label else "corporate_number"
            if key == "corporate_number":
                conditions.append({"path": "employer.has_corporate_number", "value": True})
        if number == 5:
            conditions.append({"path": "employer.industry_primary", "value": "その他 Others"})
        if number in {6, 7}:
            index = repeated_index(label)
            if index is not None:
                key = f"{key}.{index}"
        return f"{root}.{key}", conditions, False
    if code and code.startswith("4."):
        key = next((key for fragment, key in SUPPORT_PLAN_BY_TEXT if fragment in label), None)
        if key is None and "上記(1)" in label:
            key = "explanation_in_person_or_video"
        if key is None:
            return None
        return (
            f"specified_skilled_worker.support_plan.{key}",
            [{"path": "case.target_status_variant", "value": "ssw_1"}],
            False,
        )
    if code and code.startswith("5."):
        number = int(code.split(".")[1])
        if number not in SUPPORT_ORGANIZATION:
            return None
        key = SUPPORT_ORGANIZATION[number]
        conditions = [
            {"path": "case.target_status_variant", "value": "ssw_1"},
            {"path": "specified_skilled_worker.support_method", "value": "entrusted"},
        ]
        if number == 2:
            key = "has_corporate_number" if "有無" in label else "corporate_number"
            if key == "corporate_number":
                conditions.append({"path": "specified_skilled_worker.support_organization.has_corporate_number", "value": True})
        return f"specified_skilled_worker.support_organization.{key}", conditions, False
    if "顔写真" in label:
        return "specified_skilled_worker.application.photo_file", [], True
    if "申請に先立ち" in label:
        return "specified_skilled_worker.application.applicant_intent_confirmed", [], True
    if "申請内容の確認" in label:
        return "specified_skilled_worker.application.content_confirmed", [], True
    if "取次者" in label:
        if "氏名" in label:
            return "settings.intermediary.name", [], False
        if "郵便番号" in label:
            return "settings.intermediary.postal_code", [], False
        if "住所" in label:
            return "settings.intermediary.address", [], False
        if "所属機関" in label:
            return "settings.intermediary.organization", [], False
        if "電話" in label:
            return "settings.intermediary.phone", [], False
    if "通知送信用メールアドレス再入力" in label:
        return "settings.receiving_method.notification_email_confirmation", [], False
    if "通知送信用メールアドレス" in label:
        return "settings.receiving_method.notification_email", [], False
    if "在留カードの受領方法" in label:
        return "specified_skilled_worker.application.card_receiving_method", [], False
    if "受領方法" in label:
        return "settings.receiving_method.method", [], False
    if "受領官署" in label:
        return "specified_skilled_worker.application.card_receiving_office", [], False
    if "登録支援機関に1号特定技能外国人支援計画" in label and "委託" in label:
        return "specified_skilled_worker.support_method", [{"path": "case.target_status_variant", "value": "ssw_1"}], False
    if "技能水準" in label:
        if "評価区分" in label:
            return "specified_skilled_worker.eligibility.skill_level_assessment", [], False
        sub = int(code.split(".")[1]) if code and "." in code else 2
        if "その他の評価方法" in label:
            return "specified_skilled_worker.eligibility.skill_other_evidence", [], False
        index = max(0, (sub - 2) // 2)
        key = "test_location" if "受験地" in label else "name"
        conditions = [{"path": f"specified_skilled_worker.eligibility.skill_tests.{index}.name", "operator": "!=", "value": ""}] if index else []
        return f"specified_skilled_worker.eligibility.skill_tests.{index}.{key}", conditions, False
    if "日本語能力" in label:
        sub = int(code.split(".")[1]) if code and "." in code else 2
        if "評価区分" in label:
            return "specified_skilled_worker.eligibility.japanese_level_assessment", [], False
        if "その他の評価方法" in label:
            return "specified_skilled_worker.eligibility.japanese_other_evidence", [], False
        index = max(0, (sub - 2) // 2)
        key = "test_location" if "受験地" in label else "name"
        conditions = [{"path": f"specified_skilled_worker.eligibility.japanese_tests.{index}.name", "operator": "!=", "value": ""}] if index else []
        return f"specified_skilled_worker.eligibility.japanese_tests.{index}.{key}", conditions, False
    if "保証金" in label:
        return "specified_skilled_worker.eligibility.guarantee_deposit_exists", [], False
    if "徴収・管理機関名" in label:
        return "specified_skilled_worker.eligibility.guarantee_collecting_organization", [{"path": "specified_skilled_worker.eligibility.guarantee_deposit_exists", "value": True}], False
    if "徴収金額・管理財産" in label:
        return "specified_skilled_worker.eligibility.guarantee_amount", [{"path": "specified_skilled_worker.eligibility.guarantee_deposit_exists", "value": True}], False
    if "在日親族及び同居者" in label:
        if "有無" in label and not re.search(r"0[1-9]", label):
            return "applicant.family.has_japan_relatives_or_cohabitants", [], False
        match = re.search(r"0([1-9])", label)
        index = int(match.group(1)) - 1 if match else 0
        suffix = (
            "relationship" if "続柄" in label else "name" if "氏名" in label else
            "birth_date" if "生年月日" in label else "nationality_region" if "国籍" in label else
            "will_cohabit" if "同居予定" in label or "同居の有無" in label else "workplace_or_school_name" if "勤務先" in label else
            "residence_card_or_certificate_number"
        )
        return f"applicant.family.japan_relatives_or_cohabitants.{index}.{suffix}", [{"path": "applicant.family.has_japan_relatives_or_cohabitants", "value": True}], False
    if "国籍・地域" in label:
        return "applicant.nationality_region", [], False
    if label == "メールアドレス":
        return "applicant.japan_contact.email", [], False
    if "生年月日" in label:
        return "applicant.birth_date", [], False
    if "氏名" in label and "代理人" not in label:
        return "applicant.name_roman", [], False
    if "性別" in label:
        return "applicant.sex", [], False
    if "出生地" in label:
        return "applicant.birth_place", [], False
    if "配偶者の有無" in label:
        return "applicant.marital_status", [], False
    if "職業" in label and "職歴" not in label:
        return "applicant.occupation", [], False
    if "本国における居住地" in label:
        return "applicant.home_country_address", [], False
    if "日本における連絡先" in label:
        suffix = "postal_code" if "郵便番号" in label else "address" if "居住地" in label or "住居地" in label else "mobile" if "携帯" in label else "phone" if "電話" in label else "email"
        return f"applicant.japan_contact.{suffix}", [], False
    if "旅券" in label:
        suffix = "expiry_date" if "有効期限" in label else "number"
        return f"applicant.passport.{suffix}", [], False
    if "現に有する在留資格" in label:
        return "case.target_status_variant" if profile.startswith("renewal_") else "applicant.current_status", [], False
    if "在留カードの有無" in label:
        return "applicant.has_residence_card", [], False
    if "ED番号" in label:
        return "applicant.ed_number_letters" if "英字" in label else "applicant.ed_number_digits", [], False
    if "在留カード番号" in label:
        return "applicant.residence_card_number", [], False
    if "在留期間の満了日" in label:
        return "applicant.current_period_expiry_date", [], False
    if "特定技能1号での通算在留期間" in label:
        suffix = "years" if "年数" in label else "months"
        return f"specified_skilled_worker.cumulative_ssw_1_stay_{suffix}", [], False
    if "在留期間" in label and "希望" not in label and "満了日" not in label:
        return "applicant.current_period_of_stay", [], False
    if "希望する在留期間" in label:
        return "specified_skilled_worker.requested_period_of_stay", [], False
    if "変更の理由" in label:
        return "specified_skilled_worker.application.change_reason", [], False
    if "更新の理由" in label:
        return "specified_skilled_worker.application.renewal_reason", [], False
    if "申請対象者の住居地" in label:
        return "specified_skilled_worker.application.residence_prefecture", [], False
    if "入国目的" in label or "希望する在留資格" in label:
        return "case.target_status_variant", [], False
    if "入国予定年月日" in label:
        return "entry_plan.planned_entry_date", [], False
    if "上陸予定港" in label:
        if "その他" in label:
            return "entry_plan.planned_port_other", [{"path": "entry_plan.planned_port", "value": "その他 Others"}], False
        return "entry_plan.planned_port", [], False
    if "滞在予定期間" in label:
        return "entry_plan.planned_period_years" if "年数" in label else "entry_plan.planned_period_months", [], False
    if "同伴者の有無" in label:
        return "applicant.family.has_accompanying_members", [], False
    if "査証申請予定地" in label:
        return "entry_plan.visa_application_location", [], False
    if "過去の出入国歴" in label:
        root = "applicant.immigration_history"
        if "有無" in label:
            return f"{root}.has_entries", [], False
        if "回数" in label:
            return f"{root}.entries_count", [{"path": f"{root}.has_entries", "value": True}], False
        return f"{root}.latest_entry.start_date" if "始期" in label else f"{root}.latest_entry.end_date", [{"path": f"{root}.has_entries", "value": True}], False
    if "直近の出入国歴" in label:
        key = "start_date" if "始期" in label else "end_date"
        return f"applicant.immigration_history.latest_entry.{key}", [{"path": "applicant.immigration_history.has_entries", "value": True}], False
    if "過去の在留資格認定証明書交付申請歴" in label:
        root = "applicant.immigration_history.prior_coe_applications"
        if "有無" in label:
            return f"{root}.has_history", [], False
        return f"{root}.denial_count" if "不交付" in label else f"{root}.count", [{"path": f"{root}.has_history", "value": True}], False
    if "犯罪を理由とする処分" in label:
        return "applicant.immigration_history.criminal_record", [], False
    if "退去強制又は出国命令" in label:
        root = "applicant.immigration_history"
        if "直近" not in label and "有無" in label and "回数" not in label:
            return f"{root}.deportation_or_departure_order", [], False
        key = "deportation_count" if "回数" in label else "deportation_latest"
        return f"{root}.{key}", [{"path": f"{root}.deportation_or_departure_order", "value": True}], False
    if "代理人" in label:
        suffix = "name" if "氏名" in label else "relationship" if "本人との関係" in label else "postal_code" if "郵便番号" in label else "address" if "住所" in label else "mobile" if "携帯" in label else "phone"
        return f"proxy.{suffix}", [], False
    if "職歴の有無" in label:
        return "applicant.has_employment_history", [], False
    if "部分合計" in label:
        return None
    if "職歴" in label:
        suffix = "start_date" if "入社" in label else "end_date" if "退社" in label else "company_name_local"
        index = repeated_index(label) or 0
        return f"applicant.employment_history.{index}.{suffix}", [{"path": "applicant.has_employment_history", "value": True}], False
    if "主たる活動内容" in label:
        return None  # The SSW page keeps this other-status control hidden.
    return None


def mapping_for(fields: list[dict], profile: str) -> dict:
    mappings = []
    seen_ids: set[str] = set()
    for order, field in enumerate(fields, start=1):
        resolved = field_path(field, profile)
        if resolved is None:
            continue
        path, conditions, manual_only = resolved
        # Unrelated high-skilled-professional controls are present in the saved DOM.
        if "特別高度人材" in field["label"] or "特別加算" in field["label"]:
            continue
        controls = [control for control in field["controls"] if control["input_type"] != "file"]
        if not controls:
            controls = field["controls"][:1]
        control = next((c for c in controls if c["input_type"] == "text"), controls[0]) if path.endswith("birth_date") else controls[0]
        transform = (
            "date_yyyymmdd" if path.endswith(("birth_date", "expiry_date", "start_date", "end_date", "registration_date")) else
            "nationality_region" if path == "applicant.nationality_region" else
            "sex_ja" if path == "applicant.sex" else
            "marital_yes_no" if path == "applicant.marital_status" else ""
        )
        item = {
            "canonical_id": path if path not in seen_ids else f"{path}@{field['no'] or order}",
            "value_path": path,
            "form_order": order,
            "display_no": field["no"],
            "section": field["section"],
            "label": field["label"],
            "field_name": control["field_name"],
            "field_id": control["field_id"],
            "input_type": control["input_type"],
            "required": field["required"],
        }
        if transform:
            item["transform"] = transform
        if conditions:
            item["visible_when"] = conditions
        value_map = value_map_for(field, path)
        if value_map:
            item["value_map"] = value_map
            item.pop("transform", None)
        if path.startswith((
            "specified_skilled_worker.eligibility.skill_tests.",
            "specified_skilled_worker.eligibility.japanese_tests.",
            "specified_skilled_worker.overseas_intermediary.",
            "employer.industry_secondary_other.",
        )) or path.endswith(("skill_other_evidence", "japanese_other_evidence")):
            manual_only = True  # Assessment choice controls visibility; not established in live QA.
        if manual_only:
            item["manual_only"] = True
        elif field["required"] and (
            path.startswith(("specified_skilled_worker.support_plan.", "specified_skilled_worker.organization.compliance."))
            or path.startswith("specified_skilled_worker.application.card_receiving_")
            or path == "specified_skilled_worker.application.residence_prefecture"
            or path in {
                "specified_skilled_worker.contract.hours_equivalent_to_regular_worker",
                "specified_skilled_worker.contract.salary_at_least_japanese",
                "specified_skilled_worker.contract.different_treatment",
                "specified_skilled_worker.contract.home_leave_available",
                "specified_skilled_worker.contract.return_travel_cost_covered",
                "specified_skilled_worker.contract.health_and_life_support",
                "specified_skilled_worker.eligibility.guarantee_deposit_exists",
                "specified_skilled_worker.contract.payment_method",
                "employment.job_category_primary",
                "employer.industry_primary",
            }
        ):
            item["manual_required"] = True
        if profile == "renewal_specified_skilled_worker" and path == "specified_skilled_worker.requested_period_of_stay":
            option_texts = [option["text"] for c in field["controls"] for option in c["options"]]
            for variant, prefix in (("ssw_1", "特定技能１号"), ("ssw_2", "特定技能２号")):
                matching = [text for text in option_texts if text.startswith(prefix)]
                if not matching:
                    raise ValueError(f"period options missing for {variant}")
                variant_item = {
                    **item,
                    "canonical_id": f"{path}@{variant}",
                    "visible_when": [{"path": "case.target_status_variant", "value": variant}],
                    "value_map": {text: text for text in matching},
                }
                mappings.append(variant_item)
                seen_ids.add(variant_item["canonical_id"])
            continue
        mappings.append(item)
        seen_ids.add(item["canonical_id"])
    return {
        "schema_version": "1.0.0",
        "form_definition": f"{profile}.json",
        "description": f"Specified Skilled Worker {profile}; human-confirmed values only. No inferred defaults.",
        "mappings": mappings,
    }


def value_map_for(field: dict, path: str) -> dict[str, str]:
    options = [option["text"] for control in field["controls"] for option in control["options"]]
    choice_type = (
        "applicant.current_period_of_stay" if path == "applicant.current_period_of_stay" else
        "industry" if path.startswith("specified_skilled_worker.contract.industry.") else
        "business_category" if path.startswith("specified_skilled_worker.contract.business_category.") else ""
    )
    if choice_type:
        # Preserve every official choice, and accept only aliases with an
        # unambiguous equivalent in this saved RASENS form.
        choices = {text: text for text in options if text and "選択してください" not in text}
        aliases = {
            "applicant.current_period_of_stay": {"1年": "１年"},
            "industry": {
                "農業分野": "農業分野 Agriculture",
            },
            "business_category": {
                "耕種農業全般": "耕種農業（農業分野） General crop farming（Agriculture）",
            },
        }[choice_type]
        choices.update({alias: target for alias, target in aliases.items() if target in choices})
        return choices
    if path == "specified_skilled_worker.contract.payment_method":
        choices = {text: text for text in options if text}
        cash = "通貨払 Paid in cash"
        bank = "口座振込み Paid into a bank account"
        choices.update({
            alias: target for alias, target in {
                "通貨払": cash,
                "口座振込": bank,
                "口座振込み": bank,
            }.items() if target in choices
        })
        return choices
    if path == "specified_skilled_worker.application.card_receiving_method":
        mail = next((text for text in options if text.startswith("郵送")), "")
        counter = next((text for text in options if text.startswith("窓口")), "")
        return {"mail": mail, "office_counter": counter} if mail and counter else {}
    if path == "applicant.marital_status":
        married = next((text for text in options if text.startswith("有")), "")
        single = next((text for text in options if text.startswith("無")), "")
        return {"married": married, "single": single, "unmarried": single} if married and single else {}
    if path == "case.target_status_variant":
        first = next((text for text in options if "１号" in text), "")
        second = next((text for text in options if "２号" in text), "")
        return {"ssw_1": first, "ssw_2": second} if first and second else {}
    if path == "specified_skilled_worker.support_method":
        entrusted = next((text for text in options if "委託する" in text and "委託しない" not in text), "")
        own = next((text for text in options if "委託しない" in text), "")
        return {"entrusted": entrusted, "self": own} if entrusted and own else {}
    yes = next((text for text in options if normalized(text).startswith(("有", "はい", "Yes"))), "")
    no = next((text for text in options if normalized(text).startswith(("無", "いいえ", "No"))), "")
    return {"true": yes, "false": no} if yes and no else {}


def main() -> None:
    for profile, source in SOURCES.items():
        fields = parse_fields(source)
        form = {
            "schema_version": "1.0.0",
            "source_file": source.name,
            "description": f"PII-free saved RASENS field inventory for {profile}",
            "fields": fields,
        }
        mapping = mapping_for(fields, profile)
        for output in OUTPUTS:
            for directory, payload in (("form_definitions", form), ("mappings", mapping)):
                path = output / directory / f"{profile}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{profile}: {len(fields)} form fields, {len(mapping['mappings'])} mapped rows")


if __name__ == "__main__":
    main()
