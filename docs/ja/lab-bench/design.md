> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/lab-bench/design.md`](../../../.kiro/specs/lab-bench/design.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `633ca20f08a386981a4da2b5bcfb02986995804f55742bfacd18f2ef2c8db2a7`

# 設計: lab-bench（コア）

この設計は、コア（Requirements 1-16）をセクション 1-14 で扱い、フロントエンド（Requirement 17）を「決定事項」の後にある「フロントエンド」の部で扱います。コアのどの部分もフロントエンドに依存しません。コアは Python ライブラリと 2 つのコマンドから成り、フロントエンドはそれらをラップします。

この設計を書く中で行った決定は、末尾の「決定事項」に挙げています。

## 1. 概要

```
            front end (Req 17, "Front end")     builder / tests
                     |                                |
                     v                                v
   +------------------------------- core API (bench.core) ---------------------------+
   |  Session: start / register / run / verdict / end / stop   (one lock, Req 1.4)    |
   |    |            |            |            |            |                          |
   |  specfiles    lang         conditions   adapter      record ---- seal/verify     |
   |  (parse lab   (check +     (classify,   (contract,   (append-only log,           |
   |   spec files)  evaluate)    match)       fake app)    blobs, hash chain)         |
   |                                                         |                         |
   |                                       scan (blind scan, used by session + CLI)   |
   +----------------------------------------------------------------------------------+
```

- フロントエンドは Dr. Kiro のツール呼び出しをコアの呼び出しに変換し、その結果を表示します。フロントエンドはゲートを追加しません。
- セッションの状態はすべて記録から導かれます。セッションを開き直すと、そのログを再生します（セクション 6.4）。
- Python 3.12 標準ライブラリ以外の実行時依存はありません。使うのは `ast`、`tomllib`、`hashlib`、`json`、`zlib`、`fcntl`、`threading` です。開発時の依存は `pytest`、`hypothesis`、`ruff` です。

## 2. パッケージ構成

```
bench/
  pyproject.toml            uv project "lab-bench", Python 3.12, console scripts bench-scan, bench-verify
  uv.lock
  src/bench/
    core/
      session.py            Session and the six bench actions
      outcome.py            Ran / Refused / BenchFailure, Message spans
      ids.py                session, experiment, trial and prediction ids
    adapter.py              Adapter protocol and declaration types
    lang/
      check.py              syntax-tree whitelist
      evaluate.py           tree-walking evaluator with a step counter
      experiment.py         experiment file structure (header, PHASE, MODE, PARAMS, TRIALS, knob functions)
    specfiles/
      hypotheses.py         hypothesis blocks in requirements.md, frozen part
      discovered.py         the "## Discovered spec" table in design.md
      ears.py               EARS shape check
    conditions.py           condition classes and prediction matching
    record/
      store.py              append-only log and blob store in the bench state folder
      canonical.py          canonical JSON
      chain.py              SHA-256 hash chain, seal, verify
    scan/
      terms.py              term extraction (extractors: mjcf, wiring-json, fake-json)
      tokens.py             tokeniser shared by terms and text
      patterns.py           path, file name and credential patterns
      levels.py             author levels for files, records and sidecars
      scan.py               the scan call and the bench-scan command
    fake/
      adapter.py            fake application
      model/fake_model.json fake part names for scan tests
      scan_sources.toml
  tests/
    unit/ ...
    properties/
      test_session_machine.py   stateful test of the gates (Req 16.1-16.3)
      test_record.py            hash chain and reproducibility (16.4, 16.5)
      test_lang.py              evaluator whitelist and step bound (16.6)
      test_scan.py              blind scan and quoting (16.7, 16.8)
```

## 3. コア API と結果 (Req 1)

```python
class Session:
    @classmethod
    def start(cls, config: SessionConfig) -> Outcome: ...          # Req 3
    @classmethod
    def open(cls, config: SessionConfig) -> "Session": ...             # replay, section 6.4
    def register(self, hypothesis_id: str) -> Outcome: ...          # Req 6
    def run(self, experiment_path: str) -> Outcome: ...             # Req 4, 5, 7
    def verdict(self, experiment_id: str, verdict: str, words: str) -> Outcome: ...  # Req 8
    def end(self) -> Outcome: ...                                   # Req 10.4, 11.1, 12
    def stop(self, reason: str) -> Outcome: ...                     # Req 11.4, builder only
    def fail(self, action: str, public: str, detail: str) -> BenchFailure: ...  # Req 11.3, builder side only
```

- `fail` は、コアの外、つまりビルダー自身のプロセスで起きるベンチ障害（フロントエンドが画像ファイルを書く場合、F5）を、コアが自身の障害を記録するのとまったく同じように記録します: 公開用の理由を持つ `failure` エントリ、`builder.log` への詳細、そして `stopped` としての封印です。フロントエンドはこれを Dr. Kiro に公開しません。

- `SessionConfig` は必須フィールドだけを持ちます。`session_id`、`application`、`adapter`、`lab_dir`、`spec_files`（ラボからの相対パスで指定する 3 つのパス）、`experiments_dir`（ラボからの相対パス）、`state_dir`、`sessions_dir`、`seed`、`scan_sources`、`stop_list` です。フィールドが 1 つでも欠けていれば開始は拒否されます (1.3)。セッション ID はビルダーが与えます。これにより、同一の 2 つのセッションは同一の記録を生成します (3.4)。`open` は同じ設定を受け取り、記録の start エントリがそれと一致することを確認します。
- 返す内容: `run` は実験 ID、各試行の ID、計測値（または未計測結果）と画像、残りの予算を返します。`register`、`verdict`、`end` は残りの予算だけを返します。条件クラス、結果、フラグはノートブックのために記録されますが、返されません。ベンチ内部のパスが Dr. Kiro に届くことはありません。
- ラボの外を指すパス（絶対パス、`..` を含むパス、解決するとラボフォルダーの外になるパス、またはブラインドスキャンが検出したパス）は、拒否の中でそのまま返されることも、記録に書き込まれることもありません。拒否エントリには、パスの代わりにベンチの文として「a path outside the lab」が記録され、完全なパスは `builder.log` に書かれます (9.6)。こうしないと、パスを 1 つ打ち間違えただけでセッション全体が封印できなくなります。スキャンはどのレベルでもパスを検出するからです。
- `Outcome` は `Ran(result)`、`Refused(message)`、`BenchFailure(message)` のいずれかです (1.1)。
- `Message` はスパンのリストです。ベンチが書く `BenchText(text)` と、Dr. Kiro のファイルからコピーした `Quote(text, file, line)` があります。どのスパンも作成者を持つので、スキャンは正しいレベルを適用できます (15.4, 15.5, 15.8)。フロントエンドはスパンを表示するだけで、独自のメッセージ文を組み立てることはありません。
- セッションごとに 1 つの `threading.Lock` がすべての操作を囲み、状態フォルダーに対する `fcntl` ロックが、別のプロセスが同じセッションを開くことを防ぎます (1.4)。各操作は、読み取り、確認、追記を 1 つのクリティカルセクションの中で行います。
- コアは、フロントエンド、トランスポート、エージェントフレームワーク、フックのいずれからも何もインポートしません (1.2)。ruff のルール（`banned-api` / `flake8-tidy-imports`）と、`bench.core` を単独でインポートするテストがこれを強制します。

## 4. アダプター契約 (Req 2)

```python
@dataclass(frozen=True)
class FunctionKnob:  name: str; low: float; high: float; sample_times: tuple[float, ...]; trial_seconds: float
@dataclass(frozen=True)
class NumberKnob:    name: str; low: float; high: float
@dataclass(frozen=True)
class Measurement:   name: str; unit: str; kind: Literal["scalar", "series"]; not_measured: tuple[str, ...]
@dataclass(frozen=True)
class Declaration:   knobs: tuple[Knob, ...]; measurements: tuple[Measurement, ...]
                     picture: PictureKind; budget: int; fake: bool; goal: str; measured_by: str

class Adapter(Protocol):
    def declaration(self) -> Declaration: ...
    def run_trial(self, inputs: ComputedInputs, seed: int) -> TrialResult | TrialFailure: ...

@dataclass(frozen=True)
class TrialResult:   values: Mapping[str, float | tuple[float, ...] | NotMeasured]; picture: Picture
@dataclass(frozen=True)
class NotMeasured:   outcome: str; reason: str          # outcome must be declared for that measurement
@dataclass(frozen=True)
class TrialFailure:  public_reason: str; detail: str
```

- ノブ名と計測名は Python の識別子でなければなりません。実験ファイルと予測の中で使えるようにするためです。
- `sample_times` と `trial_seconds` は、宣言の他の部分と一緒に Dr. Kiro に伝えられます (2.10)。body-lab では、これらは制御レートから決まります。チャンネルと部位の対応およびその符号はアダプターの内部にとどまり、宣言には入りません。
- `PictureKind` はメディアタイプ（`image/png`、`image/gif`、`image/webp`）です。画像はそのタイプのバイト列です。
- ベンチはすべての `TrialResult` を検証します (2.4-2.6)。宣言されたすべての計測値があること、余分なキーがないこと、スカラー値が有限の浮動小数点数であること、系列値が有限であること、`NotMeasured.outcome` がその計測に対して宣言されていること、画像が宣言されたタイプであることを確認します。いずれかに違反すればベンチ障害です。
- `TrialFailure` は 2 つの部分から成ります。`public_reason` は Dr. Kiro の言葉で書かれ（「the run did not settle」）、ビルダーレベルのスキャンを経て記録と Dr. Kiro に渡されます。`detail`（ログ、トレースバック）はビルダー側のログにだけ書かれます。これにより、障害の後でも封印済みの記録をスキャンできる状態に保てます (11.3, 11.5, 13.1)。`run_trial` が送出した例外はベンチ障害となり、その `public_reason` は固定のベンチの文、詳細はトレースバックです。
- 画像は記録される前に、埋め込まれたテキストがないか確認されます。対象は PNG の `tEXt`/`zTXt`/`iTXt`/`eXIf` チャンク、GIF のコメント拡張とアプリケーション拡張、WebP の `EXIF`/`XMP` チャンクです。これらがあればベンチ障害です（Blind: ベンチが返すのは画像であり、それ以外は返しません）。
- ベンチは遅い試行を捕捉しません。長時間の実行はフロントエンドの扱う事柄です (17)。
- 決定性 (2.8, 2.9) はアダプターの性質です。ベンチがこれに頼るのは、完全な繰り返しを拒否するときだけです。

## 5. ラボ仕様ファイルの形式 (Req 6, 12)

`dr-kiro` のテンプレートは、ここに書かれたとおりにこれらの形式を使います。

### 5.1 `requirements.md` の仮説

````markdown
### H3: <short title>

WHEN <condition>, THE <system> SHALL <response>.

```prediction
[[prediction]]
id = "P1"
measurement = "<measurement name>"
range = [<low>, <high>]
label = "outside"            # inside | new-combination | outside | not-comparable
[prediction.when]
<parameter> = <value>
<parameter> = <value>
```

Notes and results appended here are free text (6.7).
````

- 仮説はレベル 3 の見出し `### H<n>`（`: title` は任意）で始まり、次のレベル 1 からレベル 3 の見出しまで続きます。
- **凍結部分** (6.1): 見出し行、ステートメント（見出しとフェンスの間のすべてのテキスト）、そして情報文字列が `prediction` である最初のフェンス付きブロック（フェンスを含む）です。その閉じフェンスより後はすべて自由です。凍結コピーは、そのスパンの正確なバイト列で、改行は `\n` に正規化されます。6.6 の比較はバイト単位の一致です。
- 予測ブロックは TOML で、`tomllib` で解析されます。予測 ID はローカル（`P1`）で、グローバル ID は `H3.P1` です。`range` は両端を含み、計測の単位で表します。`series` の計測に対する予測は登録時に拒否されます。
- EARS の形 (6.3, `ears.py`): ステートメントは 1 文で、`THE <x> SHALL <y>`、`WHEN <c>, THE <x> SHALL <y>`、`WHILE <c>, THE <x> SHALL <y>`、`IF <c>, THEN THE <x> SHALL <y>`、`WHERE <c>, THE <x> SHALL <y>` のいずれかに一致し、キーワードは大文字でなければなりません。内容は確認しません。
- 条件がノブの範囲外かどうかは、数値ノブと同じ名前のパラメーターについてだけ確認します。その他のパラメーターには宣言された範囲がありません (6.3)。

