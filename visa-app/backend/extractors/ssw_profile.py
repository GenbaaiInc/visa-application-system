"""Small, independent extraction profile for specified skilled worker cases."""

import copy
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from .schema import SCOPE_APPLICANT_IDENTITY_SCHEMA, SCOPE6_REVIEW_SCHEMA, _fv, _object_of_fields


SSW_EXTRACTION_SCOPES = (
    "applicant_identity",
    "ssw_status",
    "ssw_employer",
    "ssw_contract",
    "ssw_eligibility",
    "ssw_dispatch",
    "ssw_support_organization",
    "ssw_recruitment",
    "ssw_self_support",
)


def _section(properties: dict) -> dict:
    return {"type": "OBJECT", "properties": properties, "required": list(properties)}


_TEST_SCHEMA = {
    "type": "ARRAY",
    "items": _object_of_fields(["name", "test_result", "test_location"]),
}

_TEXT_LIST = {"type": "ARRAY", "items": _fv()}


def _fields_with_lists(fields: list[str], lists: list[str]) -> dict:
    schema = _object_of_fields(fields)
    for name in lists:
        schema["properties"][name] = copy.deepcopy(_TEXT_LIST)
        schema["required"].append(name)
    return schema


_ROOT_SECTIONS = {
    "applicant": _section({name: _fv() for name in (
        "residence_card_number", "current_status", "current_period_of_stay",
        "current_period_expiry_date",
    )}),
    "employer": _fields_with_lists(
        [
            "name", "corporate_number", "postal_code", "address",
            "phone", "capital_jpy", "annual_sales_jpy", "employee_count",
            "employment_insurance_office_number", "representative_name",
            "industry_primary", "industry_other",
        ],
        ["industry_secondary", "industry_secondary_other"],
    ),
    "employment": _object_of_fields(["monthly_salary", "job_category_primary"]),
    "entry_plan": _object_of_fields(
        ["planned_entry_date", "planned_port", "planned_period_years", "planned_period_months"]
    ),
}

_SSW_SECTIONS = {
    "employment_type": _fv(),
    "support_method": _fv(),
    "requested_period_of_stay": _fv(),
    "cumulative_ssw_1_stay_years": _fv(),
    "cumulative_ssw_1_stay_months": _fv(),
    "application": _object_of_fields(["change_reason", "renewal_reason"]),
    "eligibility": _section({
        "skill_level_assessment": _fv(),
        "skill_other_evidence": _fv(),
        "japanese_level_assessment": _fv(),
        "japanese_other_evidence": _fv(),
        "skill_tests": copy.deepcopy(_TEST_SCHEMA),
        "japanese_tests": copy.deepcopy(_TEST_SCHEMA),
    }),
    "contract": _fields_with_lists(
        [
            "start_date", "end_date", "weekly_hours", "monthly_hours",
            "hours_equivalent_to_regular_worker", "hourly_base_pay",
            "comparable_japanese_salary", "payment_method",
        ],
        ["industry", "business_category", "job_category_other"],
    ),
    "workplace": _object_of_fields(
        ["name", "postal_code", "address", "labor_insurance_number"]
    ),
    "dispatch_destination": _object_of_fields([
        "name", "corporate_number", "employment_insurance_office_number",
        "postal_code", "address", "phone", "representative_name",
        "dispatch_start_date", "dispatch_end_date",
    ]),
    "support_organization": _object_of_fields([
        "name", "corporate_number", "employment_insurance_office_number",
        "postal_code", "address", "phone", "representative_name",
        "registration_number", "registration_date", "office_name",
        "office_postal_code", "office_address", "support_manager_name",
        "support_staff_name", "available_languages", "monthly_fee",
    ]),
    "recruiter": _object_of_fields([
        "name", "corporate_number", "employment_insurance_office_number",
        "postal_code", "address", "phone", "permit_number", "permit_accepted_date",
    ]),
    "overseas_intermediary": _object_of_fields(
        ["name", "country_region", "postal_code", "address", "phone"]
    ),
    "self_support": _object_of_fields(
        ["manager_name", "manager_position", "staff_name", "staff_position"]
    ),
}


def _scope_schema(*, root: tuple[str, ...] = (), ssw: tuple[str, ...] = ()) -> dict:
    properties = {name: copy.deepcopy(_ROOT_SECTIONS[name]) for name in root}
    if ssw:
        properties["specified_skilled_worker"] = _section(
            {name: copy.deepcopy(_SSW_SECTIONS[name]) for name in ssw}
        )
    return _section(properties)


def _status_schema(case_meta: dict) -> dict:
    application_type = case_meta.get("application_type")
    root_names = (
        ("employment", "entry_plan")
        if application_type == "certificate_of_eligibility"
        else ("employment", "applicant")
    )
    ssw_names = [
        "employment_type",
        "support_method",
        "cumulative_ssw_1_stay_years",
        "cumulative_ssw_1_stay_months",
    ]
    if application_type != "certificate_of_eligibility":
        ssw_names.append("requested_period_of_stay")
        ssw_names.append("application")
    if case_meta.get("target_status_variant") == "ssw_2":
        ssw_names.remove("support_method")

    schema = _scope_schema(root=root_names, ssw=tuple(ssw_names))
    if application_type != "certificate_of_eligibility":
        reasons = schema["properties"]["specified_skilled_worker"]["properties"]["application"]
        other_reason = "renewal_reason" if application_type == "change_of_status" else "change_reason"
        reasons["properties"].pop(other_reason)
        reasons["required"].remove(other_reason)
    return schema


