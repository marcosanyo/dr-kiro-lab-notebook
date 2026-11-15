# 現在の状況

Kiro Web とローカルの Kiro の引き継ぎ用です。セッションの最初に読み、最後に更新します（`.kiro/steering/handoff.md`）。
経緯は git と各 spec の tasks・Decisions にあります。

最終更新: 2026-11-15（ローカル）。`wind-tunnel` のタスク 16（チェックポイント）を実行した。タスク 1〜15 の実装は終わっている。

## 終わったこと

- `lab-bench`（ベンチのコアとフロントエンド）: タスク 1〜22 完了（22 は `end` での最後のスナップショット）。
- `dr-kiro`（Dr. Kiro のエージェント、ステアリング、テンプレート、ラボを作るコマンド）: タスク 1〜5 完了。
- `wind-tunnel`: タスク 1〜15 の実装が終わった（`model/`、`adapter/`、`lab/`、Docker での測定）。タスク 16 のチェックポイントの結果:
  `model/` 144 件、`adapter/` 133 件（スキップ 1、slow 3 件は対象外）、`bench/` 500 件が通り、3 か所とも ruff の check と format は指摘なし。
  `bench-scan` は `wind-tunnel/lab` と、`wind-tunnel-told-set --out` で一時ファイル（リポジトリの外、確認後に削除）へ書いた told 文の両方で指摘なし。
  `form-knowledge-review.md` は埋まっている。`circle-check.json`、`extreme-runs.json`、`spikes/sheet/results.md`（合成シートと本物のシートの両方）がある。
  `scripts/ja-check.sh` は 6 件が古いと報告した（下の「訳」）。
- `body-lab`: タスク 1〜5 完了。最初のセッション `sessions/body-lab/body-1` は 40 試行で `ended` として封印され、
  ブラインドスキャンも検出なし。
- body-1 で、Dr. Kiro が最後に埋めた `## Discovered spec` の表が封印された記録に入っていないと分かった
  （スナップショットは実行と判定のときだけで、表は最後の判定の後に埋まるため）。`lab-bench` の spec を直した:
  受け付けられた `end()` は検査した 3 ファイルを `"for": "end"` のスナップショットとして封印の前に記録する。
  stop のときは取らない（ユーザーの決定）。body-1 は表なしのまま残す。ノートでの見せ方は `lab-notebook` で決める。

## 次の一手

1. Kiro（オーケストレーター）: `docs/ja` の訳を更新する（下の「訳」）。その後 `sh scripts/ja-check.sh` を通す。
2. **あなた:** 下の「未決の質問」に答える。特に (1) は、24 回のセッションの前に決めるのがよい。
3. **あなた（最後にまとめて）:** タスク 17〜19（24 回のセッション、封印の確認とコミット、接続時間の自己申告）。手順は `wind-tunnel/README.md`。
4. Kiro: `lab-bench` のタスク 23-26 が終わっているか、`wind-tunnel` のタスク 1.1 が確認する（以前からの項目）。
5. **`lab-notebook` の spec の項目（まだ書いていない）:** ノートブックの動く画像。`body-lab` と `wind-tunnel` は同じ画像シートの形なので、シートのフレームを順に見せる方法を両方のラボについて 1 回、その spec で決める（`wind-tunnel` 要件の Decision 25）。

## 未決の質問（あなたへ）

1. **試行の失敗とセッションの終了。** 試行が 1 回でも失敗するとセッションが終わる。範囲内のランダムな 30 点のうち 2 点が収束しなかった
   （`cl_amp` の規則、`aspect` が約 2.5、`angle` が約 1 度。`spikes/timing/random-points.md`）。割合は 6.7%、95% 区間は 1.8〜21.3%。
   24 回のセッションで 1 回以上失敗する確率は約 81% と見積もっている。選択肢:
   (a) その領域を測って `check_inputs` に規則を足す。
   (b) 「収束しなかった」を、呼び出しだけを終える実行後の拒否にする（予算は使わない）。`lab-bench` の変更になる。
   (c) そのまま受け入れる。
2. **環境の一時的な失敗。** 5 回の実行が 0.5 秒以内に終了コード 127 で終わり、その後は普通に動いた。再現していない。
   同名のケースフォルダーが残っていると `create_case_folder` が `FileExistsError` で失敗する。セッション中のシードとフォルダー名の対応、
   残ったフォルダーがセッションを止めるかどうかは、下の「調べたこと」にまとめた。