### 5.2 `design.md` の Discovered spec 表

```markdown
## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | <rule> | <scope> | E2, E5 | H4.P1, H6.P2 | validated | |
| R2 | <rule> | <scope> | E3 | H5.P1 | rejected | R3 |
```

- この表は `design.md` の最後のレベル 2 セクションでなければならず、表の後には空白以外何も置けません (12.1)。
- 表を確認するのは `end()` だけです。その時点で、表には少なくとも 1 行が必要です (12.5)。セッション中は空でも、存在しなくてもかまいません。スナップショットは `design.md` をそのままコピーし、確認は一切しません。受け付けられた `end()` の最後のスナップショットには、確認に通った `design.md` が入ります (10.4, 12.6)。ノートブックは表をここから読みます。
- リストはカンマ区切りの ID です。空のセルが許されるのは「predictions」と「replaced by」だけです。
- 12.3 のステータス確認は純粋関数 `check_row(row, record) -> list[Problem]` で、直接テストされるほか、ステートマシンの中でもテストされます。

## 6. セッションの流れ (Req 3, 6-11)

### 6.1 `run(path)` のゲート順序

確認は次の順序で行います。最初に失敗した確認で拒否となり、その時点ではまだ何も変わっていません (9.2)。同じ入力からは常に同じ理由が得られるよう、順序は固定です。

1. セッションが開いている（封印されていない）。
2. 登録済みのすべての仮説の凍結部分が一致する (6.6)。
3. ファイルが `experiments_dir` の中にあり、読み取れる。
4. 構文木のホワイトリスト (4.2)。ヘッダーが仮説を指している (7.1)。`PHASE` と `MODE` が有効である (7.2, 5.1)。
5. モードの制限 (5.1-5.3)。
6. 判定待ちの実験がない (7.3)。
7. すべての試行をステップ上限内で評価し (4.4-4.6)、計算済み入力を生成する。
8. どの試行も以前の計算済み入力を繰り返していない (7.4)。
9. 予算が試行の分をまかなえる (7.5)。
10. 3 つのラボ仕様ファイルが読み取れる。その内容はこの時点で読み込まれ、スナップショットに使われる (10.1, 10.2)。
11. アダプターで試行を順に実行する。障害が起きればここで止まる (7.8)。
12. 実験、試行、予測結果 (7.7)、スナップショットを記録し、結果を返す (7.6)。

スナップショットはステップ 10 で読み込んだ仕様ファイルを使います。そのため、試行の実行中にファイルが変更されても、ファイルとそれが属する実行の内容は一致します。

### 6.2 その他の操作

- `register(id)`: 開いていること、凍結の確認、ブロックの検索、解析、EARS、予測が有効であること (6.2, 6.3)、完全な繰り返しの確認 (6.5)、分類 (6.4)、凍結コピーとハッシュの記録。
- `verdict(eid, v, words)`: 開いていること、凍結の確認、実験が存在し判定がまだないこと (8.2)、値が有効であること、`supported` の確認 (8.3)、仕様ファイルが読み取れること、判定、フラグ (8.4)、スナップショット (10.1) の記録。
- `end()`: 開いていること、凍結の確認、判定のない実験がないこと、3 つのラボ仕様ファイルが読み取れ、一度だけ読み込むこと (10.2)、読み込んだ `design.md` での表の確認 (12)、その内容の最後のスナップショットを `"for": "end"` で記録 (10.4)、その後 `ended` として封印 (11.1)。拒否された `end()` はスナップショットを記録しません (10.3)。
- `stop(reason)`: 表の確認も最後のスナップショットも行わずに `stopped` として封印します (11.4, 10.5)。ビルダーだけが使えます。フロントエンドはこれを Dr. Kiro に公開しません。
- どの操作でもベンチ障害が起きると、公開用の理由を付け、最後のスナップショットを取らずにセッションを `stopped` として封印します (11.3, 10.5)。
- 予算がゼロのとき、`run` はステップ 9 で拒否しますが、`verdict` と `end` は引き続き使えます (11.2)。

### 6.3 ID とシード

- 実験には、ベンチが実行順に `E1, E2, ...` と番号を付けます。試行にはセッション全体を通して `T1, T2, ...` と番号を付けます。
- 試行のシード: `SHA-256(session seed as decimal text + ":" + trial number)` の先頭 8 バイトをビッグエンディアンで読んだ値です (3.2)。どちらのアプリケーションもこれを無視しますが、試行と一緒に記録されます。

### 6.4 記録からの状態

セッションは、記録にない状態を一切持ちません。`Session.open` はハッシュチェーンを検証し、ログを再生して状態を再構築します。これにより、フロントエンドはセッションを失わずに再起動でき、プロパティテストには状態を計算する 2 つ目の方法が得られます（セクション 10）。

## 7. 実験言語 (Req 4, 5)

### 7.1 ファイル構造

```python
# H3: <title>
import math

PHASE = "map"                       # map | rules | test | best
MODE = "sweep"                      # compare | sweep
PARAMS = ["amp", "period"]
SWEEP = ["amp"]                     # sweep mode only: the 1 or 2 swept parameters
TRIALS = [
    [0.2, 1.0],
    [0.4, 1.0],
    # ... exactly 6 rows in sweep mode, 1 to 3 in compare mode
]

def <function knob name>(t, amp, period):
    ...
```

- 最初の行 `# H<n>`（`: title` は任意）が仮説を指します。その行の `H<n>` より後の部分や、任意のコメントを変更しても、計算済み入力は変わらないので、新しい実験にはなりません (7.4)。
- `TRIALS` の各行は、パラメーターの値を `PARAMS` の順に与えます。辞書はサブセットに含まれないため、代わりにリストを使います。
- 各**関数ノブ**について、ファイルはそのノブと同じ名前の関数を定義します。この関数は `t` とパラメーターを名前で受け取ります。ベンチは各サンプル時刻にこの関数を呼び出します。
- 各**数値ノブ**については、そのノブが `PARAMS` に含まれる（値を直接与える）か、ファイルがそのノブと同じ名前の関数を定義してパラメーターを受け取り数値を返すかのどちらかです。必ずどちらか一方だけです。
- sweep モードでは、`SWEEP` に含まれないパラメーターはすべての行で同じ値でなければなりません (5.3)。
- compare の各バリアントは、同じ関数を通る `TRIALS` の行です。構造の異なるバリアントは、フラグパラメーターと `if` を使って表します。たとえば、ある行で `amp2 = 0` として 2 つ目のチャンネルを静止させます。`dr-kiro` のテンプレートにその例があります。

### 7.2 ホワイトリスト (4.2)

許可される構文木ノード: `Module`、`Import`（`import math` のみ、トップレベル）、`FunctionDef`（デコレーターなし、デフォルト値のない位置パラメーター）、`Return`、`Assign`（単一の名前のターゲット）、`AugAssign`、`If`、`IfExp`、`For`（単一の名前のターゲット、`else` 節なし、リスト値または `range(...)` 呼び出しを反復）、`Break`、
`Continue`、
`Compare`、`BoolOp`、`UnaryOp`、`BinOp`、`Constant`（int、float、bool。str はトップレベルの `PHASE`/`MODE`/`PARAMS`/`SWEEP` の値としてのみ）、`Name`、`List`、インデックス付きの `Subscript`（スライスなし）、`Call`、`Attribute`（`math` の数値関数と定数の名前に対する `math.<name>` のみ）、`Expr`（docstring のみ）、`Pass`、およびこれらに必要な演算子ノードとコンテキストノードです。

呼び出しが許されるのは、ファイル内で定義された関数、`math.<name>`、そして `abs`、`min`、`max`、`len`、`range`（整数の引数で、`for` の反復対象としてのみ）です。それ以外はすべて、行番号と構文要素を示して拒否されます。`While` はホワイトリストに含まれません。ループの反復ごとにステップが消費されるので、ステップ上限は再帰だけでなくループも制限します。

**ステップ上限: `STEP_BOUND = 5_000_000`**（task 6 の計測の後にユーザーが確認しました）。この上限は、1 つの実験ファイルのすべての試行とすべてのサンプル時刻にわたる、トップレベルを含むすべてのステップを数えます。上限を超えたファイルは拒否となります。これは実行のゲート順序 (6.1) のステップ 7 で、予算の確認より前、どの試行の実行よりも前に検出されるので、予算を消費しません。計測用のフィクスチャは `bench/tests/fixtures/step_bound/` にあり、`bench/scripts/measure_steps.py` で計測しました。最も重いものは 1,661,521 ステップを使いました。

### 7.3 評価器 (4.3-4.6)

