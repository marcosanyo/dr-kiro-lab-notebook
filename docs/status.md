# 現在の状況

Kiro Web とローカルの Kiro の引き継ぎ用です。セッションの最初に読み、最後に更新します（`.kiro/steering/handoff.md`）。
経緯は git と各 spec の tasks・Decisions にあります。

最終更新: Kiro Web、2026-11-19、ダークモード（夜の実験室）の後（ブランチ `feat/notebook-dark-mode`、main の 06c344e から）。

## ノートの棚（ブランチ `feat/notebook-shelf`、2026-11-19、ローカル）
- ノートの見せ方を作り直した。1 セッション = 1 冊のノート。夜が初期で、ボタンで昼。仕様は `.kiro/specs/notebook-shelf/`（訳つき）。
- 人が書くもの: `notebook/choices/<app>/<session>.toml` と `notebook/choices/cover.toml`。`model` は body-2 と wt-004 が `claude-sonnet-5.5`。body-1、wt-002、wt-003 は `<fill in>` のまま（聞いていない）。`date` は各記録が git に入った日。body-2 の題は目隠しスキャンが `Backwards` を拒んだので `The Reversed Wave`。
- **ロボットの絵の撮り直し（済み）:** `uv run notebook-retake --sessions sessions --out notebook/display --session body-1 --session body-2`。記録の入力から全 79 試行を走らせ直し、x、y、heading、track 3 本が記録と厳密に一致した。体を追う上からのカメラで 0.2 秒ごと 25 コマ、1 コマ 320px（床 50cm 幅）。シートは `notebook/display/`（20MB、色の下位 3 ビットを落としてある）、`manifest.toml` にハッシュと元の記録の絵のハッシュ。`notebook-build --display notebook/display` で表示。`scripts/view-notebook.sh` は付けてある。アダプターは変えていない（自由カメラで足りた）。
- **風洞の絵:** 走らせ直していない。大きい絵にはソルバーのサンプリングを変える必要があり、`wind-tunnel` の spec の変更になるため。代わりに記録のコマから体と渦のまわりを切り抜いて出す（`zoom.py`）。走らせ直すなら相談したい。
- 見た目: 数字は短く（`+3.9 cm`、`0.75 m`、`cd 0.993`）、見どころは写真 2 枚（一緒に再生、つまみ、「t = 3.0 s forward 38 cm」）、付箋 3 枚、枠つきのグラフで 1 画面、全部の実験は 2 列のカード、計画は 1 行で押すと全文、発見した spec は条件と根拠を閉じた。
- 見ていないもの: 実機の 360px の全体、昼の画面の細部（script 抜きと iframe で確認）。`notebook` のテストと ruff は通る。
## ダークモード（夜の実験室）（ブランチ `feat/notebook-dark-mode`）
- **済み（2026-11-19）:** システムの `prefers-color-scheme: dark` のときだけ、夜の配色になる。CSS だけで、切り替えボタンもスクリプトも保存もない。設定がなければ昼の紙のまま。
  - 見た目: 反転ではなく、ランプの下の暗い机に置いた同じノート。方眼の線、綴じ穴、余白の赤線、付箋（暗い黄色）、カード、タブはそのまま、色だけ夜の値。インクは明るい青（Dr. Kiro）、明るい鉛筆、温かい白（コメンタリー）。
  - 記録の画像（シート、コマ、拡大した画像）にはフィルターも反転もかけない。写真の枠は暗い中間色に 1px の縁（`--photo-edge`、昼は透明）。軌跡の SVG は `currentColor` のまま、インクの色に従う。
  - 外れの赤、書き直し用の赤、判子（MISSED を含む）は明るくし、役割は同じ。
  - 変わるのは `notebook.css` の `@media (prefers-color-scheme: dark)` の中の `:root` 1 つだけ（色のカスタムプロパティだけ）。`:root` に `color-scheme: light dark` を足した。動き、`prefers-reduced-motion`、レイアウト、文言は同じ。
  - spec: 要件 6.2 を「1 つの見た目、2 つの配色」に変え、Decision 52 を足した。設計の表、訳（ハッシュ）、`notebook-visual.md` の「Night lab」の節と夜のコントラストの組。
  - テスト: `test_visual.py` に夜の組のコントラスト（9 色 × 9 背景、すべて 4.5:1 以上）、夜の値とステアリングの一致、夜のブロックが色だけを変えること、切り替えもスクリプトもないことを足した。`_custom_properties()` は夜のブロックの外の `:root` だけを読むように変えた（昼の確認は今までどおり）。ゆるめたテストはない。
  - 画面: Playwright で dark と light、1280px と 390px、表紙、セッションページ（body-2）、spec の表（wt-004）。`.kiro/artifacts/screenshots/nm-*.png`。どれも横スクロールなし。
