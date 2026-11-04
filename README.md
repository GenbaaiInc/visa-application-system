# 在留資格申請支援システム

申請資料の読み取り・確認を行う `visa-app` と、確認済みの値を RASENS の画面へ入力補助する Chrome 拡張を含むリポジトリです。技人国と特定技能、認定（COE）・変更・更新を扱います。実申請の判断・最終送信は人が行います。

## 別の PC で始める

このリポジトリは公開されていますが、実案件資料・評価用 fixture・認証情報は含まれません。引き継ぎ担当者から **コミット ID**、必要に応じて制限付きデータの受け渡し方法を確認してください。今回の引き継ぎ対象は `docs/tokutei-skill-design` ブランチです。GitHub の `main` が本番と同じ内容とは限りません。

```bash
git clone https://github.com/GenbaaiInc/visa-application-system.git
cd visa-application-system
git switch --track origin/docs/tokutei-skill-design
```

必要なものは Node.js / npm、Python 3.12、ローカルで実サービスを動かす場合は権限のある Google Cloud アカウントです。`visa-app` のコードは次のように準備・テストできます。

```bash
cd visa-app/frontend
npm ci
npm run build
npx playwright install chromium
npx playwright test

cd ../backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q
```

ローカル画面は、別々のターミナルで `visa-app/backend` から `.venv/bin/python -m uvicorn main:app --reload --port 8080`、`visa-app/frontend` から `npm run dev` を実行します。画面から実データやクラウド資源にアクセスするには、別途認証・権限が必要です。環境設定や構成の詳細は [visa-app/AGENTS.md](visa-app/AGENTS.md) を参照してください。

Chrome 拡張は [rasens-autofill/extension/README.md](rasens-autofill/extension/README.md) にローカル読込手順があります。拡張の配布・更新は Cloud Run へのアプリ配置とは別作業です。

## 置き場と本番

| 場所 | 内容 |
| --- | --- |
| `visa-app/frontend/` | レビュー画面（React） |
| `visa-app/backend/` | API、Gemini 抽出、入力値生成（FastAPI） |
| `rasens-autofill/extension/` | RASENS 入力補助 Chrome 拡張 |
| `visa-eval/` | 抽出精度の評価用コードと、Git 管理外の実資料 |
| `docs/` | 業務・設計資料。現行構成の入口は [こちら](visa-app/docs/006_current_architecture/README.md) |

本番アプリは Google Cloud プロジェクト `visa-codex-mvp`、リージョン `asia-northeast1` の Cloud Run サービス `visa-app` です：[本番 URL](https://visa-app-913363513517.asia-northeast1.run.app/)。案件データは Firestore、原資料は Cloud Storage、Gemini API キーは Secret Manager で管理します。GitHub を取得しても本番データや秘密情報は取得されません。

デプロイ前には [リリース記録](docs/shared/019_application_workflows/リリース記録.md) と稼働中の Cloud Run リビジョン・コンテナ digest を照合してください。過去の本番版には未コミットのローカル変更からビルドされたものがあり、Git のコミットだけでは本番との一致を証明できません。`gcloud` の既定プロジェクトが別件になっている場合があるため、GCP コマンドには `--project visa-codex-mvp`、Cloud Run の操作には `--region asia-northeast1` も明示します。デプロイ方法と権限は [visa-app/AGENTS.md](visa-app/AGENTS.md) にあります。

## 実資料の扱い

実案件資料、`visa-eval/raw/`、`visa-eval/test_cases_from_raw/` の案件別データ、`visa-eval/eval_runs/`、`qa/` は個人情報を含む可能性があり Git に入れません。別 PC への移動は、所有者が指定する安全な方法で、GitHub とは別に行ってください。評価データの配置と実行方法は [ローカル実験の手順](docs/local_experiment_onboarding.md) を参照してください。公開 issue や AI チャットにも実名・住所・旅券番号等を貼らないでください。

全体の案内は [docs/README.md](docs/README.md)、各プロジェクト固有の注意事項はそれぞれの `AGENTS.md` にあります。