- 確認済みの木を対象とする、木をたどるインタープリターです。実行のために `exec`、`eval`、`compile` を呼ぶことはありません。`ast.parse` は木を作るためだけに使います。
- 訪れたノードごとに 1 ステップが消費され、ファイル全体で `STEP_BOUND` (7.2) に対して数えられます。関数呼び出しの深さ (100) と評価の入れ子 (200) にも上限があるので、深い再帰は Python の `RecursionError` ではなく拒否になります。
- 値は `int`、`float`、`bool`、およびこれらのリストです。文字列はトップレベルの定数にだけ存在します。リストや文字列に対する算術、絶対値が 2^53 を超える `int` の結果、固定の上限より長いリストは拒否されます。これにより、1 ステップで際限なくメモリを確保することはできません。
- エラー（ゼロ除算、インデックスの範囲外、引数の数の誤り、`math` の定義域エラー）は、行とエラーを示す拒否になります (4.5)。引用される行は `Quote` スパンです (15.8)。
- 範囲と有限性は、すべての計算済み入力について確認されます。最初に失敗したサンプル時刻が示されます (4.6)。
- 計算済み入力: 数値ノブは浮動小数点数、関数ノブは宣言されたサンプル時刻での浮動小数点数のタプルです。試行キーは、計算済み入力の正規 JSON の `SHA-256` です (7.4)。

## 8. 条件と予測結果 (Req 6.4, 6.5, 7.7)

パラメーター集合 `S` と値 `v` を持つ予測について:

- **比較可能な試行**: 実験がちょうどパラメーター集合 `S` を（名前で）宣言していた、以前の試行です。
- **比較不能**: 比較可能な試行が 1 つもない場合です。
- `S` の各パラメーターについて、試した値とは比較可能な試行におけるその値の集合であり、試した範囲とはその最小値から最大値までです。
- **試した範囲の外**: いずれかの値が、その試した範囲の外にある場合です。
- **新しい組み合わせ**: すべての値がそれぞれ試した値のいずれかであり、かつその組（タプル）がまだ試されていない場合です。
- **試した範囲の内**: それ以外の場合です（すべての値が範囲内にあり、少なくとも 1 つの値が試した値の間に厳密に入っている）。
- すでに試された組とまったく同じ組は、登録時に拒否され、その実験が示されます (6.5)。

値は、TOML ブロックと `TRIALS` のテキストから解析した浮動小数点数として比較されます。同じ 10 進表記からは同じ浮動小数点数が得られます。

実行後の予測結果: その実験の試行のうち、同じパラメーター集合と同じ値を持つものを使います。その計測値が範囲内なら的中、範囲外なら外れ、`NotMeasured` なら確認不能、一致する試行がなければ未実行です。後から変わりうるのは未実行だけです (7.7)。

判定フラグ (8.4) は、その仮説のすべての予測の現在の結果を使います。

## 9. 記録と封印 (Req 9, 10, 13)

### 9.1 ベンチの状態フォルダーでの保存

```
<state_dir>/<session-id>/
  log.jsonl          one entry per line, append-only
  blobs/<sha256>     experiment files as written, snapshots, pictures
  builder.log        wall-clock times, adapter detail, tracebacks (not hashed, not sealed)
```

- エントリ: `{"seq": n, "kind": ..., "body": {...}, "prev": <hash>, "hash": <hash>}`。種類: `start`、`register`、`refusal`、`experiment`、`trial`、`outcome`、`verdict`、`flag`、`snapshot`、`failure`、`seal`。
- `snapshot` エントリは `for`（`experiment`、`verdict`、`end` のいずれか）、前の 2 つの場合は実験 id、3 つの仕様ファイルそれぞれへの blob の参照を持ちます。封印された `ended` の記録には、`seal` エントリの直前にちょうど 1 つの `end` スナップショットがあります。`stopped` の記録にはありません (10.4, 10.5)。
- テキストフィールドはすべて `{"author": "bench" | "dr-kiro", "text": ...}` です。メッセージは作成者付きのスパンのリストです。blob への参照は、その blob の内容の作成者を持ちます (9.5)。
- `hash = SHA-256(prev + canonical JSON of the entry without "hash")`。最初の `prev` は 64 個のゼロです。blob はエントリの中で SHA-256 によって参照されるので、チェーンはすべてのファイルを対象にします (13.3)。
- 正規 JSON: キーはソート済み、空白なし、UTF-8、浮動小数点数は Python の `repr` で表記、NaN や無限大はなし。実時間の値は含みません (3.3)。
- 書き込み: 行を追記し、ファイルとフォルダーをフラッシュして `fsync` します。ログファイルは追記モードでのみ開きます。

### 9.2 封印

1. `seal` エントリを追記します。内容は終了理由（`ended` または `stopped`）、理由の文、残りの予算、最終ハッシュです。
2. 記録された作成者を使って、ログと blob に対してブラインドスキャンを実行します (13.1, 15.6)。検出があれば封印は失敗し、そのエントリまたは blob と行が示され、記録は状態フォルダーにだけ残ります。
3. `log.jsonl` と `blobs/` を `sessions/<application>/<session-id>/` にコピーします。上書きは拒否します (13.5)。コピーはその隣の一時フォルダーに書き込んでから名前を変更するので、書きかけのセッションが現れることはありません。

`bench-verify <folder>` はチェーンとすべての blob のハッシュを再計算し、最初の不一致を示します (13.4)。

### 9.3 記録の内容 (13.2)

上記のエントリは、13.2 に挙げたすべてを保持します。`lab-notebook` 仕様はこれだけを読みます。ここにないものが必要になった場合、それは 2 つ目の情報源を作るのではなく、この仕様の変更になります。

## 10. フェイクアプリケーション (Req 14)

- ノブ: 識別子の名前を持つ関数ノブ 1 つと数値ノブ 1 つ。計測: スカラー 2 つと系列 1 つ。スカラーの 1 つは、入力に対する決定的なルールで発生する未計測結果を宣言します。
- 試行結果は、入力の単純な閉じた形の関数です。これは本当の結果ではなく、宣言には `fake = True` があり、記録にもそれが残ります (14.5)。
- 画像: `zlib` で書いた、テキストチャンクを持たない小さな PNG です。
- 障害と未計測結果は、固定の入力値によってのみ発生します (14.2)。そのため、新しいアダプターで開き直したセッションも同じように動作します。`gain` が 2.5 を超えると `turn` について未計測結果 `lost` が返り、`gain == 0.125` では `TrialFailure` が返り、`gain == 0.375` では例外が送出されます。アダプターは状態を持ちません。
- `fake/model/fake_model.json` は架空の部位名を保持し、`scan_sources.toml` はそれを `fake-json` 抽出器とともに指定します (14.3)。

## 11. ブラインドスキャン (Req 15)

### 11.1 ソースと用語

- 各アプリケーションは `<application>/adapter/scan_sources.toml`（`lab/` の外）を持ち、そこにモデルファイルとソルバーファイル、およびそれぞれの抽出器を列挙します (15.2)。ベンチは `mjcf`（`rules.md` に従い、`name`、`class`、`joint`、`material`、`texture`、`model` 属性の値）、`wiring-json`（アクチュエーター名）、`fake-json` を同梱します。`wind-tunnel` 仕様は独自の抽出器を追加します。
- 用語には、各ソースファイルについて、そのファイル名、最初のドットの前の部分、最後のドットの前の部分も含まれます。他の用語と同じく、許可リストと除外リストで除かれます。（11.2 のファイル名パターンは別です。）
- 許可リスト（宣言にあるノブ名、計測名、未計測結果名）と除外リストのファイルにある語を取り除きます (15.3)。

### 11.2 照合

- テキストと用語は、文字でも数字でもない文字、および camelCase の境界で分割され、小文字のトークンになります。用語は連続するトークンの並びに一致します。そのため `upper_arm` は「upper arm」「upperArm」「upper-arm」に一致し、`leg` は `leg_amp` や「legs」に一致します（複数形の `s` と `es` も照合されます）。
- トークンがすべて数字である派生語（たとえば `01` という名前）は、決して用語になりません。
- パス: `..` セグメント、絶対パス、および `model/`、`adapter/`、ソースが指定するソルバーディレクトリ、ソースファイルの名前のいずれかを含むパスです。絶対パスとは、既知のルートフォルダー（Linux と macOS: `/home`、`/root`、`/Users`、`/private`、`/var`、`/Volumes`、`/opt`、`/etc`、`/tmp`、`/usr`、および `patterns.py` にあるその他のもの）、`~/`、またはドライブ文字で始まるパスです。こうすることで、実験コード中の除算がパスと見なされることはありません。スキャン時には、現在のホームフォルダーとリポジトリの絶対パスも、それが何であれ検出対象になります。
- ファイル名: 各ソースファイルのフルの名前と、そのステム（最初のドットの前の部分）を、全体として、大文字小文字を区別せず、両方のレベルで照合します。ステムは、1 文字のとき、または除外リストにあるとき（用語と同じトークン形式）はスキップします。フルの名前は常に照合します（要件 20、C1）。
- 認証情報: AWS アクセスキー ID（`AKIA`/`ASIA` + 16）、秘密鍵のヘッダー、GitHub トークンのプレフィックス、および長い値が続く `key|secret|token|password` の代入です。パターンは `patterns.py` にあります。

### 11.3 レベル (15.4-15.7)

- `lab/` フォルダーの中では、Dr. Kiro の 3 つの仕様ファイルと `experiments/` 内のすべてが Dr. Kiro レベルで、それ以外はすべてビルダーレベルです。
- 記録の中では、各テキストフィールドと各 blob に記録された作成者に従います。
- その他の生成ファイル（ノートブックのビルド出力、公開ファイル）は、作成者ごとの文字範囲を列挙したサイドカー `<file>.authors.json` を持たなければなりません。これは `lab-notebook` 仕様が生成します。スキャン対象のファイルにレベルの情報源がなければ、スキャンは失敗します (15.7)。
- `lab/` フォルダー内の画像（`.png`、`.gif`、`.webp`）はテキストとして読まれません。拡張子が示すメディアタイプについて `check_picture`（セクション 4）を通り、失敗は種類 `picture` の検出になります (15.9)。
- `dr_kiro` の glob に当てはまるラボのファイルで、バイトが `bench.drkiro` のパッケージデータにある 3 つのテンプレートのどれかと等しいものは、ビルダーレベルです（`scan/scan.py` の `TEMPLATE_BYTES`、15.11）。
- `source.json` のあるフォルダーは最終仕様の写しです（`scan/levels.py` の `copy_pieces`、15.10）: 3 つのファイルは、SHA-256 が `source.json` の示すものと等しいとき Dr. Kiro のレベルで、`source.json` の文字列はビルダーレベルです（記録と同じくハッシュは飛ばす）。不一致、欠けたファイル、それ以外のファイルはスキャンを失敗させます。ハッシュが記録のものかどうかは、スキャンではなく `bench-check-discovered`（`dr-kiro` 設計 7.3）が確認します。
- `bench-scan <paths...>` は検出ごとに `file:line: kind: match` を出力し、検出が 1 つでもあれば 0 以外の終了コードで終了します。