- **気づいたこと（直していない）:** 規則の文の「≤」（U+2264）が、同梱の Lora に字がなく四角に見える（昼も夜も同じ。前から）。
- **次の一手:** ユーザーがスマホで画面の画像を見て、直しを返す。そのあと PR を作る。
- `docs/brief.md` の「One theme, with no switch」はユーザーの文書なので変えていない。

## ノートの見た目の直し（ブランチ `feat/notebook-polish`、新しいブランチは切らない）
- **済み（2026-11-19）:** 表紙と spec の表を直した。1 つ直すごとにコミットした。
  - 除外リストに `spacing` を足した（ユーザー承認。出どころは風洞の `constants.toml` で、`ahead` と同じ）。小見出しは字の間を少し空けた。
  - 表紙: OUTCOME の行を消して MISSED の判子だけにした。付箋は記録の数字だけの 1 文にした（例: 「expected x between 0.2 and 3 m, measured -0.2047 m: below the range, on the other side of zero」）。
    details は規則のカードの中に入れた。ラボのタブは外れた予測のラボ（LAB II）を最初に開く（並びは LAB I が左のまま）。
  - 表紙の最初の画面: 上の段に予測のカード、付箋、拡大した画像シート、その下の段に動く写真と軌跡を置いた（1000px 以上）。スマホ幅では軌跡の前後の空白を詰めた。画像のボタンは 44px にした。
  - セッションページの発見した spec の表は、行ごとのカードで見せる。書き直し用の赤（`--rewrite-red`）は外れの赤と別にした。
  - 表紙の語数の上限は 240 語（ユーザー承認）。spec（要件 13 ほか）、設計、訳、`notebook-visual.md` を、できあがりに合わせて直した（この順で最後に直した）。
- **済み（2026-11-19、ユーザーの画面確認の後の直し）:**
  - 付箋: body-2 の宣言の `measured_by`（「x は開始時に体が向いている方向」）を読み、「expected to go forward 0.2 to 3 m, went back 0.2047 m」と言う。数字は記録のもので、表紙のいつもの 4 桁（0.2047。0.20 ではない）。`measured_by` に向きの文がなければ、前の中立な文のまま。
  - 動き: 拡大した画像（体が大きいシート）が 1 コマずつ動く。全体の画像は「whole picture」の側で、play を押したときだけ動く（body-lab のラボのカードの小さい画像も同じ）。コマの間隔は `notebook/layouts.toml` の `interval`（body-lab 220 ms、風洞 150 ms）。風洞は記録の 6 コマだけで、間のコマも補間もない。動きを減らす設定では止めた状態で始まる。
  - spec のカード: 閉じた状態は規則の文、状態の判子、replaced by の行だけ。scope と run band、experiments、predictions、開いた行は `<details>` を開くと出る（CSS の `:has` で隠す。`:has` がないブラウザーは全部見せる）。「What the record says was run…」はページの上に 1 回。rejected のカードは規則の文だけに取り消し線。
  - ゆるめたテスト: なし。構造に合わせて変えたもの: `test_milestone_1_real.py` の取り消し線の 2 件（取り消し線を引く範囲が規則の文だけになったので、確かめる範囲を合わせた。より厳しくなった）、`test_visual.py` の `@supports` の読み取りと取り消し線の確認、`test_photo_plots.py` の間隔の確認（CSS の変数から figure の `data-interval` へ）。
