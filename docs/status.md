# 現在の状況

Kiro Web とローカルの Kiro の引き継ぎ用です。セッションの最初に読み、最後に更新します（`.kiro/steering/handoff.md`）。
経緯は git と各 spec の tasks・Decisions にあります。

最終更新: 2026-11-13（ローカル）。GIF 読み取りチェックが失敗したため、`wind-tunnel` の画像を PNG の画像シート 1 枚に変えた（要件・設計・タスクと訳を更新、ブランチ `spec/wind-tunnel`）。`lab-bench` は変えていない。

## brief の改訂（ブランチ `docs/brief-final-edit`）

- `docs/brief.md` を今の方針に合わせた: 題は Dr. Kiro's Lab Notebook、決め台詞は The experiment gets the final edit.。ノートは発見した spec の表が中心
  （ベンチの状態の語 4 つを文字で出す）。新しい spec `build-from-spec`（4.5）を足し、publish は 4.6 になった。`angle` [0, 15]°、画像は PNG の画像シート、
  MCP は決定済み、レイアウトは今のフォルダーに合わせた。`.kiro/steering/product.md` も合わせた。
- **次の一手:** `lab-notebook` の要件を作る（brief 4.4。残る DECIDE は、走らせた条件の区切り方と body-lab での見せ方）。その後に `build-from-spec` の要件を作る（4.5）。
- **残っている件:** Dr. Kiro の雛形（`bench/src/bench/drkiro/files/workflow.md` と各ラボの `lab/.kiro/steering/workflow.md`）に
  「否定された規則は表から消さず、`rejected` の行として残す」の 1 文を足す。`partly` と `rejected` のどちらに書くかは Dr. Kiro に任せたまま。
  `impl/wind-tunnel` が main に入ってから別に直す。次のセッションから条件が変わることを、その時 `dr-kiro` の spec の Decisions に残す。
  封印済みの body-1 と wt-004 は書き換えない。
- リプレイで取り消し線が出るのが、途中のスナップショットに表がある時だけかどうかは、`lab-notebook` の spec で確かめる。

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

1. **あなた:** `wind-tunnel` の設計の承認時に、シートの配置の提案（要件 9.4、Decisions 24）を確認する: 6 フレーム、2 行 3 列、セル 400 x 200、フレームは t = 145〜150（間隔 1.0）、セルの間に 4 ピクセルの隙間（シートは 1208 x 404。隙間なしなら 1200 x 400）。隙間は私（ビルダー）の追加提案で、不要なら設定を 0 にする。
   GIF チェックはもうユーザーの手順ではない。シート読み取りチェックはビルダーが実行する（タスク 7.1 が `spikes/sheet/` の合成シートで、タスク 14.5 が本物のシートで）。7.1 は Kiro CLI が要るのでローカルの Mac で動かす。結果は `spikes/sheet/results.md` に入り、タスク 7.2 がゲートとして読む。
2. Kiro: `lab-bench` のタスク 23-26（ノブの `description` 項目。body-lab の golden ファイルが先）を実行する。`wind-tunnel` のタスク 1.1 がその完了を確認する。
3. Kiro: `wind-tunnel/tasks.md` を Run All Tasks で実行する。タスク 1.1〜13.2 と 15.1 は Kiro Web でも動く（7.1 は Kiro CLI が要るのでローカルのみ）。タスク 14.1〜14.5 は Docker が要るので Mac のみ。
4. **`lab-notebook` の spec の項目（まだ書いていない）:** ノートブックの動く画像。`body-lab` と `wind-tunnel` は同じ画像シートの形なので、シートのフレームを順に見せる方法を両方のラボについて 1 回、その spec で決める（`wind-tunnel` 要件の Decision 25）。
5. あなた（最後にまとめて）: タスク 17〜19（24 回のセッション、封印の確認とコミット、接続時間の自己申告）。
- 途中で止まる可能性がある所（結果次第）: 合成シートの読み取り失敗（7.1）、本物のシートをエージェントが説明できない（14.5）、stop list の提案（タスク 12.4）、端のコーナー／端に近い 32 回の実行の報告（14.4）、円柱チェックの失敗（14.2）。

## 環境ごとの注意

- **Kiro Web**: hook は動かない。テストと ruff は `sh bench/scripts/check.sh`、訳の確認は `sh scripts/ja-check.sh` を手で実行する。
  Python 3.12 は `UV_PYTHON=/root/.pyenv/versions/3.12.13/bin/python3.12 UV_PYTHON_DOWNLOADS=never` で指定する。
  MuJoCo の描画テスト 2 件はスキップされる（OpenGL なし）。Docker は使えない。
- **ローカル（Mac）**: hook が動く（タスク完了でテストと ruff、英語 spec の保存で訳の更新を促す）。
  コマンドは `uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --reinstall` で入れる。
  body-1 の埋まった表の控えは `bench-run/body-1/design-final.md`（git 管理外、この Mac だけ。参照用でノートには使わない）。
  Dr. Kiro はラボのフォルダーで `kiro-cli chat --agent dr-kiro` から起動し、`export` は同じターミナルで行う。
- **共通**: セッション記録（`sessions/`）は作った環境ですぐコミットする。