### 11.4 Dr. Kiro への出力 (15.8)

どの結果を返す前にも、セッションは各 `BenchText` スパン、計測名、公開用の理由をビルダーレベルでスキャンし、各 `Quote` スパンを Dr. Kiro レベルでスキャンします。検出があればベンチ障害です。その公開用の理由は固定のベンチの文で、検出内容は `builder.log` に書かれます。

## 12. 要件の対応範囲

| 部分 | 要件 |
|---|---|
| `core/session.py`, `core/outcome.py` | 1, 3, 6.6, 7.1-7.6, 7.8, 8, 9.1, 9.2, 10, 11 |
| `adapter.py` | 2 |
| `lang/` | 4, 5, 7.4 |
| `specfiles/hypotheses.py`, `ears.py` | 6.1-6.3, 6.6-6.8 |
| `specfiles/discovered.py` | 12 |
| `conditions.py` | 6.4, 6.5, 7.7, 8.4 |
| `record/` | 3.3, 3.4, 9.3-9.5, 13 |
| `fake/` | 14 |
| `scan/` | 2.2, 13.1, 15 |
| `tests/properties/` | 16 |

## 13. テストするプロパティ (Req 16)

ステートフルテスト（`hypothesis.stateful.RuleBasedStateMachine`）は、一時的なラボの中でフェイクアプリケーションに対して実行します。そのルールは次のことを行います。仮説を書いて編集する（有効なもの、無効なもの、凍結部分の内側と外側の編集、追記されたメモ、元に戻す操作）、登録する、実験ファイルを書く（有効なもの、禁止された構文要素、範囲外、繰り返し、多すぎる試行）、実行する、判定を与える（すべての値、結果と一致するものと矛盾するもの）、Discovered spec 表を書く（各ステータス、整合するものとしないもの）、終了する、停止する。テストは、期待される状態の単純な参照モデルを保持します。

各ステップの後の不変条件:

| # | プロパティ | Req |
|---|---|---|
| P1 | 仮説がそれより前に登録されていない実験は、一度も実行されていない。 | 7.1 |
| P2 | 操作が受け付けられている間、すべての凍結部分は記録されたコピーと一致していた。 | 6.6 |
| P3 | 予測ブロックの後に追記されたテキストが拒否を引き起こしたことはない。 | 6.7 |
| P4 | 同じ試行キーを持つ 2 つの試行はない。 | 7.4 |
| P5 | 以前の実験に判定がない間に実行された実験はない。 | 7.3 |
| P6 | 使用した予算は実行した試行の数に等しく、予算を超えることはない。 | 7.5, 11.2 |
| P7 | 拒否が変えたのは、それ自身のログエントリだけである。 | 9.2 |
| P8 | 未計測結果に対して値は記録されていない。 | 2.5 |
| P9 | 外れに対して `supported` が記録されたことはない。 | 8.3 |
| P10 | フラグは、8.4 が定めるときにちょうど存在する。 | 8.4 |
| P11 | すべての実行、判定、受け付けられた `end` にはスナップショットがあり、拒否と停止にはない。 | 10 |
| P12 | Dr. Kiro に返されるものはすべて、計測値、未計測結果、画像、予算、またはメッセージスパンである。 | 7.6 |
| P13 | `end` は、表が記録と一致するとき（的中が範囲内または比較不能のものだけである validated の行を含む）にちょうど受け付けられる。 | 12, 16.3 |
| P14 | ログから再生した状態（`Session.open`）は、実行中の状態と等しい。 | 9, 13 |
| P15 | 封印済みの記録は検証に通り、どのバイトを反転させても検証は失敗する。 | 13.3, 13.4 |
| P16 | 同じシードと同じ操作の並びからは、バイト単位で同一の封印済みの記録が得られる。 | 3.4 |
| P17 | 禁止ノードを含むランダムなプログラムは拒否され、どの評価もステップ上限を超えず、Python のエラーも送出しない。 | 4 |
| P18 | 仕込んだ派生語はビルダーレベルでは検出され、Dr. Kiro レベルでは無視される。パス、ファイル名、認証情報は両方のレベルで検出される。 | 15 |
| P19 | 派生語を含む Dr. Kiro の文を引用する拒否は拒否のままであり、同じ語がベンチの文言にあればベンチ障害になる。 | 15.8 |
| P20 | 終了した記録の `end` スナップショットにある `design.md` は、その記録に対する表の確認に通る。 | 10.4, 12.6, 16.3 |

## 14. 作業を止めて相談する条件

- brief にある 5 つの項目を超えてアダプター契約に追加しなければ満たせない要件。
- 妥当な時間内にステップ上限に収まらない、プロトタイプのような実験。
- ブラインドスキャンが、私が言い換えられない通常のベンチの文言を検出し、その語を除外リストに入れなければならなくなる場合。
- ここにある形式が、Dr. Kiro にとって使えないと `dr-kiro` 仕様が判断した場合。
- MCP スパイクの発見のうち、フロントエンドではなくコアの変更を必要とするもの。
- 標準ライブラリ以外の実行時依存が必要になる場合。

## 決定事項

タスクを書く前にユーザーが承認しました。

1. **ループ。** リストまたは `range(...)` に対する `for` は、`break` と `continue` を含めて許可します。`while` は許可しません。ステップ上限はループにも適用されます (Requirement 4.1、セクション 7.2)。
2. **ステップ上限。** まず計測し、その後でユーザーに提案します（tasks.md、task 6）。それまでは固定しません。
3. **制御レート。** Dr. Kiro に伝えます。これは身体ではなく計測器に属するものだからです (Requirement 2.10)。決して示さないのは、どのチャンネルがどの部位をどの符号で駆動するかです。ユーザーの依頼により、`body-lab/model/README.md` はその旨を記すよう更新されました。
4. Discovered spec 表の **`id` 列** (Requirement 12.1)。
5. **`observed`** は、引用されたどの予測も外れていないことを意味します。任意のクラスの的中、未実行の予測、確認不能の予測は許されます (Requirement 12.3、task 12 のチェックポイントで改訂)。控えめに主張するのは問題ありませんが、過大に主張すると拒否されます。
6. **`end` での最後のスナップショット。** 最初の body-lab セッション（`sessions/body-lab/body-1`）の後で追加しました。このセッションでは、埋めた表がどの記録エントリにも入りませんでした。Dr. Kiro は最後の判定の後で表を埋めますが、スナップショットは実行と判定のときにしか取られていなかったためです。受け付けられた `end()` は、確認したファイルを記録するようになりました (Requirement 10.4, 12.6)。停止したセッションには最後のスナップショットを取りません (10.5)。これはユーザーの決定です。`body-1` は封印されたまま、表なしで残します。それをノートブックでどう見せるかは `lab-notebook` spec で決めます。
7. **ファイル名のステムと除外リスト**（要件 20、2026-11-16 にユーザーが承認、C1-C4 を参照）: ファイル名パターンは、1 文字のステムと除外リストにあるステムをスキップする。フルの名前は常に照合する。

---

# フロントエンド (Requirement 17)

出典: `spikes/mcp/results.md` と、Requirement 17 に記録されたユーザーの決定です。`spikes/` 以下のものは、実行時に一切インポートもコピーもされません（`structure.md`）。スパイクで分かったことは、コードとしてではなく、理由としてここで使います。

## F1. 概要

```
 Kiro CLI            --stdio-->  bench-mcp (MCP server, builder side)  -->  core Session
  Dr. Kiro: file tools            4 tools, one FIFO queue                    (design sections 3-9)
  + bench tools                   writes picture files into lab/pictures/
        |
        +-- pre-tool hooks (in lab/.kiro/hooks/):  confine  -> refuse paths outside the lab
        |                                          calllog  -> append every call to a builder-side log
        +-- post-tool hook:                        calllog
```

- セッションを保持するプロセスは `bench-mcp` だけです。Dr. Kiro は、その 4 つのツールを通してのみコアに到達します。
- フックはベンチの中ではなく、Kiro のプロセスツリーの中で動きます。フックはセッションについて何も知りません。
- フロントエンドはゲートを追加しません (17.1)。拒否の文はすべてコアから来ます。

## F2. パッケージ構成

`bench/src/bench/` の下に追加するもの（セクション 2）:

```
frontend/
  server.py        MCP server: tool definitions, queue, call into the core
  render.py        Outcome -> MCP result (section F4)
  pictures.py      write picture files into lab/pictures/ (F5)
  describe.py      tool descriptions built from the adapter declaration (F3)
  config.py        read the session config file named by BENCH_SESSION_CONFIG (F7)
  stop.py          the bench-stop command (F7)
  hooks/
    confine.py     the confinement hook (F8)
    calllog.py     the logging hook (F9)
```

追加するコンソールスクリプト: `bench-mcp`、`bench-stop`、`bench-lab-hooks`。`bench-lab-hooks <lab>` は `confine.py` と `calllog.py` をコピーし、3 つのフック JSON ファイルを `<lab>/.kiro/hooks/` に書き込みます。ラボ内のフックはラボ外のパスを指してはならないため（`rules.md`、Blind）、このコピーが必要です。各ラボ内のコピーがソースとバイト単位で等しいことをテストで確認します。

MCP SDK をインポートするのはフロントエンドだけです。`bench.core` は引き続きフロントエンドを一切インポートしません。task 1 のインポート禁止ルールは、そこでの `mcp` も禁止します。D1 を参照してください。

## F3. ツール (17.2, 17.4)

| ツール | 入力 | コアの呼び出し |
|---|---|---|
| `register_hypothesis` | `id: str` | `Session.register` |
| `run_experiment` | `path: str`、ラボからの相対パス | `Session.run` |
| `record_verdict` | `experiment: str`, `verdict: str`, `words: str` | `Session.verdict` |
| `end_session` | なし | `Session.end` |