- **済み（2026-11-19、全体の絵と帯の直し）:**
  - 全体の絵（体が小さい）と、コマを並べた形は、ページのどこにも出さない（表紙、セッションページ、ラボのカード、スクリプトなしの場合も）。body-lab の試行は拡大した絵だけを見せる。「whole picture」を押すと同じ場所、同じコマで全体の絵に替わり、同じ間隔で 1 コマずつ動く。「magnified picture」で戻る。スクリプトがないときは最初の 1 コマだけ。ラボのカードも最初の 1 コマで、play で動く。風洞の絵は今までどおり。
  - 帯の説明は閉じた `<details>`（「How to read the bands」）にした。
  - R2 の replaced by の最後の「, R1」は、置き換える行へのリンクを文のあとに別に付けていたのが原因。記録の replaced by は R1 だけで、リストにあるのは記録の置き換えだけ。リンクは規則の文そのものにした。
  - main（#37、`build` が除外リストに入った）を取り込み、`stop-list.txt` と `test_scan.py` の衝突は `ahead`、`spacing`、`build` が全部残る形で直した。
  - 変えたテスト: `test_photo_real.py`（body-lab は拡大した 1 つの figure、全体のシートは名指しだけ、ラボのカードは最初の 1 コマ）、`test_photo_plots.py`（`"still"` から `"first"` と `data-whole-src`）。ゆるめたものはない。
- **済み（2026-11-20、絵の見出し）:** 表紙の拡大した絵の見出しから「the cells in reading order」を外し、「magnified around the body, one recorded frame at a time」にした。「whole picture」に替えると「the whole picture, one recorded frame at a time」に替わり、戻ると元に戻る。スクリプトがないときは最初の見出し。
- **次の一手:** ユーザーが画面を見て、直しを返す。そのあと PR を作る。
  （前の回の次の一手:）ユーザーがスマホで画面の画像を見て、直しを返す。そのあと PR を作る。PR の説明には、ゆるめたテストの 2 か所と、その理由を書く。
- **未解決:** main の風洞のテストが 2 件落ちている。ノートとは混ぜず、ノートの PR が終わった後に、別の小さな PR で直す。どの 2 件かは、まだ調べていない。
- `docs/ja/lab-notebook/tasks.md` の訳は、以前から原文と食い違っていた（ブランチ作成前から `ja-check` が止まっていた）。このとき原文に合わせて直した。

## brief の改訂（ブランチ `docs/brief-final-edit`）
- `docs/brief.md` を今の方針に合わせた: 題は Dr. Kiro's Lab Notebook、決め台詞は The experiment gets the final edit.。ノートは発見した spec の表が中心
  （ベンチの状態の語 4 つを文字で出す）。新しい spec `build-from-spec`（4.5）を足し、publish は 4.6 になった。`angle` [0, 15]°、画像は PNG の画像シート、
  MCP は決定済み、レイアウトは今のフォルダーに合わせた。`.kiro/steering/product.md` も合わせた。
- **次の一手:** `lab-notebook` の PR（下の「ラボノートブック」を参照）。その後に `build-from-spec` の要件を作る（4.5）。
- **済み:** Dr. Kiro の雛形（`bench/src/bench/drkiro/files/workflow.md` と各ラボの `lab/.kiro/steering/workflow.md`）に
  「否定された規則は表から消さず、`rejected` の行として残す」の 1 文を足した。`partly` と `rejected` のどちらに書くかは Dr. Kiro に任せたまま。
  これから始めるセッションは、この 1 文がある条件で始まる。`dr-kiro` の spec（要件 3.7、設計 5.2、Decision 8）に記録した。
  封印済みの body-1 と wt-004 はこの文なしで作られており、書き換えない。
- リプレイで取り消し線が出るのが、途中のスナップショットに表がある時だけかどうかは、`lab-notebook` の spec で確かめる。

## ラボノートブック、チェックポイント 11（ブランチ `feat/lab-notebook`）
- **2026-11-17、ユーザーの答え: 最初の画面は 4 つの直しつきで承認。**
  1. カバー: 広い画面でトラックを写真の横に置く（要件 13.1、13.7 の「beside」）。写真と予測の文の間の大きな空きをなくす。
     カードの「chosen by a person」はカードのそばに置く。
  2. カバー: 各行のスタンプに「checked by the bench」のラベルを残す（要件 8.2 はカバーにも当てはまる。spec の変更は不要）。
     60 語の上限（13.6）は、`<details>` の外のほかの説明文を削って守る。
  3. `rejected` の行: 取り消し線は行の文だけにかけ、スタンプのラベルにはかけない。
  4. 選んだ外れの付箋: 測定の名前を分けて読みやすくする（「measured x: <値>」）。
