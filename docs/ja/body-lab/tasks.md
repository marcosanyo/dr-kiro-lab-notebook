> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/body-lab/tasks.md`](../../../.kiro/specs/body-lab/tasks.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `107f8c2b2e6398cc635677ac28e2c26b51a95abddc76f0ed0bdd27130ba274b6`

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

## 改訂: 2 つ目のボディ（要件 7）

先に `lab-bench` のタスク 38（`variant` 設定）が要る。ブランチ `feat/second-body`。

- **7. ボディ `b` とボディの選択** — 完了
  - `specimen_02.xml`、`BODIES`、`sim.build(settings, body)`、`BodyAdapter(variant=...)` と `variants`（設計 10）。`scan_sources.toml` の 2 つ目のソース。`tests/test_bodies.py`。伝える文のゴールデンファイルはそのまま。README にオプションとラベルを書く。
  - _要件: 7.1-7.6_

- **8. 同じ入力を両方のボディで** — 完了
  - 設計 10 の比較を 3 つのプローブだけで行った（body-1 と body-2 の全試行の再実行は、ユーザーの指示でクレジット節約のため省いた）。`scripts/compare_bodies.py`。結果、ボディ `a` と `b`（x、y は m、heading は度）:
    - 全チャンネル 0: `a` x 4.8e-05、y -2.1e-05、heading 0.009。`b` x 2.5e-05、y -5.3e-06、heading -0.004。
    - 車輪のチャンネル +1: `a` x -0.230、y 0.011、heading 39.18。`b` x 2.5e-05、y -5.3e-06、heading -0.004（動かない）。
    - 車輪のチャンネル -1: `a` x 0.113、y 0.027、heading -34.96。`b` x 2.5e-05、y -5.3e-06、heading -0.004（動かない）。
    - タイヤがないと、ボディ `b` は 3 つのプローブのどれでも動かない。軸は床を押せない。
  - _要件: 7.8_

- **9. 目隠しの確認** — 完了（封印された記録とノートの分は本番の後）
  - 済み: リポジトリのラボの `bench-scan`（検出なし）。ラボのコピーは `diff` で同じと確認（違うのは空の `experiments` と `pictures` のフォルダーだけ）。`bench-new-session` は variant なしと `c` を拒否し、`a, b` と名指しする。`b` では開始し、開始エントリーは `"b"`。新しい記録（封印なし）の `bench-scan` は検出なし。
  - 未了（ユーザーの指示で本番のセッションの後）: 体 `b` の封印された記録と `bench-verify`、ノートのビルド。
  - _要件: 7.3, 7.4, 7.7, 7.9_
