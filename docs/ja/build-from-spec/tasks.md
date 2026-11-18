> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/build-from-spec/tasks.md`](../../../.kiro/specs/build-from-spec/tasks.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読まず、タスクの実行や完了チェックは英語版だけで行います。この訳のチェック状態は訳した時点のものです。
> 原文 SHA-256: `eb23d31aae5cfe8796055f14185abeb179a5630fcd5ba11669d0124776036112`
# 実装計画: build-from-spec
## Overview
`build-from-spec` のタスクです。`requirements.md`（要件 1-19）と `design.md` から作りました。このワークツリーではなく、**メインフォルダー** `/Users/rk/dev/llm/hackathon/dr-kiro-lab-notebook` で実行します。実装は、別のチャットのノートブックの作業が main にマージされ、ユーザーが go と言ってからだけ始めます。両方がメインフォルダーを使うためです（決定 18）。この計画のどれも、それまでは始めません。

実行するリクエストは `build-from-spec/requests/stop-ahead.toml` です: 6 回の実行、`spec`、`none`、`record` で `n` = 1 と 2、元セッションは `sessions/body-lab/body-2`。`straight-ahead` と `turn-right` はコミットされたままで、実行しません。body-2 がその合格範囲の内側の試行をすでに含んでいるためです（決定 18）。
順序は次のとおりです。まず `lab-bench` の 2 つの改訂を、そのテストと、`lab-bench` および `dr-kiro` 仕様の対応する文言とともに行います（パート 1、設計 3.14）。次に `build-from-spec/` の uv プロジェクトを、依存の順にモジュールごとに、それぞれのテストとプロパティテストとともに作ります（パート 2）。そのあと、設計の第 9 節の実装時チェック、準備の確認、実行を行います（パート 3）。最後に `lab-notebook` 仕様への引き継ぎと最終チェックポイントです。
どの Kiro か: すべてのタスクは **ビルダー** が行います。リーダーが現れるのはパート 3 だけで、実行スクリプトが起動します。Dr. Kiro は関わりません。
## Notes for the user and for every sub-agent
- **どこで実行するか。** パート 1 と 2 はシミュレーターのディスプレイも Docker も Kiro CLI も必要とせず、Kiro Web でもローカルでも動きます。`build-from-spec/` は `body-lab-adapter` にパスで依存し、それには `mujoco` が必要です。ある環境でインストールまたは import できなければ、**止めて報告します**。依存を外しません。**[local Mac]** と付いたタスクは、モデル付きの Kiro CLI を必要とし、ユーザーの Mac で動かします。
- **プロジェクトのチェック**（"the checks"）。パート 1 では、`sh bench/scripts/check.sh` と body-lab アダプターのテスト（ゴールデンファイルは変更なし）。パート 2 では、`build-from-spec/` で `uv run pytest`、`uv run ruff check`、`uv run ruff format --check` が通ること。すべてのタスクは、そのパートのチェックで終わります。Python 3.12 は `uv` 経由のみ。`build-from-spec/uv.lock` はコミットします。
- **プロパティテスト**は `hypothesis` を 100 例以上で使い、それぞれ `build-from-spec/tests/properties/` の下の独立したファイルに書き、`# Feature: build-from-spec, Property N: <title>` のタグを付けます。それぞれが、テスト対象のコードの後に置く独立したサブタスクです。`lab-bench`、`wind-tunnel`、`lab-notebook` の計画と同じく、この計画にオプションのタスクはありません。
- **フィクスチャ。** テストは、テスト用の `APPS` テーブル（設計 3.1）を通したフェイクのアプリケーション、git のチェック用の一時的な git リポジトリ、本物のフェイクセッションが作った記録を使います。body-lab を使うのは、要件が名指しする箇所（予算、body-2 の許可された id）だけです。フィクスチャの数値は、結果として示されることは決してありません（`rules.md` 4）。
- **変更しないもの**: `body-lab/`、`sessions/body-lab/`、`sessions/wind-tunnel/`、`discovered/`、`docs/brief.md`、ルートの `README.md`、`.kiro/blind-scan/stop-list.txt`、`build-from-spec/requests/` にあるコミット済みのリクエストファイル。`bench/` を変えるのはパート 1 だけです。後のタスクが別のベンチの変更を必要としそうなら、**止めて報告します**。
- **停止条件。** **Stop and ask（止めて確認）** のタスクはユーザーへの日本語の報告で終わり、ユーザーが答えるまで次のタスクは始まりません。停止条件に出会ったサブエージェントは報告し、決めません（`rules.md` 2、6）: 観察されなかった設計第 9 節のチェック、書き換えでは消せないビルダーレベルのテキストのブラインドスキャンの検出、設計の述べるとおりに振る舞わないベンチの関数、拒否またはブロックされたコマンド、そして要件が、ビルダーに止まるよう指示するすべての実行結果（要件 13.5、16.4）。
- **ブラインドのルール。** 部品、関節、アクチュエーター、ソルバーの名前を、リーダーのビルダーのファイル、ベンチの出力、実行情報ファイルに書きません。ビルダーのテキストでのスキャンの検出は、除外リストではなく、言い換えで直します。
- **コミット。** タスクが変えたファイルだけを、1 つずつ名前を指定して、共著者の行なしでコミットします。実行記録は、削除、上書き、同じ実行 ID での再実行を決してしません（要件 13.3）。
## Tasks
### パート 1: lab-bench の改訂（設計 3.14）
- **1. 発見された spec の表なしで終了する** — 完了
  - **1.1 `discovered_table` 設定をコアとセッション設定に加える** — 完了
    - `SessionConfig`（`bench/src/bench/core/session.py`）: 新しいフィールド `discovered_table: str`、デフォルトなし。`Session._check_config` は、`"required"` と `"not-required"` 以外の値を、設定名を挙げて拒否する。開始エントリーは `"discovered_table"` を持ち、`Session.open` はそれを `seed` と同じように設定と比べる。`Session._end`: `check_table` のブロックは、値が `"required"` のときだけ動く。判定ゲート、3 つのファイルの 1 回の読み取り、`"for": "end"` のスナップショット、`ended` としての封印は変わらない。
    - `bench/src/bench/frontend/config.py`: フィールドを読み、文字列であることを確かめる。
    - `bench-new-session`（`bench/src/bench/drkiro/session.py`）は `discovered_table = "required"` を書く。`bench/tests/labkit.py` とベンチのテストのすべての設定は `"required"` を述べ、`bench/README.md` のサンプル `session.toml` にはその行が加わる。
    - ユニットテスト: `"not-required"` のとき、表のない `end` は `ended` として封印され、`final_spec` が読める終了スナップショットを持つ。判定が保留中ならやはり拒否する。値がない、または不明なら、設定名を挙げて開始時に拒否される。開始エントリーはその値を持つ。`"required"` のとき、既存のすべての終了のテストが変更なしで通る。
    - 確認方法: パート 1 のチェック。
    - _要件: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_
  - **1.2 `end_session` の説明を設定によって変える** — 完了
    - `bench/src/bench/frontend/describe.py`: 設計 3.14.1 のとおりの `END_BASE`、`END_TABLE`、`descriptions(decl, discovered_table)`。不明な値は設定名を挙げて例外を出す。`bench/src/bench/frontend/server.py`: `BenchServer` は `descriptions(session.declaration, session.config.discovered_table)` を呼ぶ（唯一の呼び出し元）。
    - テスト（`bench/tests/frontend/test_describe.py`、`test_server.py`）: `"required"` のとき、`end_session` は現在のリテラルとバイト単位で等しい。`"not-required"` のとき、`End the session. Every experiment needs a verdict.` に等しい。他の 3 つのテキストは両方の値で等しい。不明な値は例外を出す。それぞれの値で起動したサーバーは、対応する `end_session` のテキストを挙げる。
    - 確認方法: パート 1 のチェック。body-lab のゴールデンの告げるテキストは変わらない。
    - _要件: 8.3, 12.5, 12.9_
  - **1.3 改訂前に封印された記録が有効なままであることをテストする** — 完了
    - テストは、`sessions/body-lab/body-1`、`sessions/body-lab/body-2`、`sessions/wind-tunnel/wt-004` で `bench-verify` と `final_spec` を走らせる。これらの開始エントリーには `discovered_table` がなく、どちらも通る。
    - マージの前に、`bench.drkiro.session.open_sessions` で、`bench-run/` に開いているセッションがないことを確かめる（設計 3.14.1）。あれば**止めて報告します**。
    - 確認方法: パート 1 のチェック。
    - _要件: 12.8_