- 1、3、4 は `.kiro/steering/notebook-visual.md` に先に書き、その後にページを直した（要件 6.6）。
- この後の進み方は下の「ラボノートブック」を参照。

## ラボノートブック（ブランチ `feat/lab-notebook`、PR はこのブランチのもの）
- **今の状態:** タスク 1〜18 と 8.1 は済み。15.2 と 17 も済み。この版は予測のグラフまでで止める（Decision 48）:
  リプレイ（要件 16 とそのテスト）は保留: 本物の封印済み記録が各ステップの表を示すまで、つまり Dr. Kiro のテンプレートを変えて、新しいセッションが途中のステップの表つきで走るまで待つ。
  同じ試行数の比較、入力の線、試行ごとの軌跡はこの版に入れない。タスク 19〜21 は止めた。リプレイのコードはリポジトリに残るが、今はビルドしない。
- Decision 49: `rejected` の行の「replaced by」タブは、表を出したときに開いている（要件 8.13、設計 N31）。
- Decision 50: body-lab の各試行の動く画像の隣に、体の拡大画像を出す。wind-tunnel の画像には付けない（流れがシート全体を動くため）。領域は、フレーム間で変わるピクセルの箱に 4 px の余白を足し、セルで切ったもの。
  フレーム以上になる最小の整数倍で最近傍拡大し、何も動かなければセル全体。記録には軌跡の座標から画像のピクセルへの対応がないので、軌跡は使わない（要件 7.9、設計 N32）。
- **まだ:** タスク 22〜24（`built.html`、done-when のテスト、引き渡し）。拡大画像と開いたタブを 360px の幅でブラウザーで見ていない。
- body-1 の `measured_by`（質問 7）は答えた・閉じた。
- 納品の順序は Decision 40。ブラインドスキャンのため、ノートブックは `bench` と両方のアダプターにパスで依存する（Decision 42。シミュレーターやソルバーは動かさない）。
- 途中の段で読めない表は書かれたまま出す（要件 Decision 18、設計 N26）。
- ルート `.kiro/` へのリンクは置かない（README を書くときに決める）。公開時のサイトの再スキャン方法は publish の spec で決める。
- **README のステップへ:** README の限界に 1 行: ベンチの end 拒否文の中の引用 `H11.P3: hit/not-comparable` は、記録では書き手が Dr. Kiro になっている（ベンチの意図、`bench/src/bench/specfiles/discovered.py` の `_summary`）。ノートは記録どおり Dr. Kiro のインクで出し、注記を添える。ベンチは直さない（ユーザーの決定）。
## Dr. Kiro の spec の写し（ブランチ `feat/discovered-spec-export`）
- 終わった各セッションの Dr. Kiro の 3 ファイルを、封印された記録の最後のスナップショットから `discovered/<app>/<session>/` に写す
  （`bench-export-spec`）。`source.json` に元のエントリーと各ファイルの SHA-256 を書く。`bench-check-discovered sessions discovered` が
  全部の写しを記録と照らす（公開の前に実行し、テストでも動く）。`wt-004` の写しはコミット済み。body-1 は終了スナップショットがないので写しなし
  （`discovered/README.md` に理由）。`dr-kiro` 要件 5.4・8、Decisions 9〜12、`lab-bench` 要件 15.10・15.11。
- ラボの `.gitignore` から `.kiro/specs/` を外し、ラボの 3 ファイルはテンプレートの状態で git に入れた。
- **セッションが終わったら:** `bench-verify` と `bench-scan` の後に `bench-export-spec sessions/<app>/<id> discovered` と
  `bench-check-discovered sessions discovered` を実行し、封印済みフォルダーと写しを一緒にコミットする。
- **ローカルの作業ツリーの注意:** `body-lab/lab` と `wind-tunnel/lab` の `.kiro/specs/lab/` は、前のセッションの Dr. Kiro の内容のまま
  「変更あり」と表示される（git にはテンプレートが入っている）。次の `bench-new-session` がテンプレートに戻す。この 6 ファイルはコミットしない。
- 次の体のセッション（2 回目）は、新しいセッション id で始める。そのセッションには写しが作れる。

