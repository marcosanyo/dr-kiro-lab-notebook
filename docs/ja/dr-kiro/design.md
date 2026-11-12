> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/dr-kiro/design.md`](../../../.kiro/specs/dr-kiro/design.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `6ff10319d735b033972716c4f452ba8669588a16994adc498b8c5e0f0de80bae`

# 設計: dr-kiro

Requirements 1-7 を扱います。`lab-bench`（コア、フロントエンド F1-F12）の上に成り立ちます。ユーザーとともに行った決定は末尾に挙げています。

## 1. ラボの構成

```
<application>/lab/
  .kiro/
    agents/dr-kiro.json          agent definition (builder)
    agents/dr-kiro-prompt.md     the prompt (builder)
    steering/method.md           how to work with the bench (builder, always included)
    steering/workflow.md         the four phases and the discovered spec (builder, always included)
    hooks/                       confine.py, calllog.py and three hook files (builder, bench-lab-hooks)
    specs/lab/requirements.md    Dr. Kiro's files, written from the templates by bench-new-session
    specs/lab/design.md
    specs/lab/tasks.md
  experiments/                   Dr. Kiro's experiment files (git-ignored)
  pictures/                      written by the bench (git-ignored)
```

セッション設定はラボの外の `bench-run/<application>/<session id>.toml` に置きます（git の管理対象外、`structure.md`）。

## 2. パッケージ構成

```
bench/src/bench/drkiro/
  __init__.py
  lab.py            bench-make-lab: write the builder files, install the hooks
  session.py        bench-new-session: check, reset, write templates, start, write the config
  files/            the builder files and templates, as they are copied
    dr-kiro.json
    dr-kiro-prompt.md
    method.md
    workflow.md
    requirements.md
    design.md
    tasks.md
```

これらのファイルはパッケージデータで、バイト単位でそのままコピーされます。英語で書かれ（`rules.md` 5）、実行から取ったパス、部位の名前、数値を一切含みません。

## 3. エージェント定義 (Req 2)

`lab-bench` 設計 F10 に次のフィールドを加えます:

```json
{
  "name": "dr-kiro",
  "description": "Experimenter: discovers the spec of an unknown system from evidence.",
  "prompt": "file://./dr-kiro-prompt.md",
  "resources": ["file://.kiro/steering/**/*.md"]
}
```

- `file://` を使った `prompt` は、エージェントファイルのフォルダーを基準に解決されます（kiro.dev、カスタムエージェントの設定リファレンス）。
- `resources` は、開始時に 2 つのステアリングファイルを読み込みます。ステアリングのドキュメントには、カスタムエージェントは自分ではステアリングを読み込まないとあります。設定リファレンスには、カスタムエージェントは既定のリソースを継承するとあります。明示的な glob はどちらの場合でも機能します。継承される既定のリソースが追加しうるのはユーザー自身のグローバルなステアリングだけで、それはこのリポジトリのビルダーのテキストではありません。ほかのステアリングが現れないことは手動セッションで確認します（`lab-bench` の task 21、C14 と同様）。
- ステアリングのフロントマターは `inclusion: always` です。そのため、Kiro がこれらのファイルをステアリングとして読み込んでも同じように振る舞います。

## 4. プロンプト (Req 2.2)

10 行ほどです。内容は次のとおりです: あなたは実験者の Dr. Kiro である。ベンチのツールが説明する入力と計測項目以外は何も知らないシステムを研究する。目標はシステムの仕様であり、証拠に基づいて 3 つの仕様ファイルに書く。一人で作業する: ユーザーに決して質問せず、決して回答を待たない。`end_session` の呼び出しに成功するか、セッションが終了したとベンチが報告するまで続ける。方法とワークフローのステアリングに従う。方法のルールはプロンプトでは一切繰り返さないので、情報源は 1 つです。

## 5. ステアリング (Req 3)

### 5.1 `method.md`

短いセクションで、それぞれ数個の箇条書きです:

- **ループ。** `requirements.md` に仮説を書き、登録し、それを指定する実験ファイルを 1 つ書き、実行し、その画像を開き、判定を記録し、`design.md` と `tasks.md` を更新する。そして次へ進む。
- **仮説。** EARS の 1 文と `prediction` ブロック（形式は下記）。各予測は、計測項目、パラメーター値、計測がその外に出うる範囲を指定する。各予測には、自分が考える条件クラスのラベルを付ける。登録した後は、見出し、記述、ブロックを決して編集しない。メモと結果はブロックの下に書く。
- **実験。** ファイル形式（下記）: 最初の行は `# H<n>: <title>`、続いて `PHASE`、`MODE`、`PARAMS`、`TRIALS`、そして時間関数の入力ごとに関数を 1 つ。単純な数式だけ: 関数、ローカル変数、`if`、リストまたは `range` に対する `for`、リスト、算術演算、`math`。実験をまたいでパラメーター名を同じに保つ。パラメーター名を変えると予測が比較できなくなる。構造が異なる compare のバリアントには、フラグとなるパラメーターを加え、`if` でそれに応じて分岐する。入力の各組は 1 回だけ実行される。完全な繰り返しは拒否される。
- **画像。** 各試行の画像はファイルで、そのパスを実行が返す。ファイルツールで開く。
- **パス。** ファイルには自分のフォルダーからの相対パスだけを書き、絶対パスは決して書かない。
- **ベンチが断ったとき。** 拒否は何を直すべきかを述べる: 直して続ける。ベンチ障害はセッションを終わらせる: 止まる。

### 5.2 `workflow.md`

- **4 つのフェーズ**と、その `PHASE` の値: システムを把握する（`map`）、ルールを述べる（`rules`）、一度も実行していない条件を予測してルールを検証する（`test`）、ルールを使って最良の点を予測する（`best`）。それぞれの狙いを 1 行で述べる。test または best の予測には、`new-combination` または `outside` のラベルを付けるべきである。
- **予算。** 試行ごとに 1 単位を使う。test と best のフェーズのために十分な分を残す。数値は示さない。
- **各判定の後。** 今何を信じているかとその理由で `design.md` を更新し、`tasks.md` のタスクにチェックを付けるか、タスクを追加する。
- **終了。** `## Discovered spec` の表を埋める: 1 行に 1 つのルールで、その適用範囲、根拠となる実験と予測、ステータスを書く。4 つのステータスと、それぞれが当てはまるとき（`lab-bench` Requirement 12.3）を平易な言葉で述べる: 引用したどの予測も外れていなければ `observed`。引用したすべての予測が的中し、少なくとも 1 つが試していない条件のものである場合に限り `validated`。いくつかが的中しいくつかが外れたなら `partly`。1 つでも外れたなら `rejected` で、それを置き換えるルールの id を添える。その後 `end_session` を呼ぶ。拒否されたら、示されたとおりに表を直す。

### 5.3 例 (Req 3.6)

`method.md` と `workflow.md` は、`lab-bench` 5.1、5.2、7.1 の形式どおりのフェンス付きの例を載せます: 仮説ブロック、フラグとなるパラメーターを持つ compare 実験、sweep 実験、Discovered spec 表です。値はすべて山括弧のプレースホルダー（`<low>`、`<high>`、`<value>`、`<measurement>`、`<parameter>`）です。プレースホルダーは有効な TOML でも Python でもないので、例をそのままコピーしたものは、Dr. Kiro が埋めるまでベンチに拒否されます。例では汎用の入力名（`<input>`）を使うので、どのアプリケーションの名前も現れません。

## 6. テンプレート (Req 4)

```
requirements.md   # Requirements / ## Hypotheses
design.md         # Design / ## Observations / ## Discovered spec  + table header and separator row only
tasks.md          # Tasks / - [ ] Map the system / - [ ] State rules / - [ ] Test the rules / - [ ] Predict the best point
```

空の表はすべてのスナップショットに通り、`end_session` でだけ拒否されます（`lab-bench` 12.5）。

## 7. コマンド (Req 5)

### 7.1 `bench-make-lab <lab>`

エージェントファイルとプロンプトを `.kiro/agents/` に、2 つのステアリングファイルを `.kiro/steering/` にコピーし、`bench-lab-hooks` のインストーラーを実行します。上書きするのはそれらのファイルだけです。`experiments/` がなければ作成し、ラボの `.gitignore`（`experiments/`、`pictures/`）を書きます。

### 7.2 `bench-new-session`

```
bench-new-session --application <name> --adapter <module:factory> --scan-sources <toml> --stop-list <file>
                  --lab <lab> --state <dir> --sessions <dir> --session-id <id> --seed <n> --config-out <file>
```

引数はすべて必須です（`rules.md` 2）。手順は次のとおりで、どの手順もメッセージを出して失敗し、ステップ 4 より前では何も変更しません:

1. ラボにビルダーのファイルがある（`bench-make-lab` で作られたもの）。なければ拒否する。
2. 状態フォルダー内のすべてのセッションフォルダーで、最後のエントリーが封印エントリーである。そうでなければ、そのセッションを示して拒否する。セッションはフォルダーで区別する。この確認では、各記録を記録の検証器で開く。
3. 設定ファイルがまだ存在しない。セッション id は 1 回だけ使う。
4. `experiments/` と `pictures/` 内のすべてのファイル、および `.kiro/specs/lab/` 内の 3 つのファイルを削除する。これらは前のセッションの Dr. Kiro のファイルであり、封印済みの記録がそれらを保持している（`lab-bench` 13.2）ので、失われるものはない。
5. 3 つのテンプレートを `.kiro/specs/lab/` にコピーする。
6. 与えられた値で `Session.start` を実行する。拒否されたらそれを表示し、コマンドは失敗する。
7. 設定ファイル（`lab-bench` F7 のフィールド、パスはそのファイルからの相対パス）を `resume = true` で書き、セッションを閉じる。

