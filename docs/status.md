# 現在の状況

Kiro Web とローカルの Kiro の引き継ぎ用です。セッションの最初に読み、最後に更新します（`.kiro/steering/handoff.md`）。
経緯は git と各 spec の tasks・Decisions にあります。

最終更新: 2026-11-13（ローカル）

## 終わったこと

- `lab-bench`（ベンチのコアとフロントエンド）: タスク 1〜21 完了。
- `dr-kiro`（Dr. Kiro のエージェント、ステアリング、テンプレート、ラボを作るコマンド）: タスク 1〜5 完了。
- `body-lab`: タスク 1〜5 完了。最初のセッション `sessions/body-lab/body-1` は 40 試行で `ended` として封印され、
  ブラインドスキャンも検出なし。
- body-1 で、Dr. Kiro が最後に埋めた `## Discovered spec` の表が封印された記録に入っていないと分かった
  （スナップショットは実行と判定のときだけで、表は最後の判定の後に埋まるため）。`lab-bench` の spec を直した:
  受け付けられた `end()` は検査した 3 ファイルを `"for": "end"` のスナップショットとして封印の前に記録する。
  stop のときは取らない（ユーザーの決定）。body-1 は表なしのまま残す。ノートでの見せ方は `lab-notebook` で決める。

## 次の一手

1. Kiro（ローカル）: `lab-bench` タスク 22（`end` での最後のスナップショット）を実装する。風洞のセッションの前に必要。

2. その後、brief 5 の順番で `wind-tunnel`（brief 4.3）。あなた: `docs/requests/wind-tunnel.md` を `TEMPLATE.md` から作って埋める（任意）。
3. Kiro: 要件の前に質問をまとめる。brief 4.3 に `[DECIDE]` はないが、決めることは多い
   （Docker の使い方、メッシュの作り方、試行の長さ、画像の形式、circle check の手順）。
4. Kiro: 要件・設計・タスクを書く → 実装 → circle check（Strouhal 数が文献値の 5% 以内）→ 24 試行のセッション。

## 未解決の質問

- なし。

## 環境ごとの注意

- **Kiro Web**: hook は動かない。テストと ruff は `sh bench/scripts/check.sh`、訳の確認は `sh scripts/ja-check.sh` を手で実行する。
  Python 3.12 は `UV_PYTHON=/root/.pyenv/versions/3.12.13/bin/python3.12 UV_PYTHON_DOWNLOADS=never` で指定する。
  MuJoCo の描画テスト 2 件はスキップされる（OpenGL なし）。Docker は使えない。
- **ローカル（Mac）**: hook が動く（タスク完了でテストと ruff、英語 spec の保存で訳の更新を促す）。
  コマンドは `uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --reinstall` で入れる。
  body-1 の埋まった表の控えは `bench-run/body-1/design-final.md`（git 管理外、この Mac だけ。参照用でノートには使わない）。
  Dr. Kiro はラボのフォルダーで `kiro-cli chat --agent dr-kiro` から起動し、`export` は同じターミナルで行う。
- **共通**: セッション記録（`sessions/`）は作った環境ですぐコミットする。
