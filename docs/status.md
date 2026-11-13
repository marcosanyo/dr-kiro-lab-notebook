# 現在の状況

Kiro Web とローカルの Kiro の引き継ぎ用です。セッションの最初に読み、最後に更新します（`.kiro/steering/handoff.md`）。
経緯は git と各 spec の tasks・Decisions にあります。

最終更新: 2026-11-13（ローカル）。`wind-tunnel` の要件・設計・タスクを更新し、`lab-bench` に要件 18（ノブの説明）とタスク 23-26 を追加した。

## 終わったこと

- `lab-bench`（ベンチのコアとフロントエンド）: タスク 1〜22 完了（22 は `end` での最後のスナップショット）。
- `dr-kiro`（Dr. Kiro のエージェント、ステアリング、テンプレート、ラボを作るコマンド）: タスク 1〜5 完了。
- `wind-tunnel`: 要件・設計・タスクが書けた（実装は未着手）。
- `body-lab`: タスク 1〜5 完了。最初のセッション `sessions/body-lab/body-1` は 40 試行で `ended` として封印され、
  ブラインドスキャンも検出なし。
- body-1 で、Dr. Kiro が最後に埋めた `## Discovered spec` の表が封印された記録に入っていないと分かった
  （スナップショットは実行と判定のときだけで、表は最後の判定の後に埋まるため）。`lab-bench` の spec を直した:
  受け付けられた `end()` は検査した 3 ファイルを `"for": "end"` のスナップショットとして封印の前に記録する。
  stop のときは取らない（ユーザーの決定）。body-1 は表なしのまま残す。ノートでの見せ方は `lab-notebook` で決める。

## 次の一手

1. **あなた（Run All Tasks の前に）:** GIF チェックを行い、結果を `spikes/gif/results.md` に書いてコミットする（`bench-run/fake/lab` で fake-tester エージェントを起動して `pictures/check.gif` を開かせる）。`wind-tunnel` のタスク 7.1 がこのファイルを読み、なければ止まる。
2. Kiro: `lab-bench` のタスク 23-26（ノブの `description` 項目。body-lab の golden ファイルが先）を実行する。`wind-tunnel` のタスク 1.1 がその完了を確認する。
3. Kiro: `wind-tunnel/tasks.md` を Run All Tasks で実行する。タスク 1.1〜13.2 と 15.1 は Kiro Web でも動く。タスク 14.1〜14.4 は Docker が要るので Mac のみ。
4. あなた（最後にまとめて）: タスク 17〜19（24 回のセッション、封印の確認とコミット、接続時間の自己申告）。
- 途中で止まる可能性がある所（結果次第）: stop list の提案（タスク 12.4）、端のコーナー／端に近い 32 回の実行の報告（14.4）、円柱チェックの失敗（14.2）。

## 環境ごとの注意

- **Kiro Web**: hook は動かない。テストと ruff は `sh bench/scripts/check.sh`、訳の確認は `sh scripts/ja-check.sh` を手で実行する。
  Python 3.12 は `UV_PYTHON=/root/.pyenv/versions/3.12.13/bin/python3.12 UV_PYTHON_DOWNLOADS=never` で指定する。
  MuJoCo の描画テスト 2 件はスキップされる（OpenGL なし）。Docker は使えない。
- **ローカル（Mac）**: hook が動く（タスク完了でテストと ruff、英語 spec の保存で訳の更新を促す）。
  コマンドは `uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --reinstall` で入れる。
  body-1 の埋まった表の控えは `bench-run/body-1/design-final.md`（git 管理外、この Mac だけ。参照用でノートには使わない）。
  Dr. Kiro はラボのフォルダーで `kiro-cli chat --agent dr-kiro` から起動し、`export` は同じターミナルで行う。
- **共通**: セッション記録（`sessions/`）は作った環境ですぐコミットする。