## 8. セッションの実行 (Req 6)

`bench/README.md` に "Running Dr. Kiro" というセクションを加えます:

```sh
bench-make-lab body-lab/lab                       # once, and after builder files change
bench-new-session ... --config-out bench-run/body-lab/<id>.toml
export BENCH_SESSION_CONFIG="$PWD/bench-run/body-lab/<id>.toml"
export BENCH_HOOK_LOG="$PWD/bench-run/body-lab/<id>.hook-log.jsonl"
cd body-lab/lab
kiro-cli chat --agent dr-kiro                     # then type the start line
```

- 開始の一文: `Begin the session.` 再開の一文: `Continue the session.`
- 対話なしの場合（ビルダーが `KIRO_API_KEY` を持つとき）:
  `kiro-cli chat --v3 --no-interactive --require-mcp-startup --agent dr-kiro "Begin the session."`
  `--trust-all-tools` は使いません: エージェントの権限ルールが Dr. Kiro に必要なものをすでに許可しており、それ以外はフックが拒否します。
- セッションの後: `bench-stop` は、セッションが自分で終了しなかった場合にだけ使います。

## 9. テスト (Req 7)

例によるテストで、`bench/tests/drkiro/` に置きます:

| テスト | Req |
|---|---|
| `bench-make-lab` で作ったラボが、フェイクアプリケーションについて `bench-scan` に通る。 | 1.3, 7.1 |
| フェンス付きの各例が、プレースホルダーをフェイクの宣言に合うテスト用の値に置き換えたとき、`parse_hypothesis`、`prepare`/`compute`、`parse_table` に受け付けられる。 | 3.6, 7.2 |
| エージェントファイルが、`lab-bench` F10 にセクション 3 のフィールドを加えたものに等しい。 | 2.1 |
| `bench-new-session` が、開いているセッションがあると拒否する。実行後のラボにはビルダーのファイルとテンプレートだけがあり、セッションが開いていて、設定には `resume = true` がある。 | 5.2, 5.3, 7.3 |

手動（Req 7.4）: Kiro CLI で、`bench-run/fake/` にあるフェイクアプリケーションのラボを使い、予算 12 試行でセッションを 1 つ行います。ビルダーが送るのは開始の一文と、必要なら再開の一文だけです。合格条件: 記録が `ended` の封印で終わり、封印済みフォルダーに対する `bench-scan` が何も報告しないこと。

## 10. 要件の対応範囲

| 部分 | 要件 |
|---|---|
| `files/dr-kiro.json`, `files/dr-kiro-prompt.md` | 2 |
| `files/method.md`, `files/workflow.md` | 1, 3 |
| `files/requirements.md`, `design.md`, `tasks.md` | 4 |
| `lab.py` | 1.1, 5.1, 5.4 |
| `session.py` | 5.2, 5.3 |
| `bench/README.md` | 6 |
| `bench/tests/drkiro/`, 手動セッション | 7 |

## 11. 作業を止めて相談する条件

- Kiro CLI が `resources` を通じてステアリングを読み込まない場合、またはラボの外からステアリングを読み込む場合。
- 再開の一文では解決しない形で、Dr. Kiro が `end_session` の前に止まる場合。
- ブラインドスキャンがビルダーのファイルを検出し、唯一の解決策が除外リストの語になる場合。

## 決定事項

この仕様を書く前にユーザーが承認しました:

1. ラボは 1 つのコマンドで作ります。ビルダーのファイルはすべてのアプリケーションで同じです (Req 1, 5)。
2. ステアリングファイルは 2 つです: 方法とワークフロー (Req 3.1)。
3. Dr. Kiro はユーザーに決して尋ねません。開始の一文と再開の一文は固定です (Req 2.2, 6)。
4. 予算の配分は数値で示しません。最後の 2 つのフェーズのために予算を残します (Req 3.4)。
5. 例は目に見えるプレースホルダー付きで、`lab-bench` の形式で示します (Req 3.6)。
6. `rules.md` の文言チェックは過剰なため取りやめます。それについては Dr. Kiro のファイルに何も入れません。
7. 検証は最小限です: いくつかの自動テストと、短いフェイクセッション 1 つです (Req 7)。