- **2. `bench-check-discovered` が実行記録を飛ばす** — 完了
  - **2.1 `check_copies` で `sessions/build-from-spec/` を飛ばす** — 完了
    - `bench/src/bench/record/spec_copy.py`: `RUN_RECORDS = "build-from-spec"`。`_records` はそのフォルダーを飛ばす。`check_copies` は、そのフォルダーがあるとき、レポート行 `build-from-spec: reader run records, no copies` を加える。他は何も変えない。
    - テスト（`bench/tests/unit/test_spec_copy.py`）: リポジトリのセッションを一時フォルダーにコピーし、さらに `sessions/build-from-spec/body-lab/<run-id>/`（終了スナップショット付きで `ended` として封印されたフェイクの記録）とその隣の `<run-id>.run.json` を置く。`check_copies` は問題を報告せず、飛ばした行を挙げる。`discovered/build-from-spec/<run-id>/` を加えると問題として報告される。別のアプリケーションのフォルダーの下にある `log.jsonl` のないフォルダーは、やはり例外を出す。
    - 確認方法: パート 1 のチェック。リポジトリで `bench-check-discovered sessions discovered` が通る。
    - _要件: 13.7_
- **3. `lab-bench` と `dr-kiro` 仕様の文言** — 完了
  - **3.1 改訂を `lab-bench` と `dr-kiro` の仕様に書く** — 完了
    - `.kiro/specs/lab-bench/requirements.md`、`design.md`、`tasks.md`: それぞれに既存の改訂の書き方で改訂のセクションを 1 つずつ、終了の設定とその `end_session` の文（この仕様の要件 12、設計 3.14.1）と、`sessions/build-from-spec/` を飛ばすこと（要件 13.7、設計 3.14.2）について、次の空いている要件番号で書く。改訂の `lab-bench` のタスクは、この計画のタスク 1 と 2 を指し、それらが終わったときにチェックを付ける。
    - `.kiro/specs/dr-kiro/requirements.md` の要件 8.4: 「終了スナップショット付きで `ended` として封印されたすべての Dr. Kiro のセッション記録」とし、`sessions/build-from-spec/` のリーダーの実行記録は対象外と名指しする。`dr-kiro` の設計がそれを述べている箇所でも同じ変更をする。
    - この仕様が決めたこと以上は書かない。どちらかの仕様の既存の文が、この仕様が決めない形で変更と矛盾するなら、**止めて報告します**。
    - 確認方法: 変更した各仕様ファイルで `validate_spec_format` が通る。
    - _要件: 12.5, 13.7_
  - **3.2 変更した仕様ファイルの日本語訳を更新する** — 完了
    - `docs/ja/lab-bench/` と `docs/ja/dr-kiro/`: 3.1 で変えたすべてのファイルの訳を、`原文 SHA-256` のヘッダー付きで（`japanese-translations.md`）。
    - 確認方法: `sh scripts/ja-check.sh` が `lab-bench` と `dr-kiro` について古いものなしと報告する。
    - _要件: 12.5, 13.7_
