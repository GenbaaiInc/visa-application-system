# 特定技能・更新fixture QA（2026-09-17）

> 入力候補の正誤、不足73件の内訳、受領PDFとの人物照合は[2026-09-30の追加調査](更新QA_入力項目と修正範囲_2026-09-30.md)を参照。ページ参照があるだけでは値の正しさを保証しない。

## 目的

受領した特定技能資料について、AIへ渡す入力資料とRASENS入力済み確認PDFを混ぜずに整理し、その入力で抽出と表示件数を確認する。

## 正しいデータの分け方

今回のQAでは、次のように分ける。

| 役割 | 置き場所 | AI入力 |
|---|---|---|
| 更新申請の元資料 | `visa-eval/test_cases_from_raw/ssw_received_20260913/applicant_renewal_001/input/files/` | 使う |
| RASENS申込確認PDF | `visa-eval/raw/特定技能/2026-09-13/` | 使わない |
| golden候補 | `expected_verified/` | まだ作らない |

受領したRASENS申込確認PDFは、更新資料とは申請人が一致しない。そのため、このfixtureの正解監査資料やgolden作成根拠にも使わず、未対応の受領原本としてのみ保存する。Gemini入力へも入れない。

変更申請資料は複数申請人を含む束だったため、1案件1人の評価fixtureとしては、人物ごとのページ範囲を確認してから分割する。今回は更新1人分を先にQA対象にした。

## 実行

fixture:

```text
visa-eval/test_cases_from_raw/ssw_received_20260913/applicant_renewal_001/
```

dry-run:

```sh
visa-app/backend/.venv/bin/python visa-eval/scripts/run_gemini_bytes_eval.py \
  visa-eval/test_cases_from_raw/ssw_received_20260913/applicant_renewal_001 \
  --dry-run
```

実行:

```sh
visa-app/backend/.venv/bin/python visa-eval/scripts/run_gemini_bytes_eval.py \
  visa-eval/test_cases_from_raw/ssw_received_20260913/applicant_renewal_001 \
  --run-id ssw-renewal-correct-input-20260917
```

生成物:

```text
visa-eval/eval_runs/ssw_renewal_correct_input_20260917/ssw_received_20260913__renewal_001/
```

## 結果

| 指標 | 件数 | 意味 |
|---|---:|---|
| Gemini入力 | 1 PDF / 約1.98 MiB | 更新資料だけ。RASENS確認PDFは含めない |
| 抽出された非空のcase_data | 33 | 案件メタとsource情報を除いた値ありパス |
| RASENS rows | 31 | 現時点でapplication-dataに出た投入候補 |
| rows skipped empty | 250 | mapping上はあるが、値が空で投入しない項目 |
| 必須不足 | 73 | 設定項目も含むapplication-data上の不足 |
| 人確認待ち | 5 | RASENS上または担当者確認が必要な項目 |
| レビュー画面表示行 | 153 | FieldPanelの表示ロジックで表示される行数 |

## 本番画面での再確認

整理済みfixtureの更新資料1 PDFだけを本番環境の新規QA案件へアップロードし、特定技能1号・在留期間更新としてGemini抽出を実行した。抽出はエラーなく完了し、レビュー画面へ遷移した。申請の保存・送信、RASENSへの入力は行っていない。

| 本番画面の確認項目 | 件数 |
|---|---:|
| アップロード資料 | 1 PDF |
| レビュー画面の表示行 | 153 |
| 値または固定設定が表示された行 | 35 |
| そのうち資料ページの根拠が付いた行 | 31 |
| 未入力表示の行 | 118 |

表示行のセクション別内訳は、下記のオフライン検算とすべて一致した。したがって、今回の資料で「抽出結果が少数しか表示されない」という状態ではなく、申請全体の153項目を表示し、そのうち資料から確認できた31項目にページ根拠が付く状態まで確認できた。

`35` はAI抽出件数そのものではない。レビュー画面上の手続き・在留資格などの固定設定を含む。一方、オフラインの `33` は保存された非空の抽出データ数であり、画面へのmapping対象外を含む。このため、目的の異なる件数として分けて扱う。

レビュー画面表示行の内訳:

| セクション | 行数 |
|---|---:|
| 申請人・その他 | 43 |
| 特定技能雇用契約 | 34 |
| 特定技能所属機関・支援 | 39 |
| 登録支援機関 | 16 |
| 1号特定技能外国人支援計画 | 14 |
| 申請条件 | 2 |
| 申請概要 | 4 |
| 受領方法 | 1 |

## 解釈

前回の合成PNG QAで少なく見えた主因は、入力資料が短い合成データで、抽出される値自体が少なかったため。実資料fixtureでは、抽出値は33、RASENS rowsは31まで増えた。

一方、画面は全317項目を常時表示するものではない。特定技能では、案件メタ、抽出済み・必須不足・人確認に関係する項目を中心に表示する。したがって、見るべき件数は次のように分ける。

- AI抽出の量: 非空の `case_data` パス数。
- RASENS投入候補: `application_data.rows` の件数。
- レビュー画面の見え方: FieldPanelに表示される行数。
- 申請完了に必要な不足: `missing_required_fields` と `pending_manual_fields`。

このfixtureは「抽出・表示・application-data生成が動く」ことの確認であり、全項目の正解率測定ではない。正解率を測るには、この申請人と一致するRASENS出力または人手確認済みの正解値から `expected_verified/case_data.golden.json` を作る必要がある。今回の申込確認PDFは別人なので使わない。
