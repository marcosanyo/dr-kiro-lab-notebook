# 現在の状況

Kiro Web とローカルの Kiro の引き継ぎ用です。セッションの最初に読み、最後に更新します（`.kiro/steering/handoff.md`）。
経緯は git と各 spec の tasks・Decisions にあります。

最終更新: 2026-11-17（ローカル、最終リハーサル後）。`wind-tunnel` のタスク 16 まで完了。次はタスク 17（ユーザーの実セッション）。
## 終わったこと
- `lab-bench`（ベンチのコアとフロントエンド）: タスク 1〜22 完了（22 は `end` での最後のスナップショット）。
- `dr-kiro`（Dr. Kiro のエージェント、ステアリング、テンプレート、ラボを作るコマンド）: タスク 1〜5 完了。
- `wind-tunnel`: タスク 1〜16 完了（`model/`、`adapter/`、`lab/`、Docker での測定、チェックポイント）。
  最後のコード変更の後、本物の Docker で最終リハーサル（`wind-tunnel/rehearse_session.py`、約 4 分）が通った。
  同じリハーサルは、古いコードでは間を置いた後の呼び出しで失敗する。
- `body-lab`: タスク 1〜5 完了。最初のセッション `sessions/body-lab/body-1` は 40 試行で `ended` として封印され、
  ブラインドスキャンも検出なし。
- body-1 で、Dr. Kiro が最後に埋めた `## Discovered spec` の表が封印された記録に入っていないと分かった。`lab-bench` の spec を直した:
  受け付けられた `end()` は検査した 3 ファイルを `"for": "end"` のスナップショットとして封印の前に記録する。
  stop のときは取らない（ユーザーの決定）。body-1 は表なしのまま残す。ノートでの見せ方は `lab-notebook` で決める。
- `docs/ja` の訳は `sh scripts/ja-check.sh` が通る状態（`wind-tunnel` の Decision 43、設計の Decision 30 を含む）。
## タスク 17 の状況（ユーザーの作業）
- 最初の実試行は 2 回とも失敗し、原因を直した:
  - `wt-001`: 最初の `run_experiment` で失敗。Gmsh がワーカースレッドで動いた（シグナル）。封印のスキャンが `application` と `image` を指摘した。どちらも直した（Decision 41、42）。
  - `wt-002`: E1 を 3 試行で実行。その後、前の呼び出しの約 20 秒後の呼び出しで、`gmsh::initialize` の SIGSEGV により `bench-mcp` が落ちた。
    メッシュを子プロセスで作るようにして直した（Decision 43、設計の Decision 30）。スレッドの行列は `spikes/timing/gmsh-threads.md`。
  - どちらのセッションも封印もコミットもしていない。状態のフォルダーは `bench-run/wind-tunnel/state`（git 管理外）に残り、id は再利用できない。
  - 残ったケースフォルダー `bench-run/wind-tunnel/9fe3f7e964ddc328` は `wt-002` の試行 4 のもの。
  - `wt-003`: 最初の操作（H1 の登録）で終わった。予測 P2 の `range = [1, 1]` は通常の拒否になるはずだったが、拒否の文に
    `empty`（OpenFOAM の patch 型でもある語）が入っていて、`Session._finish` のスキャンで bench failure になった（Decision 44）。
    `empty` ほか 4 語を stop list に入れ、ベンチ自身の文を全部スキャンするテスト（掃引）を足した。
  - `wt-002` と `wt-003` は `stopped` として封印済み（`sessions/wind-tunnel/`、コミットしていない）。id は再利用できない。
- `wt-003` の後の修正（最後のコード変更）: `range` の下限が上限以上のときの拒否文を、Dr. Kiro が直せる文に変えた
  （下限は上限より厳密に小さくする、1 つの値は範囲として受け付けない、値がちょうど 1 つの数なら `[0.5, 1.5]`（値 1 の場合）のような小さな範囲を書く）。
  `bench/src/bench/specfiles/hypotheses.py`、テストは `bench/tests/unit/test_hypotheses.py` と、本物の Session を通す
  `wind-tunnel/adapter/tests/test_register_refusal.py`（通常の拒否で、ベンチ障害ではない）。コミット `fc85e5e`。
  この変更の後、本物の Docker で最終リハーサルが通り、封印、`bench-verify`、`bench-scan` も問題なし。`docs/ja` の訳も最新（`ja-check` 通過）。
- `wind-tunnel/lab` には `wt-003` の残りがある（`bench-new-session` が初期化する）。
- 次のセッションは `wt-004`、シード `20261118`。コマンドは `wind-tunnel/README.md` の「Running a session」。
  前のセッションがクラッシュして封印されていない場合は、`bench-new-session` の前に
  `bench-stop <設定ファイル> --reason <理由>` で閉じる（理由はビルダーの文としてスキャンされる。ソルバーやメッシュの語を入れない）。
- 掃引: ベンチ自身の文字列（`bench/tests/message_sweep.py` の固定ルール、1006 個）を、両アプリの導出語と本物の stop list でスキャンする。
  `wind-tunnel/adapter/tests/test_message_sweep.py` と `body-lab/adapter/tests/test_message_sweep.py`。
- 未決: Dr. Kiro レベルの文に単独の `P` や `U` があると、ファイル名パターン（`0/p.in`、`0/U.in`）に当たる。スキャン規則の変更になるので、あなたの判断を待つ（Decision 44）。
- タスク 17 の後、ビルダーがタスク 18、次にタスク 19（ユーザー）、20、21 を行う。
## ユーザーが片づけるもの
- git の worktree `/private/tmp/wt-old`、`wt-old2`、`wt-old3`: `git worktree list` で確認し、それぞれ `git worktree remove --force <path>`、最後に `git worktree prune`。
- `spikes/sheet/check-sheet.png`: 追跡されていない。私たちがコミットするものではない。
- 古い Kiro CLI のプロセス（5 個、残っていれば）。
## 次の一手
1. **あなた:** タスク 17（`wt-003` で 24 回のセッション）。その後、封印の確認とコミット。
2. Kiro: タスク 18。あなた: タスク 19（接続時間の自己申告）。その後タスク 20、21。
3. Kiro: `lab-bench` のタスク 23-26 が終わっているか、`wind-tunnel` のタスク 1.1 が確認する（以前からの項目）。
4. **`lab-notebook` の spec の項目（まだ書いていない）:** ノートブックの動く画像。`body-lab` と `wind-tunnel` は同じ画像シートの形なので、シートのフレームを順に見せる方法を両方のラボについて 1 回、その spec で決める（`wind-tunnel` 要件の Decision 25）。
## 未決の質問（あなたへ）
1. **クラッシュ後に残ったケースフォルダーの扱い。** 再開したセッションは同名のフォルダーとぶつかり、`FileExistsError` で失敗する（失敗を隠さない設計）。
   ユーザーが `mv` で脇へ移す。自動では扱わない。
2. **試行の失敗はセッションを終える**（タイムアウト、不完全、メッシュ）。収束しない試行は結果として扱う（Decision 37）ので終わらない。
3. 予算 24 は `docs/brief.md` の値。
4. `docs/brief.md` は `angle` を [0, 30] とし、spec は [0, 15]（ユーザーの決定、Decision 34）。
5. 接続時間（タスク 19）はユーザーの自己申告である。
6. 同じ実行の時間にはばらつきがある（12〜35 秒、最も遅い実行は 100.6 秒、上限は 140 秒）。
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