- **4. チェックポイント** — 完了
  - すべてのテストが通ることを確認し、疑問があればユーザーに尋ねる。`sh bench/scripts/check.sh`、body-lab アダプターのテスト（ゴールデンファイルは変更なし、`git diff --stat body-lab/` は空）、`bench-check-discovered sessions discovered`、両方のラボでの `bench-scan` を走らせる。日本語で報告する。
### パート 2: `build-from-spec/` プロジェクト
- **5. プロジェクトとアプリケーションのテーブル** — 完了
  - **5.1 `build-from-spec/` の uv プロジェクトと `apps.py` を作る** — 完了
    - `build-from-spec/pyproject.toml`: Python `>=3.12,<3.13`、依存は `lab-bench`（`frontend` グループなし）と `body-lab-adapter` をパスで。コンソールスクリプトは `bfs-check-request`、`bfs-run`、`bfs-run-file`、`bfs-check-runs`。dev グループは `pytest`、`hypothesis`、`ruff`。ruff の設定は `bench` と同じ。`uv lock` を実行する。
    - 設計 2.1 のパッケージの骨組み。`App` と `APPS`（body-lab、予算 12）を設計 3.1 のとおりに持つ `apps.py`。カレントフォルダーに `.git` がなければ開始を拒否する共有ヘルパー（設計 B24）。各コマンドは、そのタスクのスタブまで、"not implemented" で 0 以外の終了コードになる。
    - ユニットテスト: body-lab のエントリーの予算は 12。テーブルにないアプリケーションを引くと "no reader budget is decided for <application>" になる。`uv.lock` に `mcp` がない。`bench/pyproject.toml` と body-lab の `pyproject.toml` は `build-from-spec` を名指ししない。リポジトリのルートの外で実行したコマンドは拒否される。
    - 確認方法: パート 2 のチェック。`bench/` で `sh bench/scripts/check.sh` がやはり通る。
    - _要件: 1.1, 1.2, 1.3, 4.3, 4.7_
- **6. リクエストファイル** — 完了
  - **6.1 `request.py` を書く: parse、print、inside** — 完了
    - 設計 3.2 のとおりの `PassRange`、`Request`、`RequestError`、`parse_request`、`print_request`、`inside`。拒否は要件 2.2 の順で、それぞれファイルとフィールドまたは行を挙げる。
    - ユニットテスト: コミット済みの 3 つのリクエストが parse される。手書きのファイルでの要件 2.2 の各拒否。int の境界は float として読まれ、bool の境界は拒否される。`inf` と `nan` は拒否される。境界と等しい値は範囲の内側。
    - 確認方法: パート 2 のチェック。
    - _要件: 2.1, 2.2, 2.3, 2.4_
  - **6.2 リクエストの往復のプロパティテストを書く** — 完了
    - **Property 1: Request round trip**
    - **Validates: Requirements 2.1, 2.4**
  - **6.3 不正なリクエストのプロパティテストを書く** — 完了
    - **Property 2: Malformed requests are refused by name**
    - **Validates: Requirements 2.2**
  - **6.4 `check_request` と `bfs-check-request` を書く** — 完了
    - 設計 3.2 のとおりの `check_request` とコマンド: parse し、そのあと `id` と `words` を `Scanner.from_config([App.scan_sources], stop_list)` でビルダーレベルでスキャンする。検出は `<file>:<line>: <kind>: <match>` で、終了コード 1。元の確認 `source_trials_inside` と `--source <record path>`（必須、デフォルトなし。要件 3.5、決定 19）。"no findings" で終了コード 0。何も書かない。
    - ユニットテスト: `--source sessions/body-lab/body-2` 付きの `stop-ahead` で検出なし、ファイルの変更なし。`straight-ahead` は T31、T34、T35、T37、T38、T39 を挙げて拒否され、`turn-right` は T19、T25、T29 を挙げて拒否される（決定 18）。範囲にフェイクの元の試行を含むリクエストは、その試行を挙げて拒否される。`--source` がなければ拒否される。検証に通らない元は、パスを挙げて拒否される。`words` と `id` に仕込んだフェイクの語（コピーの中で、フェイクのアプリケーションのスキャンのソースを使う）は、行を挙げて失敗する。形式の誤りはフィールドを挙げて失敗する。
    - 確認方法: パート 2 のチェック。
    - _要件: 3.1, 3.2, 3.3, 3.4_
- **7. ラップするアダプター** — 完了
  - **7.1 `wrap.py` を書く** — 完了
    - `reader/<application>/<request-id>/<budget>` のファクトリーを返すモジュールの `__getattr__`（PEP 562）と、設計 3.3 のとおりの `ReaderAdapter`: `budget` と `goal` を置き換えた宣言、何も捕まえずに入力とシードを渡す `run_trial`、ラップされたアダプターが持つときだけ設定される `builder_versions` と `check_inputs`。
    - ユニットテスト: 宣言は、予算とゴール以外ラップされたものと等しい。ゴールはリクエストの `words` とバイト単位で等しい。試行の結果と `TrialFailure` は変わらずに返る。送出されたエラーはそのまま通る。不完全なファクトリー名は、足りないもの（アプリケーション、リクエスト、予算）を挙げて拒否される。不明なアプリケーション、`App.budget` と異なる予算、別のアプリケーションのリクエストは拒否される。ダンダー名は `AttributeError` を出す。ファクトリー名を持つ設定での `bench.frontend.config.load` はアダプターを作る。
    - 確認方法: パート 2 のチェック。
    - _要件: 8.1, 8.2, 8.4, 8.5, 8.6_