## 体の 2 回目のセッション（body-2）
- body-1 は最後の表が記録に入っていないので、body-2 を走らせる（`body-lab` タスク 6、設計の Decision 9）。body-1 は消さない。
- body-2 は、雛形に「否定された規則は `rejected` の行として残す」の 1 文が足された条件で走る（body-1 にはない）。シード 2。
- **済み（2026-11-16、`471ca88`）:** `ended` で封印、39/40 試行、再開の一文なし。検証・スキャン・書き出し・照合がすべて通った。
  表は 14 行（`validated` 2、`observed` 4、`rejected` 8）。写しは `discovered/body-lab/body-2/`。結果は `body-lab` タスク 6 に記録した。
- body-1 のラボの最後の 3 ファイルの控えは `bench-run/body-1/lab-final/`（git 管理外、この Mac だけ）。

## build-from-spec（ブランチ `spec/build-from-spec`、worktree `.worktrees/build-from-spec`）
- 要件は承認済み、設計まで完成（訳も `docs/ja/build-from-spec/`）。元のセッションは `sessions/body-lab/body-2`。
- 本命の依頼は `build-from-spec/requests/stop-ahead.toml`（6 回）。body-2 の 39 試行に範囲内のものは無いと確認済み。`straight-ahead` と `turn-right` は body-2 に範囲内の試行があるため走らせない（Decision 18）。範囲は走らせた後に変えない。
- 実装は、別のチャットのノートが main に入り、ユーザーが「始めて」と言ってから。
- **次の一手:** ユーザーに声をかけてから、元のフォルダーで実装する。最初に lab-bench の 2 つの修正（`discovered_table` 設定、`check_copies` が `sessions/build-from-spec/` を飛ばす）。
- 実装時に確かめること: 設計 9 節（headless の `kiro-cli chat --no-interactive` で確認が出ないか、`--resume`、ハッシュ名の画像が開けるか など）。

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
7. **【答えた・閉じた】body-1 の宣言の `measured_by`（タスク 14.1 で発見）。答え: 封印済み body-1 の start エントリーのシミュレーター名と版はそのまま残し、ノートは見せず、記録は変えない。** 封印済みの `sessions/body-lab/body-1` の start エントリーにあるベンチの文
   `measured_by` は、最後がシミュレーターの名前と版（「MuJoCo 4.0.1.」）で終わる。Dr. Kiro が見た可能性がある。body-2 の宣言にはない（宣言の違いはこの 1 点だけ）。
   ノートは `measured_by` を見せない（`lab-notebook` 設計 N30）。記録もベンチも変えていない。
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

## build-from-spec（ブランチ `feat/build-from-spec-project`）
- **済み:** タスク 1〜17（ベンチの修正、ソース試行つきのリクエストの確認、ラッピングアダプター、リーダーのファイル、作業フォルダー、縮約コピー、relied-on 行、結果プログラム、実行情報ファイル、実行チェック、ターン、テストつきの `bfs-run`）。チェックポイント 17 は通過。
- **18.1 observed:** インストールできた。`uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter --with-editable ./build-from-spec --with-editable ./wind-tunnel/adapter --with-executables-from build-from-spec --reinstall`
- **18.2 partly:** 素の Kiro CLI の `--resume` は observed（AMBER-17、往復 2 回、セッション 1 つ）。リーダーレベルのヘッドレスは not observed。
  以前のリーダーの実行の最初のターンで `bench-mcp` が起動に失敗した（終了コード 3）。原因は未特定。有力な仮説は、別のプロセスが状態フォルダーのロックを持っていたこと（`build-from-spec/README.md` を参照）。
- **18.3 限界あり:** 素の Kiro CLI は画像の blob を開かなかった。答えは 320x360 で、実際の大きさは 1600x360。要件 6.5 の限界であり、`record` の実行の前にユーザーの決定が要る。
- 計画外の本物の実行 `stop-ahead-none-1`（シード 1812、数えない）が `bench-run/build-from-spec/unplanned/` にある（git 管理外）。
- 本物の 6 回の実行は、この PR が main に入り、新しいブランチを切ってから始める。
- **次の一手:** 画像の限界と最初のターンの失敗についてユーザーの決定、その後タスク 19.1。
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