3. **同じ実行のばらつき。** 同一入力の実行時間は 12〜35 秒の幅がある。測った中で最も遅い実行は 100.6 秒で、上限は 140 秒。
4. **コーナー 0.99 は受け付ける**（56.5 秒で収束）。拒否は、`aspect` により 0.04 または 0.08 より下、0.997 または 0.995 より上。
5. `permissions.yaml` の `rm -rf` の拒否規則が 2 回当たり、サブエージェントが止まった。意図どおりで問題はない。
6. `docs/ja` の訳は最後に更新する。

## 調べたこと（質問 2、コードは変えていない）

- シードの出所: セッションの設定のシードと試行番号から、`bench/src/bench/core/ids.py:67-74`（`trial_seed`、SHA-256 の先頭 8 バイト）で決める。
  呼び出しは `bench/src/bench/core/session.py:574`。試行番号はセッション内で通し番号（`session.py:567`）。
- アダプターは `adapter.py:116` で `create_case_folder(self._case_base, seed)` を呼ぶ。名前は 16 桁の 16 進数のシード（`runner.py:67-71`）。
  置き場は `bench-run/wind-tunnel/`（`adapter.py:59`、`environment.py:28`）。
- 同じセッション内では試行番号が重ならないので、名前は重ならない（ハッシュの衝突を除く）。
- 別のセッションでも、セッションのシードが同じなら同じ試行番号は同じ名前になる。同じ Mac の同じ置き場を使う。
  成功した試行のフォルダーは `trash/` に移り、次の試行の頭で消える（`adapter.py:105`、`:154`、`runner.py:98`）。
  失敗した試行のフォルダーは削り込んで残る（`adapter.py:188`）。最後の成功した試行の `trash/` も、次の `run_trial` まで残る。
- 同名のフォルダーがあると `path.mkdir(exist_ok=False)`（`runner.py:79`）が `FileExistsError` を出す。
  `adapter.py:116` は `try` の外で、アダプターは捕まえない。`session.py:585` の `except Exception` が捕まえ、
  `ADAPTER_RAISED`（`session.py:72`、「the trial stopped with an error in the application」）の bench failure になる。セッションは止まる。
  `TrialFailure` ではなく、予算は使わない拒否でもない。
- 今の `bench-run/wind-tunnel/` には、以前の測定の `0000000000000000`、`0000000000000001`、`0000000000000386` のフォルダーがある。
  実セッションのシードは SHA-256 から来るので、これらと重なる可能性は事実上ない。重なりうるのは、同じセッションのシードを使い直したときだけ。
- 確かめていないこと: 5 回の終了コード 127 とこの仕組みの関係。127 の実行は、フォルダーを移した後に起きた（`random-points.md`）。

## 訳

`sh scripts/ja-check.sh` が古いと報告したファイル（6 件）: `docs/ja/lab-bench/requirements.md`、`docs/ja/lab-bench/design.md`、
`docs/ja/lab-bench/tasks.md`、`docs/ja/wind-tunnel/requirements.md`、`docs/ja/wind-tunnel/design.md`、`docs/ja/wind-tunnel/tasks.md`。
このタスクでは訳していない。オーケストレーターが別の手順で更新する。

## 環境ごとの注意

- **Kiro Web**: hook は動かない。テストと ruff は `sh bench/scripts/check.sh`、訳の確認は `sh scripts/ja-check.sh` を手で実行する。
  Python 3.12 は `UV_PYTHON=/root/.pyenv/versions/3.12.13/bin/python3.12 UV_PYTHON_DOWNLOADS=never` で指定する。
  MuJoCo の描画テスト 2 件はスキップされる（OpenGL なし）。Docker は使えない。
- **ローカル（Mac）**: `bench-scan` は入れ済みのツールの環境に `wind_tunnel` がないと動かない（今は入っていない）。
  このチェックポイントでは `wind-tunnel/adapter` で `uv run bench-scan ...` を使った。told 文の一時ファイルのスキャンには、
  同じ場所に `<file>.authors.json`（全体を `bench` の作者にした範囲）が要る。ツールを入れ直す場合は README の `uv tool install` を使う。
  hook が動く（タスク完了でテストと ruff、英語 spec の保存で訳の更新を促す）。
  コマンドは `uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --reinstall` で入れる。
  body-1 の埋まった表の控えは `bench-run/body-1/design-final.md`（git 管理外、この Mac だけ。参照用でノートには使わない）。
  Dr. Kiro はラボのフォルダーで `kiro-cli chat --agent dr-kiro` から起動し、`export` は同じターミナルで行う。
- **共通**: セッション記録（`sessions/`）は作った環境ですぐコミットする。
