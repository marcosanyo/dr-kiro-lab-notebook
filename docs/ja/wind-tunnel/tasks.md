> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/wind-tunnel/tasks.md`](../../../.kiro/specs/wind-tunnel/tasks.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読まず、タスクの実行や完了チェックは英語版だけで行います。この訳のチェック状態は訳した時点のものです。
> 原文 SHA-256: `99ed7cddc668f7fbe70f84f2236fe8498ee60f6099a378f27dea3a1ec9bffdf2`
# 実装計画: wind-tunnel

## Overview

2 番目のアプリケーションのタスクです。`requirements.md`（要件 1-18）と `design.md` から作りました。サブエージェントを 1 タスクにつき 1 つ割り当てるオーケストレーターが、「Run All Tasks」で実行します。順序は次のとおりです: `lab-bench` の改訂の確認、モデル（Docker なし）、シート読み取りゲート、アダプターと宣言、ブラインドスキャン、ラボとレビュー一覧、Docker のステップ（ローカルの Mac のみ）、README の事実、チェックポイント、そして最後にまとめて、ユーザーが必要なステップです。

## Notes for the user and for every sub-agent

- **画像は PNG のシート 1 枚です**（要件 9、Decisions 23-24）。GIF 読み取りチェックが失敗したためです（`spikes/gif/results.md`）。配置（6 フレーム、2 行 3 列、セル 400 x 200、隙間 4、間隔 1.0）はユーザーが設計の承認時に確認するまで提案で、タスクは `constants.toml` の値を使います。
- **シート読み取りチェックは、ユーザーではなくビルダーが実行します**（要件 9.7、9.10、18.2）。タスク 7.1 は合成のテスト用シートを作り、`kiro-cli chat` で偽ラボのエージェントに読ませます。Kiro CLI と `bench-run/fake` が要るのでユーザーの Mac で実行し、Kiro Web ではそこで止まって報告します。タスク 7.2 がゲートで、`spikes/sheet/results.md` を読み、チェックがない、追跡されていない、失敗のとき止まります。タスク 14.5 は本物のシートで同じチェックを繰り返します。「Run All Tasks」の前にユーザーの手順はありません。
- **`lab-bench` のタスク 23-26 を先に終えます**（ノブの `description` 項目、`lab-bench` 要件 18）。それらはここでなく `.kiro/specs/lab-bench/tasks.md` にあります。タスク 1.1 は確認するだけで、終わっていなければ止まります。
- **どこで実行するか。** タスク 1.1-13.2 と 15.1 は Docker も画面も要らず、Kiro Web でもローカルでも動きます。ただしタスク 7.1 は Kiro CLI が要るのでローカルで動かします（結果がコミットされた後は、タスク 7.2 と以降のタスクはどこでも動きます）。Kiro Web で Gmsh をインストールまたは import できなければ、タスク 2.1 は止まって報告します（Gmsh を省略しません）。**[local Mac + Docker]** の付いたタスク（14.1-14.5）は Kiro Web で実行できません（`handoff.md`、要件 18.4）: それらはユーザーの Mac で「Run All Tasks」を実行し、Kiro Web から完了にしてはいけません。
- **「X のチェック」** とは、`wind-tunnel/model/`、`wind-tunnel/adapter/`、`bench/` のそれぞれで、`uv run pytest`（低速のテストは除外）、`uv run ruff check`、`uv run ruff format --check` が通ることです。`bench/` では `sh bench/scripts/check.sh` を使います。すべてのタスクは、触れた各プロジェクトのチェックで終わります。Python 3.12 は `uv` 経由のみ（`tech.md`）。`uv.lock` はコミットします。
- **プロパティテスト**は `hypothesis` を 100 例以上で使い、コメントに `Feature: wind-tunnel, Property N: <title>` のタグを付けます。それぞれが独立したサブタスクで、テスト対象のコードの後に置きます。この計画にオプションのタスクはありません。
- **停止条件。** **Stop and ask（止めて確認）** のタスクはユーザーへの書面の報告で終わり、ユーザーが答えるまで次のタスクは始まりません（ユーザー宛ての報告は日本語、`rules.md` 5）。停止条件に出会ったサブエージェントは報告し、決めません: 別の方法も、範囲、時間上限、設定、許容誤差、stop list、伝えるテキストの変更もしません（`rules.md` 2、6）。停止条件は: 設計の S1-S8、円柱チェックの文献の出典または適合範囲が読めない・確認できない場合（タスク 14.2）、`lab-bench` との衝突（要件 14.2）、確認できない OpenFOAM または Docker の詳細（S5）、タスク 12.4 と 14.4 の提案、失敗したシート読み取りチェック（7.1）、エージェントが説明できないシート（14.5）です。
- **ブラインドのルール。** `model/`、`adapter/`、`requirements.md`、`design.md` のどれも `lab/` にコピーしません（要件 12.6）。コードのコメントと名前は要件 13.4 に従います: 伝える集合の語が導かれたソルバーの語と衝突したら、ビルダーが選んだものを改名し、次に言い換え、それから尋ねます。
- **作り上げた数値なし。** 結果である数値は、すべて記録された実行から来ます。設定の初期値は `constants.toml` にそう印を付け、名前のあるタスクが確認します。プレースホルダーは `<not yet measured>` です。
- **コミット。** タスクが変えたファイルだけを、1 つずつ名前を指定して、共著者の行なしでコミットします。ルートの `README.md`、`docs/brief.md`、`body-lab/model/`、`.kiro/blind-scan/stop-list.txt` は、どのタスクも編集しません。
- **翻訳。** このファイルと、変更したすべての英語 spec には `docs/ja/` に日本語の参考訳があります。最後のコミットの前に `sh scripts/ja-check.sh` が古い訳なしと報告します。

## Tasks

- **1. `lab-bench` への依存** — 完了
  - **1.1 `lab-bench` の改訂が終わっていることを確認する** — 完了
    - `.kiro/specs/lab-bench/tasks.md` を読み、タスク 23、24、25、26 にチェックが付いていることを確認する。`bench/src/bench/adapter.py` の `FunctionKnob` と `NumberKnob` が `description` 項目を持つことを確認する。`sh bench/scripts/check.sh` と `body-lab/adapter` のテスト（golden の比較）を走らせる。
    - どれかが偽なら、どの部分かを**止めて報告**する。改訂をここで実装しない。
    - 確認方法: 報告が 4 つのチェック、項目、通ったチェックを述べる。
    - _要件: lab-bench の 1.4, 14.2, 18.4_

- **2. モデルのプロジェクトと設定** — 完了
  - **2.1 `wind-tunnel/model/` を `uv` プロジェクトとして、設定とともに作る** — 完了
    - `pyproject.toml`（プロジェクト `wind-tunnel-model`、Python 3.12、依存 `gmsh` と `numpy`、開発依存 `pytest`、`hypothesis`、`ruff`）、設計の Data Models の表の全キーを持つ `constants.toml`、`src/wind_tunnel_model/settings.py`: 読み込み、検証、キーの欠落・余分・プレースホルダー・型の誤りの拒否、環境から何も読まない、`with_reynolds(x)` の提供（設計 6、14.2）。
    - 値: brief の値（レイノルズ数 150、領域 6 / 18 / 7、終了時刻 150、平均は 80 から、クーラン数 0.8、3 プロセス、140 s）、板の厚さ 0.08、`min_arc = 0.0314` と `min_line = 0.0025`（コーナーのルール、設計の Decision 23）、`max_delta_t = 0.05`、Decision 8 のパッチ名、設計 7 の画像設定（提案の配置、Decision 16）。メッシュサイズ、`initial_delta_t`、`vorticity_limit` は初期値で、それを確認するタスク（4.1、14.1、14.4）を名指すコメントを付ける。ファイルにプレースホルダーは書かない。
    - ローダーは `max_delta_t <= ESTIMATOR_MAX_DT`（0.05）を確認する。`ESTIMATOR_MAX_DT` は `settings.py` で定義する。また、`frames` が `rows * columns` に等しいこと、最初のフレームの時刻が `average_from` より前でないことを確認する。`settings.py` は `frame_times(settings)` を提供する（設計 7）。
    - Gmsh が import できることを確認する（`uv run python -c "import gmsh"`）。インストールまたは import できなければ、**止めて報告**する。Gmsh を外したりメッシャーを替えたりしない。
    - 単体テスト: 実ファイルが読み込める。キーの欠落、余分なキー、プレースホルダーの文字列、誤った型、0.05 を超える `max_delta_t`、`rows * columns` に等しくない `frames`、`average_from` より前の最初のフレームが、それぞれキーを名指して拒否される。`with_reynolds` はコピーを返し、元は 150 のまま。実ファイルはフレームの時刻 145、146、…、150 を与える。
    - 確認方法: `model/` のチェック。
    - _要件: 6.6-6.9, 7.2, 9.3, 9.4, 10.1, 14.1_
  - **2.2 フレーム時刻のプロパティテストを書く** — 完了
    - **Property 16: Frame times follow the settings**
    - **Validates: Requirements 9.3, 9.4**

- **3. ジオメトリ** — 完了
  - **3.1 ボディの輪郭を書く** — 完了
    - 設計 2 の `geometry.py`: `outline(aspect, corner, splitter, angle, settings)` は `Line` と `Arc` の順序づけられた閉じたタプルを返す。半径は `corner * min(1, aspect) / 2`。長さがちょうど 0 の部分は省く。板は `a/2 - t` から `a/2 + splitter` まで、切り口 `x_c` つき。回転は設計 2 の行列（正の角度は先端側を +y の向きに動かす）。負または定義できない部分は `GeometryError`（短い部分はここでは拒否しない。それは実行の前に `input_rule.py` のコーナーのルールが行う、設計の Decision 23）。Gmsh は import しない。
    - 単体テスト: (1, 1, 0, 0) の円。(1, 0, 0, 0) の正方形。`corner` 1 での板。16 の端のコーナーの組み合わせがそれぞれ有効な輪郭を与える。正の `angle` でボディの先端側が軸の上にある。
    - 確認方法: `model/` のチェック。
    - _要件: 3.3, 3.6, 6.1-6.5, 6.10_
  - **3.2 輪郭のプロパティテストを書く** — 完了
    - **Property 1: Outline is closed and valid for every knob value**
    - **Validates: Requirements 3.3, 6.10**
  - **3.3 角の半径のプロパティテストを書く** — 完了
    - **Property 2: Corner radius follows the definition**
    - **Validates: Requirements 6.1, 6.2**
  - **3.4 板と回転のプロパティテストを書く** — 完了
    - **Property 3: Plate and rotation**。`angle` の文が伝える角度の符号を含む。
    - **Validates: Requirements 3.6, 6.3, 6.4**

- **4. メッシュ** — 完了
  - **4.1 Gmsh のレシピとメッシャーのインターフェースを書く** — 完了
    - 設計 3 の `mesh.py`: `Mesher` プロトコル、`GmshMesher`（組み込みカーネル、輪郭からの円弧、設定からの領域、サイズ場、z 方向に 1 層の押し出し、`[patches]` から名づけた 5 つの物理グループ、乱数シードなし、明示的なアルゴリズムとスレッド数）、`FakeMesher`（固定の小さなファイル）、`MeshError`。Gmsh のテストには `needs_gmsh` の印を付け、Gmsh が import できない所でだけ、見える理由つきでスキップする。
    - 円と、板つきの長いボディのセル数を報告する。セル数から見て 140 s の実行が現実的でなさそうなら、タスクの報告でそう述べる。初期のサイズはタスク 14.1 が確認し、円柱チェックを走らせるまでは尋ねずに変えてよい（要件 6.8）。
    - 単体テスト: 16 の端のコーナーの輪郭が、5 つの名前つきグループを持つメッシュファイルを作る。同じ入力はバイト単位で同一のファイルを 2 回作る。
    - 確認方法: `model/` のチェック。
    - _要件: 6.8, 6.9, 7.2, 10.2_

- **5. ケースの生成とソルバー出力** — 完了
  - **5.1 ケースのテンプレートとケース生成器を書く** — 完了
    - `model/case/` のテンプレートと `Allrun`（設計 4）、`casegen.py`（`render_case`: `@NAME@` を設定から置き換え、ファイルは並べ替え、`\n` 終端、埋まらないプレースホルダーはエラー）。力の関数オブジェクト、画像グリッド上の渦度サンプリング、3 プロセス分割を含める。OpenFOAM なしでは確認できない綴りは、分かっている最善で書き、報告に挙げる。タスク 14.1 が確認する。
    - 単体テスト: 生成したケースが粘性 `speed * height / reynolds` を持つ。`@` が残らない。2 回の生成がバイト単位で同一。
    - 確認方法: `model/` のチェック。
    - _要件: 6.6, 6.7, 6.9, 10.1, 10.2_
  - **5.2 ケース生成のプロパティテストを書く** — 完了
    - **Property 11: Case generation is deterministic and complete**
    - **Validates: Requirements 6.6, 6.7, 10.1, 10.2**
  - **5.3 ソルバー出力のパーサーを書く** — 完了
    - `solver_output.py`: 力のファイルをパースする（列は設計の Data Models。合計のみ）。ファイルの欠落・読めない、非有限値、行なし、時刻が増えないものを拒否する。サンプリングした渦度のファイルを配列とマスクにパースする。テスト側のライターは `tests/` に置く。
    - 単体テスト: 力のファイルの例。非有限値のファイル。空のファイル。点が欠けた渦度サンプル。
    - 確認方法: `model/` のチェック。
    - _要件: 8.1, 9.1_
  - **5.4 力のファイルのプロパティテストを書く** — 完了
    - **Property 12: Force file round trip**
    - **Validates: Requirements 8.1**

- **6. 推定器と落ち着き基準** — 完了
  - **6.1 推定器を書く** — 完了
    - 設計 5 の `estimators.py`: 時間重みつきの平均、`cd`、`cl_mean`、`cl_amp`、`shedding`、周波数格子上の最小二乗を黄金分割探索で精密化したストローハル数の推定器（FFT なし、乱数なし）。`shedding` が 0 のときストローハル数は無し（`None`）。落ち着いた部分の純関数。
    - 単体テスト: St 0.164 の正弦波が 1% 以内で得られる。一定の揚力は `shedding` 0 でストローハル数なし。不均等な時刻の系列。
    - 確認方法: `model/` のチェック。
    - _要件: 4.2, 4.6, 5.1, 5.2, 5.6_
  - **6.2 ストローハル数の精度のプロパティテストを書く** — 完了
    - **Property 4: Strouhal accuracy**
    - **Validates: Requirements 5.2, 5.3**
  - **6.3 振幅と平均のプロパティテストを書く** — 完了
    - **Property 5: Amplitude and mean accuracy**
    - **Validates: Requirements 5.4**
  - **6.4 shedding の旗のプロパティテストを書く** — 完了
    - **Property 6: Shedding flag and the absent Strouhal number**
    - **Validates: Requirements 4.4, 4.5, 5.5**
  - **6.5 決定性のプロパティテストを書く** — 完了
    - **Property 7: Estimators are deterministic and shift-invariant**
    - **Validates: Requirements 5.1, 5.6**
  - **6.6 落ち着き基準を書く** — 完了
    - 設計 5 と要件 8.3 の `settle.py`: 落ち着いた部分の前半と後半、`cd` の 2% の規則、下限 0.002 つきの `cl_amp` の 10% の規則、shedding のとき 5 周期以上、割り算なしの比較、失敗した規則を名指す理由。
    - 単体テスト: 定常な系列。傾斜。振幅のドリフト。周期が少なすぎる。
    - 確認方法: `model/` のチェック。
    - _要件: 8.3_
  - **6.7 落ち着き基準のプロパティテストを書く** — 完了
    - **Property 8: Settle criterion**
    - **Validates: Requirements 8.3**

- **7. シート読み取りゲート** — 完了
  - **7.1 合成シートでシート読み取りチェックを行う [local Mac + Kiro CLI]** — 完了
    - `spikes/sheet/make_sheet.py` を書く（スクラッチ領域: `spikes/` の外は実行時に使ってはならない。`bench.pictures.encode_png` は使ってよい）。`spikes/sheet/check-sheet.png` を書く。これは**合成のテスト用入力で、結果ではない**（スクリプトと `results.md` にそう書く）: 2 行 3 列の 6 セル、各セル 400 x 200 で 4 ピクセルの黒い隙間（提案の配置、1208 x 404）、各セルに固有の背景色、固有の位置の点、スクリプト内の小さなビットマップフォントで描いた数字 1〜6（このチェックのためだけ）。スクリプトは読む順に各セルの期待する色、点の位置、数字も出力する。PNG を `bench-run/fake/lab/pictures/check-sheet.png`（git 管理外）にコピーする。
    - 2026-11-13（`spikes/gif/results.md`）と同じように実行する: `bench-run/fake/lab` から、`BENCH_SESSION_CONFIG=<repo>/bench-run/fake/session.toml` と `BENCH_HOOK_LOG=<repo>/bench-run/fake/hook-log.jsonl` を export して、`kiro-cli chat --agent fake-tester --no-interactive --trust-workspace --trust-tools=fs_read "<question>"` を走らせる。質問は、エージェントに `pictures/check-sheet.png` を開かせ、6 つのセルを読む順（左から右、上から下）に、背景色、点の位置、数字を報告させる。質問は期待値を何も与えない。1 回だけ実行する。答えが一部間違っていても、シートを易しくして再実行しない。
    - `spikes/sheet/results.md`（追跡、名前を指定して）を書く: 日付、Kiro CLI のバージョン、配置とサイズ、質問、答え、スクリプトからの期待値、読み取りの hook ログの行、判定。**合格:** 6 セルすべてが正しい。**不合格:** 答えとともにユーザーに（日本語で）**止めて確認**する。画像の形式、配置、サイズは変えない。
    - `kiro-cli` または `bench-run/fake` が使えない場合（たとえば Kiro Web）は**止めて報告**する。チェックを省略しない。
    - 確認方法: `spikes/sheet/results.md` があり、判定が「合格」で 6 セルすべてが正しい。
    - _要件: 9.7, 9.8, 18.2_
  - **7.2 ゲート: シート読み取りチェックの結果を読む** — 完了
    - `spikes/sheet/results.md` が存在し、git で追跡され（`git ls-files spikes/sheet/results.md`）、合成シートの判定が「合格」と記録していることを確認する。このタスクは読むだけである。ファイルがない、追跡されていない、または失敗とあれば、どれかを**止めて報告**する。ファイルを作ったり編集したりせず、画像の形式を切り替えない（要件 9.8）。タスク 8.1 以降は始めない。
    - 確認方法: 報告が、判定を記録しているファイルの行を引用する。
    - _要件: 9.7, 9.8, 9.9, 18.2_
- **8. アダプターのプロジェクトと宣言** — 完了
  - **8.1 アダプターのプロジェクトと宣言を作る** — 完了
    - `wind-tunnel/adapter/` を `uv` プロジェクト `wind-tunnel-adapter` として（Python 3.12。依存は `lab-bench` と `wind-tunnel-model` をパスで、`numpy`。開発依存 `pytest`、`hypothesis`、`ruff`。`slow` マーカーは既定で除外。コンソールスクリプト `wind-tunnel-told-set` と `wind-tunnel-circle-check` は、モジュールをタスク 8.2 と 11.3 が書く）。`declaration.py`: 要件 3.1 の範囲を持つ 4 つの `NumberKnob`、要件 3.2 の文を `description` に（厚さは設定から）、`strouhal` に `not_shedding` を持つ 5 つの計測、`measured_by`（要件 4.2、4.3）、`image/png`、予算 24、要件 11.2 のゴール。`scan_adapter()`（宣言のみ、環境チェックなし）。
    - 単体テスト: 宣言が `check_declaration` を通る。4 つのノブの文が、spec ファイルから読んだ要件 3.2 と等しい（`.kiro/` がない所では見える理由つきでスキップ）。`splitter` の文の数が設定の厚さと等しい。各文が 800 文字以下の 1 行。`measured_by` がしきい値 0.01 を述べ、平均の時刻・実行の長さ・ほかのソルバーの数を述べない。
    - 確認方法: `adapter/` と `model/` のチェック。
    - _要件: 1.1-1.4, 3.1-3.5, 4.1-4.5, 11.1-11.3, 14.1, 14.2_
  - **8.2 伝える集合の書き出しを書く** — 完了
    - コマンド `wind-tunnel-told-set --out PATH` の `told_set.py`: `scan_adapter().declaration()` に `bench.frontend.describe.declaration_text` を呼び、末尾の改行以外は何もなしでテキストを書く。パスは必須。
    - 単体テスト: 2 回の実行が同一のバイトを書く。ファイルがツールの説明に含まれる宣言のテキストと等しい。ファイルにパス・バージョン・セッションの値がない。
    - 確認方法: `adapter/` のチェック。
    - _要件: 2.1-2.4_
  - **8.3 伝える集合の書き出しのプロパティテストを書く** — 完了
    - **Property 13: Told set export equals the declaration**。説明を持つ生成された宣言で。
    - **Validates: Requirements 1.1, 2.1, 2.2, 2.3, 2.4**

- **9. 失敗と画像** — 完了
  - **9.1 失敗の対応づけを書く** — 完了
    - 設計 8 の `failures.py`: 3 つの種類、それぞれの固定の公開理由、`detail` に原因・ノブの値・ケースフォルダー・ソルバーのログの末尾を持つ試行の失敗。
    - 単体テスト: 各種類が固定の公開理由を与える。理由にノブの値がない。
    - 確認方法: `adapter/` のチェック。
    - _要件: 8.1, 8.2, 8.4-8.6, 8.8_
  - **9.2 失敗の対応づけのプロパティテストを書く** — 完了
    - **Property 9: Failure mapping**
    - **Validates: Requirements 8.1, 8.4, 8.5, 8.8**
  - **9.3 画像シートを書く** — 完了
    - 設計 7 の `picture.py`: 固定の上限での渦度から色の添字への写像、固定の 255 エントリーの色の表 1 つと固定のマスク色、フレームごとに 1 セル（サンプリング格子がそのままセル、リサイズなし）、セルを隙間の色の配列に時間順（左から右、次に上から下）にコピー、RGB のタプルの行を `bench.pictures.encode_png` で符号化。numpy と `bench.pictures` だけ。文字は描かない。
    - 単体テスト: 合成した場のシートが `image/png` として `bench.pictures.check_picture` を通る。設定ファイルでサイズが 1208 x 404。セル `k` がフレーム `k` の色と等しい（`zlib` を使うテスト側のデコーダー）。隙間のピクセルが隙間の色。同じ場は同じバイトを与える。隙間の設定 0 では 1200 x 400。
    - 確認方法: `adapter/` のチェック。
    - _要件: 9.1-9.5_
  - **9.4 画像のプロパティテストを書く** — 完了
    - **Property 14: Picture sheet mapping and file**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
- **10. 環境とランナー** — 完了
  - **10.1 環境チェックを書く** — 完了
    - 設計 6 の `environment.py`: Docker に届く、`model/image-lock.toml` のダイジェストでイメージがある、ダイジェストが等しい、CPU が 3 以上。失敗はそれぞれ、どれか、期待したもの、見つけたものを名指す。pull も別のタグもなし。`bench-run/wind-tunnel/environment.jsonl` の行（時刻なし）。ロックファイルがなければ、タスク 14.1 を走らせる必要があると述べるエラー。コマンドは注入した関数を通して出すので、テストに Docker は要らない。
    - 単体テスト: 偽のコマンド関数での 4 つの失敗のそれぞれ。通るチェックは 1 行を書く。封印された記録のテキストにはそれが何もない。
    - 確認方法: `adapter/` のチェック。
    - _要件: 7.1, 7.3-7.6_
  - **10.2 ランナーを書く** — 完了
    - 設計 6 の `runner.py`: `Runner` プロトコル、`DockerRunner`（`docker run` のコマンドライン、140 s の上限からの残り時間、タイムアウトで kill、異常終了と出力の欠落は `SolverFailure`）、`bench-run/wind-tunnel/` の下でシードで名づけたケースフォルダー（失敗では残し、成功では消す）。
    - 注入したプロセス関数での単体テスト: コマンドライン。タイムアウトは kill して `timeout` を送出する。ゼロでない終了は `detail` にログの末尾を入れて送出する。既存のケースフォルダーはエラー。
    - 確認方法: `adapter/` のチェック。
    - _要件: 7.2, 8.1, 8.2, 8.7, 8.8, 10.1, 10.5, 10.6_

- **11. 実行パイプライン、円柱チェック、数値** — 完了
  - **11.1 アダプターとそのパイプラインを書く** — 完了
    - `adapter.py`: `WindAdapter`（構築時の環境チェック、レイノルズ数の引数なし）、フロー図に沿った `run_trial`: 入力の検証（4 つの名前ちょうど、有限、範囲内、クリップなし）、輪郭、メッシュ、ケース、実行、パース、推定器、落ち着き、画像。`shedding` 0 は `NotMeasured("not_shedding", "the lift does not oscillate: cl_amp is not above 0.01")` に写す。想定外の例外は捕まえない。テスト側の `FakeRunner` が、既知の正弦波から合成した力と渦度のファイルを書く。
    - 単体テスト: 偽物を通した落ち着いた実行が `check_result` を通る。`not_shedding` の対応づけ。偽物を通した各失敗の種類。レイノルズ数が `circle_check.py` からだけ到達できる（両方の `src/` の構文木をたどるテスト）。ロックファイルがない間、`WindAdapter()` がロックがないというメッセージで失敗する。
    - 確認方法: `adapter/` のチェック。
    - _要件: 3.3, 3.4, 4.4, 4.5, 6.7, 8.1-8.8, 10.2, 14.2_
  - **11.2 結果の契約のプロパティテストを書く** — 完了
    - **Property 10: Result contract and seed independence**
    - **Validates: Requirements 3.3, 3.4, 10.2, 17.1**
  - **11.3 円柱チェックを書く** — 完了
    - 設計 10 の `circle_check.py` とコマンド `wind-tunnel-circle-check`: 要件 15.4 の 3 つの定数からの `literature(re)`、`with_reynolds(100.0)` での、`run_trial` と同じパイプラインを通した円柱の実行、パーセントでの差、要件 15.5 の項目を持つ `wind-tunnel/circle-check.json` のライター。低速のテスト（マーカー `slow`）はここで書き、タスク 14.2 が走らせる。
    - 単体テスト（Docker なし）: `literature(100)` が 1e-6 以内で 0.164335 で、5% の帯が 0.1561 から 0.1726。偽の計測値での JSON ライターが 15.5 の全項目を持つ。ストローハル数を与えない円柱は、理由つきで `passed = false` を書く。
    - 確認方法: `adapter/` のチェック。
    - _要件: 15.1-15.5, 15.7_
  - **11.4 コード量のスクリプトと数値のファイルを書く** — 完了
    - `wind-tunnel/count_lines.py` は、ロックファイル・仮想環境・キャッシュを除き、`wind-tunnel/adapter/` と `wind-tunnel/model/` の空行でもコメントでもない行を数え、テストファイルは別の行に挙げ、`wind-tunnel/numbers.md` のコード量の部分を書き換える。`numbers.md` を、接続時間 `<not yet measured>`、コード量 `<not yet measured>` で作る（スクリプトがタスク 15.1 で埋める）。
    - 単体テスト: 空行、コメント、ロックファイル、テストファイルのある小さなツリーが期待どおりの数を与える。
    - 確認方法: テストが通る。スクリプトで `ruff` がクリーン。
    - _要件: 16.1-16.3_

- **12. ソルバーファイルのブラインドスキャン** — 完了
  - **12.1 ベンチに抽出器を書く** — 完了
    - 設計 9 の `bench/src/bench/scan/foam_terms.py`: `openfoam-dict`、`shell-words`、`toml-names`、`python-names`。`terms.py` の `EXTRACTORS` に登録。標準ライブラリのみ。読めない・パースできないファイルは、ファイルと問題を名指す `ScanError`。`bench/` のほかが変わる必要があるなら、**止めて報告**する（要件 14.2）。
    - 手作りの小さなフィクスチャでの単体テスト: キーワード、パッチ名、関数オブジェクト名、スクリプト名、プレースホルダー `@NAME@`。除いた構文語。パースできないファイル。
    - 確認方法: `sh bench/scripts/check.sh`。
    - _要件: 13.1, 13.2, 14.2_
  - **12.2 植えたソルバーの語のプロパティテストを書く** — 完了
    - **Property 15: Planted solver terms are found**
    - **Validates: Requirements 13.1, 13.2, 13.7**
  - **12.3 スキャンをつなぎ、伝えるテキストを導かれた語に対してテストする** — 完了
    - `wind-tunnel/adapter/scan_sources.toml`: ソルバーファイルとジオメトリスクリプトとその抽出器、`body-lab` と同じラボの配置、`adapter = "wind_tunnel.adapter:scan_adapter"`（要件 13.5）。13.8 のテストを書く: 導かれた語が伝える集合（`scan_adapter()` の `declaration_text`）に現れない。
    - `wind-tunnel/model/` から導かれた語に対し、伝えるテキストと、ここまでに書いたすべてのビルダーレベルのテキストを `bench-scan` する。ヒットごとに、ビルダーが選んだ識別子を改名し、それでなければテキストを言い換える（この順序、要件 13.4）。`.kiro/blind-scan/stop-list.txt` は編集せず、伝えるテキストはユーザーの承認なしに変えない（要件 1.7）。残るものを `wind-tunnel/blind-scan-findings.md` に挙げる（語、出典のファイルと行、テキストのファイルと行）。
    - 単体テスト: 13.8 のテストが通る。または findings ファイルが、それを失敗させるヒットをちょうど挙げる。
    - 確認方法: `bench/`、`adapter/`、`model/` のチェック。
    - _要件: 13.3-13.8_
  - **12.4 止めて確認: stop list の提案（findings が残る場合のみ）** — 完了
    - `wind-tunnel/blind-scan-findings.md` に残る語がなければ、そこに「none」と記録して先へ進む。
    - 残る場合は、残る各語についてユーザーへの提案を**止めて報告**する: 導かれた語、出典のファイルと行、それを含むテキストとその行、その語がボディの構造について何も言わない理由。ユーザーが語ごとに承認または拒否するのを待つ。その後、承認された語だけを `.kiro/blind-scan/stop-list.txt` に加え、タスク 12.3 のスキャンを再実行し、拒否された語についてはテキストを言い換える。伝えるテキストの変更は、先にユーザーの承認が要る。
    - 確認方法: スキャンが、伝える集合とビルダーレベルのテキストに検出なしと報告する。stop-list の差分は承認された語だけを含む。
    - _要件: 1.7, 13.4, 13.9_

- **13. ラボと形の知識のレビュー** — 完了
  - **13.1 ラボを作る** — 完了
    - `bench-make-lab wind-tunnel/lab`（`body-lab` と同じ `dr-kiro` のコマンド）を走らせ、結果をコミットする。ラボには流れに固有のものを何も置かない。生成されたビルダー作成ファイルが、ベンチが宣言から作るアプリケーション固有のテキスト以外は、`bench-make-lab` が `body-lab/lab` に作るものと等しいこと、`wind-tunnel/lab` への `bench-scan` が何も報告しないことのテストを加える（`bench/tests/drkiro/` の様式、またはアダプターのテスト）。
    - 確認方法: `wind-tunnel/lab` への `bench-scan` が検出なし。触れたプロジェクトのチェック。
    - _要件: 14.3, 12.1, 12.2_
  - **13.2 形の知識のレビュー一覧を書く** — 完了
    - `wind-tunnel/form-knowledge-review.md`: Dr. Kiro が読めるテキストごとに 1 行: `wind-tunnel/lab/` のビルダー作成ファイルの各々、伝える集合の全体、4 つのノブの文の各々（どの文がジオメトリの定義かの注記と、影響を述べる文がないこと）、`measured_by`、ゴール、`failures.py` の固定の公開理由の各々。各行は「reviewed, no form knowledge」と、レビューした者（「builder」）を述べる。ビルダーがテキストを読んだ後に書く。影響を述べる、または含意するテキストがあれば、行を書かずにそれを**止めて報告**する。
    - 完全性のテスト（内容のチェックではない）: ラボのビルダー作成ファイルのすべて、すべてのノブ、すべての公開理由が、一覧に行を持つ。
    - 確認方法: 完全性のテスト。触れたプロジェクトのチェック。
    - _要件: 12.1-12.5_

- **14. Docker のステップ — [local Mac + Docker]** — 完了
  - **14.1 イメージのロックを記録し、1 試行を最後まで実行する [local Mac + Docker]** — 完了
    - pull なし: `opencfd/openfoam-default:2412` が Mac にあることを確認する。なければ**止めて報告**する。pull も代替もしない（要件 7.4）。`docker image inspect` から `wind-tunnel/model/image-lock.toml`（arm64 ビルドのダイジェストとイメージ ID）を書く。何も作り上げない。
    - レイノルズ数 150 の円柱の 1 試行を `WindAdapter` で走らせ、実時間を報告する。タスク 5.1 が挙げた綴りとオプション（関数オブジェクトの時間窓、サンプラーの配置、コンテナ内のユーザー ID）と、初期のメッシュサイズ、`initial_delta_t` を確認する。詳細が確認できない、1 回の実行が 140 s を超える、または 6 回が 900 s に収まらないなら、**止めて報告**する（S4、S5）。
    - 確認方法: 実行が落ち着く。計測が `check_result` を通る。シートが画像チェックを通る。報告が時間と、確認・変更したものを挙げる（ここでの変更は、円柱チェックの前なので許される）。
    - _要件: 7.1, 7.3, 8.7, 11.4_
  - **14.2 円柱チェックを実行する [local Mac + Docker]** — 完了
    - `wind-tunnel-circle-check` を走らせる。`wind-tunnel/circle-check.json` が書かれる。測定したストローハル数が文献値の 5% 以内なら通る（要件 15.3）。実行の前に、`circle_check.py` の文献の定数と出典が要件 15.4 と等しいことを確認する。出典または適合範囲が読めない・確認できない、またはレイノルズ数 100 がその外にあると示唆するものがあれば、**止めて報告**する。論文が与えない範囲を README に述べない。
    - チェックが失敗したら、その差を**止めて報告**する。通すために許容誤差、文献値、メッシュ、設定を変えない（要件 15.7）。
    - 確認方法: `circle-check.json` が `passed = true` で、15.5 の全項目を持ち、値が実行から来ている。
    - _要件: 15.1-15.5, 15.7_
  - **14.3 同じ入力 2 回のチェックを実行する [local Mac + Docker]** — 完了
    - 低速のテストを書いて走らせる: 1 つの入力の 2 回の実行が、同一の計測と同一の画像を与える（要件 10.4）。違えば**止めて報告**する。主張を弱めない。
    - 確認方法: 低速のテストが通る。
    - _要件: 10.3, 10.4_
  - **14.4 端のコーナーと端に近いケースを実行し、色の上限を固定する [local Mac + Docker]** — 完了
    - 低速のテストを書き、32 のケースを 1 つずつ扱う: 4 つのノブの 16 の端のコーナーの組み合わせと、16 の端に近いケース（各ノブを端から範囲の 0.001 と 0.01 の所に、ほかの 3 つは範囲の真ん中）。値は宣言された範囲から計算する（`angle` は [0, 15]、Decision 34）。`check_inputs` が拒否するケース（コーナーのルール、要件 6.11）は、メッセージつきで `refused` と記録し、実行しない。ケースから `wind-tunnel/extreme-runs.json`（ノブの値、結果、実時間または拒否メッセージ）を書く。
    - **止めて確認:** 拒否されなかった実行のどれかがタイムアウトする、メッシュにできない、失敗する、落ち着かない、または 115 s を超えるなら、ノブの値、結果、時間を、要件 17.6 の選択肢つきで、ユーザーに（日本語で）**止めて報告**する。範囲、時間上限、`min_arc`、`min_line`、設定を変えず、先へ進まない。
    - 拒否されなかった実行のすべてが 115 s 以内に落ち着いたときだけ: 固定の規則（これら 32 のうち落ち着いた実行について、6 フレームでの渦度の絶対値の実行ごとの 99 パーセンタイルの最大値を、整数に切り上げる。設計の Decision 24）で `constants.toml` の `vorticity_limit` を設定し、固定する（要件 9.5）。
    - 確認方法: `extreme-runs.json` が実行から来た 32 のケースを挙げ、どの実行も 115 s 以内に落ち着いた。上限がデータから設定された。
    - _要件: 9.5, 17.2, 17.6_
  - **14.5 本物のシートでシート読み取りチェックを行う [local Mac + Docker + Kiro CLI]** — 完了
    - 円柱（`aspect` 1、`corner` 1、`splitter` 0、`angle` 0）の試行を、固定した色の上限で `WindAdapter` から 1 回走らせ、返った PNG を `bench-run/fake/lab/pictures/real-sheet.png`（git 管理外）に書く。`bench.pictures.check_picture` を通ること、設定のサイズであることを確認する。
    - タスク 7.1 と同じように偽ラボのエージェントを走らせ、質問は 1 つ: 各セルを読む順に、渦はどこにあるか、セルの間でパターンは変わるか。質問は、渦がどう見えるか、何を期待するかを言わない。
    - 質問、答え、シートのサイズと SHA-256、日付を `spikes/sheet/results.md`（追跡、名前を指定して）に、記録した観察として追記する。答えは正解と照らして判定しない。
    - **止めて確認:** エージェントがシートを説明できない（セルが 0 または 1 つと報告する、または画像が見えないとだけ報告する）なら、答えをユーザーに（日本語で）**止めて報告**する。画像の形式、配置、サイズは変えない。
    - 確認方法: `spikes/sheet/results.md` に本物のシートの答えがあり、エージェントがセルを説明した。
    - _要件: 9.10_

- **15. README の事実** — 完了
  - **15.1 `wind-tunnel/README.md` を書き、`numbers.md`（コード量）を埋める** — 完了
    - `count_lines.py` を走らせてコード量を埋める。README は記録されたファイルだけから書く: アプリケーションがどう計測するか（`measured_by` と同じ意味）、予算とモードのコスト（要件 11.3）、タスク 14.1 からの 1 回の実行と 1 回の実験の時間（900 s に収まる）、決定性の限界（要件 10.3）、`circle-check.json` からの円柱チェックの値と差、`extreme-runs.json` からの極端な実行の結果、画像の形（時間順の 6 フレームの PNG シート 1 枚で、2 行 3 列、振動しないボディはほぼ同じセルになる。要件 9.11）、`spikes/sheet/results.md` に記録されたシート読み取りチェックの結果、レビュー一覧が保証ではなくレビューであるという記述（要件 12.4）、インストールとセッションの始め方（`body-lab/README.md` のとおり: `uv tool install --editable './bench[frontend]' --with-editable ./wind-tunnel/adapter --reinstall`、`bench-make-lab`、`bench-new-session`）、そしてユーザーが報告するまで接続時間は `<not yet measured>`。ルートの `README.md` は編集しない。
    - 確認方法: README のすべての数が追跡されている結果ファイルにある。`bench-scan` は要らない（`lab/` にない）が、ソルバーの識別子を `lab/` にコピーしない。
    - _要件: 4.7, 9.10, 9.11, 10.3, 11.4, 12.4, 15.6, 16.2, 16.4, 17.4_

- **16. チェックポイント — Stop and ask（止めて確認）** — 完了
  - `model/`、`adapter/`、`bench/` のチェック（低速でないテストと ruff）、`wind-tunnel/lab` と、書き出した伝えるテキスト（`wind-tunnel-told-set --out` でリポジトリ外の一時ファイルへ）への `bench-scan`、`sh scripts/ja-check.sh` を走らせる。`form-knowledge-review.md` が埋まっていて完全であること、`circle-check.json`、`extreme-runs.json`、`spikes/sheet/results.md`（両方のチェック）があること、`docs/status.md` が次の一手を名指していることを確認する。
  - 通ったものと通らなかったものを日本語で報告する。これで「Run All Tasks」が単独でできる部分が終わる。タスク 17-19 はユーザーの手が要る。
  - _要件: 12.3, 13.7, 13.8, 17.1, 17.2_


## Hands-on steps (the user), and the builder step between them

タスク 17 と 19 はユーザーが必要です（要件 18.1、18.3）。タスク 18 はタスク 17 の後に続くビルダーのステップです: ユーザーがタスク 17 の完了を伝えた後に走ります（Decision 39）。サブエージェントは、それより前にはこれらのタスクを実行せず、チェックも付けません。

- **17. ユーザーのステップ: Kiro CLI で 24 回のセッションを始めて終える** — 未着手
  - ユーザーが自分で行い、画面を録画する（Decision 39）。Mac で: コマンドをインストールし、`bench-new-session` でセッションを作り（アプリケーション `wind-tunnel`、アダプター `wind_tunnel.adapter:WindAdapter`、シードとセッション ID はユーザーが選ぶ）、2 つの変数を export し、`wind-tunnel/lab/` から `kiro-cli chat --agent dr-kiro` で Dr. Kiro を起動する（手順は `wind-tunnel/README.md`）。`Begin the session.` と入力する。ターンが早く終わったら `Continue the session.`。合格: セッションが予算を使い切って（24 回）終わる、または Dr. Kiro 自身の `end_session` で終わる。
  - _要件: 17.3, 18.1_

- **18. ビルダーのステップ（タスク 17 の後）: セッションの封印の確認とコミット** — 未着手
  - ユーザーがタスク 17 の完了を伝えた後にだけ走らせる。`bench-verify sessions/wind-tunnel/<session-id>` と、`wind-tunnel/lab` および封印済みフォルダーへの `bench-scan` を走らせる。両方が通ったときだけ、`sessions/wind-tunnel/<session-id>/` を、作った環境で（`handoff.md`）名前を指定してコミットする。どちらかに失敗した記録はコミットしない（要件 17.5）。
  - _要件: 17.3, 17.5, 18.1_

- **19. ユーザーのステップ: 接続時間を報告する** — 未着手
  - ユーザーが、要件の承認から最初のフルセッションの開始までの実時間をビルダーに伝える。ビルダーは「self-reported by the user」の言葉つきで `wind-tunnel/numbers.md` に記録し、推定しない（要件 16.1）。
  - _要件: 16.1, 18.1_

## After the user steps

- **20. セッションの結果を記録する** — 未着手
  - タスク 17-19 が終わった後にだけ走らせる。`wind-tunnel/README.md` と `wind-tunnel/numbers.md` を、封印されたセッション（ID、24 回、`ended`）、`bench-verify` と `bench-scan` の検証結果、自己申告の接続時間で更新する。brief の「done when」が求めるとおり。`docs/status.md`（日本語）と、変えた spec テキストの訳を更新する。
  - _要件: 16.1, 16.4, 17.3, 17.4_

- **21. 最後のチェックポイント** — 未着手
  - Ensure all tests pass, ask the user if questions arise。`model/`、`adapter/`、`bench/` のチェック。`sessions/wind-tunnel/<session-id>` への `bench-verify` と `bench-scan`。`wind-tunnel/lab` への `bench-scan`。形の知識の一覧が埋まっている。`sh scripts/ja-check.sh` が古い訳なしと報告する。

## Notes

- すべてのタスクが必須で、オプションはありません。
- 各タスクは、それが扱う要件を参照します。プロパティテストは設計の普遍的な性質を検証し、単体テストは例とエッジケースを扱います。
- 波は、同じファイルに書くタスクを分けます。3 つの Docker の波は 1 タスクずつです。Docker の実行は重なってはならないからです（各 3 プロセス、140 s の上限）。

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1", "5.1", "5.3", "6.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4", "4.1", "5.2", "5.4", "6.2", "6.3", "6.4", "6.5", "6.6"] },
    { "id": 4, "tasks": ["6.7", "7.1"] },
    { "id": 5, "tasks": ["7.2"] },
    { "id": 6, "tasks": ["8.1"] },
    { "id": 7, "tasks": ["8.2", "9.1", "9.3", "10.1", "10.2", "11.4", "12.1"] },
    { "id": 8, "tasks": ["8.3", "9.2", "9.4", "11.1"] },
    { "id": 9, "tasks": ["11.2", "11.3", "12.2"] },
    { "id": 10, "tasks": ["12.3"] },
    { "id": 11, "tasks": ["12.4"] },
    { "id": 12, "tasks": ["13.1"] },
    { "id": 13, "tasks": ["13.2"] },
    { "id": 14, "tasks": ["14.1"] },
    { "id": 15, "tasks": ["14.2"] },
    { "id": 16, "tasks": ["14.3"] },
    { "id": 17, "tasks": ["14.4"] },
    { "id": 18, "tasks": ["14.5"] },
    { "id": 19, "tasks": ["15.1"] }
  ]
}
```
