> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/lab-notebook/requirements.md`](../../../.kiro/specs/lab-notebook/requirements.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `f8b09b6d25c1ab248d022a048c6c867096ecc1c7f0fafb7c012bf647a4b19676`
# Requirements Document
Spec: `lab-notebook`。
## Introduction
ラボノートブックは、封印済みセッション記録から作る静的な Web サイトです。訪問者（たとえばハッカソンの審査員）が、Dr. Kiro が何を発見したかを 60 秒で理解でき、そのすべての行に証拠があることを確認できるようにします。ノートブックは Dr. Kiro の `## Discovered spec` 表（`lab-bench` 要件 12）を中心に組み立てます。表は封印済み記録が持つとおりに見せ、ステータス、行、置き換えを作り出すことはありません。
出典: `docs/brief.md` のセクション 1-3 と 4.4（4.1 と 4.5 を含む）、`lab-bench` の要件（とくに要件 6、7、10、12、13、15）、`bench/src/bench/conditions.py`（ベンチの条件クラス）、`bench/src/bench/scan/levels.py`（ブラインドスキャンの書き手別サイドカーファイル）、`body-lab` と `wind-tunnel` の spec（画像シート）、`sessions/` の封印済み記録、そして「Decisions」に記録したユーザーの回答です。`.kiro/steering/` のステアリングはすべて適用されます。とくに `rules.md` です。
どの Kiro か: ノートブックは**ビルダー**が作り、**訪問者**（人）が読みます。**Dr. Kiro** と**リーダー**（`build-from-spec`）はノートブックを見ません。ノートブックはすべての `lab/` フォルダーの外で作られ、どちらにも渡されません。各要件は、誰に関わるものかを明記します。
ノートブックが現在作られる元の記録（`sessions/` から読んだ事実。要件をテスト可能にするために使います。ノートブックが再掲する結果ではありません）:
- `body-lab/body-1`: 終了（ended）、40 試行、仮説 11 件、予測結果 18 件（うち外れ 8 件）、スナップショット 22 件（各実行後と各判定後）、`end` スナップショットなし。どのスナップショットの `## Discovered spec` 表も行がありません。パラメーター名は Dr. Kiro が実験ごとに宣言し、1 つの名前が実験によって別の意味になることがあります。
- `wind-tunnel/wt-004`: 終了、24 試行中 18 試行、実験 6 件、予測結果 17 件（うち外れ 1 件）。`end` スナップショットには行 R1-R6 の表があります（`validated` 4 行、`partly` 1 行、`observed` 1 行、`rejected` なし）。1 つの試行は、5 つの計測すべてについて未計測結果 `not_settled` を持ちます。
- `wind-tunnel/wt-002`: 停止（stopped）、3 試行、実験 1 件、的中 2 件、登録されたまま一度も走らなかった仮説 1 件、表の行なし。
- `wind-tunnel/wt-003`: 最初の操作で停止、0 試行、スナップショットなし。
- `body-lab/body-2`: Dr. Kiro が終了、40 試行中 39 試行（残り予算 1）、仮説 11 件、実験 11 件、予測結果 24 件、スナップショット 23 件、拒否 3 件（`register` 1 件、`end` 2 件）、判定フラグ 1 件（E5、判定 `partly`、件数は的中 0、外れ 1）。`end` より前のすべてのスナップショットの `## Discovered spec` 表には行がなく、ベンチの表リーダーはそれを受理しません（Decision 45）。`end` スナップショットには 14 行あります: `validated` は R9、R11、`observed` は R1、R5、R7、R13、`rejected` は R2（R1 に置き換え）、R3（R11）、R4（R5）、R6（R7）、R8（R9）、R10（R11）、R12（R13）、R14（R13）。1 つの行が複数の行を置き換えることがあり（R11、R13）、置き換える行が置き換えられる行より前にあることがあり（R2 を R1 が置き換える）、置き換える行が `observed` であることもあります。セルにはエスケープされたパイプ（`\|heading\|`）が含まれます。Dr. Kiro は、反証された規則を `rejected` 行として残すよう、テンプレートで教えられていました（`dr-kiro` 要件 3.7）。
- body-2 の 2 件の `end` 拒否は同じメッセージを持ち、メッセージは部分に分けて記録されています: ベンチの文 "the discovered spec table does not agree with the record: "、".kiro/specs/lab/design.md line 32: "、"row "、引用（書き手 `dr-kiro`）"R13"、": "、"a validated rule needs at least one hit that is a new combination or outside the tried range ("、引用（書き手 `dr-kiro`）"H11.P3: hit/not-comparable"、")"。記録には、拒否された `design.md` の写しがありません（スナップショットは、受理された終了のときだけ取られます）。封印された R13 は `observed` です。2 つ目の引用が書き手 `dr-kiro` で記録されているのは意図的です。予測 id は Dr. Kiro のものなので、ベンチは引用した結果の要約を引用として扱います（`bench/src/bench/specfiles/discovered.py`、`_summary`）。ただし "hit" と "not-comparable" はベンチの言葉です。
- body-2 では、E11 が新しいパラメーター名 `sq` を宣言したため、パラメーターグループ {a1, s3, f, sq} に以前の試行がなく、H11.P3 は `not-comparable` です。R13 は E10（{a1, s3, f}）と E11（{a1, s3, f, sq}）を引用しており、パラメーターグループは 2 つです。
- body-2 の 9 試行は、body-1 の試行と同じ試行キーを持ちます（body-1/body-2: T7/T7、T8/T8、T3/T4、T2/T3、T4/T5、T6/T25、T1/T2、T5/T6、T9/T9）。計測値はすべて完全に等しいのに、パラメーター名は異なります（一方は `k`、他方は `a0`..`a4`）。
- body-2 H4.P1（試行 T12、パラメーター `a` 1、`f` 1、`ph` 1.5）: `x` の登録範囲 [0.2, 3.0]、計測された `x` は -0.2047（向き -84.25、`y` 0.097）。R4（`rejected`、R5 に置き換え。R5 は `observed` で E4 と E5 を引用し、予測は引用しません）が引用しています。T12 のシートでは、ボディが約 4 分の 1 回転しています。0.2 m の後方へのずれは画像ではかすかです（ボディは 320 × 180 のセルの中で約 30 px）。記録された軌跡でははっきり見えます。
- body-lab のゴール（宣言から）: "Move the body as far as possible in the direction it faces at the start: maximise x."
範囲: ノートブックのビルド（`uv` で実行する Python プログラム）、それが書き出すサイト、ステアリングとして書くビジュアルシステム、コミット済みの選択ファイル、フレームレイアウト表、そしてテストです。デプロイは `publish` にあります。「Built from the spec」に出る実行は `build-from-spec` が行い、この spec はそれを見せるだけです。
## Glossary
- **Notebook（ノートブック）**: ここで規定する静的 Web サイト。
- **Build（ビルド）**: 入力（要件 1）を読み、サイトを書き出す Python プログラム。
- **Site（サイト）**: ビルドが書き出すファイル。HTML、CSS、JavaScript、PNG ファイルで、他から取得したものは含まない。
- **Visitor（訪問者）**: サイトを読む人。
- **Record（記録）**: `sessions/<application>/<session-id>/` にある封印済みセッション記録（`lab-bench` 要件 13）。
- **Ended session, stopped session（終了したセッション、停止したセッション）**: 封印エントリーの `end` が `ended` または `stopped` である記録。
- **Snapshot（スナップショット）**: 記録の中にある Dr. Kiro の 3 つの lab spec ファイルの写し。実行後（`for` が `experiment`）、判定後（`for` が `verdict`）、または受理された終了時（`for` が `end`）に取られる（`lab-bench` 要件 10）。
- **Discovered spec table（発見された spec の表）**: スナップショットの `design.md` にある `## Discovered spec` 表。ベンチ自身の表リーダーで読む。
- **Row（行）**: 発見された spec の表の 1 行。列は id、rule、scope、experiments、predictions、status、replaced by。
- **Status word（ステータスワード）**: `validated`、`partly`、`observed`、`rejected` のいずれか。行に書かれ、終了時にベンチが検査する（`lab-bench` 要件 12.3）。
- **Verdict（判定）**: 実験後の仮説に対する Dr. Kiro の判断。`supported`、`partly`、`rejected` のいずれかと、Dr. Kiro の言葉（`lab-bench` 要件 8）。
- **Prediction outcome（予測結果）**: ベンチが記録した的中、外れ、確認不能、未実行。
- **Condition class（条件クラス）**: 登録時に記録される、予測の条件についてのベンチの分類: `inside`、`new-combination`、`outside`、`not-comparable`（`bench/src/bench/conditions.py`）。
- **Dr. Kiro's label（Dr. Kiro のラベル）**: Dr. Kiro が予測自身に付けたクラス。条件クラスの隣に記録される。
- **Cited experiments, cited predictions（引用された実験、引用された予測）**: 行が挙げる実験 id と予測 id。
- **Cited trials（引用された試行）**: 行の引用された実験のすべての試行。
- **Prediction trials（予測の試行）**: 結果エントリーが行の引用された予測に属する試行。
- **Parameter group（パラメーターグループ）**: 1 セッション内で、同じパラメーター名の集合を宣言するすべての実験の試行。ベンチが予測を比較する試行の集合（`lab-bench` 要件 6.4）。
- **Run band（走行バンド）**: 1 つのパラメーターグループの 1 つのパラメーターについて、何が走ったかを描いたもの（要件 9）。
- **Picture sheet（画像シート）**: 1 試行の 1 枚の PNG。等しいセルを、時間順に左から右、次に上から下へ並べる。
- **Frame layout table（フレームレイアウト表）**: 各アプリケーションの画像シートのレイアウトを示す、ノートブックの表（要件 7）。
- **Moving picture（動く画像）**: 画像シートを 1 セルずつ、時間順に繰り返し見せるもの。
- **Choice file（選択ファイル）**: セッションのハイライトと外れた予測を指定する、ユーザーが書いたか承認した、コミット済みのファイル（要件 12）。
- **Cover file（カバーファイル）**: カバーが見せるものを指定する、ユーザーが書いたか承認した、コミット済みのファイル（要件 13）。
- **Ink（インク）**: 誰が書いた文かを示す、固定された 3 つの文字スタイル。Dr. Kiro のインク、解説のインク、鉛筆。
- **Commentary（解説）**: ノートブックのためにビルダーが書いた文（見出し、説明、ラベル）。
- **Replay（リプレイ）**: セッションの 1 ステップ時点のセッションページ（要件 16）。
- **Step（ステップ）**: 判定後に取られた 1 つのスナップショット、または `end` スナップショット。
- **Build-from-spec run（build-from-spec の実行）**: `build-from-spec` の封印済み実行記録 1 件（`docs/brief.md` 4.5）。
- その他の用語は `lab-bench` に従う。
---
## Requirements
### Requirement 1: Inputs of the build
**対象:** ビルダー。
**User Story:** ビルダーとして、ノートブックを封印済みでコミット済みの入力だけから作りたい。サイト上のすべての行を記録までたどれるようにするためである。
#### Acceptance criteria
1. THE build SHALL read only: the records in `sessions/`; the choice files and the cover file; the frame layout table; the commentary word list (Requirement 5.5); the build-from-spec runs and their committed requests, in the places the `build-from-spec` spec defines; the files the bench's blind scan reads (the applications' model and solver files and the stop list, `lab-bench` Requirement 15), read only through the bench's scan (Requirement 20); and the notebook's own source files
2. THE build SHALL NOT read `discovered/`, any `lab/` folder, `bench-run/`, or any file that is not listed in 1.1。
3. THE build SHALL take every folder it reads and the output folder as explicit arguments, and SHALL refuse to run, naming the missing argument, if one is missing. It SHALL NOT fill in a default folder。
4. IF the output folder exists and is not empty, THEN THE build SHALL refuse, naming it, and SHALL NOT overwrite or merge into it。
5. THE build SHALL run with Python 3.12 through `uv`, as its own `uv` project in `notebook/`, SHALL need no Node and no Docker, and SHALL run no simulator or solver. It SHALL depend on the bench and on both applications' adapter packages by path only, so that the bench's blind scan can import each adapter's declaration for the allow list (`bench/src/bench/scan/terms.py`) (Decision 42)。
### Requirement 2: Checks before anything is written
**対象:** ビルダー。
**User Story:** ビルダーとして、記録が約束するものと違う入力に最初に出会った時点でビルドを止めたい。サイトが壊れた記録や改変された記録を見せないようにするためである。
#### Acceptance criteria
1. WHEN the build starts、THE build SHALL run every check of this spec (Requirements 1.3, 1.4, 2, 4.2, 7, 12, 13, 19.2 and 20) on all inputs before it writes any file to the output folder。
2. IF a hash chain check (`lab-bench` Requirement 13.4) fails, THEN THE build SHALL fail, naming the record and the first entry or file that does not match。
3. IF a record in the sessions folder given to the build is not sealed, or has a trial labelled fake (`lab-bench` Requirement 14.5), THEN THE build SHALL fail, naming the record. Tests MAY build fixture records into a temporary output folder that is never published。
4. IF a record is an ended session with an `end` snapshot, THEN THE build SHALL run the bench's own discovered spec table check (`lab-bench` Requirement 12) on that snapshot's `design.md` against the record, and SHALL fail, naming the row, if the check fails。
5. IF an ended session has no `end` snapshot (body-1), THEN THE build SHALL show the session as "no table" (Requirement 10.9) and SHALL NOT run the table check。
6. THE build SHALL read discovered spec tables with the bench's own table reader, and SHALL NOT have a second reader。
7. IF any check of this spec fails, THEN THE build SHALL fail, naming the file and the problem, and SHALL leave the output folder absent or empty。
8. THE build SHALL NOT skip a record, a row, a trial or a picture to make a build pass。
### Requirement 3: What the site is
**対象:** ビルダーと訪問者。
**User Story:** 訪問者として、スマートフォンで動き、他のサーバーに何も求めない素朴な Web サイトがほしい。速く、プライベートで、長持ちするようにするためである。
#### Acceptance criteria
1. THE site SHALL be plain HTML, CSS and JavaScript, written by the build, with no framework, no third-party library and no build step in Node。
2. THE site SHALL make no request to any host other than its own: no CDN, remote font, analytics, embed or remote image. Every asset SHALL be a file of the site, referenced by a relative URL that contains no `..`. Every page SHALL be at the site root, and only pictures and assets SHALL be in subfolders (Decision 46)。
3. THE site SHALL have no chat box and no control that starts an experiment, a session or a build-from-spec run, and SHALL send no data anywhere。
4. THE text, the discovered spec tables and the experiment entries SHALL be present in the HTML as written by the build, and SHALL need no script to be shown; moving pictures and the replay controls MAY need JavaScript。
5. WHEN the viewport is 360 CSS pixels wide、THE page's scroll width SHALL NOT exceed the viewport width; a wide table MAY scroll inside its own box。
6. WHEN a visitor's browser asks for reduced motion、THE site SHALL show each moving picture stopped on its first cell, with a control to step and to play it。
7. THE site's own text SHALL be in English。
### Requirement 4: Text by its author, shown as written
**対象:** ビルダーと訪問者。この規則は Dr. Kiro の言葉を守る。
**User Story:** 訪問者として、すべての文を誰が書いたかを見たい。また Dr. Kiro の言葉を、書かれたとおりに読みたい。主張を、私たちの解説や計測と区別できるようにするためである。
#### Acceptance criteria
1. THE site SHALL show every text in one of three inks, with fixed meanings used everywhere: Dr. Kiro's ink for text whose recorded author is Dr. Kiro; pencil for text whose recorded author is the bench (measurements, outcomes, condition classes, reasons, counts) and for numbers the build computes from them; commentary ink for the builder's text. Status words are the one exception: they are shown in the bench's stamp style (Requirements 8.2, 15.2)。
2. THE ink of a text SHALL follow from the author recorded with it in the record (`lab-bench` Requirement 9.5), or, for the notebook's own text, from the build source. IF the author of a text cannot be determined, THEN THE build SHALL fail, naming the text's place in the record。例外: Dr. Kiro がベンチに渡し、ベンチが書き手のない固定の語として記録する値（判定の語と、予測についての Dr. Kiro のラベル）は、Dr. Kiro のインクで見せる SHALL（要件 15.1、17.4）。THE build SHALL それぞれを、Dr. Kiro のレベルに加えてビルダーのレベルでもスキャンする（要件 20.1）（Decision 47）。
3. THE site SHALL show text written by Dr. Kiro as written: the same characters in the same order, with its line breaks, HTML-escaped, and not rendered as Markdown or HTML. The cells of a discovered spec table are shown as the bench's table reader gives them。
4. FOR ALL texts written by Dr. Kiro、the text content of the element that shows the text, parsed from the written HTML, SHALL equal the text in the record character for character, including line breaks (round-trip property)。
5. THE ink SHALL be distinguishable without colour: each ink SHALL also differ in typeface or style, and a legend of the three inks SHALL be reachable from every page。
6. Text SHALL have a contrast ratio of at least 4.5:1 against its background。
### Requirement 5: Honest numbers and words
**対象:** ビルダー。
**User Story:** 訪問者として、サイト上のすべての数値が記録された実行から来ていてほしい。実際より良く見せるものが何もないようにするためである。
#### Acceptance criteria
1. EVERY number THE site shows as a result SHALL be taken by the build from a record field (a measurement, a range, a count, a budget, a condition value) or computed by the build from record fields in a way this spec names。
2. THE notebook's source files SHALL contain no number presented as a result; tests use fixtures that are labelled as fixtures and are never written to a site (`rules.md` 4)。
3. THE site SHALL show measured values in lists, tables, charts and the cover rounded to 4 significant digits, and SHALL show the recorded value in full in the opened trial. Counts, budgets and ids SHALL NOT be rounded。
4. WHEN a measurement is a not-measured outcome、THE site SHALL show the outcome name and the bench's reason as recorded, and SHALL NOT show or plot a value for it。
5. THE commentary SHALL describe the body's motion only by direction, distance, heading, speed, symmetry and which channels were active, and SHALL contain no word that suggests human injury or disability (`rules.md` 4). A test SHALL check the commentary against a word list kept in `notebook/` and approved by the user; adding or removing a word needs the user's approval. Dr. Kiro's text is shown as written (4.3) and is not changed by this rule。
### Requirement 6: The visual system
**対象:** ビルダー（後続の部分の一貫性）とユーザー（結果を参照と比べる）。
**User Story:** 訪問者として、ダッシュボードではなく科学者の紙のノートがほしい。ページが作業の記録のように読めるようにするためである。
#### Acceptance criteria
1. THE builder SHALL write the visual system as a steering file, `.kiro/steering/notebook-visual.md`, before the pages are built: paper, the three inks, the miss red, the status stamp, pinned instant photos, sticky notes, the strike-through of a rejected row, type, spacing, and the narrow-screen layout。
2. THE site SHALL have one theme and no theme switch。
3. Moving pictures SHALL be shown as instant photos pinned to the page; side notes in commentary ink SHALL be shown as sticky notes。
4. THE miss red SHALL be used only for missed predictions and their measured values, and SHALL always come with the word "miss"; on the cover the stamp "missed" says it (13.9)。
5. Halloween SHALL appear only as small decoration that holds no text, does not overlap any text, table, chart or experiment entry, and does not lower the contrast of any text below the ratio of Requirement 4.6. THE decoration SHALL be inline in the page markup, not a separate file, and SHALL carry no namespace URL (Decision 46)。
6. WHEN the user describes a difference from the reference、THE builder SHALL update this requirement or the steering file first, and the pages after。
### Requirement 7: Picture sheets and moving pictures
**対象:** ビルダーと訪問者。
**User Story:** 訪問者として、各試行が動くのを見たい。数値を読まなくても、何が起きたかが分かるようにするためである。
#### Acceptance criteria
1. THE notebook SHALL keep a frame layout table, `notebook/layouts.toml`, with one entry per application: the number of frames, rows, columns, and the gap in pixels between cells, with the application's spec named as the source of each entry (`body-lab` design: 10 frames, 2 rows of 5, no gap; `wind-tunnel` Requirement 9.4: 6 frames, 2 rows of 3, a gap of 4 pixels)。
2. IF an entry's number of frames does not equal its rows times its columns, THEN THE build SHALL fail, naming the entry。
3. WHEN the build reads a trial's picture、THE build SHALL check that the media type is `image/png`, that the file passes the bench's picture check, and that its width and height divide exactly into the layout of its application (columns times the cell width plus the gaps, and likewise for rows). IF a check fails, THEN THE build SHALL fail, naming the record, the trial and the sizes。
4. THE notebook SHALL NOT change any file in `bench/`。
5. IF a record's application has no entry in the frame layout table, THEN THE build SHALL fail, naming it。
6. THE site SHALL show a moving picture by showing the cells of the sheet in reading order (left to right, then top to bottom), one at a time at a fixed rate set in the visual system, and then starting again。
7. THE site SHALL copy each picture as recorded, byte for byte, under a name made from its blob hash, and SHALL NOT re-encode it。
8. A moving picture SHALL have controls to pause, to step one cell, and to see the whole sheet at once; on a narrow screen and on a touch screen each control SHALL be at least 44 by 44 CSS pixels。
9. FOR each body-lab trial's moving picture, except the small pictures of the lab cards (Requirement 13.4)、THE site SHALL show beside it (on the cover, in the top row of the miss: 13.1) an enlarged picture of the moving body: a magnified view, derived by the build from the record's own picture sheet, in which the body in its cell is readable. THE build SHALL choose the region of the enlarged picture as the box, over all frames of the sheet, of the pixels that change between frames, plus a margin of 4 pixels, clipped to its cell; SHALL scale it by the smallest whole-number factor (nearest neighbour) that makes it at least as large as the frame; and, WHEN no pixel changes, SHALL use the whole cell. THE build SHALL NOT use the track to choose the region, because the records hold no mapping from track coordinates to picture pixels. THE build SHALL derive the enlarged picture at build time, SHALL NOT change the recorded PNG file (Requirement 7.7 still holds for it), SHALL write the enlarged picture as a file of the site with a name made from the blob hash, and SHALL give it the alt text "Magnified view of the picture beside it", which uses no word of the commentary word list (Requirement 5.5) (Decision 50). THE site SHALL NOT show an enlarged picture beside a wind-tunnel trial's moving picture, because the flow moves through the whole sheet and no region of it is the moving body (Decision 50)。
### Requirement 8: The discovered spec table
**対象:** 訪問者とビルダー。表を書いたのは Dr. Kiro で、検査したのはベンチ。
**User Story:** 訪問者として、発見された spec の表を中心に置き、各規則のステータスをベンチの言葉で、その証拠をひと押しで見たい。何が見つかり、どれほど確かかが分かるようにするためである。
#### Acceptance criteria
1. THE site SHALL show each table as the snapshot it comes from holds it (the `end` snapshot on the session page, or the step's snapshot in the replay): every row, in the order written, with every cell, and SHALL NOT add, drop, merge, reorder or edit a row, a status or a replacement。
2. EVERY row SHALL show its status word written out, in the style of the bench's stamp, labelled "checked by the bench" for a table from an accepted `end` snapshot and "not checked by the bench" for any other table. Colour MAY add to the word and SHALL NOT replace it。
3. WHERE a row has the status `rejected`、THE site SHALL strike the row through, keep its text readable, keep it in its place in table order, and show directly beside it a tab "replaced by <id>" with the id named in its "replaced by" cell; WHEN a visitor opens the tab, THE site SHALL show the replacing row's rule text in small type with a link to that row in its own place in the table (Decision 32)。
4. IF the "replaced by" cell of a `rejected` row names no row of the same table, THEN THE site SHALL show the cell as written, with commentary that it names no row of this table, and SHALL NOT pick a row or open a tab with a rule text。
5. WHERE a row has the status `partly`、THE site SHALL show each cited prediction whose outcome is miss in the miss red, with the word "miss", the registered range and the measured value。
6. WHERE a row has the status `observed`、THE site SHALL explain the word with the bench's check: "seen in experiments; no cited prediction missed; Dr. Kiro does not claim validated", and SHALL show, when the row is opened, the condition class of each cited prediction as recorded。
7. WHERE a row has the status `validated`、THE site SHALL show, when the row is opened, each cited hit whose condition class is `new-combination` or `outside`, with its condition class。
8. WHEN a visitor presses a row、THE site SHALL open the row's cited experiments and cited predictions: for each prediction, the hypothesis it belongs to, its conditions, its registered range, its condition class and Dr. Kiro's label, its outcome, and the measured value, each linking to its experiment entry (Requirement 11)。
9. THE scope cell SHALL be shown as Dr. Kiro wrote it, in Dr. Kiro's ink, with the run bands of the row (Requirement 9) beside it. THE build SHALL NOT read the scope text to compute anything。
10. WHERE one or more `rejected` rows name a row in their "replaced by" cell、THE site SHALL show on that row the reverse links "replaces <id>, <id>", one per such row, in table order, each linked to the rejected row。
11. THE site SHALL draw each row in full exactly once per table; a replacing row's rule text in a "replaced by" tab is the only repeated text。
12. FOR ALL generated tables、each row SHALL be drawn in full exactly once, each `rejected` row whose "replaced by" cell names a row of the table SHALL have exactly one tab naming that row, and each row's reverse links SHALL be exactly the `rejected` rows that name it (property test)。
13. WHERE a row has the status `rejected` and its "replaced by" cell names exactly one other row of the table、THE site SHALL show the row's "replaced by" tab open by default, so that the replacing row's rule text and the link to that row are readable when the table is shown, without a click. THE tab's content and link SHALL be as in 8.3, and a visitor MAY close the tab (Decision 49)。
14. THE site SHALL show each row of the table as a card, one block per row, with its stamp, its rule text and its other cells, each of the other cells with the name of its column as a small caption; the row's refused-end note and its opened row (8.8) SHALL be inside the card. THE header row SHALL stay in the HTML and out of sight. THE card of a `rejected` row SHALL be in the rewrite red (Decision 51). WHERE the column beside the margin has room for two cards, THE cards SHALL stand side by side。
### Requirement 9: What was run, beside each row
**対象:** 訪問者とビルダー。
**User Story:** 訪問者として、規則の scope の隣に、記録によれば実際に何が走り、どの試行も走らせなかったものが何かを見たい。主張を証拠と自分で比べられるようにするためである。
#### Acceptance criteria
1. THE build SHALL choose a row's parameter groups, its cited ticks, its prediction ticks and its marked span only from the row's cited trials and prediction trials; the other ticks of each run band SHALL be the remaining trials of those parameter groups in the same session (9.3)。
2. THE build SHALL divide the cited trials into parameter groups by the exact set of parameter names their experiments declare, the bench's definition (`lab-bench` Requirement 6.4). Experiments whose name sets differ SHALL never be one group, even if they share names, and a name shared by two groups SHALL NOT be treated as one parameter。
3. FOR each parameter of each parameter group of a row、THE site SHALL draw one run band: a tick for each value of the parameter among all trials of that parameter group in the session; the ticks of the cited trials stronger; the ticks of the prediction trials strongest; and the span between the lowest and highest cited value marked。
4. WHERE the parameter is a number knob、THE run band SHALL span the knob's declared range from the record's declaration, and the parts of the declared range outside the lowest and highest value of the parameter group in the session SHALL be hatched and labelled "no trial"。
5. WHERE the parameter is one Dr. Kiro declared (it has no declared range)、THE run band SHALL span from the lowest to the highest value among the parameter group's trials and the cited predictions' conditions, and only the parts outside the tried values SHALL be hatched as "no trial"。
6. THE site SHALL show combinations of tried values that no trial ran only through the condition class word of each cited prediction (`new-combination`), and SHALL NOT draw a grid of combinations。
7. THE parameter names Dr. Kiro declared SHALL be shown in Dr. Kiro's ink, with a link to the experiment file that declares them。
8. WHERE an application's knobs are functions of time (body-lab)、THE site SHALL also show, for each cited trial, one small line plot per channel of its computed input over time, from the record's `inputs`, against the declared range [-1, 1] of the channel, in pencil。 Not in this version (Decision 48)。
9. FOR ALL records and rows、the ticks of a run band SHALL be exactly the recorded values of that parameter for all trials of its parameter group in the session, and no hatched part SHALL contain such a value (property test over generated records)。
### Requirement 10: The session page
**対象:** 訪問者。
**User Story:** 訪問者として、発見されたものから始まり、すべての実験まで降りていける、セッションごとの 1 ページがほしい。どの主張も確かめられるようにするためである。
#### Acceptance criteria
1. THE session page SHALL show these sections first, in this order: the discovered spec table as a notebook page, with a sticky note pointing to the chosen missed prediction (Requirement 12) and the moving pictures of the chosen trials pinned in its margin; the highlight; the progress; Dr. Kiro's plan; and every experiment entry. The other sections of the session page (Requirement 17; Requirement 14.5 is not in this version and Requirement 16 is on hold, Decision 48) SHALL follow them。
2. IF the missed-prediction choice is "none", THEN THE sticky note SHALL show the choice file's reason。
3. THE highlight SHALL show the chosen contrast (two trials side by side) and the chosen best result as moving pictures with their measured values, labelled "chosen by a person"。
4. IF the contrast or the best result is "none", THEN THE highlight SHALL show "none" and the choice file's reason in its place。
5. THE progress SHALL show the budget used and the budget, the experiments by phase, and the counts of each prediction outcome, from the record。
6. Dr. Kiro's plan SHALL be the `tasks.md` of the session's last snapshot, shown as written (Requirement 4.3)。
7. WHERE a session is an ended session with an `end` snapshot、THE table SHALL come from that snapshot; WHERE a session is a stopped session with snapshots, THE table SHALL come from its last snapshot, with its status words labelled "not checked by the bench" (10.14 applies where the reader does not accept the table)。
8. EACH experiment entry SHALL show: the hypothesis's frozen part as written; its predictions, with conditions, range, condition class (labelled "classified at registration") and Dr. Kiro's label; the experiment file as written; each trial with its parameter values, its measurements or not-measured outcomes, and its moving picture; each prediction outcome; the verdict with Dr. Kiro's words; and the verdict flag if the bench recorded one。
9. IF an ended session's record has no `end` snapshot (body-1), THEN THE session page SHALL show "no table" in place of the table, with commentary that the record holds no table, and SHALL list every missed prediction of the session in its place. THE build SHALL NOT fill in a table. "No table" SHALL be used for no other case (Decision 45)。
10. WHERE an application's measurements include series (body-lab `track_x`, `track_y`, `track_heading`)、THE experiment entry SHALL show the recorded track of each trial as a small overhead path in pencil, unless the series is a not-measured outcome。 Not in this version (Decision 48)。
11. WHERE a record holds refusal entries with action `end`, and a quote part of a refusal message equals the id of a row of the shown table exactly, character for character、THE session page SHALL attach to that row a sticky note in the bench's stamp style: "the bench refused to end this session N times", with N the number of such refusal entries, each refusal message shown as recorded with each part in the ink of its recorded author, the note that the sealed row's status is the one shown in the table, and the commentary "the record holds no copy of the table that was refused" (Decision 33; body-2 R13)。
12. THE build SHALL attach the note of 10.11 only by exact equality of a quote part with a row id, SHALL NOT read any other meaning from a refusal message, and SHALL NOT infer or show what changed between refusals or between a refused table and the sealed table。
13. WHEREVER the site shows a refusal message、THE site SHALL show with it a commentary note that quotes in a refusal message are recorded with Dr. Kiro as author, and that some quotes, such as a summary of cited outcomes, are composed by the bench from Dr. Kiro's ids; the quote itself SHALL be shown as recorded, in Dr. Kiro's ink (Decision 34). Which quotes the note points to is decided in the design; without parsing the message, the note covers every quote part of the message。
14. IF the bench's table reader does not accept the table of the snapshot the page shows (this includes a table with no rows, which the reader refuses; every snapshot of the real records before `end` is such a table), THEN THE site SHALL show that snapshot's `## Discovered spec` section as written, in Dr. Kiro's ink; the message the reader returned, as returned, in pencil; and the commentary "the bench's table reader did not accept this table"; and, WHERE the table is not from an accepted `end` snapshot, the label "not checked by the bench". THE build SHALL NOT parse the message, SHALL NOT guess rows, and SHALL NOT call such a case "no table" (Decision 45)。
### Requirement 11: Links to one experiment
**対象:** 訪問者。
**User Story:** 訪問者として、1 つのセッションの 1 つの実験へ直接リンクしたい。証拠を誰かに示せるようにするためである。
#### Acceptance criteria
1. EACH experiment entry SHALL have an address made from the application, the session id and the experiment id, and the same inputs SHALL give the same address in every build。
2. WHEN a visitor opens that address、THE site SHALL show the session page at that experiment entry, opened。
3. EACH trial and each prediction SHALL have its own address within its experiment entry。
### Requirement 12: Choice files
**対象:** ビルダー（提案する）とユーザー（選ぶ）。
**User Story:** ユーザーとして、各セッションのハイライトと外れた予測を人が選び、そう表示されていてほしい。ベンチが行っていない選択を、サイトが主張しないようにするためである。
#### Acceptance criteria
1. EVERY record SHALL have one committed choice file, `notebook/choices/<application>/<session-id>.toml`, that names: a contrast (two different trial ids of the record) or "none"; a best result (one trial id) or "none"; a missed prediction (one prediction id) or "none"; and, for each "none", a reason written by the user of 1 to 300 characters。
2. THE builder SHALL propose candidates for each choice file, drawn from the record, and the user SHALL approve or change them before the file is committed。
3. IF a record has no choice file, or a choice file names no record, THEN THE build SHALL fail, naming it。
4. IF a choice names a trial or prediction that is not in the record, or a missed prediction whose outcome is not miss, THEN THE build SHALL fail, naming the choice。
5. IF a choice file says "none" for the missed prediction while the record has a missed prediction, THEN THE build SHALL accept it only with its reason, and the session page SHALL still list every missed prediction。
6. IF a record has no trial (wt-003) and its choice file does not say "none" for all three choices, THEN THE build SHALL fail, naming the choice file。
7. THE site SHALL label every chosen item "chosen by a person"。
8. THE reasons in a choice file are builder-level text and SHALL pass the blind scan at the builder level (Requirement 20)。
### Requirement 13: The cover
**対象:** 訪問者。
**User Story:** 訪問者として、外れた予測を 1 つ見せる、静かな最初の画面がほしい。実験が最後の編集をすることがすぐ分かるようにするためである。
#### Acceptance criteria
1. THE cover SHALL show, in this order: a head (a kicker, the title, the tagline and one line naming the three inks, linked to the ink legend); the missed prediction; the reader (13.11); and one tab per lab (13.4). THE missed prediction SHALL be a top row, a row of evidence below it, and the card of rules below that (13.2). THE top row SHALL hold the claim card (the prediction in Dr. Kiro's ink; the registered range and the measured value in pencil, one under the other, each with a small heading; and the stamp "missed" in the miss red), the sticky note (13.8) and, WHERE the trial is a body-lab trial, the magnified picture of Requirement 7.9. THE row of evidence SHALL hold one large instant photo playing the image sheet of the trial recorded with the outcome of the missed prediction that the cover file names, and the track (13.7)。
2. WHEN the table of that session's `end` snapshot has rows、THE card of rules SHALL show every row that cites the prediction as a card of its own and, for each such row that is `rejected`, one line in its card with the id and the rule text of the row that replaces it (the replacing row is not drawn again as a card); IF no row cites the prediction, THEN THE cover SHALL say so。
3. IF the cover file says "none" for the prediction, THEN THE cover SHALL say that the session has no missed prediction, in place of the photo。
4. BELOW, THE cover SHALL show one tab per lab, in the order of the cover file. THE panel of a tab SHALL show a small moving picture, the trial of which the cover file names, the lab's ended sessions (each with its trial count and the number of rows of its `end` table per status word, or "no table"), and a link to the lab's list of sessions. Only the panel of the checked tab SHALL show, with no script. WHEN the page is loaded, THE tab of the lab of the missed prediction SHALL be the checked one; IF the cover file says "none", THEN the first tab。
5. THE cover file, `notebook/choices/cover.toml`, SHALL name the session of 13.1 and either a prediction or "none", and the session and trial of each lab tab, with the four words of the tab (kicker, title, engine, unit); the cover SHALL label the choices "chosen by a person"; and the build SHALL fail, naming the entry, if the file is missing, names a stopped session, names a session, trial or prediction that is not in the records, names a prediction whose outcome is not miss, or says "none" while that session has a missed prediction。
6. THE cover's commentary visible before any detail is opened SHALL be at most 240 words, counted as whitespace-separated tokens, excluding Dr. Kiro's text and recorded values. Details SHALL open on demand。
7. WHERE the trial of 13.1 has recorded series measurements (body-lab track)、THE cover SHALL also show the recorded track of that trial as an overhead path in pencil in the row of the photo, unless the series is a not-measured outcome (Decision 36). THE track SHALL be drawn in a box cropped to the drawing, so that no empty band stands above or below it on a narrow screen (Decision 51)。
8. THE sticky note SHALL show the measured value with the name of the measurement and its unit, one sentence of what happened, and the conditions of the prediction, from the record alone: "expected <measurement> between <low> and <high> <unit>, measured <value> <unit>: below the range" (or "above the range"), with ", on the other side of zero" added WHEN the range lies on one side of zero and the value on the other; for a not-measured outcome, "expected <measurement> between <low> and <high> <unit>, not measured: <the recorded reason>". THE sentence SHALL NOT name a direction of travel, because the record declares none, and the build SHALL fail IF the value of a missed prediction lies inside its range。
9. THE cover SHALL NOT show a row for the outcome of the missed prediction; the stamp "missed" says it。
10. THE `<details>` of the cover SHALL be the last part of the card of rules, inside it。
11. WHERE the build has build-from-spec runs、THE cover SHALL show, after the missed prediction, a section of the reader: what the runs were, the committed request in words, and the number of runs that passed per setup, each number from the run files。
12. WHEN the viewport is 1000 CSS pixels wide or wider、THE top row SHALL have two columns, the magnified picture at the left and, at its right, the claim card and the sticky note side by side, and THE row of evidence SHALL follow below the top row, so that the prediction, the measured value and the stamp stand in the first screen with the picture (Decision 51). On a narrow screen the cover SHALL be one column in this order: the claim card, the sticky note, the magnified picture, the moving picture, the track and the card of rules。
### Requirement 14: Lab pages and stopped sessions
**対象:** 訪問者とビルダー。
**User Story:** 訪問者として、停止したものを含め、ラボのすべてのセッションを見たい。うまくいかなかったことが何も隠されないようにするためである。
#### Acceptance criteria
1. EACH lab SHALL have a page listing all its records, ended and stopped, in one list, with the same fields and the same type size for every record, ordered by session id in code-point order。
2. FOR each stopped session、THE site SHALL show the seal's end and the bench's reason as written, the budget used (the budget minus the recorded remaining budget), and what the record contains: the numbers of trials, experiments, hits and misses, the hypotheses registered and never run, whether there is a table, and, if the record has a failure entry, the action at which the session stopped。
3. THE commentary about a stopped session SHALL be one fixed text from the notebook's source, the same for every stopped session, with the bench's recorded reason shown as written beside it, and SHALL pass the blind scan at the builder level。
4. A stopped session SHALL NOT appear on the cover。
5. IF two or more trials of the same application, in any records, have the same recorded trial key (the hash of the computed inputs), THEN THE session page of each of those records SHALL show a compact list of those pairs: for each pair, the session and trial ids, each trial's parameter names and values as written, and whether all their recorded measurements are exactly equal (for example wt-002 T1 and wt-004 T1; the 9 pairs of body-1 and body-2). WHEN a visitor opens an entry of the list, THE site SHALL show the two trials' moving pictures side by side (Decision 35)。 Not in this version (Decision 48)。
6. A stopped session with snapshots SHALL have a session page with every section of Requirement 10, its table as in 10.7 and 10.14 (wt-002: its last snapshot's section as written, with the bench reader's message); a stopped session without snapshots (wt-003) SHALL have a page that shows only the content of 14.2 (the sentence of 16.9 is on hold, Decision 48)。
### Requirement 15: Verdicts and status words kept apart
**対象:** 訪問者。
**User Story:** 訪問者として、仮説に対する Dr. Kiro の判定と、ベンチが検査した規則のステータスを、決して混同したくない。`partly` と `rejected` が、読む場所ごとに 1 つの意味だけを持つようにするためである。
#### Acceptance criteria
1. THE site SHALL show a verdict only inside an experiment entry or a replay step, always as "verdict on H<n>:" followed by the word, in Dr. Kiro's ink, as Dr. Kiro's judgement。
2. THE site SHALL show a status word only in a discovered spec table row or in a reference to a row by its id, in the bench's stamp style, never in Dr. Kiro's ink. This is the one exception to Requirement 4.1. Commentary that defines a status word (Requirement 8.6, the ink legend, Requirement 18) MAY name the word in commentary ink, not in the stamp style。
3. WHERE the bench recorded a verdict flag、THE site SHALL show the flag as a bench note beside the verdict, with the recorded counts of each prediction outcome。
### Requirement 16: Replay

**On hold (Decision 48).** 以下の基準はすべて、書かれたままにする。ビルドは今はこれを実装せず、サイトにリプレイのページはない。
**対象:** 訪問者とビルダー。
**User Story:** 訪問者として、セッションを 1 実験ずつたどり、そのときのページを見たい。規則が取り消し線で消され、置き換えられる様子を、起きたとおりに見るためである。
#### Acceptance criteria
1. THE replay SHALL have one step for each snapshot taken after a verdict, in record order, and one final step for the `end` snapshot if the record has one. Snapshots taken after a run SHALL NOT be steps。
2. AT each step、everything on the session page SHALL show the state as of that step: the table, Dr. Kiro's plan and requirements from that step's snapshot; and the experiments, trials, outcomes, verdicts and budget from the record entries before that snapshot's entry in record order, plus that entry. WHERE a chosen item or a pinned picture is not among those entries, THE replay SHALL leave it out, with commentary that it has not been run at this step。
3. AT a step other than the `end` step、THE status words SHALL be shown with the characters Dr. Kiro wrote, in the bench's stamp style, labelled "not yet checked by the bench"。
4. WHERE a step's table holds a `rejected` row、THE replay SHALL strike it through and show its replacement beside it (Requirement 8.3). Strike-through SHALL appear only where a step's table holds such a row。
5. IF a `rejected` row's "replaced by" cell at a step is empty or names no row of that step's table, THEN THE replay SHALL strike the row through, show the cell as written, and show commentary that the named row is not in the table at this step, and SHALL NOT pick a replacement。
6. IF the bench's table reader does not accept the table of a step's snapshot (including a table with no rows), THEN THE replay SHALL show that step's table as in 10.14, and SHALL NOT guess its rows。
7. THE replay SHALL be labelled "replay of a sealed record" on every step, and SHALL NOT be presented as live。
8. THE replay SHALL have controls to step back, step forward and play. THE address of a step SHALL include its 1-based step number in record order, SHALL be the same in every build from the same inputs, and opening it SHALL show that step。
9. IF a record has no step, THEN THE session page SHALL show, in place of the replay controls, that the record has no snapshot to replay; for wt-003 this is shown in addition to the content of 14.2。
10. FOR ALL steps of all records、THE replay test SHALL check that the shown table equals the bench reader's rows of that step's snapshot, and that the shown entries are exactly the record entries before that snapshot's entry in record order, plus that entry。
11. A test fixture record, labelled as a fixture and never written to a site, SHALL have a middle step whose table holds a `rejected` row and its replacement, and the test SHALL check 16.4 against it。
12. WHERE a record holds refusal entries、THE replay SHALL show each refusal as an event of the step whose entries it belongs to by 16.2 (the first step whose snapshot entry comes after it in record order), with its message as in 10.11 and 10.13; in body-2 the two `end` refusals are shown in the `end` step, after the step of the E11 verdict. THE replay SHALL attach the refused-end note of 10.11 to a row only at a step whose table holds that row。
### Requirement 17: The prediction chart
**対象:** 訪問者。
**User Story:** 訪問者として、すべての予測を計測値と並べて見たい。外れが的中と同じくらい見えるようにするためである。
#### Acceptance criteria
1. THE session page SHALL show, within the progress (Requirement 10.5), a prediction chart of every registered prediction of the session。
2. EACH prediction SHALL show its registered range and its measured value on one scale per measurement, spanning the lowest to the highest of all registered range bounds and measured values of that measurement in the session, with the same mark size for a hit and a miss; a miss SHALL be in the miss red with the word "miss"。
3. A prediction that is not run or not checkable SHALL be shown with that word and its range, and with no measured value。
4. EACH prediction SHALL show its condition class in the bench's word, labelled "classified at registration", and Dr. Kiro's label beside it in Dr. Kiro's ink. WHERE they differ、THE site SHALL show both as they are, without comment on which is right。
5. EACH prediction SHALL link to its experiment entry。
### Requirement 18: How the lab works
**対象:** 訪問者。
**User Story:** 訪問者として、方法を数分で理解したい。表がなぜ信頼できるかが分かるようにするためである。
#### Acceptance criteria
1. THE page SHALL explain the two levels of spec: the builder's specs, which built the lab, and Dr. Kiro's lab spec, which it writes from evidence。
2. THE page SHALL say what Dr. Kiro can and cannot touch: its lab folder's spec and experiment files, the four bench tools, no shell, no other folder。
3. THE page SHALL show the two applications side by side, from the declaration in each record: knobs and ranges, measurements, budget, picture kind and goal. IF records of one application hold different declarations, THEN THE page SHALL show each distinct declaration with its session ids。
4. THE page SHALL show, per session, how often the bench refused and why: the count of refusals by action, and each refusal's reason as recorded (with "a path outside the lab" where the record has it)。
5. THE page's commentary SHALL NOT quote builder spec files, and SHALL name or link no file or folder outside a lab, including the repository's root `.kiro/` (Decision 43)。
### Requirement 19: Built from the spec
**対象:** 訪問者。実行は `build-from-spec` がリーダーで行う。この spec はそれを見せるだけ。
**User Story:** 訪問者として、発見された spec だけを読んだ Kiro が、リクエストが求めたことを、spec なしの場合や生の記録だけの場合と比べて、うまくできたかを見たい。失敗した実行も含めて。
#### Acceptance criteria
1. WHILE no build-from-spec run is committed、THE section SHALL say that there are no runs yet。
2. WHEN build-from-spec runs exist、THE build SHALL check each run record with its hash chain check before use, and SHALL fail as in Requirement 2.2 if a check fails。
3. FOR each run、THE section SHALL show the request in words, the pass condition as committed (its ranges) with the commit hash of the request file as recorded in the run record, the spec rows the reader named before running, the measured result, and pass or fail as recorded。
4. THE section SHALL group runs by request and show the runs of the three setups (with the spec, with no spec, with the raw record only) beside each other. WHERE a request has no run for a setup、THE section SHALL show "no run" in that setup's place。
5. Runs that failed or stopped SHALL be shown like the others, in the same list, at the same size。
6. THE build SHALL check pass or fail with the check `build-from-spec` provides, and SHALL fail, naming the run, if the recorded result disagrees. THE site SHALL NOT judge a run itself。
7. THE spec rows a reader relied on SHALL link to those rows of the session the spec came from。
8. THE implementation of 19.2-19.7 SHALL come in tasks after the `build-from-spec` spec defines its records; until then 19.1 holds。
### Requirement 20: Blind scan of the site
**対象:** ビルダー。
**User Story:** ビルダーとして、サイトを、ベンチ出力と同じブラインドスキャンで、各文の書き手のレベルで走査したい。公開によってモデルが漏れないようにするためである。
#### Acceptance criteria
1. BEFORE it writes the site、THE build SHALL scan every text that goes into the site with the bench's blind scan (`lab-bench` Requirement 15): the notebook's own text, choice files and the cover file at the builder level (terms, paths and file names, credentials); bench-written text from the records at the builder level; and Dr. Kiro's text at the Dr. Kiro level (paths and file names, credentials), using the author recorded with it。
2. IF the scan finds anything, THEN THE build SHALL fail, naming the source file and line and the kind of finding, and SHALL write nothing。
3. FOR each text file it writes to the site、THE build SHALL write one sidecar file `<file>.authors.json` in the format the bench's scan reads (`bench/src/bench/scan/levels.py`), listing the character ranges of the file by author, so that the blind scan can scan the written site again at each text's author level (for `publish`) without a change in `bench/`. IF a written text has no author, THEN the scan SHALL fail (`lab-bench` Requirement 15.7)。
4. THE pictures SHALL pass the bench's picture check (Requirement 7.3)。
5. A test SHALL show that a term planted in the notebook's own text fails the build, and that the same term in Dr. Kiro's text in a fixture record does not。
### Requirement 21: Reproducible build
**対象:** ビルダー。
**User Story:** ビルダーとして、同じ入力から同じサイトができてほしい。公開されたノートブックを再ビルドして、バイト単位で比べられるようにするためである。
#### Acceptance criteria
1. THE same inputs SHALL give the same site, byte for byte. THE build SHALL write no time, date, random value, host name or absolute path into the site。
2. THE build SHALL order everything it lists by a rule written in the design, never by file system order。
3. THE build's dependencies SHALL be locked in `notebook/uv.lock`。
4. A test SHALL build the site twice from the same inputs and compare every byte。
### Requirement 22: Done when
**対象:** ビルダーとユーザー。
**User Story:** ユーザーとして、ノートブックが完成する明確な時点がほしい。次の spec を始められるようにするためである。
#### Acceptance criteria
1. THE site SHALL build from the records of both labs in `sessions/`, with the committed choice and cover files。
2. EVERY row of every discovered spec table SHALL show its status word (test over all records)。
3. THE replay SHALL match the snapshots at every step (Requirement 16.10 and 16.11)。 On hold (Decision 48)。
4. THE user SHALL accept the first screen. The builder SHALL show the cover on a desktop screen and a 360-pixel-wide screen and record the user's answer in `docs/status.md`; any change the user asks for goes first into Requirement 6 or the steering file (6.6)。
5. THE session page of body-2 SHALL show its 8 `rejected` rows struck through, each with its "replaced by" tab (8.3) and each replacing row with its reverse links (8.10), and R13 SHALL carry the refused-end note (10.11); a test SHALL check this on the real body-2 record. The test of the strike-through at a middle replay step with the fixture of 16.11 is on hold (Decision 48)。
---
## Decisions
項目 1-13 は、この要件が書かれる前のセッションでユーザーが決めました。項目 14-31 は、ユーザーの委任のもとでビルダーが決めました（ユーザーの項目 14: "any remaining details: the builder decides and writes the decision into the requirements"）。項目 32-44 は、body-2 の記録が封印された後にユーザーが決めました。各項目に "(user)" と付けてあり、委任のもとでビルダーが決めた部分にはそう書いてあります。ここにあるものは、どの規則にも例外を作りません。
1. **What was run, per row**（user）。行が引用する実験のすべての試行。そのうち、行が引用する予測の試行を強調する。どちらも行が引用するものから来る（要件 9.1、9.3）。
2. **Prediction chart**（user）。すべての予測を見せる。条件クラスはベンチの言葉で "classified at registration" と付けて見せ、Dr. Kiro のラベルは Dr. Kiro のインクで隣に置く。違いはそのまま見せる（要件 17）。
3. **Frame layout**（user）。ノートブックは、アプリケーションごとの小さな表（フレーム、行、列）を持ち、各アプリケーションの spec を出典として名指しする。ピクセルサイズがレイアウトで割り切れないシートは、ビルドを失敗させる。`bench/` は変更しない（要件 7）。
4. **Highlight and cover miss chosen by a person**（user）。各セッションの選択はコミット済みのファイルで、サイトでは "chosen by a person" と表示する。ビルダーが候補を提案し、ユーザーが承認する。ファイルのないセッションはビルドを失敗させる（要件 12、13）。
5. **Verdicts and status words kept apart**（user はルールの決定をビルダーに委任）。ルールは要件 15: 判定は常に、実験エントリーまたはリプレイのステップの中で、Dr. Kiro のインクの "verdict on H<n>:" として見せる。ステータスワードは、表の行または行への参照にだけ、ベンチのスタンプのスタイルで現れる。
6. **Run and not run**（user）。ベンチの定義: 同じパラメーター名の集合、`outside`、`new-combination`、`inside`。表示は案 A: ノブごとに 1 本のバンド。宣言された範囲、試した値ごとの目盛り、行が引用する試行の強調、試した範囲の外を "no trial" としてハッチング。走らなかった組み合わせは、引用された各予測のクラスの語を通して見せる（要件 9.3-9.6）。
7. **body-lab parameters**（user）。Dr. Kiro が宣言したパラメーター名の集合でグループ化し、名前だけでは決して統合しない。名前は Dr. Kiro のインクで、実験ファイルへのリンクつき。宣言された範囲はないので、「走らなかった」は試した範囲の外だけを意味する。各チャンネルの入力の時間変化を、[-1, 1] に対して描く小さな折れ線プロット（要件 9.2、9.5、9.7、9.8）。
8. **Stopped sessions**（user）。終了したものと同じ一覧に、同じ大きさで、カバーには出さない。封印の end と理由は書かれたとおりに、使った予算、記録の内容。解説は、ブラインドスキャンに落ちる言葉で原因を名指ししない。記録をまたいで計算済み入力が等しい試行は、機械的に導出して並べて見せる（要件 14）。
9. **Replay steps**（user）。判定後のスナップショットごとに 1 ステップ、加えて `end` スナップショット。取り消し線は、スナップショットの表が `rejected` 行を持つ場所にだけ付ける。決して表示されないフィクスチャで検証する（要件 16）。
10. **Cover, option A**（user）。外れた試行のシートを再生する、大きな 1 枚のピン留め写真。予測は Dr. Kiro のインク、計測値は鉛筆、"miss" は赤。引用する行とその置き換えを隣に。下にラボごとのカード 1 枚と小さな動く画像。外れのないセッションは、そう述べる（要件 13）。
11. **Session page, option B**（user）。表を最初に、ノートのページとして、外れた予測を指す付箋と、余白にピン留めした動く画像つき。body-1 は、外れた予測つきの "no table" を見せる（要件 10）。
12. **Built from the spec**（user）。要件は今書く。実装は後のタスクで行う。実行が存在するまで、セクションはまだないと述べる（要件 19）。
13. **Only sealed records**（user）。ノートブックは `discovered/` ではなく `sessions/` を読む（要件 1.2）。
14. **Choice file content, and stopped sessions**（builder）。記録ごとに TOML ファイル 1 つ。contrast、best、missed prediction を持ち、それぞれユーザーの理由つきで "none" でもよい。試行のないセッション（wt-003）は 3 つすべてを "none" とする。ファイルは存在しなければならない。カバーはセッションをまたぐので、カバーの予測と各ラボカードの試行は、別のカバーファイルで指定する（要件 12、13.5）。
15. **Gap in the layout table**（builder）。wind-tunnel のシートには 4 ピクセルの隙間があるので（1208 × 404 = 3 × 400 + 2 × 4 、2 × 200 + 4）、表はセル間の隙間も持つ。これがないとセルを切り出せない。body-lab のエントリーは隙間 0（1600 × 360 = 5 × 320、2 × 180）（要件 7.1）。
16. **The end table is checked again at build time**（builder）。ビルドは `end` スナップショットにベンチ自身の表検査を実行する。食い違いは、壊れた記録かベンチの欠陥であり、ビルドを失敗させる（要件 2.4）。
17. **Status words in the middle of a replay**（builder）。ベンチは表を最後にしか検査しないので、それより前のステップの語は、Dr. Kiro が書いたとおりに、"not yet checked by the bench" と付けて見せる。ノートブックはステータスを計算しない（要件 16.3）。
18. **A table the reader does not accept at a middle step**（builder）。書かれたとおりに、ラベルつきの文とともに見せ、行は推測しない（要件 16.6）。これは記録をあるがままに見せるもので、何も補わない。ユーザーが確定した。Decision 45 で拡張。
19. **Ticks across the session, emphasis from the row**（builder）。走行バンドの目盛りは、セッション内のパラメーターグループのすべての試行である。したがって "no trial" は、セッション内に試行がないことを意味する。引用された試行と予測の試行は、より強く描く（要件 9.3）。これは brief（"conditions that no trial in the session ran"）と項目 1 を組み合わせたものである。
20. **Dr. Kiro's text not rendered as Markdown**（builder）。書かれたとおりに、エスケープし、改行つきで見せる。表のセルはベンチのリーダーから来る。Markdown を描画すると、見せるものが変わってしまう（要件 4.3）。
21. **Rounding**（builder）。一覧とチャートでは有効数字 4 桁。試行を開いたときは、記録された値の全体（要件 5.3）。
22. **Equal trials across records**（builder）。記録された試行キーと、記録されたすべての計測値の完全な一致で比べる。wt-002 と wt-004 だけでなく、そのような組が存在するところではどこでも見せる（要件 14.5）。
23. **Phone and motion**（builder）。狭い幅として 360 CSS ピクセル。モーション低減を尊重する。画像とリプレイは JavaScript を必要としてよいが、すべての文は必要としない（要件 3.4-3.6）。
24. **Inks without colour, and contrast**（builder）。各インクは、色に加えて書体またはスタイルでも異なる。文字のコントラストは 4.5:1 以上。Halloween の装飾はそれを下げない（要件 4.5、4.6、6.5）。
25. **Commentary word list**（builder）。動きの言葉づかいの規則は、`notebook/` にあるレビュー済みの一覧に対して、ノートブック自身の文でテストする（要件 5.5）。Dr. Kiro の文は書かれたとおりに見せる。
26. **Explicit folders, no overwrite**（builder）。すべての入力フォルダーと出力フォルダーは引数である。存在して空でない出力フォルダーは拒否される（要件 1.3、1.4）。
27. **Series measurements**（builder）。body-lab の記録された軌跡は、鉛筆の小さな経路として見せる。ベンチが記録した計測である（要件 10.10）。
28. **Cover length**（builder）。カバーの解説は最大 240 語（要件 13.6。60 語だった。Decision 51 を参照）。
29. **Build-from-spec pass or fail**（builder）。ノートブックは `build-from-spec` が提供する検査を使い、食い違えばビルドを失敗させる。実行を自分で判定することはない（要件 19.6）。
30. **Rescanning the written site**（builder）。ビルドは、公開（`publish`）のために、ブラインドスキャンが各書き手のレベルでサイトを再び走査するのに必要なものを書き出す（要件 20.3）。方法は項目 38 で決着した。
31. **Review pass**（builder）。基準をテスト可能性のために鋭くした（書き出す前に走る検査、fake 試行の規則とテストフィクスチャ、ベンチの文のインク、停止したセッションと途中のリプレイステップにおける未検査の表、"none" の選択、尺度と順序）。ユーザーの決定は変わっていない。
32. **Replacement display**（user）。行は表の順序のまま。取り消し線を引いた各 `rejected` 行の隣に、タブ "replaced by <id>" があり、開くと置き換える行の規則の文が小さな文字で見える。置き換える行は逆リンク "replaces <id>, <id>" を持つ。どの行も 2 回全体を描かれることはなく、プロパティテストで検査する。これは brief の "the row that replaced it stands beside it" についてのユーザーの読み方であり、文字どおりの読み方に優先する。body-2 はこれを必要とする: R11 と R13 はそれぞれ複数の行を置き換え、R1 は、自身が置き換える R2 より前にある（要件 8.3、8.4、8.10-8.12）。
33. **Refused ends are shown**（user）。ベンチのスタンプのスタイルの付箋 "the bench refused to end this session N times" を、id が拒否メッセージの引用の文字列と完全に等しい行に付ける（body-2 R13）。各メッセージは記録されたとおりに、各部分をその記録された書き手のインクで見せ、封印された行のステータスが表にあるものであるという注記と、解説 "the record holds no copy of the table that was refused" を添える。ノートブックは、拒否の間に何が変わったかを推測せず、メッセージから他の意味を読み取らない。リプレイでは、拒否は、その手前にあるエントリーを持つステップのイベントである（body-2: E11 の判定のステップと `end` のステップの間）。要件 18.4 の拒否の件数は残る（要件 10.11、10.12、16.12）。
34. **Quotes composed by the bench**（user）。引用 "H11.P3: hit/not-comparable" は、記録された書き手が `dr-kiro` なので、記録されたとおり Dr. Kiro のインクで見せる。解説の注記は、拒否メッセージの引用は Dr. Kiro を書き手として記録されること、そしてベンチが、表検査の引用結果の要約のように、Dr. Kiro の id からその一部を組み立てることを説明する。ベンチは変更しない。メッセージを解析せずに、組み立てられた引用へ機械的に注記を向けられるかどうかは設計に委ねる。できなければ、注記は拒否メッセージのすべての引用部分を対象とする（要件 10.13）。
35. **Equal trial keys**（user）。セッション id と試行 id、書かれたとおりのパラメーター、計測値が完全に等しいかどうかを示す、組のコンパクトな一覧。エントリーを開くと、2 つの動く画像が並んで見える（要件 14.5）。
36. **Cover choice**（user）。カバーは body-2 の H4.P1（試行 T12）を見せる: 前進と予測したが、ボディは後方へ動き、向きを変えた。引用する行は R4 で、R5 に置き換えられている。ラボカード: body-lab の body-2 T31、wind-tunnel の wt-004 T1。後方へのずれは画像ではかすかなので、カバーは写真の隣に、記録された軌跡も鉛筆で見せる。この部分は、ユーザーの委任のもとでビルダーが決めた（要件 13.7）。カバーファイル自体は、タスクで書く。
37. **Choice files, approved content**（user）。ファイルはタスクで、次の内容で書く:
    - body-lab/body-1: contrast T22 と T30、best T39、missed H8.P1。
    - body-lab/body-2: contrast T25 と T30、best T36、missed H8.P6。
    - wind-tunnel/wt-002: contrast T1 と T3、best "none"、理由 "no trial without shedding"、missed "none"、理由 "no prediction missed"。
    - wind-tunnel/wt-003: contrast、best、missed のすべて "none"、理由 "no trial was run"。
    - wind-tunnel/wt-004: contrast T1 と T8、best T12、missed H5.P3。
38. **Rescanning the written site, resolved**（user）。ベンチは今、書き手ごとの文字範囲を列挙するサイドカー `<file>.authors.json` を読む（`bench/src/bench/scan/levels.py`）。ビルドは書き出すテキストファイルごとにサイドカーを 1 つ書くので、`bench/` を変えずに、各書き手のレベルでサイトを再走査できる。これにより、以前の Open question 2（走査ファイルごとに書き手のレベルが 1 つ）は解決して削除され、以前の Open question 3 が今の Open question 2 になる（要件 20.3）。
39. **Strike-through tests**（user）。body-2 の表は `end` のステップにしか存在しないので、途中のリプレイステップの取り消し線は、フィクスチャ（16.11）でテストし続ける。end の表の取り消し線、置き換えのタブ、逆リンク、そして R13 の拒否された終了の注記は、実際の body-2 の記録でテストする（要件 22.5）。
40. **Order of delivery**（user）。設計とタスクのため。最初のマイルストーン: 実際の記録から描画した、カバーと発見された spec の表。それから止まって、画面をユーザーに見せる。2 番目: 実験の一覧と動く画像、停止したセッション、"How the lab works"、走行バンド。最後: 予測チャート、リプレイ、等しい試行の一覧、入力の時系列の線。「Built from the spec」の実装（要件 19.2-19.7）はこれらの後に来る。
41. **README limits line**（user）。ベンチが引用結果の要約を書き手 `dr-kiro` の引用として記録するという事実（項目 34）は、README のステップのために、制限の節の 1 行として記録する。オーケストレーターが `docs/status.md` に書き留める。
42. **Adapters installed for the scan**（user）。ベンチのブラインドスキャンは、各アプリケーションの宣言をインポートして許可リストを読む（`bench/src/bench/scan/terms.py`、`load_app`）。このインポートはアダプターパッケージを（それを通じて MuJoCo の Python パッケージと `wind-tunnel-model` も）インポートする。そのためノートブックは、ベンチと両方のアダプターパッケージにパスで依存する。それらをインストールするが、シミュレーター、ソルバー、Docker は動かさない（設計の以前の Open question 1 の選択肢 A）。選ばなかったもの: B、各アプリケーション自身の環境で別プロセスとしてスキャンを走らせる（ビルドはプロセスを起動せず、サイトはスキャンの前にディスク上に必要になる）。C、スキャンが宣言を別の場所から取れるようにベンチを変更する（`bench/` の変更であり、許可リストはアプリケーション自身の宣言から来なければならない、`rules.md` 1）（要件 1.5）。
43. **No link to the root `.kiro/`**（user）。"How the lab works" にはリポジトリのルートの `.kiro/` へのリンクがない。ノートブックはラボの外のファイルやフォルダーを名指しせず、リンクもしない。この問いは README を書くとき（README のステップ、`docs/brief.md` セクション 5 項目 8）に改めて決める。これにより以前の Open question 2 は解決して削除される（要件 18.5）。
44. **Rescanning the written site for `publish`**（user）。`publish` が書き出されたサイトをどう再走査するか（ベンチのフォルダースキャンはすべてのファイルをテキストとして読むので、サイトの PNG ファイルは失敗する）は、`publish` の spec を書くときに決める。ノートブックは今までどおりテキストファイルごとにサイドカーを 1 つ書き（要件 20.3）、書き出す前の自前のスキャンも残る（要件 20.1、20.2）。
45. **A table the bench reader does not accept**（user、2026-11-17）。`parse_table` は行のない表に対して `TableError` を送出する（"the discovered spec table has no rules"）。そのため実記録の `end` より前のスナップショットはすべて、リーダーが受理しない表であり、行のない表を、メッセージを解析することも 2 つ目のリーダーを持つこともなく（要件 2.6）、他の受理されない表と見分けることはできない。決定: リーダーが受理しない表は、行がなくても他の理由でも、`## Discovered spec` の節を Dr. Kiro のインクで書かれたとおりに、リーダーが返したメッセージをペンシルで、コメンタリー "the bench's table reader did not accept this table" とともに見せる。ビルドはメッセージを解析しない。"no table" は `end` スナップショットのない終了済みセッション（body-1）にだけ使い、そこでは外れた予測をすべて一覧する。wt-002（停止、最後のスナップショットに行なし）は、最後のスナップショットの節をメッセージつきで、"not checked by the bench" のラベルで見せる。N12 の端のケースは変えない: 置き換え先のセルが行自身を指せば "names this row itself"、一致なし（空を含む）なら "names no row of this table"、2 つ以上なら "names more than one row"（要件 10.9、10.14、14.6、16.6、設計 N27。Decision 18 を拡張）。

46. **Flat site and wording that avoids scan terms**（user、2026-11-17）。ビルダー自身のテキストのスキャン（タスク 8.1）は 4 点に印をつけた: 相対リンクの `../`（ラボの外を指すパスと読まれる）、スタイルシートの派生語 `linear`、`thickness`、`spacing`、装飾ファイルの `xmlns` の URL（サイトの `http:` 検査が拒否する）、スキャン語である画像の属性名とスクリプトの名前。決定: すべてのページをサイトのルートに置く。アドレスは `index.html`、`how.html`、`built.html`、`legend.html`、`<app>.html`、`<app>-<session>.html`、`<app>-<session>-replay-<n>.html`。画像は `p/<sha256>.png`、アセットは `a/notebook.css` と `a/notebook.js`。どのリンクにも `..` を含めない。ビルドは、application と session の id が小文字、数字、単独のハイフンだけであること、2 つのページが同じアドレスを持たないことを検査する。スタイルシートは、印のついた語を使わない言い換えにする（除外リストは使わない）。Halloween の装飾はインライン SVG で、`xmlns` を持たない。画像のレイアウト属性は `data-tile-width` と `data-tile-height`。サイトの `http:` 検査は厳格なまま。ビルダーのテキストへのスキャンの指摘は、常に言い換えで直す（design N28）（要件 3.2、6.5、11.1、20.1、20.2）。

47. **Dr. Kiro's fixed words**（user、2026-11-17）。タスク 12.1 で、判定の語と予測についての Dr. Kiro のラベルが、ベンチの `verdict` と `register` のエントリーに書き手のない素の文字列として記録されていること（ベンチのスキャンはこれらをベンチの文字列として扱う）、一方で同じ値が拒否の `given` には書き手 `dr-kiro` つきで現れることがわかった。要件 15.1 と 17.4 は Dr. Kiro のインクを求め、4.2 はインクが記録された書き手に従うとしている。決定: これらの語は Dr. Kiro のインクのままとし、要件 4.2 に例外として書く。Dr. Kiro がこれらを選び、ベンチは固定の集合と照らして検査しただけだからである。さらにビルドはそれぞれを Dr. Kiro のレベルに加えてビルダーのレベルでもスキャンし、この例外から語が漏れないようにする。ベンチと記録は変えない（要件 4.2、15.1、17.4、20.1、design N29）。

48. **This version stops after the prediction chart; the replay is on hold**（user、2026-11-17）。封印された記録のリプレイ（要件 16 とそのテスト）は保留とする。本物の封印済み記録が各ステップの表を示すまで、つまり Dr. Kiro のテンプレートを変えて、新しいセッションが途中のステップの表つきで走るまで待つ（本物の記録は最後のステップまで表が空なので、リプレイはほとんどのステップで空の表を見せることになる）。リプレイのコードはリポジトリに残し、今はビルドしない。この版に含めないもの: 等しい試行の一覧（要件 14.5）、body-lab の入力の線（要件 9.8）、実験エントリーの中の記録された軌跡（要件 10.10）。タスク 19、20、21（予測チャートより後のマイルストーン 3 の残り）は止める。予測チャート（要件 17）と要件 5.4 はこの版に残り、カバーの軌跡（要件 13.7）も残る。これらの要件、設計の節、Property 9 と等しい試行の Property は、「not in this version」または「on hold」と印をつけて文書に残し、ビルドは実装しない。これは Decision 40 の納品順序を変える（要件 9.8、10.1、10.10、14.5、14.6、16、22.3、22.5、design の Delivery order）。
49. **Rejected-row tab open by default**（user、2026-11-17）。`rejected` の行の "replaced by" タブは、表を見せるときに開いており、置き換える規則がクリックなしで読める。中身とリンクは Decision 32 のとおり（要件 8.13、design N31）。
50. **Enlarged picture of the body, body-lab only**（user、2026-11-17）。body-lab の各試行の動く画像の隣に、動く体を拡大した画像を見せ、セルの中の体が読めるようにする。wind-tunnel の画像には付けない。流れがシート全体を動くので、動く体にあたる領域がないためである。領域は、フレーム間で変わるピクセルの箱に 4 px の余白を足し、そのセルで切ったもの。フレーム以上の大きさになる最小の整数倍で拡大する（何も動かなければセル全体）。記録には軌跡の座標から画像のピクセルへの対応がないので、軌跡は使わない。記録された画像シートからビルド時に導出する。記録された PNG ファイルは変えない。代替テキストは、隣の画像の拡大表示であることを述べ、コメンタリーの語のリストの語を使わない（要件 7.9、design N32）。
51. **Notebook polish pass**（user、2026-11-19）。カバーは最初の画面で予測と外れを見せる。上の段に主張のカード、付箋、拡大した画像を置き、その下の段に動く画像と軌跡を置く（要件 13.1、13.12）。付箋は何が起きたかを、記録の数値だけから 1 文で言う（13.8）。外れた予測の結果の行は消す。判子が言っているためである（13.9）。details は規則のカードの中に入れる（13.10）。カバーは外れた予測のラボのタブを開いた状態にし、タブの並びはカバーのファイルの順のままにする（13.4）。カバーの上限は 240 語（13.6）。スマホ幅では軌跡の箱を絵に合わせて切り詰め（13.7）、画像のボタンは 44 px の大きさにする（7.8）。発見した spec の表はカードで見せる（8.14）。`rejected` の行とカードには書き直し用の赤（`--rewrite-bg` の上の `--rewrite-red`）を使う。これは外れの赤ではなく（6.4）、外れの赤は外れにだけ使う。スタイルシートは書体 Lora、IBM Plex Mono、Caveat を、サイト自身のファイルとして、ライセンスとともに同梱する。他のホストからは何も取得しない（3.2）。"spacing" は "ahead" と同じく風洞の設定値なので、除外リストに入れる。小見出しは字の間を少し空ける。詳細はステアリングファイル `notebook-visual.md` にある。
## Open questions
なし。
