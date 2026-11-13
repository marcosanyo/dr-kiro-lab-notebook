> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/wind-tunnel/requirements.md`](../../../.kiro/specs/wind-tunnel/requirements.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `6a026c37bc50c1de12486fb38d184cd90b7bc68f9675b8c92241c158ef562cc6`

# Requirements Document

## Introduction

2 番目のアプリケーションです。OpenFOAM による、ボディのまわりの 2 次元の流れで、数値のノブが 4 つあります。スケルトンが汎用であることを示します。同じベンチ、同じ Dr. Kiro、同じノートブックで、まったく別のシステムを扱います。アダプター契約（`lab-bench` 要件 2）を通じてベンチに接続され、すべてのラボと同じ Dr. Kiro（`dr-kiro`）を使います。

出典: `docs/brief.md` のセクション 1-3 と 4.3、`body-lab/`（最初のアプリケーション。書き方と、Dr. Kiro に何を伝えるかの参考）、`lab-bench`（要件 2、5、7、15、17、設計 4、11、F3）、およびセッションで記録された回答（「Decisions」を参照）です。ステアリングはすべて適用されます。**[PROPOSAL]** と付けた値はビルダーの提案で、ユーザーがこの要件を承認するまで決定ではありません。

この spec の範囲: アダプター、`wind-tunnel/model/` のソルバー設定、`dr-kiro` のコマンドによる `lab/` フォルダーの作成、ソルバーファイル用のブラインドスキャン抽出器、円柱チェック、README 用の数値（接続時間とコード量）、そして 24 回の最初のフルセッション（`sessions/wind-tunnel/` に封印）です。

この要件の形を決める目的は 2 つあります。

- Dr. Kiro は実験だけから流れを知ります。伝えられる内容は、宣言された 1 つの集合です（要件 1）。後で、このリポジトリのラボと無関係な Kiro が、まったく同じ集合だけを与えられ、実験をせずに、比較用の spec を書きます。
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
- **落ち着いた実行（Settled run）**: 落ち着いた部分が落ち着き基準（要件 8.3）を満たす実行です。
- **ケースフォルダー（Case folder）**: 1 回の実行のフォルダーで、メッシュ、ソルバーのファイル、出力、フレームが入ります。
- **伝える集合（Told set）**: Dr. Kiro にシステムについて与える情報のすべてで、アダプターの宣言から作る 1 つのテキストです（要件 1）。
- **比較用 Kiro（Comparison Kiro）**: このリポジトリのラボと無関係な Kiro で、伝える集合とまったく同じものだけを与えられ、実験をせずに、比較用の spec を書きます。後で使うもので、ここでは作りません。
- **形の知識（Form knowledge）**: ボディの形やノブの値が流れや計測にどう影響するかについての、あらゆる記述です。
- **円柱チェック（Circle check）**: レイノルズ数 100 の円柱で計測したストローハル数を、文献と比べる実行です（要件 15）。
- **GIF チェック（GIF check）**: Dr. Kiro のファイルツールがアニメーション GIF を表示できることを、ユーザーが手で確かめるチェックです（要件 9）。
- そのほかの用語は `lab-bench` と `body-lab` のとおりです。

---

## Requirements

### Requirement 1: What Dr. Kiro is told

**対象:** Dr. Kiro と、アダプターを書くビルダー。

**User Story:** Dr. Kiro として、システムの仕組みを教えられることなく実験できるように、入力、各計測の意味、見つけるべきものを平易に述べてほしい。ビルダーとして、その記述を 1 つの集合にしたい。比較用 Kiro にまったく同じものを与えられるようにするためである。

#### Acceptance Criteria

1. THE 伝える集合 SHALL be the text of the adapter's declaration as `lab-bench` builds it for Dr. Kiro (`lab-bench` design F3)、and SHALL be built from the adapter's own declaration, with no second copy。
2. THE 伝える集合 SHALL contain exactly: 4 つのノブの名前とその範囲（要件 3）、各計測の名前、単位、意味と `strouhal` の未計測結果（要件 4）、流れが 2 次元でありレイノルズ数が 150（高さと主流速度に基づく）であること、画像の種類、予算、ゴール（要件 11）。
3. THE 伝える集合 SHALL NOT contain what any knob does、ボディの形やそれが部品を持つこと、ソルバー設定、画像の内容、および形の知識（要件 12）。
4. THE アダプター SHALL carry the told set in the fields the declaration already has (knobs, measurements, picture, budget, goal and `measured_by`)。IF the existing fields cannot hold the told set, THEN ビルダー SHALL stop and ask the user whether `lab-bench` changes, and SHALL NOT add a second channel through which Dr. Kiro learns about the system。
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

**User Story:** Dr. Kiro として、名前の付いた 4 つの数を設定したい。システムを変化させるためである。

#### Acceptance Criteria

1. THE アダプター SHALL declare exactly four number knobs, with these names and ranges (`docs/brief.md` section 1): `aspect` in [0.5, 3]; `corner` in [0, 1]; `splitter` in [0, 3]; `angle` in [0, 30] degrees。
2. THE アダプター SHALL NOT declare or tell anything else about a knob（要件 1.3）。
3. WHEN the bench passes computed inputs、THE アダプター SHALL accept every combination of values inside the four ranges, ends included, and SHALL build the body for it (Requirement 6) or fail with the reason (Requirement 8)。
4. THE アダプター SHALL NOT clip, round or default a knob value; the bench has already refused values outside a range (`lab-bench` Requirement 4.6)。

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
5. THE アダプター SHALL declare no not-measured outcome for `cd`, `cl_mean`, `cl_amp` or `shedding`: a run that cannot give them is a bench failure (Requirement 8)。
6. THE 基準長 SHALL be the height (1) and the free-stream speed SHALL be 1, so that the coefficients and the Strouhal number need no other reference。
7. THE 各計測の意味 SHALL be the same in the `measured_by` text, in `wind-tunnel/README.md`, and in the code; a change SHALL be made in all three。

### Requirement 5: Accuracy of the estimators

**対象:** ビルダー。

**User Story:** ビルダーとして、ストローハル数と振幅を 5% の違いを見分けられる精度で推定したい。円柱チェックと Dr. Kiro の結果に意味を持たせるためである。

#### Acceptance Criteria

1. THE アダプター SHALL compute `cd`, `cl_mean`, `cl_amp`, `strouhal` and `shedding` in pure functions of the force time series of the settled part, with no access to the solver。
2. THE `strouhal` の推定器 SHALL resolve the frequency to better than the 5% of the circle check。A plain Fourier transform over the settled part resolves only about 0.014 in Strouhal number, about 8% of 0.17, so it SHALL NOT be used without a refinement。THE 設計 SHALL choose the method。
3. FOR ALL synthetic lift signals that are a sinusoid of known Strouhal number, in a range the design states and justifies, with any mean, any amplitude above 0.01 and the length and sampling interval of a settled part、THE `strouhal` の推定器 SHALL return a value within **[PROPOSAL]** 1% of the known value。
4. FOR ALL synthetic lift signals that are a sinusoid with a known amplitude and mean、THE `cl_amp` and `cl_mean` estimators SHALL return values within **[PROPOSAL]** 1% of the known amplitude (absolute 1e-6 when the amplitude is 0) and the known mean。
5. FOR ALL synthetic signals、THE `shedding` の値 SHALL be 1 exactly when the estimated `cl_amp` is above 0.01。
6. THE 推定器 SHALL give the same result for the same series (no randomness)。

### Requirement 6: The body and the flow, in `model/`

**対象:** ビルダー。Dr. Kiro にはこれを一切伝えない（要件 1.3）。

**User Story:** ビルダーとして、ボディと流れを 1 か所に固定したい。Dr. Kiro が 1 つのシステムを調べることになり、値が `lab/` フォルダーに届かないようにするためである。

#### Acceptance Criteria

1. THE ボディ SHALL be a rounded rectangle of height 1 and length `aspect`, centred on the origin of its own frame。
2. THE 角 SHALL be rounded with a radius of `corner` times half of the shorter side of the rectangle。**[PROPOSAL]** The brief and the prototype notes do not define the scale of `corner`。Reading it as a fraction of the half-height (the user's reading) gives semicircular ends at `corner` = 1 for a body at least as long as it is high, and a circle at `aspect` = 1, which the circle check needs。For `aspect` below 1, a fraction of the half-height would exceed half of the length (for example `aspect` 0.5 with `corner` 0.6) and the shape would be invalid; "half of the shorter side" is the same for `aspect` of 1 or more and defined for all of [0.5, 3]。The user confirms or replaces this at approval。
3. WHERE `splitter` is above 0、THE ボディ SHALL have a plate of thickness 0.08 and length `splitter` heights, attached at the rear of the rectangle on its centre line with no gap。WHERE `splitter` is 0、THE ボディ SHALL have no plate。
4. THE ボディ、板を含めて、SHALL be rotated by `angle` degrees about the centre of the rectangle。
5. THE 正の角度の向き、およびジオメトリのそのほかの固定値（厚さ 0.08、板の取り付け位置）SHALL be written in `wind-tunnel/model/` and SHALL NOT be told to Dr. Kiro。
6. THE 流れ SHALL be laminar, two-dimensional, at Reynolds number 150 for every normal trial, with the free-stream speed 1 and the height 1。
7. THE レイノルズ数 SHALL be a builder-side parameter of the model in `wind-tunnel/model/`。It SHALL NOT be a knob, SHALL NOT be reachable from any `lab/` folder or from any input of a trial, and SHALL be set to a value other than 150 only by the circle check (Requirement 15)。
8. THE ソルバー設定 SHALL start from the values that worked in the prototype (`docs/brief.md` section 4.3): OpenFOAM v2412 `pimpleFoam`; mesh from Gmsh; laminar; domain with the inlet 6 heights ahead of the body, the outlet 18 behind, and the walls 7 above and below; run to time 150; forces averaged from time 80; frames taken near the end; an adaptive time step with a Courant limit of 0.8。THE 設計 SHALL decide what to keep and SHALL say what it changes and why; THE ビルダー SHALL ask the user before a change that alters the circle check。
9. THE ソルバー設定 SHALL live only in `wind-tunnel/model/`, as files the builder writes。No value of it SHALL be written into the adapter code as a second copy; the adapter reads `model/`。
10. IF the geometry for a combination of knob values is invalid (a self-intersecting outline, a mesh that cannot be made)、THEN the run SHALL be a bench failure with the reason (Requirement 8), and the builder SHALL report the combination to the user。

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

### Requirement 8: Failures, settling and time limits

**対象:** ビルダー（何が失敗か）、Dr. Kiro（何が見えるか）。

**User Story:** ビルダーとして、失敗した実行や落ち着かなかった実行は、作り物の値を出さず、理由とともにセッションを止めたい。記録のすべての数が、落ち着いた実行から来ていることを保証するためである。

#### Acceptance Criteria

1. IF a run ends with a non-finite value in any force, a diverged solution, an abnormal exit of the solver or the mesher, a missing or unreadable output, or the time limit of 8.7, or does not settle (8.3)、THEN the adapter SHALL return a trial failure (`lab-bench` design 4), and the bench failure rules apply (`lab-bench` Requirement 2.7 and 11.3): the session stops。
2. THE アダプター SHALL NOT retry a failed run, change the time step, the mesh or the method, fill in a value, or return a partial result。
3. **[PROPOSAL]** A run SHALL count as settled WHEN, for the first and the second half of the settled part: the means of the drag coefficient differ by no more than 2% of the mean over the whole part; the values of `cl_amp` differ by no more than the larger of 10% of the value over the whole part and 0.002; and, WHEN `shedding` is 1, the settled part holds at least 5 full periods of the lift oscillation。
4. THE 試行失敗の `public_reason` SHALL be one of a fixed small set of plain statements in Dr. Kiro's terms, such as "the trial did not settle" and "the trial could not be completed", and SHALL contain no solver, mesh, file, path, version or log text。THE `detail` SHALL hold the cause, the case folder and the solver's own message, and goes to the builder-side log only (`rules.md`, Blind)。
5. THE 失敗の `public_reason` SHALL NOT state which knob values caused it (Requirement 12)。
6. THE アダプター SHALL write nothing about a failure into any `lab/` folder。
7. **[PROPOSAL]** THE 1 回の実行の実時間の上限、メッシュ作成を含めて、SHALL be 140 s。The prototype's run took about 1.5 minutes (90 s) on 3 processes。One experiment has at most 6 runs (`lab-bench` Requirement 5.1), and the front end's longest tested call is 900 s (`lab-bench` Requirement 17.18), so 6 times 140 s is 840 s, inside the call。IF the design's measured run time makes 140 s too short, or makes 6 runs not fit in 900 s、THEN the builder SHALL stop and ask the user。The adapter SHALL NOT start runs in parallel on its own to make the call fit。
8. THE 時間の上限 SHALL be a bench failure (8.1), not a not-measured outcome。

### Requirement 9: The picture

**対象:** Dr. Kiro（画像を開く）、ビルダー（作り方）、ユーザー（手作業のチェック）。

**User Story:** Dr. Kiro として、流れが動くのを見たい。ノートブックの読者として、それが動いてほしい。

#### Acceptance Criteria

1. THE アダプター SHALL give each trial one animated GIF (`image/gif`), made from frames of the flow's vorticity, with a colour scale that is the same in every trial, so that two trials can be compared by eye。
2. THE 画像 SHALL show the body and its near wake, SHALL carry no axes, ticks, labels, legends, text or metadata, and SHALL pass the bench's picture check (`lab-bench` design 4, Requirement 15.9)。
3. THE フレーム SHALL be taken near the end of the run, from the settled part。
4. **[PROPOSAL]** THE 画像 SHALL have 24 to 48 frames, spaced evenly over the last part of the run, and a width of 480 to 800 pixels at a height of half the width。THE 設計 SHALL pick values inside these ranges and SHALL state them as adapter settings, so that they can change after the first session (as `body-lab` Requirement 4.3)。
5. THE 色スケールの固定の限界値 SHALL be written in `wind-tunnel/model/`, not in `lab/`。
6. THE 画像 SHALL NOT be described to Dr. Kiro beyond its kind (Requirement 1.2)。
7. **前提条件:** BEFORE the wind-tunnel adapter is written、THE ユーザー SHALL run the GIF check: Dr. Kiro's file tool, in Kiro CLI, reads an animated GIF。THE 結果 SHALL be recorded in a file under `spikes/` (a results file, as `spikes/mcp/results.md`), and the file SHALL be tracked in git。The builder gives the user the procedure separately。
8. IF the GIF check fails、THEN the builder SHALL stop and ask the user, and SHALL NOT switch the picture format itself (`rules.md`, Fail fast)。
9. THE 後の `tasks.md` の、アダプターのコードを書く最初のタスク SHALL be a gate that reads the GIF check's result and stops if it is missing or failed。

### Requirement 10: Determinism and case folders

**対象:** ビルダー。

**User Story:** ビルダーとして、同じマシンでは同じ入力から同じ結果を得たい。失敗した実行のファイルは、ビルダーだけのために残したい。

#### Acceptance Criteria

1. THE ソルバー SHALL run with a domain decomposition of 3 processes, with a fixed method and fixed counts written in `wind-tunnel/model/`, never chosen from the number of processors on the machine。
2. THE アダプター SHALL NOT use the trial seed (`lab-bench` Requirement 2.9); the same computed inputs SHALL give the same measurements and the same picture。
3. THE 保証 SHALL be: the same Mac, the same image digest and the same Gmsh version, with the same computed inputs, give identical measurements and an identical picture。THE アダプター SHALL NOT claim reproducibility across machines, other chips or other image builds。THIS limit SHALL be written in `wind-tunnel/README.md`。
4. THE テスト SHALL check, in a slow local test (Requirement 17), that two runs of one input give identical measurements and an identical picture。IF they differ、THEN the builder SHALL stop and ask the user, and SHALL NOT weaken the statement without asking。
5. THE アダプター SHALL make each case folder under `bench-run/` (git-ignored), with a name that identifies the session and the trial and never a `lab/` folder。
6. WHEN a run succeeds、THE アダプター SHALL remove its case folder。WHEN a run fails、THE アダプター SHALL keep the case folder, for the builder only, and SHALL name it in the `detail` of the failure。

### Requirement 11: Goal, budget and modes

**対象:** Dr. Kiro。

**User Story:** Dr. Kiro として、最良の点が何を意味し、試行がいくつあるかを知りたい。計画を立てるためである。

#### Acceptance Criteria

1. THE アダプター SHALL declare a budget of 24 trials (`docs/brief.md` section 1)。
2. **[PROPOSAL]** THE アダプター SHALL declare the goal: "Find the setting of the four knobs with the lowest cd among the settings where shedding is 0."。The prototype ran two stages, first the shapes with a small lift oscillation, then among them the one with the lowest drag; this sentence is that task in the told measurements。It names only `cd` and `shedding`, which the told set defines (Requirement 4), and no form knowledge。THE 提案した目的の後半「write the rules that explain what you find」は、すでにエージェントのプロンプトにあり（`dr-kiro` 要件 2.2）、ゴールは最良の点が最小化する計測を名指す 1 文なので（`lab-bench` 要件 2.1）、ゴールには繰り返さない。The wording is written in the same form as body-lab's goal, which names the measurement to maximise。
3. THE アダプター SHALL accept both bench modes without change (`lab-bench` Requirement 5): `compare` costs 1, 2 or 3 trials (one per variant), and `sweep` costs exactly 6 (`lab-bench` Requirement 5.4)。So the budget of 24 allows, for example, at most 4 sweeps, or 24 single-variant compares, or any mix whose trials add up to 24。
4. THE 予算、モードごとのコスト、1 回の実行の時間 SHALL be given in `wind-tunnel/README.md`, and THE 1 回の実験の時間 SHALL fit the call limit (Requirement 8.7)。

### Requirement 12: No form knowledge in lab text

**対象:** ビルダー。Dr. Kiro が自分で見つけるべきものを守る。

**User Story:** ビルダーとして、Dr. Kiro が読むものの中に、形が流れにどう影響するかを述べたものが一切ないようにしたい。発見した spec のすべての規則が、Dr. Kiro 自身の実験から来るようにするためである。

#### Acceptance Criteria

1. NO sentence in a `lab/` folder (the agent, its steering, the templates, the examples), in a bench message about the system, in the told set, in a failure's `public_reason`, or in the picture SHALL state or imply how the body's shape or a knob value affects the flow or a measurement。This includes, as examples only, any statement that a part of the body changes whether the flow sheds, that rounding changes the drag, or that a long body behaves in a certain way。
2. THE `dr-kiro` の共有ビルダーファイル are written for every application and SHALL stay as they are; THE それらの例 SHALL stay placeholders (`dr-kiro` Requirement 3.6)。
3. THE ブラインドスキャン covers terms and paths only and SHALL NOT be taken as a check of this requirement。THE チェック SHALL be a **reviewed list**: a builder-side checklist, in a file under `wind-tunnel/` that is not in `lab/`, naming every text Dr. Kiro can read (each file of `lab/` that the builder wrote, the told set, each `public_reason`), with a line per text saying "reviewed, no form knowledge" and who reviewed it。THE ビルダー SHALL fill it by reading, and the user MAY check it。
4. THE チェックリスト is a review step in the later tasks。It is not automated and it is not a guarantee; THE README SHALL say so。
5. THE この spec の要件と設計 SHALL NOT be copied into any lab text。WHERE a statement of this spec is needed in a lab text、THE ビルダー SHALL write it again from the told set, so that no form knowledge comes with it。

### Requirement 13: Blind scan for the solver files

**対象:** ビルダー。

**User Story:** ビルダーとして、ブラインドスキャンがソルバー設定とボディ自身の名前を対象にしてほしい。`lab/` フォルダーやベンチの出力に、ソルバーを明かすものがないようにするためである。

#### Acceptance Criteria

1. THE ベンチ SHALL provide a blind scan extractor for the solver files in `wind-tunnel/model/`, as `lab-bench` design 11.1 anticipates。It SHALL derive terms from: the keywords and the names (patches, fields, schemes, solvers, function objects, regions) in the OpenFOAM dictionaries and templates; the names in the mesh and geometry script; the digest-pinned image name; and the file names and stems of the source files。
2. IF the extractor cannot read or parse a solver file、THEN it SHALL fail, naming the file and the problem, and SHALL NOT skip the file (`lab-bench` Requirement 15.7)。
3. THE ブラインドスキャン SHALL remove the adapter's declaration (the four knob names, the five measurement names, the not-measured outcome and the words of the told set) and the stop list, and nothing else (`lab-bench` Requirement 15.3)。
4. IF an ordinary word that the extractor derives, such as a general name for a physical quantity, makes the scan fail on text that says nothing about the solver、THEN the builder SHALL reword the text, or ask the user to approve a stop-list entry, and SHALL NOT add the word itself (`rules.md`, Blind scan)。
5. `wind-tunnel/adapter/scan_sources.toml` SHALL name the solver files and the geometry script with their extractors, and the lab's layout, so that `bench-scan` covers the lab and every bench output。
6. THE スキャン SHALL cover the picture by the picture check (`lab-bench` Requirement 15.9)。
7. THE テスト SHALL check that a term planted from each kind of solver file (a dictionary keyword, a patch name, a function-object name, a geometry-script name) is found when planted in builder-level text, and ignored in Dr. Kiro-level text (`lab-bench` Requirement 16.7)。

### Requirement 14: The package and the lab

**対象:** ビルダー。

**User Story:** ビルダーとして、アプリケーションを契約が定めるものだけで接続したい。スケルトンが汎用のままであり、接続時間とコード量に意味があるようにするためである。

#### Acceptance Criteria

1. `wind-tunnel/adapter/` SHALL be its own `uv` project depending on `bench` (by path) and on Gmsh and the other packages the design names, locked in `uv.lock`; it SHALL need Python 3.12 through `uv` only (`tech.md`)。
2. THE アダプター SHALL provide only what the adapter contract names (`docs/brief.md` section 1): its knobs, how to run one trial, what is measured, one picture, its goal and its budget。THE ベンチ SHALL NOT change for this application, except the extractor of Requirement 13。IF another change to the bench is needed、THEN the builder SHALL stop and ask the user, because it is a change to the skeleton。
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
4. THE 文献値 SHALL be: **about 0.165**, as `docs/brief.md` section 4.3 gives it。THE プロトタイプの結果 was 0.167 (the brief; it is not a result of this spec)。THE 出典 SHALL be: `<to be confirmed from source>`。The likely source is Williamson, C. H. K., "Oblique and parallel modes of vortex shedding in the wake of a circular cylinder at low Reynolds numbers", *J. Fluid Mech.* 206, 1989; its abstract says that parallel shedding is thought to be truly two-dimensional and that a comparison of its Strouhal data with several two-dimensional simulations shows a large disparity that is not clearly understood。THE ビルダー could not open the paper, so the formula or table, its Reynolds-number range and the value at Reynolds number 100 are not confirmed, and no number other than the brief's SHALL be written here or in the README until the user confirms the source。
5. WHEN the circle check ends、THE チェック SHALL write to a file tracked in git, `wind-tunnel/circle-check.json`: the Reynolds number, the measured Strouhal number, the literature value, the source, the difference in percent, the image digest and whether it passed。Every value SHALL come from the run; none SHALL be typed in except the literature value and its source。
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
2. THE 低速のローカルテスト SHALL need Docker: the circle check, the identical-twice check (Requirement 10.4), and the run of every combination of the extreme values of the four knobs (16 runs)。IF any of the 16 does not settle or fails、THEN the builder SHALL report the combination to the user before the first full session, and SHALL NOT narrow a range or change the setup by itself。
3. ONE full Dr. Kiro session of 24 runs SHALL be run by the user on his Mac, in Kiro CLI。Pass: the record is sealed as `ended` in `sessions/wind-tunnel/<session-id>/`, `bench-verify` verifies it, and `bench-scan` on the lab and on the sealed folder reports nothing。
4. THE `wind-tunnel` の README SHALL report the circle check and the numbers of Requirement 16, as the brief's "done when" asks: the circle check within 5% of the literature value (with the difference), one full session of 24 runs completed, how long the application took to connect, and how much code it is。
5. THE ビルダー SHALL NOT commit a session record that fails `bench-verify` or the blind scan。

### Requirement 18: Steps that need the user's hands

**対象:** ビルダー（作業の順序づけ）とユーザー。

**User Story:** ユーザーとして、自分の手が必要な手順をほかと分けておきたい。タスクを一気に実行できるようにするためである。

#### Acceptance Criteria

1. THE ユーザーが必要な手順 are: the approval of these requirements, with the proposals; the GIF check (Requirement 9.7); starting and finishing the 24-run session (Requirement 17.3); and reporting the connection time (Requirement 16.1)。
2. THE GIF チェック SHALL be a gate before the adapter is written; it is the only such step before the end。
3. THE 後の `tasks.md` SHALL put every other hands-on step together at its very end, apart from the tasks the builder can run alone with "Run All Tasks"。
4. THE Docker が必要な手順 SHALL run only on the local Kiro on the user's Mac (`handoff.md`); the builder SHALL NOT mark them done from Kiro Web。

---

## Decisions

これらの要件を書く前にユーザーと決めたことです。上で **[PROPOSAL]** と付けた項目は決定ではありません。

1. **ジオメトリ。** プロトタイプの値で、ユーザーが確認済み: 高さ 1、長さ `aspect`、後ろに隙間なく付ける厚さ 0.08 の板、長さ `splitter` 高さ分、ボディ全体を長方形の中心まわりに `angle` だけ回転。固定値は `wind-tunnel/model/` だけに置く。`corner` が半高さの割合かどうかは brief では決まらない。要件 6.2 を参照。
2. **ストローハル数の推定。** 5% を分解できる方法。要件が精度を定め（要件 5）、設計が方法を選ぶ。
3. **定義。** `cl_amp` は半振幅、`shedding` は `cl_amp` が 0.01 を超えること、`strouhal` は振動しないとき未計測結果、基準長 1、主流速度 1。
4. **失敗。** 非有限値、発散、異常終了、タイムアウト、落ち着かない実行は、理由つきのベンチ障害で、理由はビルダー側だけ。落ち着き基準と時間上限は提案。
5. **Docker と Gmsh。** 公式イメージをダイジェストで固定。Gmsh はホスト上のロックされた `uv` 依存。イメージが違えばフェイルファスト。
6. **再現性。** 3 プロセスへの固定分割。同じ Mac、イメージ、入力なら同じ結果。マシンをまたぐ保証はしない。シードは使わない。
7. **ケースフォルダー。** `bench-run/` の下。成功後は削除、失敗後はビルダーだけのために残す。
8. **円柱チェック。** 円柱をレイノルズ数 100 で、ビルダー側のパラメーターで実行。低速のローカルテスト。結果は追跡されるファイルと README に。5% 以内で合格。文献の出典はまだ確認できていない。
9. **画像。** 試行ごとに 1 つのアニメーション GIF、固定の色スケール、文字なし。フレーム数とサイズは提案。ユーザーの GIF チェックが通るまでアダプターは書かない。（ユーザーが PNG から変更した。）
10. **Dr. Kiro に伝えること。** ノブの名前と範囲、各計測の意味、流れが 2 次元でレイノルズ数 150 であること（ユーザーが「ノブの名前と範囲のみ」から変更した）。ビルダーは、モデルの選択である「laminar」と、画像の内容は含めない。ユーザーはどちらも加えられる。しきい値 0.01 は `shedding` の定義の一部として伝える。伝える集合は宣言された 1 つの集合で、1 つの文書として書き出せ、比較用 Kiro に与えるものである。
11. **形の知識なし。** どのラボのテキストにも置かない。自動ではなく、レビュー済みの一覧で確認する。
12. **範囲。** アダプター、`model/`、ラボ、抽出器、円柱チェック、数値、そして `sessions/wind-tunnel/` に封印する最初の 24 回のセッション。そのセッションはユーザーが開始する。
13. **README の数値。** 接続時間はこの要件の承認から最初のフルセッションの開始まで、自己申告。コード量はスクリプトで数える。どちらも `wind-tunnel/numbers.md` に。
14. **目的。** ゴールの文は提案（要件 11.2）。

## Open questions

承認の時点でユーザーに確認すること:

1. 円柱チェックの文献の出典と値（要件 15.4）: 論文を開けなかった。
2. 落ち着き基準（要件 8.3）と、1 回の実行の実時間の上限（要件 8.7）。
3. GIF のフレーム数とサイズ（要件 9.4）。
4. ゴールの文（要件 11.2）。
5. `aspect` が 1 未満のときの `corner` のスケール（要件 6.2）。
6. 推定器の精度 1%（要件 5.3 と 5.4）。
7. 伝える集合に「laminar」を加えるか、画像を説明するか（要件 1.7）。
