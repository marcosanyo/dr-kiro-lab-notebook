> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/wind-tunnel/requirements.md`](../../../.kiro/specs/wind-tunnel/requirements.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `e69f2b2cc9ae500232f70e4bb05c74bbf0098c7211e7da2b47e981351c385c5d`

# Requirements Document

## Introduction

2 番目のアプリケーションです。OpenFOAM による、ボディのまわりの 2 次元の流れで、数値のノブが 4 つあります。スケルトンが汎用であることを示します。同じベンチ、同じ Dr. Kiro、同じノートブックで、まったく別のシステムを扱います。アダプター契約（`lab-bench` 要件 2）を通じてベンチに接続され、すべてのラボと同じ Dr. Kiro（`dr-kiro`）を使います。

出典: `docs/brief.md` のセクション 1-3 と 4.3、`body-lab/`（最初のアプリケーション。書き方と、Dr. Kiro に何を伝えるかの参考）、`lab-bench`（要件 2、5、7、15、17、設計 4、11、F3）、およびセッションで記録された回答（「Decisions」を参照）です。ステアリングはすべて適用されます。ユーザーはこの要件を、1 つの訂正つきで承認し（Decisions の項目 10）、その後、未解決の質問に「your recommendations are fine」と答えました（Decisions の項目 18-22）。まだ決まっていないことは「Open questions」に挙げます。

この spec の範囲: アダプター、`wind-tunnel/model/` のソルバー設定、`dr-kiro` のコマンドによる `lab/` フォルダーの作成、ソルバーファイル用のブラインドスキャン抽出器、円柱チェック、README 用の数値（接続時間とコード量）、そして 24 回の最初のフルセッション（`sessions/wind-tunnel/` に封印）です。

この要件の形を決める目的は 2 つあります。

- Dr. Kiro は実験だけから流れを知ります。伝えられる内容は、宣言された 1 つの集合です（要件 1）。各ノブが何であるか、各計測が何を意味するかは伝えますが、ノブが流れに何をするかは何も伝えません。後で、このリポジトリのラボと無関係な Kiro が、まったく同じ集合だけを与えられ、実験をせずに、比較用の spec を書きます。
- ユーザーの手が必要な手順がいくつかあります（要件 18）。ビルダーだけで実行できる手順とは分けておきます。

各要件は、どちらの Kiro に関するものかを示します。「ビルダー」はこのリポジトリで働く Kiro、またはベンチを操作する人です。「Dr. Kiro」は実験者のエージェントです。

## Glossary

- **ボディ（Body）**: 流れの中にある形で、ノブで決まります。丸めた長方形と、その後ろの任意の板です。
- **高さ（Height）**: 丸めた長方形の固定の高さです。値は 1 で、長さの単位です。
- **板（Plate）**: 丸めた長方形の後ろに付ける薄い板です。長さはノブ `splitter` です。
- **主流速度（Free-stream speed）**: ボディから遠いところの流れの速さです。値は 1 で、速さの単位です。
- **レイノルズ数（Reynolds number）**: `wind-tunnel/model/` で設定する数で、高さと主流速度に基づきます。通常の試行ではすべて 150 で、ノブではありません。
- **ソルバー設定（Solver setup）**: 流れを計算可能にし、Dr. Kiro には伝えないものすべてです。領域、境界条件、ソルバーとスキームの名前、時間刻み、メッシュ、実行の長さ、平均の窓、およびそれらを保持するファイルと名前です。
- **落ち着いた部分（Settled part）**: 実行のうち、平均の開始時刻から終わりまでの部分で、計測はこの部分で行います。
- **実行（Run）**: ソルバーの 1 回の実行で、1 試行です。
- **落ち着いた実行（Settled run）**: 落ち着いた部分が落ち着き基準（要件 8.3）を満たす実行です。満たさない実行は、失敗ではなく、5 つの計測すべてが `not_settled` の結果です（要件 4.5）。
- **ケースフォルダー（Case folder）**: 1 回の実行のフォルダーで、メッシュ、ソルバーのファイル、出力、サンプリングした渦度が入ります。
- **伝える集合（Told set）**: Dr. Kiro にシステムについて与える情報のすべてで、アダプターの宣言から作る 1 つのテキストです（要件 1）。
- **比較用 Kiro（Comparison Kiro）**: このリポジトリのラボと無関係な Kiro で、伝える集合とまったく同じものだけを与えられ、実験をせずに、比較用の spec を書きます。後で使うもので、ここでは作りません。
- **ノブの文（Knob text）**: 1 つのノブについて伝える定義です（要件 3.2）。`lab-bench` 要件 18 がノブに加える `description` 項目に入れます。ノブが何であるか、どの単位か、範囲の両端が何を意味するか、そのノブを定めるジオメトリの定義（ジオメトリの定義）を述べます。ノブが流れに何をするかは決して述べません。
- **ジオメトリの定義（Geometry definition）**: ノブがボディの形や位置を取り決めとしてどう定めるかの記述です。板の厚さ、板の取り付け方、回転の中心、角度の符号が当たります。ジオメトリの定義は伝えます。形の知識ではありません。
- **形の知識（Form knowledge）**: ボディの形やノブの値が流れや計測にどう影響するかについての、あらゆる記述です。ノブの文は、ジオメトリの定義も含めて、形の知識ではありません。影響を述べた文は形の知識です。
- **隠す集合（Hidden set）**: ソルバーかメッシュに属するため、Dr. Kiro に伝えないものです。ソルバー設定（計算領域、境界条件、時間刻み、実行の長さを含む）とメッシュです。ボディのジオメトリについてのそれ以外はすべて伝えます（Decisions の項目 19）。
- **端に近いケース（Near-end case）**: 1 つのノブを範囲の一方の端から範囲の 0.001 または 0.01 の距離に置き、ほかの 3 つのノブを範囲の真ん中に置く実行です（要件 17.2）。
- **円柱チェック（Circle check）**: レイノルズ数 100 の円柱で計測したストローハル数を、文献と比べる実行です（要件 15）。
- **画像シート（Picture sheet）**: 1 試行の 1 枚の PNG です。固定の時刻の渦度のフレームを、同じ大きさのセルに縮尺し、行に並べたもので、左から右、次に上から下へ、時間順に並びます（要件 9）。`body-lab` の画像と同じ形です。
- **シート読み取りチェック（Sheet reading check）**: Dr. Kiro のファイルツールが画像シートを届け、各セルを読み取れることを、ビルダーが確かめるチェックです。最初は合成のテスト用シートで、後で本物のシートで行います（要件 9.7、9.10）。
- そのほかの用語は `lab-bench` と `body-lab` のとおりです。

---

## Requirements

### Requirement 1: What Dr. Kiro is told

**対象:** Dr. Kiro と、アダプターを書くビルダー。

**User Story:** Dr. Kiro として、入力が流れに何をするかを教えられることなく実験できるように、各入力が何であるか、各計測の意味、見つけるべきものを平易に述べてほしい。ビルダーとして、その記述を 1 つの集合にしたい。比較用 Kiro にまったく同じものを与えられるようにするためである。

#### Acceptance Criteria

1. THE 伝える集合 SHALL be the text of the adapter's declaration as `lab-bench` builds it for Dr. Kiro (`lab-bench` design F3)、and SHALL be built from the adapter's own declaration, with no second copy。
2. THE 伝える集合 SHALL contain exactly: 4 つのノブの名前、その範囲とノブの文（その中のジオメトリの定義を含む。要件 3）、各計測の名前、単位、意味、`strouhal` の未計測結果 `not_shedding`、および 5 つの計測すべての未計測結果 `not_settled` と要件 4.5 の文（要件 4）、流れが 2 次元でありレイノルズ数が 150（高さと主流速度に基づく）であること、画像の種類、予算、ゴール（要件 11）。
3. THE 伝える集合 SHALL NOT contain what any knob does to the flow or to a measurement、隠す集合のいかなる部分（ソルバー設定とメッシュ設定）、画像の内容、および形の知識（要件 12）。
4. THE アダプター SHALL carry each knob text in the `description` field of its knob, which `lab-bench` Requirement 18 adds（ユーザーがこの選択肢を選んだ。Decisions の項目 18）、and the rest of the told set in the fields the declaration already has。THE アダプター SHALL NOT be written before `lab-bench` tasks 23-26 are done。IF a part of the told set cannot be carried in the fields the declaration has、THEN ビルダー SHALL stop and ask the user whether `lab-bench` changes, and SHALL NOT add a second channel through which Dr. Kiro learns about the system。
5. THE ラボのビルダーファイル SHALL add nothing about the system to the told set（`dr-kiro` 要件 1.2）。
6. THE 伝える集合 SHALL pass the blind scan at the builder level（要件 13）。
7. WHEN the told set is to change（たとえば「laminar」や画像の説明を加える場合）、THE ビルダー SHALL change this requirement first, with the user's approval（Decisions の項目 10）。

### Requirement 2: Export of the told set

**対象:** ビルダー。

**User Story:** ビルダーとして、伝える集合を 1 つの文書として取り出したい。比較用 Kiro に、Dr. Kiro に与えるものとまったく同じものを与えるためである。

#### Acceptance Criteria

1. THE アダプターパッケージ SHALL provide a command that writes the told set, produced from the adapter's declaration by the same function the front end uses for the tool descriptions, as one document, to a path the builder gives explicitly。
2. THE 文書 SHALL contain the told set and nothing else: no file name, path, version or session value。
3. WHEN the command is run twice on the same adapter、THE コマンド SHALL write byte-identical documents。
4. THE テスト SHALL check that the document equals the declaration text that the front end puts into the tool descriptions, so that the two cannot drift。

### Requirement 3: Knobs

**対象:** Dr. Kiro（何を操作するか）、ビルダー（アダプターがどう宣言するか）。

**User Story:** Dr. Kiro として、名前の付いた 4 つの数を、それぞれが何であるかの平易な記述つきで設定したい。分かった上でシステムを変化させるためである。

#### Acceptance Criteria

1. THE アダプター SHALL declare exactly four number knobs, with these names and ranges: `aspect` in [0.5, 3]; `corner` in [0, 1]; `splitter` in [0, 3]; `angle` in [0, 15] degrees。brief（`docs/brief.md` セクション 1）は `angle` を [0, 30] としているが、決定 34 のユーザーの決定がこの spec についてそれを上書きする。brief は編集しない。
2. THE アダプター SHALL tell Dr. Kiro, for each knob, its knob text in the `description` of the knob, and nothing else about the knob（要件 1.3）。THE ノブの文 are the following, and a change SHALL be made here first, with the user's approval:
   - `aspect`: "The length of the body, in body heights. The height of the body is 1, so this is the length divided by the height."
   - `corner`: "The rounding of the body's corners: the radius of each corner arc, as a fraction of half of the body's shorter side. 0 gives square corners; 1 gives the largest radius that fits."
   - `splitter`: "The length of the thin plate attached to the back of the body, the end facing away from the oncoming flow, in body heights. The length is counted from the rearmost point of the body without the plate. The plate lies along the line through the middle of the body along its length, is attached with no gap, and is 0.08 body heights thick. 0 means there is no plate."
   - `angle`: "The angle of attack, in degrees: the angle between the body's length direction and the direction of the oncoming flow, which goes in the +x direction. 0 means the two directions are the same. The body is turned about its centre, the middle of its length and of its height, and the plate turns with it. A positive angle moves the front end of the body, the end facing the oncoming flow, toward +y, and the back end toward -y."
   各文は、ノブが何であるかを述べ（ユーザーの言葉: 長さ、角の丸め、ボディの後ろの板の長さ、迎え角）、範囲の両端を定義し、Decisions の項目 19 のジオメトリの定義（板の厚さと取り付け方、回転の中心、角度の符号）を与える。どの文も、ノブが何をするかは述べない。`splitter` の文の数 0.08 は、`wind-tunnel/model/` の板の厚さ（要件 6.3）から文に書き込み、もう一度手で書かない。
3. WHEN the bench passes computed inputs、THE アダプター SHALL accept every combination of values inside the four ranges, ends included, that the corner rule of Requirement 6.11 accepts, and SHALL build the body for it (Requirement 6) or fail with the reason (Requirement 8)。コーナーのルールが拒否する組み合わせは、実行に届かない（要件 6.11）。
4. THE アダプター SHALL NOT clip, round or default a knob value; the bench has already refused values outside a range (`lab-bench` Requirement 4.6)。
5. THE ノブの文 SHALL be reviewed against Requirement 12 in the reviewed list（要件 12.3）、and SHALL pass the blind scan at the builder level, including the check of Requirement 13.8。
6. THE 角度の符号 SHALL be implemented once, in the geometry of `wind-tunnel/model/`（要件 6.4）、and a property test SHALL show that the geometry agrees with the `angle` text: for a positive angle the front end of the body moves toward +y and the back end toward -y。

### Requirement 4: Measurements

**対象:** Dr. Kiro（計測の意味として何を伝えられるか）、ビルダー（アダプターが何を計算するか）。

**User Story:** Dr. Kiro として、各計測を平易な言葉で定義してほしい。計算方法を知らなくても結果を読めるようにするためである。

#### Acceptance Criteria

1. THE アダプター SHALL declare the scalar measurements `cd`, `cl_mean`, `cl_amp`, `strouhal` and `shedding`, each with unit `1`。
2. THE `measured_by` のテキスト SHALL define them in Dr. Kiro's terms, as `body-lab` does for its measurements, and SHALL include at least:
   - 流れは +x 方向に向かい、揚力は +y 方向の力である。
   - 力は奥行き単位あたりで、密度の 2 分の 1 に主流速度の 2 乗と高さを掛けたもので割る。高さはどのノブも変えない固定の長さである。長さは高さを単位とし、速さは主流速度を単位とする。
   - `cd` は抗力係数で、ボディ全体にかかる流れ方向の力であり、落ち着いた部分の平均をとる。
   - `cl_mean` は、落ち着いた部分での揚力係数の平均である。
   - `cl_amp` は、落ち着いた部分での揚力係数の最大と最小の差の半分（ピークツーピーク値の半分）である。
   - `strouhal` は、揚力係数の振動の周波数に高さを掛け、主流速度で割ったものである。
   - `shedding` は、`cl_amp` が 0.01 を超えるとき 1、そうでないとき 0 である。
3. THE しきい値 0.01 SHALL be told, because it is part of the definition of `shedding` and not part of the solver setup。THE 平均の開始時刻、実行の長さ、およびソルバー設定のそのほかの数 SHALL NOT be told; the text says only "the settled part of the trial"。
4. THE アダプター SHALL declare for `strouhal` one not-measured outcome, named `not_shedding`, and SHALL return it, with the reason "the lift does not oscillate: cl_amp is not above 0.01", WHEN `shedding` is 0。THE アダプター SHALL NOT fill in a value of `strouhal` in that case (`lab-bench` Requirements 2.4 and 2.5)。
5. THE アダプター SHALL declare the not-measured outcome `not_settled` for all five measurements (`strouhal` has `not_shedding` as well), and SHALL return it for all five at once, with the one fixed reason "the flow had not settled within the trial", WHEN the settled part of the run does not meet the settle criterion (Requirement 8.3)。その実行は結果である: 予算の 1 試行を使い、記録が書かれ、画像シートが返され、それは落ち着いた実行と同じコードで作られる（要件 9）。THE reason SHALL hold no number of the settle criterion。`cd`、`cl_mean`、`cl_amp`、`shedding` の未計測結果は、これ以外の場合には返さない: ほかの理由でそれらを出せない実行は失敗である（要件 8）。決定 37。
   - `not_settled` の計測についての予測は、ベンチが `not-checkable`（確認不能）と判定する（`lab-bench` Requirement 7.7）。的中でも外れでもない。
   - THE `measured_by` の文 SHALL say, in Dr. Kiro's terms and without a number of the settle criterion, that when the flow has not settled within the trial the five measurements are not measured (outcome `not_settled`) and the picture is still returned, and that this says nothing about whether a longer trial would settle。The words "within the trial" SHALL be in the text。THE 文 SHALL say nothing about what the picture shows (Requirement 1.3)。（ユーザーは、画像が返されると述べる決定 37 を承認した。この文の最初の言い方は、画像が "still shows the flow" と述べており、これは画像の内容を伝えるもので、承認されていなかった。決定 40 で訂正した。）
6. THE 基準長 SHALL be the height (1) and the free-stream speed SHALL be 1, so that the coefficients and the Strouhal number need no other reference。
7. THE 各計測の意味 SHALL be the same in the `measured_by` text, in `wind-tunnel/README.md`, and in the code; a change SHALL be made in all three。

### Requirement 5: Accuracy of the estimators

**対象:** ビルダー。

**User Story:** ビルダーとして、ストローハル数と振幅を 5% の違いを見分けられる精度で推定したい。円柱チェックと Dr. Kiro の結果に意味を持たせるためである。

#### Acceptance Criteria

1. THE アダプター SHALL compute `cd`, `cl_mean`, `cl_amp`, `strouhal` and `shedding` in pure functions of the force time series of the settled part, with no access to the solver。
2. THE `strouhal` の推定器 SHALL resolve the frequency to better than the 5% of the circle check。A plain Fourier transform over the settled part resolves only about 0.014 in Strouhal number, about 8% of 0.17, so it SHALL NOT be used without a refinement。THE 設計 SHALL choose the method。
3. FOR ALL synthetic lift signals that are a sinusoid of known Strouhal number, in a range the design states and justifies, with any mean, any amplitude above 0.01 and the length and sampling interval of a settled part、THE `strouhal` の推定器 SHALL return a value within 1% of the known value。
4. FOR ALL synthetic lift signals that are a sinusoid with a known amplitude and mean、THE `cl_amp` estimator SHALL return a value within 1% of the known amplitude (absolute 1e-6 when the amplitude is 0)、AND THE `cl_mean` estimator SHALL return a value within 1% of the known mean plus amplitude / (pi * f * T)、ここで f は信号の周波数、T は落ち着いた部分の長さである（振幅が 0 で平均が 0 のとき絶対値 1e-6）。追加の項は、端数の周期が残ることで生じる最大のずれである。平均は周期の整数個ではなく落ち着いた部分全体で取るため。
5. FOR ALL synthetic signals、THE `shedding` の値 SHALL be 1 exactly when the estimated `cl_amp` is above 0.01。
6. THE 推定器 SHALL give the same result for the same series (no randomness)。

### Requirement 6: The body and the flow, in `model/`

**対象:** ビルダー。Dr. Kiro に伝えるのは 6.5 のジオメトリの定義だけで、残りは伝えない（要件 1.3）。

**User Story:** ビルダーとして、ボディと流れを 1 か所に固定したい。Dr. Kiro が 1 つのシステムを調べることになり、ソルバーの値が `lab/` フォルダーに届かないようにするためである。

#### Acceptance Criteria

1. THE ボディ SHALL be a rounded rectangle of height 1 and length `aspect`, centred on the origin of its own frame。
2. THE 角 SHALL be rounded with a radius of `corner` times half of the shorter side of the rectangle, that is `corner` times min(1, `aspect`) divided by 2（プロトタイプの定義で、ユーザーが承認済み）。`aspect` が 1 以上では、これは `corner` かける半高さに等しいので、`corner` = 1 で両端は半円になり、`aspect` = 1 では円になる。円柱チェックはこれを必要とする。`aspect` が 1 未満では、半高さに対する割合だと長さの半分を超えて形が成り立たなくなる。「短い辺の半分」は [0.5, 3] のすべてで定義される。
3. WHERE `splitter` is above 0、THE ボディ SHALL have a plate of thickness 0.08 and a length of `splitter` heights beyond the rearmost point of the rounded rectangle, on the line through the middle of the rectangle along its length, joined to the rectangle with no gap。WHERE `splitter` is 0、THE ボディ SHALL have no plate。
4. THE ボディ、板を含めて、SHALL be rotated by `angle` degrees about the centre of the rectangle, in the sense that a positive angle moves the front end of the body (the end facing the oncoming flow, at -x before the turn) toward +y and the back end toward -y。これは +x が右、+y が上を向くとき時計回りの回転である。この向きはプロトタイプと同じで、ユーザーが確認済み（Decisions の項目 19）。
5. THE 板の厚さ（0.08）、板の取り付け方、回転の中心、正の角度の向き SHALL be written in `wind-tunnel/model/` and SHALL be told to Dr. Kiro, as the geometry definitions in the knob texts（要件 3.2）。ボディのジオメトリのそれ以外の固定値は SHALL NOT exist。IF the builder adds one、THEN ビルダー SHALL tell it in a knob text, with the user's approval of the changed text（要件 1.7）, or ask the user。
6. THE 流れ SHALL be laminar, two-dimensional, at Reynolds number 150 for every normal trial, with the free-stream speed 1 and the height 1。
7. THE レイノルズ数 SHALL be a builder-side parameter of the model in `wind-tunnel/model/`。It SHALL NOT be a knob, SHALL NOT be reachable from any `lab/` folder or from any input of a trial, and SHALL be set to a value other than 150 only by the circle check (Requirement 15)。
8. THE ソルバー設定 SHALL start from the values that worked in the prototype (`docs/brief.md` section 4.3): OpenFOAM v2412 `pimpleFoam`; mesh from Gmsh; laminar; domain with the inlet 6 heights ahead of the body, the outlet 18 behind, and the walls 7 above and below; run to time 150; forces averaged from time 80; frames taken near the end; an adaptive time step with a Courant limit of 0.8。THE 設計 SHALL decide what to keep and SHALL say what it changes and why; THE ビルダー SHALL ask the user before a change that alters the circle check。
9. THE ソルバー設定 SHALL live only in `wind-tunnel/model/`, as files the builder writes。No value of it SHALL be written into the adapter code as a second copy; the adapter reads `model/`。
10. IF the geometry for a combination of knob values is invalid (a self-intersecting outline, a mesh that cannot be made)、THEN the run SHALL be a bench failure with the reason (Requirement 8), and the builder SHALL report the combination to the user。
11. THE アダプター SHALL refuse, before any run, a value of `corner` that gives a corner arc or a straight side of the body that is too short, and SHALL implement the refusal once, in `wind-tunnel/model/` (`input_rule.py`), through the optional `check_inputs` hook of `lab-bench` (要件 19)。`h` = min(1, `aspect`)、`c` = `corner` とすると、1 つのコーナーの弧の長さは (pi / 4) x `h` x `c`、ボディの最も短い直線の辺の長さは `h` x (1 - `c`) である。`corner` がちょうど 0 またはちょうど 1 のときは SHALL be accepted: 長さ 0 の部分は短いのではなく、存在しない。それ以外の `corner` は、弧が `min_arc` = 0.0314 以上で、かつ直線の辺が `min_line` = 0.0025 以上のときだけ SHALL be accepted（どちらも `constants.toml` の設定）。2 つの限界は、ボディのコーナーの弧と直線の辺にだけ適用し、板（`splitter`）やほかのノブには NEVER 適用しない。THE refusal message SHALL be one line in Dr. Kiro's terms (knob names and values only; no solver, mesh, piece, file or time) and SHALL say which values of `corner` are accepted for the given `aspect`, in the form "corner must be 0, 1, or between <lo> and <hi> when aspect is <a>"、ここで `lo` は下限を切り上げ、`hi` は上限を 3 桁に切り捨てた値で、伝える範囲がルールの許す範囲より広くならないようにする。THE adapter SHALL accept or refuse by that band, so that what is told is what is tested。THE check SHALL be a pure function of the inputs, SHALL be called by the bench for every trial of an experiment before any trial runs, and a refused combination SHALL use no budget。ジオメトリ（要件 6.1-6.4）は、短いという理由で部分を拒否しては SHALL NOT; a refused `corner` that nevertheless reaches `run_trial` SHALL raise (a bench failure), never run。理由とデータ: 決定 35。

### Requirement 7: The solver environment

**対象:** ビルダー。

**User Story:** ビルダーとして、ソルバーを固定した 1 つのイメージで実行し、メッシュをロックされたパッケージで作りたい。結果を再現でき、誤った環境が黙って使われることがないようにするためである。

#### Acceptance Criteria

1. THE アダプター SHALL run the solver only in the Docker image `opencfd/openfoam-default:2412`, pinned by digest。The tag is the one in the brief; THE ダイジェスト SHALL be recorded in `wind-tunnel/model/` at build time and SHALL be the digest of the image for the platform the builder's Mac uses (Apple Silicon, arm64, as in the prototype)。
2. THE アダプター SHALL make the mesh with Gmsh as a Python package from the adapter's own `uv` project, on the host, locked in `uv.lock` (`tech.md`)。
3. WHEN the adapter is created for a session, and before any trial、THE アダプター SHALL check that Docker is reachable and that the image is present with the recorded digest。
4. IF Docker is not reachable, or the image is missing, or its digest does not equal the recorded digest、THEN the adapter SHALL fail, saying which of the three it is, what was expected and what was found, and SHALL NOT pull, substitute another image or tag, or continue。
5. THE アダプター SHALL record the image digest and the Gmsh version on the builder side for every session。THE 宣言の `measured_by` SHALL NOT carry them, because Dr. Kiro is not told them; THE 設計 SHALL decide where the record is kept, and no text in the sealed session record SHALL fail the blind scan because of it。
6. THE アダプター SHALL need Docker only for the solver。`body-lab` and the bench SHALL NOT need Docker。
7. AFTER the checks of 7.3 and the CPU check, and before any trial, THE アダプター SHALL run a case mount probe: three times, with a fresh folder name each time, it SHALL render a small throw-away case folder in the case base, start one container with the same image, user mapping and mount as the runner, with the command `test -x /case/Allrun`, expect exit code 0, and move the folder to the trash。IF a probe does not exit 0、THEN the adapter SHALL fail with `EnvironmentFailure` named `case mount probe`, giving the expected result and the found output, and SHALL NOT retry or continue。プローブはソルバーを必要とせず、数秒かかる。失敗はビルダー側にだけ示される: Dr. Kiro が何かを見る前の、起動時にベンチサーバーを止める。決定 38。

### Requirement 8: Failures, settling and time limits

**対象:** ビルダー（何が失敗か）、Dr. Kiro（何が見えるか）。

**User Story:** ビルダーとして、失敗した実行は理由とともにセッションを止め、流れが落ち着かなかった実行は数を 1 つも含まない結果にしたい。作り物の値は決して出さない。記録のすべての数が、落ち着いた実行から来ていることを保証するためである。

#### Acceptance Criteria

1. IF a run ends with a non-finite value in any force, a diverged solution, an abnormal exit of the solver or the mesher, a missing or unreadable output, or the time limit of 8.7、THEN the adapter SHALL return a trial failure (`lab-bench` design 4), and the bench failure rules apply (`lab-bench` Requirement 2.7 and 11.3): the session stops。落ち着かない実行（8.3）はこの一覧に含まれない: それは要件 4.5 の結果である。
2. THE アダプター SHALL NOT retry a failed run, change the time step, the mesh or the method, fill in a value, or return a partial result。
3. A run SHALL count as settled WHEN, for the first and the second half of the settled part: the means of the drag coefficient differ by no more than 2% of the mean over the whole part; the values of `cl_amp` differ by no more than the larger of 10% of the value over the whole part and 0.002; and, WHEN `shedding` is 1, the settled part holds at least 5 full periods of the lift oscillation。A run for which this does not hold SHALL give the result of Requirement 4.5, not a failure。破れたルールは Dr. Kiro には伝えない。（結果にはそれを置く場所がないので、記録もしない。）
4. THE 試行失敗の `public_reason` SHALL be one of a fixed small set of plain statements in Dr. Kiro's terms, that is "the trial could not be completed" and "the trial took too long", and SHALL contain no solver, mesh, file, path, version or log text。THE `detail` SHALL hold the cause, the case folder and the solver's own message, and goes to the builder-side log only (`rules.md`, Blind)。
5. THE 失敗の `public_reason` SHALL NOT state which knob values caused it (Requirement 12)。
6. THE アダプター SHALL write nothing about a failure into any `lab/` folder。
7. THE wall-clock limit of one run SHALL be 140 s。上限が含むのは、メッシュの作成、ソルバー、ソルバーの後の作業（解析、推定器、落ち着き基準、渦度の解析、画像）で、画像まで含む。その部分のどこで超えても、実行は SHALL be a time-out。成功した実行のケースフォルダーの削除は含まず、それは実行の外で行う（要件 10.6）。The prototype's run took about 1.5 minutes (90 s) on 3 processes。One experiment has at most 6 runs (`lab-bench` Requirement 5.1), and the front end's longest tested call is 900 s (`lab-bench` Requirement 17.18), so 6 times 140 s is 840 s, inside the call。IF the design's measured run time makes 140 s too short, or makes 6 runs not fit in 900 s、THEN the builder SHALL stop and ask the user。The adapter SHALL NOT start runs in parallel on its own to make the call fit。
8. THE 時間の上限 SHALL be a bench failure (8.1), not a not-measured outcome。

### Requirement 9: The picture

**対象:** Dr. Kiro（画像を開く）、ビルダー（作り方と確認）。

**User Story:** Dr. Kiro として、流れがどう発展するかを、読み取れる 1 枚の画像で見たい。ノートブックの読者として、流れを時間順に示す画像がほしい。

#### Acceptance Criteria

1. THE アダプター SHALL 試行ごとにちょうど 1 枚の画像、すなわち画像シートを返す: 1 枚の PNG（`image/png`）で、流れの渦度のフレームを同じ大きさのセルに縮尺して行に並べたもの。色スケールはすべての試行で同じで、2 つの試行を目で比べられる。これは `body-lab` の画像の形である。（以前のアニメーション GIF はやめた: GIF 読み取りチェックが失敗した。`spikes/gif/results.md`、Decisions の項目 23。）
2. THE 画像 SHALL ボディとその近い後流を示し、軸、目盛り、ラベル、凡例、文字、メタデータを持たず、表示装置なしで作られ、`bench.pictures.encode_png` で符号化され、ベンチの画像チェックを通る（`lab-bench` 設計 4、要件 15.9）。
3. THE フレーム SHALL 固定の間隔で、実行の終わりで終わるように、落ち着いた部分から取られ、時間順に、左から右、次に上から下へ並べられる。
4. **提案、ユーザーは設計の承認時に確認する（Decisions の項目 24）:** THE シート SHALL 6 フレームを 2 行 3 列に持つ。各セルは 400 x 200 ピクセル。隣り合うセルは、色スケールにない固定の 1 色の 4 ピクセルの隙間で区切られ、外側のセルの外には隙間がない。したがってシートは 1208 x 404 ピクセルである。フレームの時刻は 145、146、…、150（間隔 1.0 時間単位、最後のフレームは実行の終わり）。フレーム数、配置、セルの大きさ、隙間、間隔は `wind-tunnel/model/constants.toml` の設定で、設定の読み込み時にまとめて検査される（フレーム数が行数 x 列数に等しいこと、最初のフレームの時刻が平均の開始時刻より前でないこと）。最初のセッションの後に値を変えることは、この要件の変更である。
5. THE 色スケールの固定の限界値 SHALL `wind-tunnel/model/` に書かれ、`lab/` には書かれない。
6. THE 画像 SHALL NOT be described to Dr. Kiro beyond its kind（要件 1.2）。ベンチは伝える行を宣言された種類から作る（"one picture (png file)"）。この spec は画像の順序や内容についての文を加えない。`lab-bench` は変わらないからである（Decisions の項目 23）。
7. **前提条件、ビルダーが実行する:** BEFORE the wind-tunnel adapter is written、THE ビルダー SHALL 合成のテスト用シートでシート読み取りチェックを行う: 2 行 3 列の 6 セルの PNG で、各セルに固有の背景色、固有の位置の点、数字がある。`spikes/sheet/` のスクリプトがテスト用の入力として作る（結果ではなく、そう明記する）。ビルダーは偽ラボのエージェントを `bench-run/fake/lab` で `kiro-cli chat --no-interactive` により起動し、読む順に各セルの色、点の位置、数字を報告させ、質問、答え、判定を git で追跡される `spikes/sheet/results.md` に記録する。6 セルすべてが正しく報告されたとき合格である。
8. IF 合成シートのシート読み取りチェックが失敗する、THEN THE ビルダー SHALL 止まってユーザーに確認し、画像の形式や配置を自分で切り替えない（`rules.md`、フェイルファスト）。
9. THE 後の `tasks.md` の、アダプターのコードを書く最初のタスク SHALL 9.7 の結果を読み、ないとき、追跡されていないとき、失敗のとき止まるゲートである。
10. WHEN 画像のレンダラーができた、THE ビルダー SHALL 本物のシート（円柱チェックまたは最初の試行から）でシート読み取りチェックを行い、各セルのどこに渦があるか、セルの間でパターンが変わるかをエージェントに尋ね、質問と答えを `spikes/sheet/results.md` に記録する。答えは記録するだけで、隠れた正解と照らして判定しない。IF エージェントがシートを説明できない（たとえばセルが 0 または 1 つと報告する）、THEN THE ビルダー SHALL 止まってユーザーに確認し、画像の形式や配置を自分で切り替えない。
11. THE README SHALL 振動しないボディではシートのセルがほぼ同じになると述べ、振動するボディのセルがどう見えるかは述べない。

### Requirement 10: Determinism and case folders

**対象:** ビルダー。

**User Story:** ビルダーとして、同じマシンでは同じ入力から同じ結果を得たい。失敗した実行のファイルは、ビルダーだけのために残したい。

#### Acceptance Criteria

1. THE ソルバー SHALL run with a domain decomposition of 3 processes, with a fixed method and fixed counts written in `wind-tunnel/model/`, never chosen from the number of processors on the machine。
2. THE アダプター SHALL NOT use the trial seed (`lab-bench` Requirement 2.9); the same computed inputs SHALL give the same measurements and the same picture。
3. THE 保証 SHALL be: the same Mac, the same image digest and the same Gmsh version, with the same computed inputs, give identical measurements and an identical picture。THE アダプター SHALL NOT claim reproducibility across machines, other chips or other image builds。THIS limit SHALL be written in `wind-tunnel/README.md`。
4. THE テスト SHALL check, in a slow local test (Requirement 17), that two runs of one input give identical measurements and an identical picture。IF they differ、THEN the builder SHALL stop and ask the user, and SHALL NOT weaken the statement without asking。
5. THE アダプター SHALL make each case folder under `bench-run/` (git-ignored), with a name that identifies the session and the trial and never a `lab/` folder。
6. WHEN a run succeeds、THE アダプター SHALL move its case folder at once into a trash folder inside `bench-run/` and SHALL delete the trash before the next run starts its clock（Decisions の項目 32）。IF the trash cannot be deleted、THEN the adapter SHALL raise and SHALL NOT continue。THE ソルバー SHALL write only what the adapter reads (the force file and the sampled vorticity)。そのためケースフォルダーは最初の実行の 5 GB よりずっと小さい（Decisions の項目 33）。WHEN a run fails、THE アダプター SHALL keep the case folder, for the builder only, and SHALL name it in the `detail` of the failure。THE kept folder SHALL hold only the solver log, the settings (the text files of `system/`, `constant/` and `0/`, without `polyMesh`), the mesh file and the force file; everything else SHALL be deleted（Decisions の項目 31）。IF the folder cannot be pruned、THEN the adapter SHALL raise and SHALL NOT continue。

### Requirement 11: Goal, budget and modes

**対象:** Dr. Kiro。

**User Story:** Dr. Kiro として、最良の点が何を意味し、試行がいくつあるかを知りたい。計画を立てるためである。

#### Acceptance Criteria

1. THE アダプター SHALL declare a budget of 24 trials (`docs/brief.md` section 1)。
2. THE アダプター SHALL declare the goal: "Find the setting of the four knobs with the lowest cd among the settings where shedding is 0."。The prototype ran two stages, first the shapes with a small lift oscillation, then among them the one with the lowest drag; this sentence is that task in the told measurements。It names only `cd` and `shedding`, which the told set defines (Requirement 4), and no form knowledge。THE 提案した目的の後半「write the rules that explain what you find」は、すでにエージェントのプロンプトにあり（`dr-kiro` 要件 2.2）、ゴールは最良の点が最小化する計測を名指す 1 文なので（`lab-bench` 要件 2.1）、ゴールには繰り返さない。The wording is written in the same form as body-lab's goal, which names the measurement to maximise。
3. THE アダプター SHALL accept both bench modes without change (`lab-bench` Requirement 5): `compare` costs 1, 2 or 3 trials (one per variant), and `sweep` costs exactly 6 (`lab-bench` Requirement 5.4)。So the budget of 24 allows, for example, at most 4 sweeps, or 24 single-variant compares, or any mix whose trials add up to 24。
4. THE 予算、モードごとのコスト、1 回の実行の時間 SHALL be given in `wind-tunnel/README.md`, and THE 1 回の実験の時間 SHALL fit the call limit (Requirement 8.7)。

### Requirement 12: No form knowledge in lab text

**対象:** ビルダー。Dr. Kiro が自分で見つけるべきものを守る。

**User Story:** ビルダーとして、Dr. Kiro が読むものの中に、形が流れにどう影響するかを述べたものが一切ないようにしたい。発見した spec のすべての規則が、Dr. Kiro 自身の実験から来るようにするためである。

#### Acceptance Criteria

1. NO sentence in a `lab/` folder (the agent, its steering, the templates, the examples), in a bench message about the system, in the told set, in a failure's `public_reason`, or in the picture SHALL state or imply how the body's shape or a knob value affects the flow or a measurement。This includes, as examples only, any statement that a part of the body changes whether the flow sheds, that rounding changes the drag, or that a long body behaves in a certain way。THE ノブの文（要件 3.2）はノブが何であるかを述べるもので、形の知識ではない。ノブが何をするかを述べた文は、どこにあっても形の知識である。
2. THE `dr-kiro` の共有ビルダーファイル are written for every application and SHALL stay as they are; THE それらの例 SHALL stay placeholders (`dr-kiro` Requirement 3.6)。
3. THE ブラインドスキャン covers terms and paths only and SHALL NOT be taken as a check of this requirement。THE チェック SHALL be a **reviewed list**: a builder-side checklist, in a file under `wind-tunnel/` that is not in `lab/`, naming every text Dr. Kiro can read (each file of `lab/` that the builder wrote, the told set including each knob text, each `public_reason`), with a line per text saying "reviewed, no form knowledge" and who reviewed it。THE ビルダー SHALL fill it by reading, and the user MAY check it。THE レビュー済み一覧 SHALL also carry a line saying that the body-lab told text (the declaration sentences, `measured_by`, the errors) is reviewed by a person for sentences that name the engine, a library or a version, including sentences filled in at run time。これには自動チェックを加えない。
4. THE チェックリスト is a review step in the later tasks。It is not automated and it is not a guarantee; THE README SHALL say so。
5. ジオメトリの定義（板の厚さと取り付け方、回転の中心、正の角度の向き）は、ボディがどう作られ、どう置かれるかを述べるもので、流れが何をするかを述べるものではないので、形の知識ではない。THE レビュー済みの一覧（要件 12.3）SHALL carry, for each knob text, a line that says which sentences are geometry definitions, and SHALL record that no sentence states an effect。定義と影響が混じる文（たとえば、定義の後に何を「減らす」「増やす」かが続くもの）は SHALL be split, and the effect removed。
6. THE この spec の要件と設計 SHALL NOT be copied into any lab text。WHERE a statement of this spec is needed in a lab text、THE ビルダー SHALL write it again from the told set, so that no form knowledge comes with it。

### Requirement 13: Blind scan for the solver files

**対象:** ビルダー。

**User Story:** ビルダーとして、ブラインドスキャンがソルバー設定とボディ自身の名前を対象にしてほしい。`lab/` フォルダーやベンチの出力に、ソルバーを明かすものがないようにするためである。

#### Acceptance Criteria

1. THE ベンチ SHALL provide a blind scan extractor for the solver files in `wind-tunnel/model/`, as `lab-bench` design 11.1 anticipates。It SHALL derive terms from: the keywords and the names (patches, fields, schemes, solvers, function objects, regions) in the OpenFOAM dictionaries and templates; the names in the mesh and geometry script; the digest-pinned image name; and the file names and stems of the source files。THE `python-names` extractor SHALL take only the names of functions, classes and module-level constants, and no string literal。EVERY extractor SHALL drop the Python reserved words (`keyword.kwlist`, `keyword.softkwlist`), the Python built-in names (`dir(builtins)`) and names of one character, and SHALL apply no other filter（Decisions の項目 29）。
2. IF the extractor cannot read or parse a solver file、THEN it SHALL fail, naming the file and the problem, and SHALL NOT skip the file (`lab-bench` Requirement 15.7)。
3. THE ブラインドスキャン SHALL remove the adapter's declared names (the four knob names, the five measurement names and the not-measured outcome names) and the stop list, and nothing else (`lab-bench` Requirement 15.3)。伝える集合の語は、ノブの文も含めて、除去されない: ノブの文は意図して伝えるものだが、スキャンはほかのビルダーレベルのテキストと同じに扱う。したがって、ノブが何であるかを伝えても、ソルバーやメッシュの識別子は開かれない。ソルバーファイルとメッシュスクリプトから導かれた語は、ノブの文にも、伝える集合のほかの部分にも、ほかのすべてのビルダーレベルのテキストにも、禁止のままである。
4. IF an ordinary word that the extractor derives, such as a general name for a physical quantity, makes the scan fail on text that says nothing about the solver、THEN ビルダー SHALL first rename the identifier it chose itself, if the word is one, then reword the text, and SHALL ask the user before it changes the told set（要件 1.7）or proposes a stop-list entry, and SHALL NOT add the word itself (`rules.md`, Blind scan)。This SHALL be raised as a question to the user and not settled by the builder。ユーザーはこの順序を受け入れた（Decisions の項目 20）。
5. `wind-tunnel/adapter/scan_sources.toml` SHALL name the solver files and the geometry script with their extractors, and the lab's layout, so that `bench-scan` covers the lab and every bench output。
6. THE スキャン SHALL cover the picture by the picture check (`lab-bench` Requirement 15.9)。
7. THE テスト SHALL check that a term planted from each kind of solver file (a dictionary keyword, a patch name, a function-object name, a geometry-script name) is found when planted in builder-level text, and ignored in Dr. Kiro-level text (`lab-bench` Requirement 16.7)。
8. THE テスト SHALL check that no term derived from the solver files and the mesh script appears in the told set (the tool description text built from the declaration, with the knob texts), so that a collision between a word of the knob texts and an identifier of the solver is found when the identifier is written, and not at the first session。
9. WHEN the derived terms of the real solver files make builder-level text fail after the builder has renamed its own identifiers and reworded the text (13.4)、THE ビルダー SHALL stop。It SHALL write a proposal for the user: for each word, the derived term, the file and line it comes from, the text and line that contains it, and why the word says nothing about the structure of the body。THE ユーザー approves or rejects each word。THE ビルダー SHALL NOT edit `.kiro/blind-scan/stop-list.txt` before the approval, and SHALL add only the approved words。IF no word remains after the renaming and rewording、THEN no proposal is made and no stop is needed。

### Requirement 14: The package and the lab

**対象:** ビルダー。

**User Story:** ビルダーとして、アプリケーションを契約が定めるものだけで接続したい。スケルトンが汎用のままであり、接続時間とコード量に意味があるようにするためである。

#### Acceptance Criteria

1. `wind-tunnel/adapter/` SHALL be its own `uv` project depending on `bench` (by path) and on Gmsh and the other packages the design names, locked in `uv.lock`; it SHALL need Python 3.12 through `uv` only (`tech.md`)。
2. THE アダプター SHALL provide only what the adapter contract names (`docs/brief.md` section 1): its knobs, how to run one trial, what is measured, one picture, its goal and its budget。THE ベンチ SHALL NOT change for this application, except the extractor of Requirement 13 and the knob description field (`lab-bench` Requirement 18, tasks 23-26, Decisions の項目 18)。IF another change to the bench is needed, or a change conflicts with the `lab-bench` spec、THEN the builder SHALL stop and ask the user, because it is a change to the skeleton。
3. THE `wind-tunnel/lab/` フォルダー SHALL be made with `bench-make-lab`, SHALL hold nothing specific to the flow, and SHALL be tracked in git as `body-lab/lab/` is。
4. `wind-tunnel` SHALL run on its own, without `body-lab` installed, and `body-lab` SHALL run without `wind-tunnel`。
5. THE アダプター SHALL NOT import or call anything under `spikes/` (`structure.md`)。

### Requirement 15: The circle check

**対象:** ビルダー。

**User Story:** ビルダーとして、ソルバー設定を既知の結果と照らして確かめたい。セッションの数値を信頼できるようにするためである。

#### Acceptance Criteria

1. THE 円柱チェック SHALL run the setup of Requirement 6 with a circle (`aspect` 1, `corner` 1, `splitter` 0, `angle` 0) at Reynolds number 100, set in the builder-side parameter of Requirement 6.7。Normal runs SHALL stay at 150。
2. THE 円柱チェック SHALL be a slow local test that needs Docker。It SHALL be marked so that it does not run in the ordinary tests and SHALL NOT run in Kiro Web。
3. THE 円柱チェック SHALL pass WHEN the measured Strouhal number of the circle is within 5% of the literature value。THE 差 SHALL be (measured minus literature) divided by literature, in percent。
4. THE 文献値 SHALL be the Strouhal number given by Williamson's equation (6) at Reynolds number 100。THE 出典 SHALL be: C. H. K. Williamson, "Oblique and parallel modes of vortex shedding in the wake of a circular cylinder at low Reynolds numbers", *J. Fluid Mech.* 206, 579-627 (1989), equation (6), given there "for the purpose of comparison with two-dimensional numerical computations": St = A/Re + B + C*Re, with A = -3.3265, B = 0.1816 and C = 1.600e-4, a least-squares fit to the paper's parallel-shedding data (read by the builder in the paper's PDF at https://authors.library.caltech.edu/records/wavw6-f7k56/files/WILjfm89a.pdf, PDF page 28, printed page 606)。At Reynolds number 100 the equation gives 0.164335, that is 0.1643 (computed by the builder); the brief's "about 0.165" agrees within 0.4%。The 5% band is therefore 0.1561 to 0.1726。THE チェック SHALL compute the literature value from the three constants at run time, and the record SHALL keep the constants, so that the value can be recomputed。THE 論文の本文 does not state a Reynolds-number range for the fit; its Figure 14 plots the data for Reynolds numbers from 40 to 180, and Reynolds number 100 lies inside。No range of validity SHALL be stated in the README beyond that。ユーザーが挙げた短い関連論文 Williamson, *Phys. Fluids* 31, 2742 (1988) は開けておらず（出版社のページが拒否された）、その数値は引用 SHALL NOT。THE プロトタイプの結果 was 0.167 (the brief; it is not a result of this spec)。
5. WHEN the circle check ends、THE チェック SHALL write to a file tracked in git, `wind-tunnel/circle-check.json`: the Reynolds number, the measured Strouhal number, the literature value, the source, the difference in percent, the image digest and whether it passed。Every value SHALL come from the run; none SHALL be typed in except the three constants of the equation and its source。
6. THE `wind-tunnel/README.md` SHALL report the same values and the difference。
7. IF the circle check fails、THEN the builder SHALL report the difference to the user and stop。It SHALL NOT change the tolerance, the literature value or the setup to make it pass without asking。

### Requirement 16: The numbers for the README

**対象:** ビルダーとユーザー。

**User Story:** README の読者として、このアプリケーションの接続にどれだけ時間がかかり、コードがどれだけの量かを知りたい。スケルトンの汎用性の主張を判断できるようにするためである。

#### Acceptance Criteria

1. THE 接続時間 SHALL be the wall-clock time from the approval of this spec's requirements by the user to the start of the first full session。THE ユーザー SHALL report it himself, and THE ビルダー SHALL record it in `wind-tunnel/numbers.md`, with the words "self-reported by the user", and SHALL NOT estimate it。
2. THE コード量 SHALL be the number of non-blank, non-comment lines in `wind-tunnel/adapter/` and in `wind-tunnel/model/`, counted by a script that is itself in `wind-tunnel/`, and written to `wind-tunnel/numbers.md` by the script。THE 数え方 SHALL exclude generated and locked files (the lock file, virtual environments, caches) and SHALL list the test files on their own line。
3. UNTIL a number is available、THE ファイル SHALL show the visible placeholder `<not yet measured>` (`rules.md`, Honest)。
4. THE ルートの `README.md` SHALL NOT be edited here; it is replaced in a later step (`rules.md` section 5)。`wind-tunnel/README.md` SHALL report both numbers when they exist。

### Requirement 17: Verification and the first full session

**対象:** ビルダーとユーザー。

**User Story:** ビルダーとして、各部分を検査し、フルセッションを 1 回封印したい。アプリケーションが動くことを示すためである。

#### Acceptance Criteria

1. THE 通常のテスト SHALL need no Docker and no display: the estimators (Requirement 5, with `hypothesis`), the geometry description for the corners of the knob ranges, the told set and its export (Requirement 2), the failure mapping (Requirement 8, with a fake solver that fails), the extractor (Requirement 13) and the contract check of a result。
2. THE 低速のローカルテスト SHALL need Docker: the circle check, the identical-twice check (Requirement 10.4), the run of every combination of the extreme values of the four knobs (16 runs, the end-corner cases), and the near-end cases: for each knob, the values at 0.001 and at 0.01 of its range from each end of the range, with the other three knobs at the middle of their ranges (16 runs)。値は宣言された範囲から計算し、手で書かない。THE corner rule of 要件 6.11 refuses the near-end corner values that are too close to 0 or 1 (before a run, through `check_inputs`); such a case is recorded as `refused` with the message and is not run。THE ジオメトリ SHALL NOT refuse any case。
3. ONE full Dr. Kiro session of 24 runs SHALL be run by the user on his Mac, in Kiro CLI, only after the gate of 17.6 has passed or the user has decided what to do about it。THE user はそれを自分で開始して終了し、画面を録画する。彼は実験者の役だけを務める（決定 39）。Pass: the record is sealed as `ended` in `sessions/wind-tunnel/<session-id>/`, `bench-verify` verifies it, and `bench-scan` on the lab and on the sealed folder reports nothing。WHEN the user says that the session is done、THE ビルダー（ユーザーではない） SHALL run `bench-verify` and both scans, and SHALL commit the sealed folder only if all of them pass (17.5), in the environment where it was made (`handoff.md`)。
4. THE `wind-tunnel` の README SHALL report the circle check and the numbers of Requirement 16, as the brief's "done when" asks: the circle check within 5% of the literature value (with the difference), one full session of 24 runs completed, how long the application took to connect, and how much code it is。
5. THE ビルダー SHALL NOT commit a session record that fails `bench-verify` or the blind scan。
6. WHEN the 32 cases of 17.2 have been handled、THE ビルダー SHALL write for each case, to the tracked file `wind-tunnel/extreme-runs.json`, the knob values, the outcome (settled, did not settle, mesh could not be made, solver failed, time limit, refused; `did not settle` は、5 つの計測が `not_settled` である結果の実行で、要件 4.5、記録される結果名のままである) and, for a run, the wall-clock time, all from the run; a refused case has the message and no time。IF any run that was not refused hits the time limit, fails to mesh, fails, does not settle, or takes more than 115 s (the margin rule, Decision 34)、THEN the builder SHALL stop and report the knob values, the outcome and the times to the user。THE ビルダー SHALL NOT change a range, the time limit, the limits `min_arc` and `min_line`, or the setup by itself, and SHALL NOT start the first full session。THE ユーザー decides among: a rule that refuses such values with a message in Dr. Kiro's terms (要件 6.11, `lab-bench` 要件 19), a narrower declared range (a change of Requirement 3.1), or accepting the risk。

### Requirement 18: Steps that need the user's hands

**対象:** ビルダー（作業の順序づけ）とユーザー。

**User Story:** ユーザーとして、自分の手が必要な手順をほかと分けておきたい。タスクを一気に実行できるようにするためである。

#### Acceptance Criteria

1. THE ユーザーが必要な手順 are: 提案つきの要件の承認、24 回のセッションの開始と終了（要件 17.3）で、ユーザーが画面に録画する、接続時間の報告（要件 16.1）。封印の確認と `sessions/wind-tunnel/` のコミットは、これに含まれない: ユーザーがセッションの終了を伝えた後に、ビルダーが行う（要件 17.3、決定 39）。
2. THE シート読み取りチェック（要件 9.7）SHALL be a gate before the adapter is written。ビルダー自身が実行するので、「Run All Tasks」の前にユーザーの手順はない。
3. THE 後の `tasks.md` SHALL put every other hands-on step together at its very end, apart from the tasks the builder can run alone with "Run All Tasks"。
4. THE Docker が必要な手順 SHALL run only on the local Kiro on the user's Mac (`handoff.md`); the builder SHALL NOT mark them done from Kiro Web。
5. THE 結果に依存するこの spec の停止は、手作業の手順ではない。結果がそれを求めるときだけ起き、ビルダーは止まってユーザーに報告する: stop-list エントリーの提案（13.9）、端のケースと端に近いケースのゲート（17.6）、失敗した円柱チェック（15.7）、メッシュにできないジオメトリ（6.10）、上限より遅い実行（8.7）、`lab-bench` spec との衝突（14.2）。これらは `tasks.md` に停止条件として書かれ、サブエージェントが決めずに報告するようにする。
---

## Decisions

項目 1-14 は、この要件を書く前にユーザーと決めたことです。ユーザーは、項目 10 に記した訂正と、項目 15 と 16 の承認つきで、この要件を承認しました。項目 23-27 は GIF 読み取りチェックが失敗した後に加えました。

1. **ジオメトリ。** プロトタイプの値で、ユーザーが確認済み: 高さ 1、長さ `aspect`、後ろに隙間なく付ける厚さ 0.08 の板、長さ `splitter` 高さ分、ボディ全体を長方形の中心まわりに `angle` だけ回転。固定値は `wind-tunnel/model/` だけに置く。`corner` のスケールは項目 15 で決定。
2. **ストローハル数の推定。** 5% を分解できる方法。要件が精度を定め（要件 5）、設計が方法を選ぶ。
3. **定義。** `cl_amp` は半振幅、`shedding` は `cl_amp` が 0.01 を超えること、`strouhal` は振動しないとき未計測結果、基準長 1、主流速度 1。
4. **失敗。** 非有限値、発散、異常終了、タイムアウト、落ち着かない実行は、理由つきのベンチ障害で、理由はビルダー側だけ。落ち着き基準と時間上限は項目 15 で決定。
5. **Docker と Gmsh。** 公式イメージをダイジェストで固定。Gmsh はホスト上のロックされた `uv` 依存。イメージが違えばフェイルファスト。
6. **再現性。** 3 プロセスへの固定分割。同じ Mac、イメージ、入力なら同じ結果。マシンをまたぐ保証はしない。シードは使わない。
7. **ケースフォルダー。** `bench-run/` の下。成功後は削除、失敗後はビルダーだけのために残し、ログ、設定、メッシュファイル、力のファイルに削る（項目 31）。
8. **円柱チェック。** 円柱をレイノルズ数 100 で、ビルダー側のパラメーターで実行。低速のローカルテスト。結果は追跡されるファイルと README に。5% 以内で合格。文献の出典は項目 17 で決定。
9. **画像。** 試行ごとに 1 つの画像、固定の色スケール、文字なし。項目 23 で置き換え: PNG の画像シート。フレーム数とサイズは項目 24。
10. **Dr. Kiro に伝えること。** ノブの名前、範囲、ノブの文、各計測の意味、流れが 2 次元でレイノルズ数 150 であること。しきい値 0.01 は `shedding` の定義の一部として伝える。伝える集合は宣言された 1 つの集合で、1 つの文書として書き出せ、比較用 Kiro に与えるものである。**承認時のユーザーによる訂正:** Dr. Kiro には各ノブが何であるかを伝える。ボディの長さ、角の丸め、ボディの後ろの板の長さ、迎え角（長さ、角の丸め、後ろの板の長さ、迎え角）である。ノブが流れに何をするかは伝えない。理由: 風洞は、システムの作りについて何も隠されていなくても予測が外れることを示すためのものである。引き続き伝えないもの: ソルバー設定、メッシュ設定、画像の内容、形の知識。ノブの文は要件 3.2 にあり、ビルダーが、単位と範囲の両端の意味（"0 means there is no plate"）を含む定義として書いたもので、影響としては書かない。スキャンへの帰結は要件 13.3: 許可リストは宣言された名前だけで、ノブの文の語はほかのビルダーのテキストと同じようにスキャンされ、ソルバーとメッシュの識別子は禁止のままである。
11. **形の知識なし。** どのラボのテキストにも置かない。自動ではなく、レビュー済みの一覧で確認する。
12. **範囲。** アダプター、`model/`、ラボ、抽出器、円柱チェック、数値、そして `sessions/wind-tunnel/` に封印する最初の 24 回のセッション。そのセッションはユーザーが開始する（封印の確認とコミットはビルダーが行う。決定 39）。
13. **README の数値。** 接続時間はこの要件の承認から最初のフルセッションの開始まで、自己申告。コード量はスクリプトで数える。どちらも `wind-tunnel/numbers.md` に。
14. **目的。** ゴールの文は項目 15 で決定。
15. **提案どおりに承認**（ユーザー、承認時）: `corner` は短い辺の半分に対する割合で、radius = `corner` x min(1, `aspect`) / 2、プロトタイプと同じ（要件 6.2）。落ち着き基準: 落ち着いた部分の後半を前半と比べ、平均 `cd` は 2% 以内、`cl_amp` は 10% 以内（下限 0.002）、揚力が振動するなら 5 周期以上（要件 8.3）。1 回の実行の実時間の上限 140 s（要件 8.7）。推定器の精度 1%（要件 5.3 と 5.4。`cl_mean` については 5.4 の限界に amplitude / (pi * f * T) が加わる）。（以前の 24〜48 フレーム、幅 480〜800 ピクセルの画像は、項目 23 と 24 で置き換え）。ゴールの文 "Find the setting of the four knobs with the lowest cd among the settings where shedding is 0."（要件 11.2）。「laminar」と画像の説明は伝える集合に加えない（要件 1.7）。
16. **GIF チェックは準備され、失敗した。** `spikes/gif/make_gif.py` が `spikes/gif/check.gif`（12 フレーム）を作り、偽ラボでチェックを行った。失敗した（項目 23）。記録として `spikes/gif/` にファイルを残す。
17. **円柱チェックの文献値、ビルダーが検証済み。** Williamson (1989)、式 (6)、レイノルズ数 100 で 0.164335（要件 15.4）。1988 年の関連論文は開けておらず、数値の出典にはしない。

18. **ノブの記述: 選択肢 A**（ユーザー: "your recommendations are fine"）。`lab-bench` は各ノブに任意の `description` を得る（そちらの要件 18 とタスク 23-26）。要件 3.2 のノブの文はそこに入る。アダプターはそれらのタスクが終わるまで書かない。body-lab の宣言は変わらず、出力がバイト単位で同一であることをテストで示す。
19. **ジオメトリの定義は伝える**（ユーザー: 隠すのはソルバーとメッシュだけ）。要件 3.2 のノブの文は次を述べる: 板の厚さは 0.08 ボディ高さ（プロトタイプの値で、ユーザーが先に確認済み）、隙間なく付け、長さはボディの最後端から数え、ボディの中央を通る線上にある。回転はボディの長さと高さの真ん中まわりで、板も一緒に回る。正の角度は先端側を +y の向きに動かし、流れは +x に沿う。**向きはプロトタイプと同じ**（正の角度で先端が上がる）で、ユーザーが確認済み。計算領域は、ユーザーの決定どおり、隠す集合に残す。これらの文は定義で、要件 12 に照らして読み直した。
20. **ブラインドスキャンの衝突**は要件 13.4 の順序で解決する（ビルダーが選んだものを改名、言い換え、それでも残れば確認）。stop list はユーザーの承認があるときだけ変える。
21. **端に近いノブの値: 先に計測する。**（項目 34 と 35 で改訂: コーナーのルールが、端に近い値の一部を実行の前に拒否する。ジオメトリは今も何も拒否しない。）最初のセッションの前に、16 の端のコーナーの実行と 16 の端に近い実行（要件 17.2）を行う。タイムアウト、メッシュの失敗、ソルバーの失敗、落ち着かない実行があれば、ビルダーは止まって数値を報告する（要件 17.6）。範囲と時間上限はビルダーは変えない。端に近い距離（範囲の 0.001 と 0.01）はビルダーの提案である。
22. **OpenFOAM のキーワードの stop-list への追加**は、根拠つきで提案し、ユーザーが承認する。タスクの中の明示的な停止とする（要件 13.9）。

23. **画像 = PNG の画像シート 1 枚**（ユーザーの決定、選択肢 1）。理由: GIF 読み取りチェックが失敗した（`spikes/gif/results.md`）。Dr. Kiro のファイルツールはアニメーション GIF の最初のフレームとファイルサイズのメタデータしか届けず、動きと 2〜12 番目のフレームは Dr. Kiro に届かない。シートはフレームを時間順に 1 枚の静止画に並べ、`body-lab` の画像と同じ形にする（`body-lab` 要件 4 と設計 4）。「試行ごとに 1 枚の画像」という契約と `lab-bench` は、`lab-bench` 要件 18（ノブの説明）を含めて変わらない。伝える集合は画像を種類だけで示し、それはベンチが書く（"one picture (png file)"）。時間順についての文は `lab-bench` の変更を要するので加えない。
24. **シートの配置: 提案、ユーザーは設計の承認時に確認する。** 6 フレーム（プロトタイプと同じ）、2 行 3 列、左から右、次に上から下へ時間順。各セル 400 x 200 ピクセル（2 対 1、以前のフレームの形）。フレームは終わりで終わる間隔 1.0 時間単位（t = 145、…、150）。brief は「終わり近くのフレーム」としており、ストローハル数約 0.17 での渦放出の 1 周期は約 6 時間単位なので、間隔 1.0 の 6 フレームでほぼ 1 周期を覆う。セルの間に、固定の 1 色の 4 ピクセルの薄い隙間を加えるので、シートは 1208 x 404 ピクセルになる。隙間の理由: 自由流の渦度はほぼ 0 で、色スケールの中立色で表されるため、隙間がないと 1 つのセルの右端と次のセルの左端がつながり、1 つのセルの後流が次のセルに続くと読めてしまう。ユーザーが隙間なしを望むなら設定は 0 で、シートは 1200 x 400 になる。間隔は `wind-tunnel/model/constants.toml` の設定である。振動しないボディはほぼ同じセルになる。色スケールは試行をまたいで固定で、その上限は後で計測する値のまま、32 回のゲートから決める（要件 9.5、17.2）。**この大きさのシートが Dr. Kiro に読み取れることは主張しない:** シート読み取りチェック（要件 9.7、9.10）で確かめ、失敗すればビルダーは止まる。
25. **ノートブックの動く画像**はここでは設計しない。ノートブックはシートのフレームを順に見せる。`body-lab` も同じシートの形なので、両方のラボについて 1 回、`lab-notebook` spec で決める。`docs/status.md` に、その spec の項目として載せる。
26. **提案どおりに承認**（ユーザー）: 各範囲の 0.001 と 0.01 の端に近い値、32 回のゲート（要件 17.2、17.6）、stop-list の語を提案とユーザーの承認で扱うこと（要件 13.9）。もう未解決の質問ではない。
27. **計算領域は伝えないまま**（ユーザーの決定）。正の角度の向きはプロトタイプと同じ（項目 19）。
28. **`cl_mean` の誤差の限界（要件 5.4）: 選択肢 1**（ユーザーの決定、タスク 6.3）。推定器は変えない: `cl_mean` は、周期の整数個ではなく、落ち着いた部分での時間重みつき平均（台形則）である。理由: 窓が周期の整数個を含むことはまれで、残る端数の周期が平均を最大でも `amplitude / (pi * f * T)`（`f` は信号の周波数、`T` は落ち着いた部分の長さ）だけずらすため、平均の 1% という以前の限界は、平均が 0 に近いときには成り立たない。限界は、既知の平均の 1% に `amplitude / (pi * f * T)` を足したものになった。`cl_amp` の限界は変わらない。
29. **抽出器のルール、タスク 13.1: 選択肢 1**（ユーザーの決定）。`wind-tunnel/lab` のブラインドスキャンは、一般的な語の指摘を 115 件報告した。抽出器を 2 つの固定のルールで絞り、よくある文字列についての判断は入れない: (a) `python-names` は関数、クラス、モジュールレベルの定数の名前だけを取り、文字列リテラルは取らない。(b) すべての抽出器は、標準ライブラリのリストを使って、Python の予約語（`keyword.kwlist`、`keyword.softkwlist`）、Python の組み込み名（`dir(builtins)`）、1 文字の名前を捨てる。ほかのフィルターは加えず、stop list は変えない（要件 13.1、設計 9）。

30. **ビルダーが選んだ 2 つのファイル名を改名、タスク 13.1**（ユーザーの方針: 指摘がビルダーの選んだ名前だけのときは、ビルダーが決める）。`wind-tunnel/lab` のブラインドスキャンは、ファイル名の語幹 `settings` と `functions` を報告した。stop list はこれらをカバーしておらず、同じ語がラボのテキスト（`.kiro/settings/**`、保護フォルダー、方法のテキスト）にあるためである。`wind-tunnel/model/settings.toml` は `wind-tunnel/model/constants.toml` に、`wind-tunnel/model/case/system/functions.in` は `monitors.in` になり、`controlDict.in` には `#include "monitors"` がある。どちらの名前もビルダーの選択で、OpenFOAM は要求しない。スキャナー、ラボのテキスト、stop list のルールは変えない。
31. **失敗した実行のケースフォルダーは削る**（ユーザーの決定、タスク 14.4）。残すのはログ、設定、メッシュファイル、力のファイルだけ（要件 10.6）。理由: 残した失敗のケースフォルダーは 4.6〜8.3 GB だった。設計の決定 20。
32. **上限はメッシュ、ソルバー、後処理を含み、削除は後に回す**（ユーザーの決定、タスク 14.4）。理由: 5 GB のケースフォルダーの削除に約 15 s かかった。成功した実行のフォルダーは `trash/` に名前を変えて移し、次の試行の開始時に、その時計の前に削除する。計測: 最も遅い入力（実行 16: 3, 1, 3, 30）の 6 回の実行は、名前の変更とゴミ箱の削除を含めて合計 507 s（それぞれ 75〜90 s）で、900 s の中に収まった。設計の決定 21。
33. **ソルバーの出力を減らす**（ユーザーの決定、選択肢 3(b)、タスク 14.4）: 円柱で 1 回の実行あたり 4.90 GB から 54 MB へ。2 つの参照入力で、同じマシンと同じイメージのダイジェストのもと、測定値、画像、力のファイルは同一（要件 10.3）。設計の決定 22。
34. **マージン 115 s と angle の範囲 [0, 15]**（ユーザーの最終決定、タスク 14.4 ステージ 3b）。マージンのルール: 宣言した範囲の中での実行の最悪の実時間は、計測で 115 s 以下とする（上限は 140 s のまま）。`angle` の上端は 15 度: 20〜30 では組み合わせ 3/0/0 と 3/0/3 が落ち着かず（`cd` についての落ち着き基準）、15 では端の 8 つの組み合わせがすべて落ち着き、最も遅いものは 95.2 s だった（`spikes/timing/extreme-v2-summary.md`）。brief は [0, 30] としている。この決定がこの spec についてそれを上書きし、`docs/brief.md` は編集しない。要件 3.1、宣言、テスト、`product.md` は [0, 15] を持つ。
35. **コーナーのルール: 2 つの限界、板は対象外、実行の前に拒否**（ユーザーの決定）。`constants.toml` の `min_edge` は、`min_arc` = 0.0314 と `min_line` = 0.0025 に置き換わる。データ（`extreme-v2-summary.md`、新しい設定）: 弧は 0.03142 から落ち着き（94.7 s と 78.7 s）、0.02749 では落ち着かず（123.3 s）、直線の辺は 0.0025 から落ち着き（111.6 s と 99.9 s）、0.002 で上限に達した。両方に 1 つの値を使うと、高い側を必要より約 12 倍多く拒否するか、上限に達する弧を受け入れてしまう。限界はボディの弧と直線の辺だけのものである: 板の長さ 0.001、0.01、0.1 は最大 62.7 s で落ち着いた。コーナー 0 または 1 は受け入れる。長さ 0 の部分は存在しないためである。拒否は実行の前に `check_inputs`（要件 6.11）を通して行うので予算は使われず、Dr. Kiro の言葉で受け入れられる範囲を伝える。ジオメトリはもうこのルールを持たない。設計の決定 23。

36. **色の上限は 5.0 に固定**（タスク 14.4、要件 9.5）。実行の前に決めたルールによる: 要件 17.2 の 32 ケースのうち落ち着いた実行について、6 フレームでの渦度の絶対値の実行ごとの 99 パーセンタイルの最大値を、整数に切り上げる。結果: 落ち着いた実行 29 回、最大値 4.5979、したがって 5。設計の決定 24。

37. **試行の中で落ち着かない流れは、失敗ではなく結果である**（ユーザーの決定、タスク 16 の後）。以前: `TrialFailure`（`not_settled`）であり、失敗はセッション全体を終わらせる（`lab-bench` 2.7、11.3）。理由: (a) 範囲内のランダムな 30 点のうち 2 点が落ち着かなかった（`spikes/timing/random-points.md`）ので、24 回のセッションは、器具の故障ではない理由でしばしば止まる。(b) 流れが落ち着かないことは試料についての発見であり、Dr. Kiro が使える。(c) ベンチは未計測値についての予測をすでに `not-checkable` と判定する（`lab-bench` Requirement 7.7）ので、`bench/` の変更は要らない（確認済み: 契約チェックは 5 つの未計測値の結果を受け入れる）。今: 実行は 1 試行を使い、その記録が書かれ、画像が返され、`cd`、`cl_mean`、`cl_amp`、`strouhal`、`shedding` はすべて `NotMeasured("not_settled", "the flow had not settled within the trial")` になる。140 s の上限とほかのすべての失敗は変わらない。変更: 1.2、4.5、8（ストーリー、8.1、8.3、8.4）、17.6（結果名は残る）、伝える文、用語集。設計の決定 25。

38. **環境チェックにケースのマウントのプローブ**（タスク 16 の後）。計測パス（`spikes/timing/random-points.md`、抽選 11〜15）の 30 回のうち 5 回が、0.4〜0.5 s で "the solver run exited with code 127" とソルバーのログ `/case/Allrun: No such file or directory` で終わった。ファイルはコンテナの起動前に書かれているにもかかわらずである。いずれも、計測ドライバーがケースフォルダーの名前を変えて脇に置いた、失敗した実行の後だった。本番ではそのような実行は `incomplete`、つまり `TrialFailure` で、セッションは終わる（`lab-bench` 2.7、11.3）。ソルバーなしの再現の結果（`spikes/timing/env_127.py`、`spikes/timing/env-127.md`）: あるフォルダー名を、その名前のフォルダーを `trash/` に移して削除した直後にもう一度作ると、1000 個のコンテナのうち 84 個がマウントをまったく見なかった（ホスト上ではフォルダーが完全なのに、コンテナに `/case` がない）。フォルダーごとに新しい名前を使うと（本番のパターン: ベンチは試行ごとに別のシードを与え、シードがフォルダーに名前を付ける）、1000 回で失敗は 0 回だった。ドライバーの、同じ名前をもう一度作る脇への名前変更も 1000 回中 0 回だった。したがって、2 つの試行が 1 つのシードを得ない限り、本番パターンのセッションにはこの障害は起こり得ず、ランナーは変えない。Docker 内の原因は分かっていない。計測ドライバーはすべての実行に 1 つの固定名を使い、これは 5 回の障害に合うが、証明されてはいない。それらの実行の間隔（約 55 s）を再現していないためである。プローブ（要件 7.7）は、ランナーと同種のコンテナが新しいケースフォルダーを見ることを確かめる（たとえば Docker が共有しないベースフォルダーを）。この障害は名前の繰り返しを必要とするので、プローブはそれを見つけられなかっただろう。そこでプローブは毎回新しい名前を使い、障害を自分で起こさない。セッションでのこの種の障害は、これまでどおり `incomplete`、`TrialFailure` で、セッションが終わり、何も再試行されない（要件 8、`rules.md` 2）。設計の決定 26。
39. **最初の完全なセッションの役割**（ユーザーの決定）。ユーザーはタスク 17 を自分で行う: Kiro CLI で 24 回のセッションを開始して終了し、画面を録画する。ビルダーは、ユーザーがタスク 17 の完了を伝えた後に、タスク 18（`bench-verify`、ラボと封印したフォルダーへの `bench-scan`、すべて通ったときだけ封印したフォルダーのコミット）を行う。タスク 19 はユーザーのままである。理由: (a) ユーザーが画面を録画するので、ビルダーのコマンドが邪魔にならずにセッションが進む。(b) 実験者の役（ユーザーが開始する Dr. Kiro）とビルダーの役（チェックとコミット）が分かれる。変更: 12、17.3、18.1、タスク 17 と 18（タスク 18 はビルダーの手順）、`README.md`。
40. **画像は `measured_by` では説明しない**（決定 37 の訂正）。最初の言い方は、画像が "still shows the flow" と述べていた。これは画像が何を示すかを伝えるもので、要件 1.3 が許さず、ユーザーも承認していなかった。決定 37 の承認が覆ったのは、画像が返されることだった。今は、文は画像が返されることを述べ、何を示すかについては何も述べない。変更: 4.5、伝える文（`declaration.py`）、設計 4、宣言のテスト。設計の決定 27。

## Open questions

1 つが未解決だが、確認であり、タスクの妨げにはならない:

1. 要件 9.4 と Decisions の項目 24 のシートの配置は提案である。ユーザーは設計の承認時に、確認するか変更する。
