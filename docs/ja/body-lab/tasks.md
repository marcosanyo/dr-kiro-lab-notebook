> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/body-lab/tasks.md`](../../../.kiro/specs/body-lab/tasks.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `283b3c6a16bcdee840e59015b12341f5bb319f0cbda4124c79aa5a524d19ab49`

# タスク: body-lab

各タスクは、`sh bench/scripts/check.sh` とアダプターのテストが通ることで終わります。

- **1. ベンチ: `goal` と `measured_by`** — 未着手
  - 両方のフィールドを `Declaration` と `check_declaration`、フェイクアプリケーション、ツールの説明（`describe.py`）に加える。dr-kiro の `workflow.md` を更新する（フェーズ 1-3 ではすべての計測項目を調べる）。
  - _要件: lab-bench 2.1, dr-kiro 3.3_

- **2. シミュレーションと計測器** — 未着手
  - `body-lab/adapter/` の uv プロジェクト。`sim.py`、`measure.py`、`settings.py`（設計 2、3）。
  - _要件: 1, 2, 5.1_

- **3. 画像とアダプター** — 未着手
  - `picture.py`、`adapter.py`、`scan_sources.toml`。設計 7 の 4 つのテスト。
  - _要件: 3, 4, 5, 6.1_

- **4. README とラボ** — 未着手
  - `body-lab/README.md`（計測のしかた、視野の大きさ、実行方法、制限）。`bench-make-lab body-lab/lab` を実行し、コミットする。
  - _要件: 2.4, 5.2, 5.4_

- **5. 40 試行の Dr. Kiro セッション 1 回** — **Stop and ask（止めて確認）** — 完了
  - ユーザーが Mac で実行する。合格: `ended` として封印され、ラボと封印済みフォルダーに対する `bench-scan` が何も報告しないこと。あわせて dr-kiro のタスク 5 の確認も行う。
  - 最初の実行の結果（body-1、macOS、2026-11-13）: 再開の一文なしで、予算の残り 0 で `ended` として封印された。`bench-verify` は 117 件を検証した。ラボと封印済みフォルダーに対する `bench-scan` は、フックを `python -B` で起動するよう変えた後に、検出なしと報告した（ラボ内の `.pyc` がスキャンを止めていた）。Dr. Kiro が挙げたステアリングは `method` と `workflow` だけだった。
  - _要件: 6.2_