- **8. リーダーのファイル** — 完了
  - **8.1 リーダーのビルダーのファイルと `build-from-spec/README.md` を書く** — 完了
    - `build-from-spec/src/build_from_spec/files/`: 設計 3.4 のとおりの `reader.json`、`reader-prompt.md`、`reader.md`（`inclusion: always` 付き）と 3 つのテンプレート。パッケージデータとして含める。英語で、パスも部品名も数値もなし。H1 の例は山括弧のプレースホルダーを使う。
    - `build-from-spec/README.md`: この部分が何か、設計 2.2 のインストールコマンド、4 つのコマンド、開始の一文 `Begin the session.` と再開の一文 `Continue the session.`、そして設計第 9 節の結果（タスク 18 で埋める）と実行のための空のセクション。
    - ユニットテスト: `reader.json` は、`name`、`description`、`prompt` を除いた JSON として `bench/src/bench/drkiro/files/dr-kiro.json` と等しく、`read`、`write`、`@bench` を持ち、シェルを持たない。テンプレートは、仮説ブロックも数字も `## Discovered spec` も持たない。`reader.md` は頼る行の接頭辞と `PHASE = "best"` を持ち、セットアップ固有の文を持たない。すべてのファイルがビルダーレベルのブラインドスキャンを通る。
    - 確認方法: パート 2 のチェック。
    - _要件: 1.1, 9.1, 9.2, 9.4, 9.6_
- **9. 作業フォルダー** — 完了
  - **9.1 セットアップ `spec` と `none` のための `folder.py` を書く** — 完了
    - 設計 3.5 のとおりの `builder_files`、`given_files`、`write_folder`、`file_hashes`、`tool_hashes`、`scan_folder`。`write_folder` は、存在するフォルダーを拒否し、`labhooks.install` でフックを書き、ベンチパッケージから `method.md` をバイト単位でコピーし、`request.md` を words そのままで書き、空の `experiments/` を作る。`spec`: `final_spec(source).files` の 3 つのファイル。`none`: 空の `given/`。`record` のセットアップはタスク 10.4 で組み込む。`tool_hashes` は `describe.descriptions(decl, "not-required")` を使う。`scan_folder` は要件 7.6 のレベルを適用する。
    - ユニットテスト: `spec` と `none` について設計 3.5 のフォルダーツリー。`method.md` はベンチパッケージのファイルの SHA-256 を持ち、`workflow.md` はない。`request.md` と宣言されたゴールは `words` と等しい。`given/` の外のどのファイルも、実行 ID、元セッションの id、パスを持たない。ビルダーのファイルに仕込んだ語は、ファイルと行を挙げてスキャンに失敗する一方、渡す仕様ファイルの同じ語は Dr. Kiro レベルで通る。一時リポジトリの作業フォルダーでの `confine.decide` は、`build-from-spec/requests/`、`sessions/`、別の作業フォルダー、`body-lab/lab/`、`notebook/` の読み取りと書き込みを拒否する。
    - 確認方法: パート 2 のチェック。
    - _要件: 4.1, 4.2, 4.5, 5.3, 7.2, 7.3, 7.5, 7.6, 7.7, 8.4, 9.3, 9.5_
- **10. 縮約した記録のコピー** — 完了
  - **10.1 `reduced.py` を書く** — 完了
    - 設計 3.6 のとおりの `Removed`、`reduce`、`check_reduced`。
    - 封印されたフェイクの記録でのユニットテスト: 残る行、残る blob、取り除かれたリスト。要件 19.3 の各失敗ケース（残る行の変更、取り除かれたスナップショット以外の行、残るスナップショットのエントリー、余分な blob、足りない blob）と、別のファイルの追加が、行または blob を挙げて報告される。
    - 確認方法: パート 2 のチェック。
    - _要件: 6.1, 6.2, 6.3, 6.4_
  - **10.2 縮約したコピーのプロパティテストを書く** — 完了
    - **Property 7: Reduced copy keeps everything but the snapshots**
    - **Validates: Requirements 6.1, 6.2, 6.4**
  - **10.3 コピーのチェックのプロパティテストを書く** — 完了
    - **Property 8: Copy check accepts the copy and finds every change**
    - **Validates: Requirements 6.3**
  - **10.4 `record` のセットアップを作業フォルダーに組み込む** — 完了
    - `record` のときの `folder.given_files` は、`reduce` で `given/record/` を書き、取り除かれたエントリーを返す。`scan_folder` は `scanner.scan_record` でそれをスキャンする。
    - ユニットテスト: 1 つのリクエストの 3 つの作業フォルダー（`spec`、`none`、`record`）は、`given/` の外で同一のツリーとバイトを持つ。`check_reduced` は書かれたコピーで通る。
    - 確認方法: パート 2 のチェック。
    - _要件: 4.1, 4.2, 6.1, 7.6_
- **11. 頼る行** — 完了
  - **11.1 `relied.py` を書く** — 完了
    - 設計 3.7 のとおりの `PREFIX`、`PROBLEMS`、`Relied`、`relied_line`、`parse_ids`、`format_ids`、`allowed_ids`、`relied_on`。問題の順は `no-h1`、`no-line`、`bad-syntax`、`unknown-id`、`late`。
    - ユニットテスト: `sessions/body-lab/body-2` の許可された id: `spec` は R1-R14 と `none`、`record` は H1-H11、E1-E11 と `none`、`none` は `none` だけ。表が parse できない元ではコマンドが失敗する。`# relies on` で始まらない最初の予測の行は `no-line`。
    - 確認方法: パート 2 のチェック。
    - _要件: 10.1, 10.2, 10.3, 10.4, 10.5_
  - **11.2 頼る行のプロパティテストを書く** — 完了
    - **Property 3: Relied-on line round trip**
    - **Validates: Requirements 10.1**
  - **11.3 凍結部分が頼るコメントを保つことをテストする — 失敗したら Stop and ask（止めて確認）** — 完了
    - フェイクセッションが、予測ブロックが `# relies on: none` で始まる H1 を登録する。記録された凍結部分の blob はその行をバイト単位で持ち、`relied_line` がそれを読み戻す。凍結部分がその行を持たなければ、**止めてユーザーに尋ねます**。ベンチも構文も変えません。
    - 確認方法: パート 2 のチェック。
    - _要件: 10.3, 10.6_