- `start` も `stop` もありません (17.2)。`get_budget` や `get_result` のツールもありません。Requirement 17.2 が挙げるのは 4 つの操作であり、残りの予算は実行のたびに返されるからです (7.6)。
- 説明は `describe.py` で `Adapter.declaration()` から組み立てます。内容は、ノブ名と範囲、関数ノブのサンプル時刻、試行の長さ、計測名と単位、未計測結果の名前、画像の種類、予算、目標と計測の方法（`goal`、`measured_by`。空でないテキストで、説明の他の部分とともにビルダーレベルでスキャンされます）です。宣言が唯一の情報源であり (2.2)、同期を保たなければならない 2 つ目のコピーはありません。Dr. Kiro のステアリングがツールの説明を参照するか、宣言を繰り返すかは、`dr-kiro` 仕様が決めます。
- 起動時に `bench-mcp` は、生成した説明をコアのスキャン（`bench.scan`）でビルダーレベルでスキャンします。検出があれば、サーバーは 0 以外の終了コードで停止し、検出内容を stderr に出力します。ここでは他のブラインド確認は追加しません。コアのスキャンがすでに記録とすべての結果を対象にしているからです (Requirement 15)。

## F4. 結果の表示 (17.3)

スパンは順番どおりにつなげてプレーンテキストにし、言葉は何も追加しません。フロントエンドは独自のメッセージ文を一切組み立てません（セクション 3）。

| コアの結果 | MCP の結果 |
|---|---|
| `Ran(result)` | JSON テキストのコンテンツが 1 つ。画像コンテンツはなし。`result` 内の画像のバイト列はパスに置き換えられる (F5)。 |
| `Refused(message)` | テキストがそのメッセージであるツールエラー。エラーフラグは SDK が設定する。 |
| `BenchFailure(message)` | テキストがそのメッセージであるツールエラー。コアはすでにセッションを stopped として封印している (11.3) ので、以降の呼び出しはすべてコアの最初のゲートで `Refused` を受け取る (6.1、ステップ 1)。フロントエンドは状態を持たない。 |

`Ran.result` は、`run` ではコアの `RunResult`、`register`、`verdict`、`end` では `Accepted` です（セクション 3）。`RunResult` では、試行の `measurements` が値と `NotMeasured` の結果を 1 つのマッピングに保持し、`picture` は `Picture`（メディアタイプとバイト列）です。表示処理は未計測結果を `not_measured` に分け、各画像をそのファイルパスに置き換えます (F5)。`Accepted` は `{"budget_remaining": <n>}` として表示されます。`Session.fail`（セクション 3）を超えてコアの変更が必要になる場合は、作業を止めて相談します（セクション 14）。

`run_experiment` の実行結果（キーはここで固定し、値はコアから来ます）:

```json
{"experiment": "E<n>",
 "trials": [{"trial": "T<n>", "measurements": {"<name>": "<value>"},
             "not_measured": {"<name>": {"outcome": "<declared>", "reason": "<text>"}},
             "picture": "pictures/E<n>-T<n>.<ext>"}],
 "budget_remaining": "<n>"}
```

## F5. 画像ファイル (17.13-17.16)

- 名前: `pictures/<experiment id>-<trial id>.<ext>`。たとえば `E3-T7.png` です。試行 ID はセッション全体を通して番号付けされる (6.3) ので、名前は一意です。`<ext>` は宣言されたメディアタイプ（`png`、`gif`、`webp`）に従います。
- 各ファイルは同じフォルダー内の一時的な名前で書き込まれ、フラッシュされてから名前を変更されます。フォルダーは最初の画像のときに作られます。すべてのファイルは結果を返す前に書き込まれます (17.15)。
- 書き込めないファイルはベンチ障害です。フロントエンドは固定のベンチの理由（「a picture could not be delivered」）と、詳細としてのシステムエラーを付けて `Session.fail` を呼び、その理由をツールエラーとして返します。その結果、記録には、ほかのベンチ障害と同じように `failure` エントリと `stopped` の封印が残ります (17.15, 11.3)。
- ラボ内のコピーをベンチが読み戻すことはありません。記録が保持するのはアダプターのバイト列です (17.16)。
- スパイクで開いたのは PNG だけでした。wind-tunnel のアニメーションのような GIF や WebP を Dr. Kiro のファイルツールが表示できるかは検証されていません。画像の形式は `wind-tunnel` 仕様が決めます。

## F6. キュー (17.17-17.21)

- すべてのツールハンドラーは、何よりも先に 1 つの `anyio.Lock` を待ちます。このロックは公平なので、呼び出しは SDK がディスパッチした順に適用されます。SDK は stdio の呼び出しを並行に処理する（スパイクでは 3 つの呼び出しが互いに 0.55 s 以内に開始しました）ので、それらを直列化するのはこのロックです。
- コアの呼び出しはワーカースレッド（`anyio.to_thread.run_sync`）で実行し、長い実行の間もイベントループが空いた状態を保ちます。クライアントがキャンセルしても、スレッドは放棄されません。実行は最後まで進んで記録され、キャンセルされた呼び出しが答えを受け取らないだけです。その後ろに並んでいた呼び出しは、その状態を見ることになります (17.19)。
- 呼び出しは、コアが返るまで開いたままにされます (17.17)。フロントエンドはタイムアウトを設定せず、進捗メッセージも出しません。スパイクでは Kiro CLI で 900 s の呼び出しがタイムアウトなしで返った（`spikes/mcp/results.md`、Q4）ので、フロントエンドは長い呼び出しに対して特別なことは何もしません (17.18)。
- シーケンス番号はコアから来る (3.3) ので、記録には適用された順序が残ります (17.20)。
- 複数の `run_experiment` 呼び出しが並行した場合: 最初のものが実行されます。次のものは判定のない実験を見つけ、6.1 のゲート 6 で拒否され、予算は使われません (17.19)。

## F7. 開始と停止 (17.5)

- `bench-mcp` は引数を取りません。`BENCH_SESSION_CONFIG` を読みます。これは、ビルダーがラボの外に書く TOML ファイルのパスです。変数、ファイル、フィールドのいずれかが欠けていれば、サーバーはメッセージを出して停止します (1.3, `rules.md` 2)。フィールドは `SessionConfig`（セクション 3）の各フィールドに 1 つずつです: `session_id`、`application`、`adapter`（`module:factory`）、`lab_dir`、`spec_files`、`experiments_dir`、`state_dir`、`sessions_dir`、`seed`、`scan_sources`、`stop_list`。それに加えて `resume`（`true` は `Session.open` で既存のセッションを開き、`false` は新しいセッションを開始します。デフォルトはありません）。
- Dr. Kiro がそのファイルや変数を見ることはありません。どのツール入力でも、それらは一切設定できません。
- Kiro が接続を閉じると、サーバーは終了し、セッションは開いたまま残ります。サーバーはセッションを終了も停止もしません。
- `bench-stop <config> --reason <text>` は `Session.open` でセッションを開き、`Session.stop` を呼びます (11.4)。状態フォルダーがロックされているため（セクション 3）、これは `bench-mcp` が動いていないときにだけ機能します。閉じた接続によって開いたまま残った記録は、この方法で停止します。

## F8. 閉じ込めフック (17.7-17.10)

すべてのツール呼び出しの前に実行されます。フックの入力は、`tool_name` と `tool_input` を持つ stdin 上の JSON です（スパイク、Q2）。どちらのフックスクリプトも標準ライブラリだけを使い、スパイクのフックと同じように、ラボを作業フォルダーとして `uv run --no-project python -B .kiro/hooks/<script>.py` で実行します（Python は `uv` 経由でのみ使う、`tech.md`）。`-B` は、Python がラボに `__pycache__` を書かないようにします。コンパイル済みのファイルはテキストではないので、ブラインドスキャンが読めないためです。

```
lab = the folder two levels above this script's folder (the script lives in <lab>/.kiro/hooks/)
```

1. stdin を JSON として読みます。それは、文字列の `tool_name` とオブジェクトの `tool_input` を持つオブジェクトでなければなりません。そうでなければ拒否します。
2. パスを受け取るツールの表（下記）でツールを探します。パスフィールドを持つツールでは、列挙されたフィールドがすべて空でない文字列でなければなりません。そうでなければ拒否します。
3. 最初の要素が `~` で始まるパスは、ラボの外として拒否します。ツールがそれをホームフォルダーに展開するかどうかを、フックは知り得ないためです。それ以外の各パスを `lab` を基準に解決し（相対パスは「ラボの中」を意味します）、`..` セグメントとシンボリックリンクも解決します。結果が `lab` 自身でもその中でもなければ、拒否します。
4. パスなしのリストにあるツールは、それ以上の確認なしに許可されます (17.10)。
5. それ以外のツール名は拒否されます。フックがそれを分類できないからです (17.9)。
6. 解決したパスが 17.7 の保護フォルダー（ラボの下の `.kiro/agents`、`.kiro/hooks`、`.kiro/steering`、`.kiro/settings`）の中にある書き込みツール（`fs_write`、`fs_append`、`str_replace`）は拒否されます。これにより、その書き込みは確認ではなく拒否で終わります (17.8)。`.kiro/specs/` への書き込みは許可されます。

拒否: 終了コード 2 で終了し、stderr に Dr. Kiro の言葉で 1 行を出力します。ラボ外のパスに対しては「That path is outside your folder. Use a path inside your folder.」、保護フォルダーへの書き込みに対しては「That file is part of the lab's setup and cannot be changed.」、不正な入力や表にないツールに対しては「That tool is not available in this lab.」です。これらの行はパスを示しません。スクリプト内の例外はすべてトップレベルで捕捉され、やはり終了コード 2 で終了します。それ以外の 0 以外の終了コードでは呼び出しが通ってしまうからです。例外の文は stderr ではなくビルダー側のログに書かれます。この捕捉は障害を拒否に変えるものであり、障害を隠すものではありません。

ツールの表。名前とパスフィールドは、スパイクのフックログ（`hook-log.jsonl`）にあるものです。`read_file`、`list_directory`、`fs_write`、`fs_append` は `path` を持ち、`file_search`、`grep_search`、`tool_load` とベンチのツールはパスを持ちません。`str_replace` は、Dr. Kiro が `requirements.md` と Discovered spec 表をその場で編集できるよう、ユーザーの依頼で追加しました。これは `fs_write` と同じパスの確認を受けます。このツールはスパイクのフックログには現れませんでした。その `path` フィールドは Kiro のツール定義から取ったもので、task 21 で確認します。`delete_file` は引き続き拒否されます。表にないツールは、フックログで確認されてここに追加されるまで拒否されます。

| クラス | ツール（パスフィールド） |
|---|---|
| パスを受け取る | `read_file` (`path`), `list_directory` (`path`), `fs_write` (`path`), `fs_append` (`path`), `str_replace` (`path`) |
| パスなし、許可 | `file_search`, `grep_search`, `tool_load`, `mcp_bench_register_hypothesis`, `mcp_bench_run_experiment`, `mcp_bench_record_verdict`, `mcp_bench_end_session` |

