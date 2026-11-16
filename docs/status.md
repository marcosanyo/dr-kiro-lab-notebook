# 現在の状況

Kiro Web とローカルの Kiro の引き継ぎ用です。セッションの最初に読み、最後に更新します（`.kiro/steering/handoff.md`）。
経緯は git と各 spec の tasks・Decisions にあります。

最終更新: ローカル、タスク 21（最後のチェックポイント）と、2026-11-16 のユーザーの 2 つの決定（Decision 45、46）の後。`wind-tunnel` のタスク 1〜21 完了。

## brief の改訂（ブランチ `docs/brief-final-edit`）
- `docs/brief.md` を今の方針に合わせた: 題は Dr. Kiro's Lab Notebook、決め台詞は The experiment gets the final edit.。ノートは発見した spec の表が中心
  （ベンチの状態の語 4 つを文字で出す）。新しい spec `build-from-spec`（4.5）を足し、publish は 4.6 になった。`angle` [0, 15]°、画像は PNG の画像シート、
  MCP は決定済み、レイアウトは今のフォルダーに合わせた。`.kiro/steering/product.md` も合わせた。
- **次の一手:** `lab-notebook` の要件を作る（brief 4.4。残る DECIDE は、走らせた条件の区切り方と body-lab での見せ方）。その後に `build-from-spec` の要件を作る（4.5）。
- **済み:** Dr. Kiro の雛形（`bench/src/bench/drkiro/files/workflow.md` と各ラボの `lab/.kiro/steering/workflow.md`）に
  「否定された規則は表から消さず、`rejected` の行として残す」の 1 文を足した。`partly` と `rejected` のどちらに書くかは Dr. Kiro に任せたまま。
  これから始めるセッションは、この 1 文がある条件で始まる。`dr-kiro` の spec（要件 3.7、設計 5.2、Decision 8）に記録した。
  封印済みの body-1 と wt-004 はこの文なしで作られており、書き換えない。
- リプレイで取り消し線が出るのが、途中のスナップショットに表がある時だけかどうかは、`lab-notebook` の spec で確かめる。

## 終わったこと
- `lab-bench`（ベンチのコアとフロントエンド）: タスク 1〜22 完了（22 は `end` での最後のスナップショット）。
- `dr-kiro`（Dr. Kiro のエージェント、ステアリング、テンプレート、ラボを作るコマンド）: タスク 1〜5 完了。
- `wind-tunnel`: タスク 1〜21 完了（`model/`、`adapter/`、`lab/`、Docker での測定、チェックポイント、実セッション `wt-004`、結果の記録）。
  最後のコード変更の後、本物の Docker で最終リハーサル（`wind-tunnel/rehearse_session.py`、約 4 分）が通った。
  同じリハーサルは、古いコードでは間を置いた後の呼び出しで失敗する。
- `body-lab`: タスク 1〜5 完了。最初のセッション `sessions/body-lab/body-1` は 40 試行で `ended` として封印され、
  ブラインドスキャンも検出なし。
- body-1 で、Dr. Kiro が最後に埋めた `## Discovered spec` の表が封印された記録に入っていないと分かった。`lab-bench` の spec を直した:
  受け付けられた `end()` は検査した 3 ファイルを `"for": "end"` のスナップショットとして封印の前に記録する。
  stop のときは取らない（ユーザーの決定）。body-1 は表なしのまま残す。ノートでの見せ方は `lab-notebook` で決める。
- `docs/ja` の訳は `sh scripts/ja-check.sh` が通る状態（`wind-tunnel` の Decision 43、設計の Decision 30 を含む）。
## タスク 17〜20 の状況
- **セッション `wt-004`**（シード 20261118、コミット `cbe5d54`）: `ended` で封印。Dr. Kiro 自身の `end_session` で終わった。
  24 試行のうち 18 を使用（予算の残り 6）。予算を使い切ったのではない（24 回は行っていない）。合格条件（要件 17.3）は
  「予算を使い切る、または Dr. Kiro 自身の `end_session`」で、後者で満たした。
  実験 6（E1〜E6）、仮説 6、記録 69 エントリ、blob 41。`bench-verify` は verified、`bench-scan`（`wind-tunnel/lab` と封印済みフォルダー）は検出なし。
  予測結果 17 件、的中 16、外れ 1（E5）。5 つの測定がすべて `not_settled` だった試行が 1 件（E4、aspect 3 / corner 1 / splitter 1 / angle 0）。
  拒否 1 件（1 つの値の範囲）。
- 停止した前の試行: `wt-001`（封印できず。git 管理外の `bench-run/wind-tunnel/state` にだけある）、`wt-002`（`e1c7565`、3 試行、`bench-mcp` の落下）、
  `wt-003`（`7c0ab08`、最初の操作で導出語が拒否文に入った）。修正は、メッシュを子プロセスで作ること、除外リストの語の追加、掃引テスト。
- **接続時間（タスク 19）**: 約 57 時間 30 分、ユーザーの自己申告（「57 時間 30 分程度」）。開始 2026-11-13 23:24:59 +0900（要件の承認を記録したコミット `2a8c62a` の時刻。
  実際の承認は数分前で、正確な記録はない）、終了 2026-11-16 08:55:00 +0900（`wt-004` の作成）。「最初の完全なセッション」は `wt-004` と読む。
  実時間で、睡眠や他の作業を含み、作業時間の合計ではない。ビルダーは計算も修正もしていない。