- **12. 結果のプログラム** — 完了
  - **12.1 `judge.py` を書く** — 完了
    - 設計 3.8 のとおりの `Judgement`、`counted_trials`、`judge`、`judge_record`: カウントされる試行は `"for": "experiment"` のスナップショットで決め、最後の試行は `parse_trial_id` で決め、範囲の内側は `inside` で決め、未計測は外側とし、結果は `not-counted`、`no-trial`、`pass`、`fail` の順。範囲に最初に入る試行。終了は封印エントリーから。最後の試行のフェーズ。
    - ユニットテスト: 拒否された呼び出しのあるフェイクの実行、ベンチ障害で途中で止まった実行（その試行はカウントされない）、`lost` のような未計測の値、試行エントリーに名指しされた測定がない場合（コマンドが失敗する）。
    - 確認方法: パート 2 のチェック。
    - _要件: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.9, 15.10_
  - **12.2 結果のチェックの順序のプロパティテストを書く** — 完了
    - **Property 4: Order of the result checks**
    - **Validates: Requirements 10.3, 10.4, 15.2, 15.3**
  - **12.3 最後にカウントされる試行のプロパティテストを書く** — 完了
    - **Property 5: Only the last counted trial decides**
    - **Validates: Requirements 2.3, 15.4, 15.6, 15.8, 15.9, 15.10**
  - **12.4 範囲に最初に入る試行と冪等性のプロパティテストを書く** — 完了
    - **Property 6: First in-range trial, and judging twice**
    - **Validates: Requirements 15.5, 15.7**
- **13. 実行データファイル、実行情報ファイル、作者のサイドカー** — 完了
  - **13.1 `runfile.py` に、実行データと実行情報ファイルの形式とサイドカーを書く** — 完了
    - 実行データファイル（設計 4.3）と実行情報ファイル（設計 4.4）を、`indent=2`、キーをソート、最後に改行の JSON として。フィールドの不足も余分も拒否するリーダー。設計 4.4 の `null` マーカー。設計 3.13 の作者のサイドカーは、プレースホルダーで作り、頼る id のトークンは `dr-kiro`、残りは `bench` とする。実行情報ファイルにパスは入れない（設計 B25）。
    - ユニットテスト: `relied_on.ids` が `null` のもの、`["none"]` のもの、引用符と非 ASCII を含む id のものの実行情報ファイル。`sidecar_pieces` はそのペアを受け入れる。
    - 確認方法: パート 2 のチェック。
    - _要件: 11.11, 14.2, 14.4_
  - **13.2 実行情報ファイルの往復のプロパティテストを書く** — 完了
    - **Property 10: Run file round trip**
    - **Validates: Requirements 14.2**
  - **13.3 サイドカーのプロパティテストを書く** — 完了
    - **Property 11: The sidecar gives every character one author**
    - **Validates: Requirements 14.4, 16.5**
  - **13.4 `write_run_file` と `bfs-run-file` を書く** — 完了
    - 設計 3.11 のステップ 1-5: 既存の実行情報ファイルを拒否する。実行データファイルを読む。封印された実行記録を検証する。記録されたコミットでの元とリクエストを読み、ハッシュを比べる。`allowed_ids` と `judge_record`。実行情報ファイルとサイドカーを一時的な名前で書き、実行記録と実行情報ファイルをスキャンし、検出がないときだけリネームする。
    - 一時リポジトリの封印されたフェイクの実行でのユニットテスト: 実行情報ファイルとサイドカーが書かれる。2 回目の呼び出しはファイルを挙げて拒否する。リーダーのテキストに仕込んだパスはスキャンに失敗し、ファイルと行を出力し、実行情報ファイルも一時ファイルも残さず、実行記録は変わらない。サイドカーのない実行情報ファイルは "no level source" で `bench-scan` に失敗する。
    - 確認方法: パート 2 のチェック。
    - _要件: 14.1, 14.2, 14.5, 16.2, 16.4, 16.5_
- **14. 以前の実行と `bfs-check-runs`** — 完了
  - **14.1 `runs.py` を書く** — 完了
    - 設計 3.12 の実行 ID のパターン。`sessions/build-from-spec/<application>/` にある 1 つのリクエストの実行記録と実行情報ファイル。`bfs-run` のフェーズ A6 が使う整合性のチェック（すべての実行記録に実行情報ファイルがある。同じシード、元セッションと封印、リクエストの SHA-256 とコミット、Kiro CLI のバージョン、モデル、エフォート）。違いはそれぞれ両方の値を挙げる。
    - ユニットテスト: リクエスト id にハイフンを含む実行 id が正しく読まれる。実行情報ファイルのない実行記録が名指しされる。違っているフィールドは両方の値とともに名指しされる。
    - 確認方法: パート 2 のチェック。
    - _要件: 4.6, 5.6, 7.8, 14.6, 17.5_
  - **14.2 `check.py`、`derive_run`、`bfs-check-runs` を書く** — 完了
    - 設計 3.12 のステップ 1-4。読むのは `sessions/build-from-spec/`、記録されたコミットでの `build-from-spec/requests/`、実行情報ファイルが名指しする元の記録だけ。実行ごとに 1 行。問題があれば、実行情報ファイルとフィールドを挙げて終了コード 1。`derive_run` は要件 18.1 の項目を返し、`lab-notebook` のビルドから import できる。
    - ユニットテスト: 変更された記録、変更されたリクエスト、変更された元、シードの異なる 1 つのリクエストの 2 つの実行情報ファイルは、それぞれフィールドを挙げて失敗する。実行の前の最後の変更ではないリクエストのコミットは失敗する。テストリポジトリでリクエストファイルに後のコミットがあっても、要件 18.1 の項目は実行ごとに、記録されたコミットでのリクエストの words と範囲とともに挙げられる。
    - 確認方法: パート 2 のチェック。
    - _要件: 14.3, 14.6, 18.1, 18.2_
  - **14.3 実行情報ファイルのチェックのプロパティテストを書く** — 完了
    - **Property 12: The run-file check finds a changed field**
    - **Validates: Requirements 14.3, 19.5**