SSW_SPLIT_SCOPE_SCHEMAS = {
    "ssw_employer": _scope_schema(root=("employer",)),
    "ssw_contract": _scope_schema(ssw=("contract", "workplace")),
    "ssw_eligibility": _scope_schema(ssw=("eligibility",)),
    "ssw_dispatch": _scope_schema(ssw=("dispatch_destination",)),
    "ssw_support_organization": _scope_schema(ssw=("support_organization",)),
    "ssw_recruitment": _scope_schema(ssw=("recruiter", "overseas_intermediary")),
    "ssw_self_support": _scope_schema(ssw=("self_support",)),
}


SSW_REVIEW_SCHEMA = SCOPE6_REVIEW_SCHEMA


def ssw_extraction_scopes(case_meta: dict) -> tuple[str, ...]:
    scopes = list(SSW_EXTRACTION_SCOPES)
    if case_meta.get("target_status_variant") == "ssw_2":
        scopes.remove("ssw_support_organization")
        scopes.remove("ssw_self_support")
    return tuple(scopes)


def ssw_scope_schema(scope: str, case_meta: dict) -> dict:
    """Drop procedure-inapplicable fields instead of emitting empty overwrite candidates."""
    if scope == "ssw_status":
        return _status_schema(case_meta)
    if scope == "applicant_identity":
        return SCOPE_APPLICANT_IDENTITY_SCHEMA
    if scope == "review":
        return SSW_REVIEW_SCHEMA
    if scope in SSW_SPLIT_SCOPE_SCHEMAS:
        return copy.deepcopy(SSW_SPLIT_SCOPE_SCHEMAS[scope])
    raise KeyError(scope)


_EVIDENCE_RULES = """\
各値は {"value": "...", "source_ref": {"document_id": "...", "page": 1,
"text_quote": "...", "confidence": 0.95}} の形で返す。
原本に直接ある値だけを抽出し、連続した原文引用と実際の文書ID・ページを付ける。
値の位置はJSON直下の source_locations に field_path とともに記録する。
PDFは pdf_bbox（1000分率bbox）、Excelは xlsx_cell（セルID）、DOCXは docx_block（ブロックID）を使う。
資料にない文字列は value=""、source_ref は空値とする。別欄・別会社・別人物の値で補わない。
明記されない有無を「無」と推測しない。1号／2号は案件メタを正本とし、資料から変更しない。
"""


_IDENTITY_RULES = """\
申請人の氏名・生年月日・国籍・性別・旅券・連絡先を抽出する。
氏名と生年月日は旅券の顔写真側の身分事項欄を優先し、MRZは照合に用いる。
旅券顔写真側のページ候補を passport_identity_page_candidates に記録する。
氏名は旅券表記の姓→名の順、生年月日はYYYY-MM-DDへ正規化する。
出生地・本国住所・日本の住所・勤務先住所は混同しない。
"""


_SSW_STATUS_RULES = """\
特定技能案件の現在の在留情報、入国予定、希望在留期間、雇用形態、
変更・更新理由、雇用の基本条件だけを抽出する。
現在の資格・在留期限・在留カード番号は applicant.* に置き、認定では空欄とする。
認定では入国予定を entry_plan.* に置き、変更・更新では入国予定を推測して埋めない。
雇用形態は明記された場合だけ direct/dispatch を入れる。
更新希望期間、変更・更新理由は、資料に明記された場合だけ入れる。
employment.job_category_primary は本人が実際に従事する仕事内容・職種の資料で確認する。
指定書の「特定産業分野」（例：農業）は職種を示す欄ではないため、
それだけを根拠に職種を埋めない。仕事内容から職種を確定できなければ空欄にする。
"""

_SSW_1_STATUS_RULES = """\
特定技能1号の支援方法は、資料に明記された場合だけ self/entrusted を入れる。
"""


_SSW_EMPLOYER_RULES = """\
所属機関・受入機関そのものの情報だけを employer.* に抽出する。
派遣先、勤務事業所、登録支援機関、職業紹介機関と取り違えない。
法人番号、雇用保険適用事業所番号、代表者、所在地、業種は、原本に直接ある場合だけ入れる。
employer.industry_primary は会社の主たる事業・業種を示す資料で確認する。
指定書の「特定産業分野」は在留資格上の分野であり、会社の主たる業種の根拠にしない。
会社の主業種が確認できなければ空欄にする。
"""