- タスク 20: `wind-tunnel/numbers.md` と `wind-tunnel/README.md` を更新した。コード行数は `count_lines.py` で数え直した:
  `adapter/` 1037、`model/` 1277、合計 2314（テストファイルを除く）、テストファイルは `adapter/` 2013、`model/` 1227。
  `design.md` の古い 1 行（`FailureKind` は `incomplete` と `timeout` の 2 種類）を直した。`docs/ja` も更新済み（`ja-check` 通過）。
- 掃引: ベンチ自身の文字列（`bench/tests/message_sweep.py` の固定ルール、1006 個）を、両アプリの導出語と本物の stop list でスキャンする。
  `wind-tunnel/adapter/tests/test_message_sweep.py` と `body-lab/adapter/tests/test_message_sweep.py`。
- 新しいセッションの手順は `wind-tunnel/README.md` の「Running a session」。前のセッションが封印されていない場合は、
  `bench-new-session` の前に `bench-stop <設定ファイル> --reason <理由>` で閉じる（理由はスキャンされる。ソルバーやメッシュの語を入れない）。
## ユーザーが片づけるもの
- git の worktree `/private/tmp/wt-old`、`wt-old2`、`wt-old3`: `git worktree list` で確認し、それぞれ `git worktree remove --force <path>`、最後に `git worktree prune`。
- `.worktrees/`: 追跡されていないフォルダー（コミットしていない）。不要なら片づける。
- 一時フォルダー: `bench-run/wind-tunnel/` の中の古いケースフォルダー（`9fe3f7e964ddc328` ほか）や、`/private/tmp` の一時ファイル。`bench-run/` は git 管理外。
- `spikes/sheet/check-sheet.png`: 追跡されていない。私たちがコミットするものではない。
- 古い Kiro CLI のプロセス（5 個、残っていれば）。
## 次の一手
1. （済）タスク 21 と Decision 45、46。最終リハーサル（本物の Docker、封印まで）は `splitter` 1e-9 の拒否と 1e-6 の実行を含めて通った。
2. Kiro: `lab-bench` のタスク 23-26 が終わっているか、`wind-tunnel` のタスク 1.1 が確認する（以前からの項目）。
3. **`lab-notebook` の spec の項目（まだ書いていない）:** ノートブックの動く画像。`body-lab` と `wind-tunnel` は同じ画像シートの形なので、シートのフレームを順に見せる方法を両方のラボについて 1 回、その spec で決める（`wind-tunnel` 要件の Decision 25）。
## 残っているリスク
- **解消済み: 単独の `P` や `U`。** 2026-11-16 のあなたの決定で、1 文字のステムとストップリストにあるステムはファイル名として検出しない（`lab-bench` 要件 20、設計の Decision 7）。フルのファイル名（`p.in`、`U.in`）は常に検出する。
- **解消済み: `geometry`、`mesh`、`constants`、`monitors` のステム**（あなたが選択を任せた。`wind-tunnel` 要件の Decision 46）。`geometry`、`constants`、`monitors` を除外リストに入れた（普通の語で、外れる導出語はファイル名のステムだけ）。`mesh` は入れない（`[mesh]` セクションなどソルバー設定の名前でもあり、メッシュは Dr. Kiro が知ってはならない）。完全なファイル名は常に検出する。
- **新しい規則（Decision 45）:** 0 より大きく 1e-6 より小さい `splitter` は、実行の前に拒否する（予算は使わない）。約 2.5e-8 より小さいとメッシュを作れず、セッションが終わるため。下限 1e-6 は収束まで走らせた値（cd 1.27591、45.0 s）。32 回の実行の両端のケースと `extreme-runs.json` は変わらない。
- 再現性は同じ Mac と同じイメージのビルドに限る。セッション全体（Dr. Kiro の実験の選び方）は再現しない。
- 収束しない試行（`wt-004` の E4 など）は結果として扱う。時間のばらつきがあり、115 秒は範囲選びの規則で、1 回の実行の保証ではない。
- 接続時間は自己申告で、開始時刻はコミット時刻に合わせた値。
## 未決の質問（あなたへ）
1. **クラッシュ後に残ったケースフォルダーの扱い。** 再開したセッションは同名のフォルダーとぶつかり、`FileExistsError` で失敗する（失敗を隠さない設計）。
   ユーザーが `mv` で脇へ移す。自動では扱わない。
2. **試行の失敗はセッションを終える**（タイムアウト、不完全、メッシュ）。収束しない試行は結果として扱う（Decision 37）ので終わらない。
3. 予算 24 は `docs/brief.md` の値。
4. `docs/brief.md` は `angle` を [0, 30] とし、spec は [0, 15]（ユーザーの決定、Decision 34）。
5. 接続時間（タスク 19）はユーザーの自己申告である（記録済み）。
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
- 停止した wind-tunnel セッション `wt-002` と `wt-003` は、失敗した試行の記録としてコミット済み。`wt-001` は封印できず、git 管理外の `bench-run/` の状態フォルダーにだけある。`wt-004` は `ended` でコミット済み（`cbe5d54`）。