17.10 の前提条件: Dr. Kiro は Kiro CLI でのみ、ラボを作業フォルダーとして起動して実行されます (17.12)。そのため、検索ツールが見るワークスペースはラボです。Dr. Kiro の実行に IDE が使われることはありません。

フックの文はビルダーの文言であり、`lab/.kiro/` の他の部分とともにコアのスキャンを通ります (Requirement 15)。パスは含みません: スクリプトは親フォルダーとホームフォルダーの確認を `pathlib` の部品から組み立て、`..` セグメントや `~/` 接頭辞のようなリテラル文字列は決して使いません。スキャンはそれらをパスとして検出するからです。`bench-lab-hooks` が生成したラボに対して `bench-scan` を実行するテストがあります。

## F9. ログ記録フック (17.11)

- `calllog.py` は、ラボの外にある `BENCH_HOOK_LOG` で指定されたファイルに、呼び出しごとに 1 行の JSON を追記します: `{"phase": "pre" | "post" | "refused", "tool_name", "tool_input", "reason"?}`。閉じ込めフックも、同じ関数で拒否を書き込みます。タイムスタンプはハッシュも封印もされません。このログは記録の一部ではありません (17.11)。
- パスを環境変数から取るのは、ラボ外のパスが `lab/.kiro/` に現れないようにするためです。変数がない場合や行を書き込めない場合、pre-tool フックは終了コード 2 で終了します（ログに残らない呼び出しは作りません）。post-tool フックは呼び出しを取り消せませんが、同じく終了コード 2 で終了し、これは障害を報告するだけです。
- Kiro CLI がこの変数をフックに渡すかどうかは分かっていません。task 21 で確認します。渡さない場合は、作業を止めて相談します。

## F10. エージェント定義 (17.6, 17.7, 17.12)

機械的なフィールドです。名前、説明、プロンプトは `dr-kiro` 仕様が追加します。

```json
{
  "mcpServers": {"bench": {"command": "bench-mcp", "args": [],
      "env": {"BENCH_SESSION_CONFIG": "${BENCH_SESSION_CONFIG}"}}},
  "tools": ["read", "write", "@bench"],
  "includeMcpJson": false,
  "includePowers": false,
  "permissions": {"rules": [
    {"capability": "fs_read",  "match": ["./**"], "effect": "allow"},
    {"capability": "fs_write", "match": ["./**"], "effect": "allow"},
    {"capability": "fs_write", "match": [".kiro/agents/**", ".kiro/hooks/**", ".kiro/steering/**",
                                         ".kiro/settings/**"], "effect": "deny"},
    {"capability": "mcp",      "match": ["bench/*"], "effect": "allow"}
  ]}
}
```

- スパイクの `/**` と `../**` の deny ルールは削除しました。これらは拒否する代わりに確認を求めてしまい、またラボへの絶対パスを必要としましたが、ラボのファイルにはそれを含められないからです。閉じ込めはフックが行います。
- `bench-mcp` は `uv tool install --editable ./bench` によってビルダーの `PATH` 上に置かれるので、リポジトリへのパスがラボに現れることはありません。`env` 内の `${...}` は Kiro のエージェントドキュメントに示されている変数展開ですが、スパイクでは使っていませんでした。task 21 で確認します。うまくいかない場合は、作業を止めて相談します。
- `hook-log.jsonl` はもうラボの中にないので、それに対するスパイクの `fs_write` の deny は不要になります。
- deny は保護フォルダーへの書き込みだけを対象にします。`.kiro/specs/` は読み書きできるままです。Dr. Kiro のラボの仕様ファイルがそこにあるからです (17.7)。読み取りは deny しません: 検索ツールは deny ルールで止まらない (Q7) ので、読み取りの deny は実際に守れる以上のことを約束してしまいます。閉じ込めフックも保護フォルダーへの書き込みを拒否します（F8、ステップ 6）。
- 書き込みの deny が守られるかどうかは、エージェントがサーバーの追加を拒んだ場合についてしか観察されていません (Q7)。task 21 で `.kiro/hooks/` への書き込みと `.kiro/specs/` への書き込みを 1 つずつ試します。

## F11. テスト

- 閉じ込めフック (17.21): テストは 3 つです。ラボ外のパスを持つ呼び出しが終了コード 2 で拒否されること。不正な入力が終了コード 2 で拒否されること。保護フォルダーへの書き込みが終了コード 2 で拒否されること。
- サーバー（SDK のインプロセスクライアントとフェイクアプリケーションを使用）: 4 つのツールが一覧に出ること、拒否がコアの文を持つツールエラーであること、実行が画像コンテンツを返さず、アダプターのバイト列を持つ画像ファイルが存在すること、2 つの並行した実行が `Ran` を 1 つと `Refused` を 1 つ返すこと（ゲート 6）。これらは例によるテストです。
- ユーザーの Kiro CLI が必要なものは、テストスイートではなく手作業で確認します（task 21）。

## F12. 決定事項（ユーザーが承認済み）

- **D1. 実行時依存。** セクション 1 と 14 には、ベンチは標準ライブラリ以外の実行時依存を持たず、それが必要になったら作業を止めて相談する、とあります。MCP サーバーには `mcp` パッケージが必要です。承認された内容: `mcp==2.3.0`（スパイクで使ったバージョン）を任意の依存グループ `frontend` に固定し、コアとそのテストは標準ライブラリだけで済むようにします。
- **D2. フックログとセッション設定の置き場所。** どちらもラボの外にあり、環境変数（`BENCH_HOOK_LOG`、`BENCH_SESSION_CONFIG`）で指定されます。承認された内容: リポジトリのルートに `bench-run/` フォルダーを置き、git の管理対象外とし、`structure.md` に記載します。
- **D3. 長い呼び出し。** 必要ありません。スパイクで 900 s の呼び出しが通ったので、並行試行による代替策は用意しません。
- **D4. Dr. Kiro は Kiro CLI でのみ実行し**、ラボフォルダーで起動します (Requirement 17.12)。IDE はビルダーのためのものです。

コアを構築した後、task 17-21 のレビューで承認された内容:

- **D5. 保護フォルダー。** 保護するのは `.kiro/agents`、`.kiro/hooks`、`.kiro/steering`、`.kiro/settings` だけです。Dr. Kiro は `.kiro/specs/` で自身の仕様ファイルを読み書きします (17.7, F10)。
- **D6. 読み取りではなく変更。** Requirement 17.7 が約束するのは、Dr. Kiro が保護フォルダーを変更できないことであり、読めないことではありません（Q7: 検索ツールは deny ルールを越えて読みます）。
- **D7. フックも保護フォルダーへの書き込みを拒否します。** これにより、それらは確認ではなく拒否で終わります（17.8、F8 ステップ 6）。
- **D8. セッション設定ファイル**は、`SessionConfig` の各フィールドに 1 つずつのフィールドと、`resume` を持ちます (F7)。
- **D9. ラボ内の画像**は、ブラインドスキャンによってテキストとして読まれるのではなく、画像として検査されます (15.9, 11.3)。これはコアのスキャンを変更します。
- **D10. `Session.fail`** をコアに追加します。これにより、書き込めない画像は、ほかのベンチ障害と同じようにベンチ障害として記録されます（17.15、セクション 3、F5）。閉じ込めフックには、保護フォルダーへの書き込みを確かめる 3 つ目のテストを加えます (17.21)。

Kiro CLI での手動確認（task 21）の後に承認されたもの:

- **D11. 余分なツール。** Kiro の `read` と `write` のツール群は、`code`、`delete_file`、`disclose_context`、`tool_call` も提供します。これらはエージェントから取り除かず、表にないほかのツールと同様に閉じ込めフックが拒否します（17.6、17.9）。ベンチのツールは `tool_load` の後に `mcp_bench_<tool>` という名前でフックに届きます。`tool_call` は使われませんでした。
- **D12. Dr. Kiro のファイルでは相対パス。** Kiro はツールの入力に絶対パスを渡すので、Dr. Kiro はラボの絶対パスを知っています。`dr-kiro` 仕様では、Dr. Kiro が自分のファイルにラボからの相対パスだけを書くよう指示します。ブラインドスキャンは絶対パスを検出し、絶対パスを含むセッションは封印できないためです。

task 21 の結果（macOS の Kiro CLI、フェイクアプリケーション）: ベンチの 4 つのツールが一覧に出て、各呼び出しがコアに届きました。`BENCH_SESSION_CONFIG` はサーバーに、`BENCH_HOOK_LOG` はフックに届きました。ラボ外の読み取りと書き込み、および `.kiro/hooks/` への書き込みは、確認を求めずにフックが拒否しました。`str_replace` は `path` を持ち、`.kiro/specs/` で動作しました。エージェントは、文脈にステアリングがないと報告しました（エージェント自身の報告）。確認していないもの: `.kiro/hooks/` に対する `grep_search`（動作する想定、D6）。

---

# 改訂: ノブの説明（要件 18）

タスク 1-22 が終わった後、`wind-tunnel` spec の求めで加えました。セクション 1-14 と F1-F12 は書き換えません。ノブについてこの部分と以前のセクションが違う所では、この部分が現在の文面です。セクション 4 のデータクラスは 1 項目ずつ増えます。契約のほかは何も変わりません。

## A1. 契約（18.1, 18.2, 18.3）

```python
@dataclass(frozen=True)
class FunctionKnob:  name; low; high; sample_times; trial_seconds; description: str = ""
@dataclass(frozen=True)
class NumberKnob:    name; low; high; description: str = ""
```

- 項目は最後に置き、既定値を持つので、既存の呼び出し（`FunctionKnob("c0", -1.0, 1.0, times, 5.0)`、`NumberKnob("gain", 0.0, 3.0)`）の意味は変わりません。既定値は空のテキストで、「欠けたデータの既定値」ではありません。そのノブに説明がないことを述べており、body-lab の宣言はこの項目を設定しないことで、意図してそう述べています。
- `check_declaration` はノブごとに、範囲のチェックの後にもう 1 つチェックを持ちます: 値が `str` である。`str.isprintable() == False` の文字を持たない（改行、タブ、その他の制御文字を含む）。先頭と末尾に空白がない（`text == text.strip(" ")`）。`len(text) <= DESCRIPTION_MAX`（`DESCRIPTION_MAX = 800`）。失敗は、ノブと 4 つのどれかを名指す `DeclarationError` を送出します。
- 800 文字は 5 文ほどが入ります。ノブごとに伝えることの上限で、ツールの説明が読みやすいように選びました。wind-tunnel の最長の文は約 450 文字です。
- ほかのコードはこの項目を読みません。実験言語、仮説のチェック、条件のコードは触れません（18.3）。テストが、`.description` が A2 と A3 の 3 か所以外にないことをソースの grep で確かめます。