- **15. ターン** — 完了
  - **15.1 `turns.py` を書く** — 完了
    - 開始と再開の一文の定数、設計 3.10 の固定の `kiro-cli chat` コマンド（後のターンでは `--model`、`--effort`、`--resume` 付き）、`Prompt`、`TurnsEnd`、設計 3.10 の 4 つの規則と設計 B26 の停止理由を持つ `run_turns(launch, entries, save)`。
    - ユニットテスト: 最初のターンと後のターンのコマンド。一文は `build-from-spec/README.md` のものと等しい。停止理由は禁止された語を持たない（ビルダーレベルのスキャン）。
    - 確認方法: パート 2 のチェック。
    - _要件: 9.6, 11.6_
  - **15.2 ターンのループのプロパティテストを書く** — 完了
    - **Property 9: Turn loop**
    - **Validates: Requirements 9.6, 11.6**
- **16. `bfs-run`** — 完了
  - **16.1 `run.py` を書く** — 完了
    - 設計 3.9 の引数。すべて必須で、文字列として検証する。フェーズ A のチェック 1-9 を順に行い、何も書かない。フェーズ B（`write_folder`、`record` のための `check_reduced`、以前の実行情報ファイルとのハッシュの比較、`scan_folder`、実行データファイル、`resume = true` と `discovered_table = "not-required"` を持つ設計 4.2 のセッション設定）。フェーズ C（`config.load`、`Session.start`、`close`）。フェーズ D（作業フォルダーで Kiro CLI を使う `run_turns`、標準入力は閉じ、出力は `<run-id>.turn-<k>.log`、`BENCH_SESSION_CONFIG` と `BENCH_HOOK_LOG` は絶対パス、`KIRO_API_KEY` は環境からだけ）。フェーズ E（封印されたとき実行情報ファイル。封印エントリーはあるが封印されたフォルダーがないときは報告して停止。ターンの規則が実行を止めるときは固定の理由で `bench-stop` を行い、そのあと実行情報ファイル。`bench-stop` が失敗したら出力して停止）。終了コードは設計の "Error Handling" のとおり。`sessions/build-from-spec/` がなければ作る。
    - 確認方法: パート 2 のチェック。
    - _要件: 4.4, 4.6, 4.7, 5.1, 5.2, 5.4, 5.5, 5.6, 5.7, 7.1, 7.3, 7.4, 7.8, 11.1-11.11, 13.1, 13.5, 13.6, 17.3, 17.4, 17.5_
  - **16.2 `bfs-run` の拒否のテストを書く** — 完了
    - 何かを書く前に（作業フォルダーもファイルもなし）: 追跡されていないリクエスト、変更されたリクエスト（ステージ済みと未ステージ）、検出のあるリクエスト、body-lab 以外のアプリケーション、元としての `sessions/body-lab/body-1`（終了スナップショットなし）、停止した記録、検証に通らない記録、別のアプリケーションの元、`sessions/build-from-spec/` の中の元、存在する作業フォルダー、実行記録、実行情報ファイル、実行情報ファイルのない実行記録、異なるシード、元、リクエストのハッシュまたはコミット、Kiro CLI のバージョン、モデル、エフォート、状態フォルダーの開いているセッション、そして値とともに名指しされるそれぞれの不正な引数。
    - 書いた後: 変更されたビルダーのファイルまたはツールのテキストは、名指しして拒否される。ビルダーのファイルに仕込んだ語はスキャンに失敗する。作業フォルダーは残され、名指しされる。ベンチセッションは始まらない。
    - テストは一時リポジトリと、テスト用の `APPS` テーブルを通したフェイクのアプリケーションを使う。`kiro-cli` は決して起動しない（launch はテスト関数）。
    - 確認方法: パート 2 のチェック。
    - _要件: 4.6, 4.7, 5.2, 5.5, 5.6, 5.7, 7.1, 7.4, 7.5, 7.8, 11.2, 11.7, 11.8, 11.10, 17.5, 19.4_
  - **16.3 フェイクの launch でのエンドツーエンドのテストを書く** — 完了
    - コアを通してフェイクセッションを動かすフェイクの `launch`（頼る行付きの H1 を登録し、実行し、判定し、`end`）は、`sessions/build-from-spec/<application>/<run-id>/` に `ended` として封印された記録と、実行情報ファイル、サイドカーを作り、`bfs-check-runs` が通る。記録のリーダーのテキストは `dr-kiro` の作者を持つ。何もしない `launch` は、2 回目のアイドルのターンの後に `bench-stop` で止められる。0 以外の終了はすぐに止められる。どちらも `end` が `stopped` の実行情報ファイルを得る。再開の一文の回数は `continue` のプロンプトと等しい。
    - 確認方法: パート 2 のチェック。
    - _要件: 9.6, 11.6, 11.9, 13.1, 13.2, 13.4, 14.1, 15.6_
- **17. チェックポイント** — 完了
  - すべてのテストが通ることを確認し、疑問があればユーザーに尋ねる。パート 1 と 2 のチェックと、`build-from-spec/` のビルダーのファイルでの `bench-scan` を走らせる。日本語で報告する。