_SSW_CONTRACT_RULES = """\
特定技能雇用契約と実際の勤務事業所だけを抽出する。
契約期間、労働時間、報酬、支払方法、従事業務分野は contract.* に置く。
支払方法が複数のチェック欄で示される場合、チェックの入った欄だけを選ぶ。
欄の名称が印刷されているだけでは選択されたことにならない。
口座振込と現金払を必ず見比べ、チェックの位置を判読できなければ payment_method は空欄にする。
source_ref.text_quote にはチェック状態が分かる原文の行を引用する。
勤務事業所名・所在地・労働保険番号は specified_skilled_worker.workplace.* に置く。
所属機関の本社情報や派遣先情報を、勤務事業所として推測入力しない。
"""


_SSW_ELIGIBILITY_RULES = """\
技能水準・日本語水準の根拠だけを specified_skilled_worker.eligibility.* に抽出する。
技能試験と日本語試験は、資料に記載された分だけtests配列へ入れる。
1号／2号や合格有無は案件メタや原本の明記を優先し、別資料から推測しない。
"""


_SSW_DISPATCH_RULES = """\
派遣先に関する情報だけを specified_skilled_worker.dispatch_destination.* に抽出する。
派遣案件でない、または派遣先が資料に明記されない場合は空欄にする。
派遣元である所属機関や勤務事業所を派遣先として複製しない。
"""


_SSW_SUPPORT_ORGANIZATION_RULES = """\
登録支援機関へ委託する場合の委託先情報だけを support_organization.* に抽出する。
所属機関、自社支援担当者、職業紹介機関を登録支援機関として扱わない。
登録番号、登録年月日、対応言語、委託費は明記がある場合だけ入れる。
"""


_SSW_RECRUITMENT_RULES = """\
職業紹介機関と国外あっせん機関だけを抽出する。
国内の職業紹介機関は specified_skilled_worker.recruiter.*、
国外の取次・あっせん機関は specified_skilled_worker.overseas_intermediary.* に置く。
所属機関、派遣先、登録支援機関とは混同しない。
"""


_SSW_SELF_SUPPORT_RULES = """\
自社支援の場合の支援責任者・支援担当者だけを specified_skilled_worker.self_support.* に抽出する。
登録支援機関へ委託する場合や資料に明記がない場合は空欄にする。
"""


_REVIEW_RULES = """\
抽出した値と資料を照合し、missing_items、findings、validation_errors を日本語で返す。
資格の適合をAIだけで確定せず、技能・日本語の根拠、雇用契約、派遣先、
現在の在留資格・期限など、不足・矛盾・人の申告事項を列挙する。
別の在留資格に固有の審査観点を流用しない。
"""

_SSW_1_REVIEW_RULES = """\
特定技能1号では、支援方法と、委託の場合の登録支援機関も確認する。
"""


def build_ssw_scoped_prompt(
    scope: str,
    case_meta: dict,
    documents: list[dict],
    extra_context: dict | None = None,
) -> str:
    document_list = "\n".join(
        f"- {doc.get('file_name', 'unknown')} (role: {doc.get('document_role', 'unknown')}, "
        f"document_id: {doc.get('document_id', 'unknown')})"
        for doc in documents
    ) or "(なし)"
    is_ssw_1 = case_meta.get("target_status_variant") != "ssw_2"
    status_rules = _SSW_STATUS_RULES + (_SSW_1_STATUS_RULES if is_ssw_1 else "")
    review_rules = _REVIEW_RULES + (_SSW_1_REVIEW_RULES if is_ssw_1 else "")
    instructions = {
        "applicant_identity": _IDENTITY_RULES + _EVIDENCE_RULES,
        "ssw_status": status_rules + _EVIDENCE_RULES,
        "ssw_employer": _SSW_EMPLOYER_RULES + _EVIDENCE_RULES,
        "ssw_contract": _SSW_CONTRACT_RULES + _EVIDENCE_RULES,
        "ssw_eligibility": _SSW_ELIGIBILITY_RULES + _EVIDENCE_RULES,
        "ssw_dispatch": _SSW_DISPATCH_RULES + _EVIDENCE_RULES,
        "ssw_support_organization": _SSW_SUPPORT_ORGANIZATION_RULES + _EVIDENCE_RULES,
        "ssw_recruitment": _SSW_RECRUITMENT_RULES + _EVIDENCE_RULES,
        "ssw_self_support": _SSW_SELF_SUPPORT_RULES + _EVIDENCE_RULES,
        "review": review_rules,
    }
    if scope not in instructions:
        raise ValueError(f"Unknown specified skilled worker scope: {scope!r}")
    parts = [
        "あなたは特定技能の申請資料から事実を抽出するAIです。",
        f"案件ID: {case_meta.get('case_id', 'unknown')}",
        f"手続き: {case_meta.get('application_type', 'unknown')}",
        f"在留資格: {case_meta.get('target_status', 'unknown')}",
        f"特定技能区分: {case_meta.get('target_status_variant', 'unknown')}",
        f"今日の日付: {datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat()}",
        "書類一覧:",
        document_list,
        instructions[scope],
    ]
    if scope == "review" and extra_context is not None:
        parts.extend(["抽出済み案件データ:", json.dumps(extra_context, ensure_ascii=False)])
    return "\n".join(parts)
