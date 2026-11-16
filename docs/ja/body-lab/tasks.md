> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/body-lab/tasks.md`](../../../.kiro/specs/body-lab/tasks.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `e4ed1885fd24e91202a2ce3604845a8d0101dff732d03b8fab7a506f5899501f`

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
- **6. 40 試行の Dr. Kiro セッションの 2 回目（body-2）** — **Stop and ask（止めて確認）** — 完了
  - 理由: body-1 の記録には、発見した spec の表が入っていない。ベンチがセッションの終わりに 3 つの仕様ファイルを記録する（`lab-bench` 10.4）前に封印されたため、終了スナップショットがなく、`discovered/` に写しもない（`dr-kiro` 決定事項 12）。body-1 は封印・コミットされたまま残す。
  - body-1 と違う条件（どれも body-2 を始める時点の main ブランチのもの）: workflow のステアリングに、否定されたルールは表に `rejected` の行として残るという文がある（`dr-kiro` 要件 3.7、決定事項 8）。`end_session` が終了スナップショットを記録する。ラボの `.kiro/specs/` はテンプレートの状態で追跡される。セッション id は `body-2`、シードは 2（body-1 はシード 1）。アダプター、モデル、目標、予算は同じ。
  - ユーザーが Mac で、ビルダーがチャットで書いた手順で実行する。合格: タスク 5 と同じで、さらに `bench-export-spec` が `discovered/body-lab/body-2/` を書き、`bench-check-discovered` が通ること。
  - その後、ビルダーが結果をここに記録し、`discovered/README.md` を更新する。
  - 結果（body-2、macOS、2026-11-16、コミット `471ca88`）: Dr. Kiro 自身の `end_session` で `ended` として封印された。40 試行のうち 39 を使用（残り 1）、拒否 3 件、再開の一文なし。`bench-verify` は 125 件のエントリーと 77 個の blob を検証した。ラボと封印済みフォルダーに対する `bench-scan` は検出なし。`bench-export-spec` が `discovered/body-lab/body-2/` を書き、`bench-check-discovered` が通り、その写しのスキャンも検出なし。表は 14 行: `validated` 2、`observed` 4、`rejected` 8（それぞれ置き換える行を示す）。Dr. Kiro が挙げたステアリングは `workflow` と `method` だけだった。
  - _要件: 6.2_