## A2. 伝えるテキスト（18.4, 18.5, 18.9）

`describe.declaration_text` はノブの行をこれまでどおり出力し、説明が空でないときだけ、` ` と説明を後ろに足します。既存の文末は変わりません: 関数ノブの行はサンプル時刻の後の `.` で終わり、数ノブの行は `per trial.` で終わります。説明はその文の後に来ます:

```
- gain: a number in [0.0, 3.0] per trial. <description>
```

説明が空なら何も足さないので、行はこの改訂の前のものとバイト単位で同一です（18.4）。説明には改行がない（A1）ので、ノブ自身の行に載ります。`wind-tunnel` spec の書き出し（その要件 2）は、この関数だけを呼びます。

## A3. 記録（18.6）

`declaration_record` は、`k.description != ""` のときだけ、ノブの辞書に `"description": k.description` を加えます。正規 JSON はキーを並べ替えるので、キーの位置は問題になりません。説明のないアプリケーションの記録には新しいキーがなく、以前に作られたものとバイト単位で同一です（3.4, 18.8）。

## A4. スキャン（18.7）

- 起動時に、`bench-mcp` は生成された説明をビルダーレベルですでにスキャンしています（F3）。伝えるテキストにはノブの説明が含まれるので、コードを変えずにそこでスキャンされます。テストで確かめます: 導かれた語を含む説明は、サーバーを止める。
- 封印された記録は、ベンチが書いたテキストについてビルダーレベルでスキャンされます（13.1）。宣言は作者 `bench` で記録されるので、説明も対象です。テストは、導かれた語を含む説明を宣言に持つセッションを封印し、封印が失敗することを確かめます。
- 許可リストは名前（ノブ名、計測名、未計測結果名）から作られ、広げません（11.1）。

## A5. body-lab は変わらない（18.8）

証明は、変更前のコードから作った 2 つの golden ファイルを、変更後に比べることです:

- `body-lab/adapter/tests/golden/told_text.txt`: `declaration_text(BodyAdapter().declaration())`。
- `body-lab/adapter/tests/golden/declaration_record.json`: `canonical_json(declaration_record(...))`。

タスク 23 が、改訂のどのコードにも触れる前にそれらを書いてコミットします。`body-lab/adapter/tests/` のテストが、現在の出力をバイト単位で比べます。golden ファイルは `bench/` ではなく body-lab のテストのものです。`bench/` のテストは body-lab を読まないからです（tasks.md の冒頭）。フェイクアプリケーションも説明を宣言しません。既存のテストがコアについて同じ証明になり、`bench/tests/fixtures/` の 2 つ目の golden ファイルの組がそれを補います。

## A6. 性質（要件 16 の様式、`Feature: lab-bench, Property N` のタグ）

| # | 性質 | 要件 |
|---|---|---|
| P21 | すべての説明が空であるすべての宣言で、`declaration_text` は、改訂前の形式からテスト内に書いた参照レンダラーのテキストと等しい。 | 18.4, 18.8 |
| P22 | すべての宣言で、空でない各説明は、宣言どおりに自分のノブの行にちょうど現れ、ノブの行はほかのノブの説明を持たない。 | 18.4, 18.9 |
| P23 | 説明の候補となるすべての文字列（任意の文字）で、`check_declaration` は、テキストで、印字可能で、先頭と末尾に空白がなく、800 文字以下のものだけを受け付け、それ以外はノブを名指して拒否する。 | 18.2 |
| P24 | すべての宣言で、記録されたノブは説明が空でないときちょうど `description` キーを持ち、すべての説明が空の宣言の記録は改訂前の形と等しい。 | 18.6, 18.8 |

## A7. 決定（ビルダーが決めた。ユーザーは wind-tunnel のセッションで選択肢 A を選んだ）

1. **項目名は `description`、最後、既定は空**、両方のノブ型。`wind-tunnel` での以前の提案は `meaning` と呼んでいました。要件 18 の名前は `description` です。
2. **空のとき記録にキーを置かない。** 古い記録がバイト単位で同一のまま残り（3.4）、body-lab の出力が変わらないため。
3. **800 文字、1 行。** 改行のあるテキストは、伝えるテキストの 1 ノブ 1 行の構造を壊す。上限は上限であって、品質のルールではない。
4. **ベンチは解釈しない。** 説明は伝えるだけで、チェックしないので、第 2 のゲートにならない。

## A8. 止めて確認することになる場合

- golden ファイルが変更後の出力と違う（18.8）: 改訂は body-lab を変えてはならない。止めて、最初に違う行を報告する。
- A1-A3 以外のコードパスが説明を読む必要がある。


---

# 改訂: アダプターの入力チェック（要件 19）

タスク 1-28 を終えた後に、`wind-tunnel` spec の求め（そのタスク 14.4）で加えました。セクション 1-14、F1-F12、A1-A8 は書き直しません。下のステップ 9a は、番号を振り直さずに 6.1 のゲート順序に加えます。

## B1. 契約（19.1, 19.4, 19.7）

`Adapter` プロトコルの外にある任意のアダプターメソッドで、`builder_versions` と同じ様式です:

```python
CHECK_INPUTS_METHOD = "check_inputs"       # def check_inputs(self, inputs: ComputedInputs) -> str | None
INPUT_REFUSAL_MAX = 400

def check_input_refusal(text: object) -> str      # raises ResultError unless the message is usable
def input_refusal(adapter: object, inputs) -> str | None   # None when the adapter has no such method
```

- メソッドは `getattr` で探す。これを持たないアダプターは、どの入力に対しても `None` を返す: body-lab とフェイクアプリケーションでは何も変わらない（宣言、伝えるテキスト、記録は手つかずで、A5 の golden 比較がその証明である）。
- `check_input_refusal` が受け付けるのは、空でなく、`str.isprintable()` を満たし、両端に空白がなく、`INPUT_REFUSAL_MAX` 文字以下の `str` だけである（`_check_description` と同種の上限だが、エラーの中の 1 文なので短い）。それ以外は `ResultError` を送出する。
- `input_refusal` は、メソッドの例外を捕まえない。

## B2. ゲート 9a（19.2, 19.3, 19.5, 19.8）

`Session._check_inputs(path, experiment)` は、予算チェック（ステップ 9）の後、spec ファイルを読む（ステップ 10）前に走る。試行を順に、それぞれ `input_refusal(adapter, trial.inputs)` を呼ぶ:

- `ResultError`（不正なメッセージ）: `_Failure(ADAPTER_BROKE_CONTRACT, "input check of trial N: ...")`、ベンチ障害。
- それ以外の例外: `_Failure(ADAPTER_RAISED, "input check of trial N: <traceback>")`、ベンチ障害。トレースバックは `builder.log` だけに書く。
- メッセージ: ビルダーログに `input check refused trial N of '<path>': <message>` の行を書き、その後 `_refuse("trial N of this experiment cannot run: <message>")`。ループは最初に拒否した試行で止まる。

この拒否は結果 2 である: `_act` が `RefusalError` を `Refused` にし、`_finish` が `refusal` エントリを 1 つだけ記録する。`experiment` エントリも `trial` エントリも書かれないので、状態、予算、試した入力の集合は変わらず、同じ入力を後の実験で使える。

## B3. ブラインドのルール（19.6）

メッセージは `_finish` を通り、`_finish` はすべての `Refused` メッセージをビルダーレベルでスキャンする（11.4, 15.8）。したがって拒否テキストはベンチの出力である: 導出された用語、パス、認証情報があれば、その呼び出しは固定の `WITHHELD` テキストのベンチ障害になり、メッセージの内容は何も示されない。アダプターの作者は、メッセージを Dr. Kiro の言葉で書く。ツールの説明は変わらない。Dr. Kiro は、拒否された値を拒否によってのみ知る。

## B4. 性質（要件 16 の様式、`Feature: lab-bench, Property N` のタグ）

| # | 性質 | 要件 |
|---|---|---|
| P25 | すべての実験（1-3 個の変種の compare、または 6 点の sweep）と、拒否される入力のすべての集合で、拒否は予算を使わず、`refusal` エントリを 1 つだけ追加する。 | 19.3 |
| P26 | 同じ実験で、どの試行での拒否も、試行が 1 つも走る前に実験全体を拒否する。名指される試行は最初のものである。拒否される試行がなければ、実験は走る。 | 19.2, 19.3 |
| P27 | すべての実験で、`check_inputs` を持たないアダプターは何も拒否しない。 | 19.1, 19.7 |
| P28 | すべての候補メッセージで、`check_input_refusal` は有効なものだけをちょうど受け付ける。それ以外のメッセージと、例外を送出するメソッドは、試行を 1 つも走らせないベンチ障害である。 | 19.4, 19.5 |
| P29 | 導出された用語を含むメッセージでは、結果は `WITHHELD` テキストのベンチ障害である。 | 19.6 |

## B5. 決定（ビルダーが、wind-tunnel spec についてのユーザーの決定に基づいて決めた）

1. **プロトコルの外の任意のメソッド**。`builder_versions` と同じで、既存のアダプターは何も変わらない。
2. **予算チェックの後**。既存の理由が順序を保つため（19.8）。大きすぎて、かつ値で拒否される実験には、予算の理由が先に出る。
3. **ベンチが試行番号を前に付ける**（`trial N of this experiment cannot run: ...`）。既存の入力の繰り返しの拒否が試行番号を名指すのと同じである。
4. **不正なメッセージは拒否ではなくベンチ障害**。アダプターの落ち度であり、Dr. Kiro には直せないため（2.6、rules.md セクション 2）。
5. **400 文字、1 行。** 上限であって、品質のルールではない。
6. **純粋さはアダプターの契約。** ベンチは、確認のために関数を 2 回呼ばない。

## B6. 止めて確認することになる場合

- 変更後に body-lab の golden ファイルが違う（18.8）。そうはなっていない: 変更なしで通る。
- 拒否される値を、試す前に Dr. Kiro に伝える必要がある（伝えるテキストの変更）。

---

# 改訂: ファイル名のステム（要件 20）

タスク 1-31 の後、2026-11-16 のユーザーの決定で加えた。セクション 1-14、F1-F12、A1-A8、B1-B6 は、今のコードの内容に合わせた 11.1 と 11.2 を除き、書き換えない。