### パート 3: 実装時のチェックと実行
- **18. 実装時のチェック（設計第 9 節）— Stop and ask（止めて確認）** **[local Mac]** — 未着手
  - 各チェックは、`bench-run/` のフェイクのアプリケーションで 1 回ずつ手で行い、結果を、使ったコマンドとともに、観察された・観察されなかったとして `build-from-spec/README.md` に書く。観察されなかったチェックは停止です。日本語で報告して尋ねる。それを回避するために、方法、フラグ、ファイルを変えない（`rules.md` 2）。
  - **18.1 コマンドをインストールし、アダプターの import を確かめる（チェック 8）** — 完了
    - `uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --with-editable ./build-from-spec --reinstall`。`PATH` の `bench-mcp` が `build_from_spec.wrap` を import する。結果を README に書く。
    - _要件: 1.2, 8.3_
  - **18.2 ヘッドレスの Kiro CLI を確かめる（チェック 1-6）** — 未着手
    - 新しいフォルダーでの設計 3.10 のヘッドレスのコマンドが、プロンプトなしで始まり（`--trust-workspace`、`--trust-tools=`、`--require-mcp-startup`）、尋ねるはずのツールは待たずに拒否される。`--no-interactive` での `--resume` が同じ会話を続ける（2 ターンの後、`kiro-cli chat --list-sessions` が 1 つを示す）。選んだ `--model` と `--effort` の値が受け入れられる（`kiro-cli chat --list-models`）。通常のターンの終わりに終了コード 0、`bench-mcp` が起動できないとき 3。`BENCH_SESSION_CONFIG` が `bench-mcp` に届き、`BENCH_HOOK_LOG` がフックに届く。`bench-mcp` は Kiro CLI が終了すると終了するので、`bench-stop` がロックを取れる。また、`--trust-tools` が `@bench` 以外のツールを挙げなければならない場合も、止めて尋ねる。
    - 各結果を README に書く。
    - _要件: 9.1, 11.6_
  - **18.3 リーダーのファイルツールが画像の blob を開けることを確かめる（チェック 7）** — 未着手
    - 封印されたフェイクの記録から作った `record` セットアップの作業フォルダーで、リーダーのファイルツールが `given/record/blobs/` の画像の blob（ハッシュ名、拡張子なし）を開く。README に "opened" か "not opened" を書く。開けなければ、README に制限として書き、どの実行よりも前にユーザーに尋ねる。
    - _要件: 6.5_
- **19. 最初の本物の実行の前の準備 — Stop and ask（止めて確認）** **[local Mac]** — 未着手
  - **19.1 準備を確認し、実行の引数を尋ねる** — 未着手
    - 設計には `bfs-run` のドライランモードがなく、`APPS` には body-lab しかないので、リハーサルはタスク 16.3 のフェイクの実行と、フェイクのアプリケーションでのタスク 18 の手でのチェックです。body-lab の実行は、そのベンチセッションが始まった瞬間からカウントされる（要件 17.4）ので、カウントされない body-lab のリハーサルは行いません。ユーザーが望むなら、要件の変更が必要になるので、**止めて尋ねます**。
    - 確認すること: タスク 11.3、16.3、18 が通り、その結果が README にある。3 つのリクエストファイルがコミット済みで変更なし、`bfs-check-request --source sessions/body-lab/body-2` が決定 19（要件 3.5）の結果を返す: `stop-ahead` は検出なし、`straight-ahead` は試行 T31、T34、T35、T37、T38、T39 を挙げて拒否され、`turn-right` は試行 T19、T25、T29 を挙げて拒否される。`sessions/body-lab/body-2` で `bench-verify` が通る。`bench-run/build-from-spec/state/` に開いているセッションがない。`KIRO_API_KEY` がビルダーの環境だけに設定されている。
    - `stop-ahead` の実行のシード、モデル、エフォートをユーザーに日本語で尋ねる。ユーザーが答えるまで何も書かない。答えを `docs/status.md` に記録する。
    - _要件: 4.4, 10.6, 17.3_
- **20. 6 つの `stop-ahead` の実行** **[local Mac]** — 未着手
  - 各実行: `uv run --project build-from-spec bfs-run --request build-from-spec/requests/stop-ahead.toml --setup <setup> --source sessions/body-lab/body-2 --seed <seed> --run <n> --model <model> --effort <effort>`。値はタスク 19.1 のもの。そのあと、実行記録のフォルダー、実行情報ファイル、そのサイドカーを、1 つずつ名前を指定してコミットする。そのあと、実行記録での `bench-verify`、`bfs-check-runs`、`sessions/build-from-spec/` での `bench-scan` が通る。一度に 1 つの実行。
  - 実行は、結果や終了にかかわらず、そのセッションが始まった時点でカウントされる。次の実行はそのあとに続く。ユーザーの承認なしに、同じリクエストとセットアップの実行を増やさない（要件 17.4）。セッションが始まる前の拒否は何もカウントしない。報告して、同じ `n` を使う（ユーザーが残された作業フォルダーを取り除いたあと、要件 11.10）。
  - 封印が失敗したとき（要件 13.5）、スキャンが実行記録または実行情報ファイルの項目を見つけたとき（要件 16.4）、`bench-stop` が失敗したとき、`bfs-check-runs` が失敗したときは、**Stop and ask（止めて確認）**。
  - **20.1 `stop-ahead-spec-1` を実行する** — 未着手
    - _要件: 13.2, 13.3, 17.1_
  - **20.2 `stop-ahead-none-1` を実行する** — 未着手
    - _要件: 13.2, 13.3, 17.1_
  - **20.3 `stop-ahead-record-1` を実行する** — 未着手
    - _要件: 13.2, 13.3, 17.1_
  - **20.4 `stop-ahead-spec-2` を実行する** — 未着手
    - _要件: 13.2, 13.3, 17.1_
  - **20.5 `stop-ahead-none-2` を実行する** — 未着手
    - _要件: 13.2, 13.3, 17.1_
  - **20.6 `stop-ahead-record-2` を実行する** — 未着手
    - そのあと、6 つの結果を、`bfs-check-runs` が出力するとおりに、各実行の終了、頼る id、再開の一文の回数とともに、日本語で報告する。
    - _要件: 13.2, 13.3, 17.1, 19.6_
