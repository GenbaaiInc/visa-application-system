"""Regression checks for the three independent SSW RASENS mappings."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SpecifiedSkilledWorkerAssetsTest(unittest.TestCase):
    def assets(self, procedure: str) -> tuple[dict, dict]:
        profile = f"{procedure}_specified_skilled_worker"
        data = ROOT / "rasens-autofill/data"
        form = json.loads((data / "form_definitions" / f"{profile}.json").read_text(encoding="utf-8"))
        mapping = json.loads((data / "mappings" / f"{profile}.json").read_text(encoding="utf-8"))
        for directory, payload in (("form_definitions", form), ("mappings", mapping)):
            backend = ROOT / "visa-app/backend/data" / directory / f"{profile}.json"
            self.assertEqual(payload, json.loads(backend.read_text(encoding="utf-8")))
        return form, mapping

    def row(self, mapping: dict, path: str) -> dict:
        return next(item for item in mapping["mappings"] if item["value_path"] == path)

    def test_required_and_targets_covered(self) -> None:
        for procedure in ("coe", "change", "renewal"):
            with self.subTest(procedure=procedure):
                form, mapping = self.assets(procedure)
                target_keys = {
                    (item["field_id"], item["field_name"])
                    for item in mapping["mappings"]
                }
                all_keys = {
                    (control["field_id"], control["field_name"])
                    for field in form["fields"] for control in field["controls"]
                }
                self.assertTrue(target_keys <= all_keys)
                self.assertEqual(len(mapping["mappings"]), len({x["canonical_id"] for x in mapping["mappings"]}))
                missing = [
                    field["label"] for field in form["fields"]
                    if field["required"] and not field["conditional"]
                    and not any((c["field_id"], c["field_name"]) in target_keys for c in field["controls"])
                ]
                self.assertEqual([], missing)
                self.assertFalse(any("特別高度人材" in x["label"] for x in mapping["mappings"]))
                self.assertFalse(any(x["value_path"] == "entry_plan.main_activity_category" for x in mapping["mappings"]))
                fields_by_target = {
                    (c["field_id"], c["field_name"]): field
                    for field in form["fields"] for c in field["controls"]
                }
                for row in mapping["mappings"]:
                    field = fields_by_target[(row["field_id"], row["field_name"])]
                    if field["conditional"]:
                        self.assertTrue(row.get("visible_when") or row.get("manual_only"), row["label"])

    def test_procedure_specific_ids_and_conditions(self) -> None:
        field_names = []
        for procedure in ("coe", "change", "renewal"):
            _, mapping = self.assets(procedure)
            variant = self.row(mapping, "case.target_status_variant")
            self.assertIn("ssw_1", variant["value_map"])
            self.assertIn("ssw_2", variant["value_map"])
            dispatch = self.row(mapping, "specified_skilled_worker.dispatch_destination.name")
            self.assertEqual(
                [{"path": "specified_skilled_worker.employment_type", "value": "dispatch"}],
                dispatch["visible_when"],
            )
            field_names.append(dispatch["field_name"])
            plan = self.row(mapping, "specified_skilled_worker.support_plan.airport_pickup")
            self.assertEqual("ssw_1", plan["visible_when"][0]["value"])
            agency = self.row(mapping, "specified_skilled_worker.support_organization.name")
            self.assertEqual("entrusted", agency["visible_when"][1]["value"])
            own = self.row(mapping, "specified_skilled_worker.self_support.manager_name")
            self.assertEqual("self", own["visible_when"][1]["value"])
            marital = self.row(mapping, "applicant.marital_status")
            self.assertIn("married", marital["value_map"])
            self.assertNotIn("true", marital["value_map"])
        self.assertEqual(["item[199].textData", "item[191].textData", "item[189].textData"], field_names)

    def test_renewal_support_plan_is_label_matched(self) -> None:
        _, renewal = self.assets("renewal")
        airport = self.row(renewal, "specified_skilled_worker.support_plan.airport_pickup")
        self.assertEqual("4.1", airport["display_no"])
        self.assertFalse(any(
            row["value_path"] == "specified_skilled_worker.support_plan.contract_explanation_in_understood_language"
            for row in renewal["mappings"]
        ))
        periods = [item for item in renewal["mappings"] if item["value_path"] == "specified_skilled_worker.requested_period_of_stay"]
        self.assertEqual({"ssw_1", "ssw_2"}, {item["visible_when"][0]["value"] for item in periods})
        for item in periods:
            variant = item["visible_when"][0]["value"]
            prefix = "特定技能１号" if variant == "ssw_1" else "特定技能２号"
            self.assertTrue(all(text.startswith(prefix) for text in item["value_map"].values()))

    def test_radio_choices_and_family_dates(self) -> None:
        coe_form, coe_mapping = self.assets("coe")
        method = self.row(coe_mapping, "settings.receiving_method.method")
        field = next(f for f in coe_form["fields"] if any(c["field_id"] == method["field_id"] for c in f["controls"]))
        selected = next(c for c in field["controls"] if c["field_id"] == method["field_id"])
        self.assertEqual({"郵送 Mailing", "メール Email"}, {o["text"] for o in selected["options"]})
        for procedure in ("coe", "change", "renewal"):
            _, mapping = self.assets(procedure)
            for index in range(6):
                date = self.row(mapping, f"applicant.family.japan_relatives_or_cohabitants.{index}.birth_date")
                self.assertEqual("text", date["input_type"])
                self.assertTrue(date["field_id"].startswith("textData1_"))

    def test_change_and_renewal_card_delivery_is_case_specific(self) -> None:
        for procedure in ("change", "renewal"):
            with self.subTest(procedure=procedure):
                _, mapping = self.assets(procedure)
                method = self.row(mapping, "specified_skilled_worker.application.card_receiving_method")
                self.assertEqual({"mail", "office_counter"}, set(method["value_map"]))
                self.assertIn("郵送", method["value_map"]["mail"])
                self.assertIn("窓口", method["value_map"]["office_counter"])
                prefecture = self.row(mapping, "specified_skilled_worker.application.residence_prefecture")
                office = self.row(mapping, "specified_skilled_worker.application.card_receiving_office")
                self.assertEqual("select", prefecture["input_type"])
                self.assertEqual("select", office["input_type"])
                self.assertTrue(prefecture["label"].endswith("住居地"))
                self.assertNotEqual(prefecture["value_path"], "applicant.japan_contact.address")
                self.assertFalse(any(
                    item["value_path"] in {"settings.receiving_method.method", "settings.receiving_method.office"}
                    for item in mapping["mappings"]
                ))

    def test_document_terms_map_only_to_confirmed_rasens_choices(self) -> None:
        for procedure in ("coe", "change", "renewal"):
            with self.subTest(procedure=procedure):
                form, mapping = self.assets(procedure)
                for index in range(3):
                    for path, alias, expected in (
                        (f"specified_skilled_worker.contract.industry.{index}", "農業分野", "農業分野 Agriculture"),
                        (f"specified_skilled_worker.contract.business_category.{index}", "耕種農業全般", "耕種農業（農業分野） General crop farming（Agriculture）"),
                    ):
                        row = self.row(mapping, path)
                        self.assertEqual(expected, row["value_map"][alias])
                        field = next(field for field in form["fields"] if field["label"] == row["label"])
                        choices = {option["text"] for control in field["controls"] for option in control["options"]}
                        self.assertIn(expected, choices)
                        self.assertEqual(expected, row["value_map"][expected])
                        self.assertNotIn("水産業分野", row["value_map"])
                if procedure != "coe":
                    period = self.row(mapping, "applicant.current_period_of_stay")
                    self.assertEqual("１年", period["value_map"]["1年"])
                    self.assertEqual("１年", period["value_map"]["１年"])

    def test_ambiguous_contract_and_company_choices_require_human_review(self) -> None:
        for procedure in ("coe", "change", "renewal"):
            with self.subTest(procedure=procedure):
                _, mapping = self.assets(procedure)
                for path in (
                    "specified_skilled_worker.contract.payment_method",
                    "employment.job_category_primary",
                    "employer.industry_primary",
                ):
                    self.assertTrue(self.row(mapping, path).get("manual_required"), path)
                payment = self.row(mapping, "specified_skilled_worker.contract.payment_method")
                self.assertEqual("通貨払 Paid in cash", payment["value_map"]["通貨払"])
                self.assertEqual("口座振込み Paid into a bank account", payment["value_map"]["口座振込"])
                self.assertNotIn("transform", self.row(mapping, "employer.industry_primary"))

    def test_only_document_neutral_metadata_emitted(self) -> None:
        for procedure in ("coe", "change", "renewal"):
            form, _ = self.assets(procedure)
            for field in form["fields"]:
                for control in field["controls"]:
                    self.assertEqual(
                        {"field_id", "field_name", "input_type", "options"},
                        set(control),
                    )
            # The required photo and final human confirmations are not autofill rows.
            _, mapping = self.assets(procedure)
            self.assertTrue(any(row.get("manual_only") and "photo_file" in row["value_path"] for row in mapping["mappings"]))


if __name__ == "__main__":
    unittest.main()