## C1. 規則（20.1-20.5）

`scan/patterns.py` の `Patterns(file_names, solver_dirs, local_paths, stop_list=())`。ソースファイルの名前ごとに:

- フルの名前は常にパターンになる。
- ステムは `name.split(".", 1)[0]`。パターンになるのは、`stem != name`（名前にドットがある）、`len(stem) > 1`、かつ `term_tokens(stem)` が除外リストの `term_tokens` に含まれないときだけである。
- ドットのない名前は `stem == name` である: それはフルの名前なので、1 文字であっても、除外リストにあっても照合される。（アプリケーションのソースファイルでこの形なのは `Allrun` だけである。この規則はテストする。）

`Scanner.__init__` は除外リストを `Patterns` に渡す。`Scanner.from_config` はすでにそれを読み込んでいる。`Patterns.find` は両方のレベルで同じなので、規則は両方で成り立つ。`geometry.py` のようなフルの名前は、これまでどおり、全体を報告し、ステム `geometry` がスキップされないときはそのステムも別に報告する。

## C2. 変わらないもの

導出された用語（11.1）、許可リスト、パス、認証情報、作者の範囲、指摘の形式。1 文字のステムから作られる用語（たとえばビルダーレベルの `u`）は変わらない。この改訂はファイル名パターンだけを対象とする。body-lab のスキャンと golden ファイルは変わらない（タスク 34 で確認する）。

## C3. 性質（要件 16 の形式、`Feature: lab-bench, Property N` のタグ）

| # | 性質 | 要件 |
|---|---|---|
| P30 | 任意のファイル名と除外リストについて、両方のレベルで: 1 文字のステムと除外リストにあるステム（どの大文字小文字でも）は見つからない。2 文字以上で除外リストにないステムは見つかる。すべてのフルの名前は見つかる。ドットのない名前は、1 文字であっても除外リストにあっても見つかる。 | 20.2-20.5 |

## C4. 決定（ユーザーの決定に基づいてビルダーが決めた）

1. **除外リストはトークン形式（`term_tokens`）で比較する。** 用語と同じ方法なので、`solver_output` と `solverOutput` はどちらも除外語 `solver_output` と等しい。`fvSchemes` のようなキャメルケースのステムは、リストに同じトークンの語（`fv_schemes`）があるときだけスキップされる。
2. **ドットのない名前はフルの名前**なので、常に照合する。代案: ステムとして扱い、短いときや除外リストにあるときにスキップする。採らなかった: ユーザーの文は、フルの名前は常に照合すると述べている。
3. **一般的な語のステムは、除外リストに入れるまで見つかる。** `geometry`、`mesh`、`constants`、`monitors` の選択はユーザーが任せ、2026-11-16 に 1 つ目、3 つ目、4 つ目を入れ、`mesh` は入れなかった（`wind-tunnel` 要件の Decision 46）。入れていないステムは、Dr. Kiro レベルでは普通の文に当たりうる。

## C5. 止めて確認することになる場合

- 変更後に、body-lab の golden ファイルまたは封印済みセッションのスキャン結果が変わる。そうはなっていない。

## D1. discovered spec 表のない終了（要件 21）

変更の全体です。`build-from-spec` spec のセクション 3.14.1 の詳細設計であり、ベンチのコードはこの spec で規定するため、ここに書きます。

| 場所 | 変更 |
|---|---|
| `SessionConfig`（`core/session.py`） | 新しいフィールド `discovered_table: str`。既定値はない。 |
| `Session._check_config` | 値が `"required"` か `"not-required"` でなければ拒否し、設定の名前を示す（21.6）。 |
| `frontend/config.py` | `FIELDS` はすでに `SessionConfig` に従うので、欠けたフィールドは名前を示して拒否される。`load` は文字列であることを検査し、受け渡す。 |
| 開始エントリー | `"discovered_table": config.discovered_table`（21.7）。`Session.open` は `seed` と同じく設定と比べる。 |
| `Session._end` | 分岐が 1 つ: `check_table` のブロックは値が `"required"` のときだけ動く。判定の検査、3 つのファイルの 1 回の読み込み、`"for": "end"` のスナップショット、`ended` としての封印はそのまま（21.2、21.3）。 |
| `frontend/describe.py` | `descriptions` が設定を受け取る。`"not-required"` のとき、`end_session` の文は表の節を含まない（21.9）。 |
| `frontend/server.py` | `BenchServer` が `descriptions(session.declaration, session.config.discovered_table)` を呼ぶ。これが唯一の呼び出し元である。 |
| `bench-new-session`（`drkiro/session.py`） | `discovered_table = "required"` を渡し、書く（21.4）。 |
| テストとドキュメント | `tests/labkit.py` とベンチのテストのすべての設定が `"required"` と書く。`bench/README.md` のサンプルの `session.toml` にその行を加える。 |

**`frontend/describe.py`。** `end_session` の文は 2 つの定数から組み立てる:

```python
END_BASE = "End the session. Every experiment needs a verdict"
END_TABLE = ", and your design.md must end with a Discovered spec table that agrees with the record"

def descriptions(decl: Declaration, discovered_table: str) -> dict[str, str]:
    if discovered_table not in ("required", "not-required"):
        raise ValueError(f"discovered_table must be required or not-required, not {discovered_table!r}")
    ...
    "end_session": END_BASE + (END_TABLE if discovered_table == "required" else "") + ".",
```

- `"required"` では現在の文がバイト単位で同じになるので、Dr. Kiro のツールの文は変わらない（21.9）。
- `"not-required"` では `End the session. Every experiment needs a verdict.` になる。
- 他の 3 つの文は設定によらない。未知の値は例外を投げる。開始時の検査がすでに拒否しているので、これは別の呼び出し元に対する守りだけである。

**テスト。** `bench/tests/unit/test_session.py`: `"not-required"` で表なしの `end` は、`final_spec` が読める終了スナップショットのある `ended` として封印される。判定が保留のままなら、引き続き拒否する。設定がないか未知の値なら、開始時に設定の名前を示して拒否する。開始エントリーは値を持つ。`"required"` では既存の終了のテストがそのまま通る。`bench/tests/frontend/test_describe.py` と `test_server.py`: `"required"` は現在の文字列をバイト単位で与える。`"not-required"` は短い文を与える。他の 3 つの文は両方の値で等しい。未知の値は例外を投げる。各値でサーバーを起動すると、対応する `end_session` の文が一覧に出る。
`bench/tests/unit/test_sealed_before_amendment.py`: 開始エントリーに `discovered_table` がない `sessions/body-lab/body-1`、`sessions/body-lab/body-2`、`sessions/wind-tunnel/wt-004` で `bench-verify` と `final_spec` が通る。

- この改訂の前に封印された記録は、開始エントリーに `discovered_table` を持たない。`bench-verify` と `final_spec` はそれを読まないので、有効なままである（21.8）。
- `Session.open` はそのキーのない記録を拒否するので、改訂の前に開始した未封印のセッションは開き直せない。改訂をマージするときに開いているセッションがあってはならない（セクション D4）。
- `bench-run/` の設定は git で無視され、封印済みセッションに属する。これらは編集しない。

## D2. bench-check-discovered が飛ばす実行記録（要件 22）

`record/spec_copy.py` の `_records` は `<sessions>/<x>/` の下のすべてのフォルダーをセッション記録として読み、`log.jsonl` のないフォルダーで例外を投げる。`sessions/build-from-spec/body-lab/` には実行記録と実行ファイルがあるので、検査はリポジトリで失敗してしまう。変更は次のとおり:

```python
RUN_RECORDS = "build-from-spec"   # sessions/build-from-spec/ holds reader run records (lab-bench Requirement 22)

def _records(sessions: Path) -> list[Path]:
    """Every Dr. Kiro session record folder under `<sessions>/<application>/`; `<sessions>/build-from-spec/` is skipped."""
    for application in sorted(p for p in Path(sessions).iterdir() if p.is_dir() and p.name != RUN_RECORDS):
        ...  # unchanged
```

- `check_copies` は、`<sessions>/build-from-spec/` が存在するとき報告の行 `build-from-spec: reader run records, no copies` を加えるので、飛ばしたことが見える（22.2）。
- ほかは何も変わらない（22.3）。`discovered/build-from-spec/` のフォルダーは、「この名前の封印済みセッション記録はない」として引き続き報告される。
- 実行記録は、`bench-verify`、`sessions/` のブラインドスキャン、`build-from-spec` の実行記録の検査によって引き続き対象となる（22.4）。
- テスト: `bench/tests/unit/test_spec_copy.py`。リポジトリのセッションを一時フォルダーにコピーし、封印済みの実行記録とその実行ファイルを `sessions/build-from-spec/body-lab/` に置く。問題はなく、飛ばした行が出る。その実行の写しが `discovered/build-from-spec/` にあれば問題になる。ほかのアプリケーションの下で `log.jsonl` のないフォルダーは、引き続き例外を投げる。

## D3. 決定（ビルダーが `build-from-spec` の決定に基づいて行った）

1. **番号は 21 と 22。** 要件 20 の後で空いている次の番号。改訂 1 件ごとに 1 つの番号を使う。`build-from-spec` の要件 12 と 13.7 は 2 件の改訂だからである。
2. **真偽値ではなく 2 つの値。** `"required"` と `"not-required"` は、記録の中で `true` と `false` よりはっきり読める（`build-from-spec` 設計 B8）。
3. **既定値なし。** 設定のない設定ファイルは、開始時に名前を示して拒否されるので、仮定された値でセッションが走ることはない。
4. **古い記録は移行しない。** 開始エントリーにはキーがないままである。`bench-verify` と `final_spec` はそれを読まない。
5. **`end_session` の文は 1 文短くなる。** ただし `"not-required"` の場合だけ。Dr. Kiro の文は変わらない。
6. **飛ばしたことは黙らず、行を加える。** `check_copies` の報告が飛ばしたフォルダーの名前を示す。
7. **`dr-kiro` の文言。** `dr-kiro` の要件 8.4 とその設計のセクションは、「終了スナップショットのある `ended` として封印された Dr. Kiro のセッション記録の各々」と述べ、実行記録は対象外と明記する。

## D4. 止めて確認することになる場合

- 改訂のマージ時に `bench-run/` にセッションが開いている。`Session.open` は、開始エントリーに `discovered_table` がないためその記録を拒否する。ビルダーは止めて報告する。
- 変更後に、既存の封印済み記録が `bench-verify` または `final_spec` で失敗する。想定していない。この経路ではコードがそのキーを読まないからである。