- **21. 実行しないリクエスト** — 未着手
  - **21.1 `straight-ahead` と `turn-right` を未実行として記録する** — 未着手
    - `build-from-spec/README.md` と `docs/status.md` に、`straight-ahead` と `turn-right` はコミット済みで未実行と、決定 18 の理由とともに書く: 元の記録 `sessions/body-lab/body-2` が、その合格範囲の内側の試行をすでに含んでいるため、セットアップを比較できない。どちらも実行しない。両方のリクエストファイルは変えない。ユーザーの承認なしに、他のどのリクエストも実行しない。
    - _要件: 17.2_
- **22. `lab-notebook` 仕様への引き継ぎ** — 未着手
  - **22.1 実行を `lab-notebook` 仕様に引き継ぐ** — 未着手
    - "Built from the spec" のセクション（`lab-notebook` の要件 19.2-19.7、そのタスク 22.1 の後）と、この仕様の要件 18.3 の制約は、`lab-notebook` 仕様のものです。ノートブックのものはここでは何も実装せず、`lab-notebook` 仕様はここでは編集しません。
    - ノートブックが読むものを `docs/status.md` に書く: `build_from_spec.check` の `derive_run`、`sessions/build-from-spec/<application>/` の実行情報ファイル、要件 18.3 の制約。ユーザーへの注記: `lab-notebook` の要件 19.3 はリクエストのコミットハッシュを「実行記録に記録されたとおり」と述べるが、この仕様はそれを実行情報ファイルに記録する（要件 14.2）。その言い方は `lab-notebook` 仕様が決める。
    - _要件: 18.3_
- **23. 最終チェックポイント** — 未着手
  - すべてのテストが通ることを確認し、疑問があればユーザーに尋ねる。走らせるもの: `sh bench/scripts/check.sh`。`build-from-spec/` での `uv run pytest`、`uv run ruff check`、`uv run ruff format --check`。body-lab アダプターのテスト。`sessions/build-from-spec/` のすべての実行記録での `bench-verify`。`bfs-check-runs`。`bench-check-discovered sessions discovered`。`sessions/`、`discovered/`、両方のラボでの `bench-scan`。`sh scripts/ja-check.sh`。
  - `docs/status.md` を日本語で更新する: 行ったこと、実行の結果、`straight-ahead` と `turn-right` が未実行であること、画像のチェックの README の結果、次のステップ（`lab-notebook` の "Built from the spec" のタスク）、1 つの環境にだけ当てはまること。`sh scripts/ja-check.sh` が古いものなしと報告したあと、`tasks.md` と `docs/ja/build-from-spec/tasks.md` を、1 つずつ名前を指定して一緒にコミットする（`handoff.md`）。
  - 完了条件（要件 19.6）、この仕様が及ぶ範囲で: 6 つの実行が存在し、封印され、`bench-verify` に通る。すべての実行情報ファイルが `bfs-check-runs` とブラインドスキャンに通る。画像の結果が README にある。結果は機械的に計算される。すべての実行を見せるノートブックは、`lab-notebook` のタスクがチェックする。
  - _要件: 13.2, 16.2, 19.6_
## Notes
- すべてのタスクは必須で、オプションのものはありません。
- 各タスクは、それが扱う要件を参照します。プロパティテストは設計の普遍的な性質を検証し、ユニットテストと例のテストは、設計の Testing Strategy のケースと、そこで名指しされる本物の記録を扱います。
- 波は、同じファイルに書くタスクを分けます: `folder.py`（9.1、10.4）、`runfile.py`（13.1、13.4）、`build-from-spec/README.md`（8.1、18.1、18.2、18.3、21.1）、`docs/status.md`（19.1、21.1、22.1）は、それぞれ 1 つの波につき 1 タスクだけが書きます。タスク 20 の実行は、リーダーのセッションを一度に 1 つしか開けないので、1 つの波に 1 つです（設計 B17）。チェックポイント（4、17、23）はグラフに入っていません。タスク 18 とタスク 19 は、ユーザーの答えが記録されるまで、後のすべての波を止めます。
## Task Dependency Graph
```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["3.1"] },
    { "id": 3, "tasks": ["3.2"] },
    { "id": 4, "tasks": ["5.1"] },
    { "id": 5, "tasks": ["6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "6.4"] },
    { "id": 7, "tasks": ["7.1", "8.1", "11.1"] },
    { "id": 8, "tasks": ["9.1", "11.2", "11.3", "12.1", "15.1"] },
    { "id": 9, "tasks": ["10.1", "12.2", "12.3", "12.4", "15.2"] },
    { "id": 10, "tasks": ["10.2", "10.3", "10.4", "13.1"] },
    { "id": 11, "tasks": ["13.2", "13.3", "14.1"] },
    { "id": 12, "tasks": ["13.4"] },
    { "id": 13, "tasks": ["14.2"] },
    { "id": 14, "tasks": ["14.3", "16.1"] },
    { "id": 15, "tasks": ["16.2", "16.3"] },
    { "id": 16, "tasks": ["18.1"] },
    { "id": 17, "tasks": ["18.2"] },
    { "id": 18, "tasks": ["18.3"] },
    { "id": 19, "tasks": ["19.1"] },
    { "id": 20, "tasks": ["20.1"] },
    { "id": 21, "tasks": ["20.2"] },
    { "id": 22, "tasks": ["20.3"] },
    { "id": 23, "tasks": ["20.4"] },
    { "id": 24, "tasks": ["20.5"] },
    { "id": 25, "tasks": ["20.6"] },
    { "id": 26, "tasks": ["21.1"] },
    { "id": 27, "tasks": ["22.1"] }
  ]
}
```
