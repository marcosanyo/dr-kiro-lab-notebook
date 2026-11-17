> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/lab-bench/requirements.md`](../../../.kiro/specs/lab-bench/requirements.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `384c418a3ba07ebfeb536c5ab8603c6d4e04e6452c8166ddb4396ff9514fda2f`

# 要件: lab-bench

## はじめに

ラボベンチは、すべてのアプリケーションが接続される骨格です。ベンチは Dr. Kiro が従う方法（実験の前に仮説、1 つの実験につき 1 回の実行、次の実行の前に判定、固定の予算）を強制し、アプリケーションのアダプターを通じて試行を実行し、起きたことすべての記録を書きます。方法のルールは、プロンプトが求めるからではなく、ベンチと Dr. Kiro の権限によって守られなければなりません。

出典: `docs/brief.md` のセクション 1-3 と 4.1、およびセッションで記録された回答です。`.kiro/steering/` のステアリングはすべて適用され、特に `rules.md` が適用されます。

要件は 2 つのグループに分かれます:

- **コア**（要件 1-16）: ゲート、記録、スナップショット、封印済みセッション記録、アダプター契約、ブラインドスキャン、プロパティベーステストです。コアはフロントエンドに依存しません。
- **フロントエンド**（要件 17）: Dr. Kiro がベンチを呼び出す方法、Dr. Kiro の権限、画像が Dr. Kiro に届く方法、長時間の実行と並列の実行です。MCP スパイクの後に決定しました。スパイクの結果は `spikes/mcp/results.md` にあります。
- **改訂**（要件 18）: ノブの任意の説明テキストです。要件 1-17 を実装した後に、`wind-tunnel` spec の求めで加えました。既存の要件も数値も変えません。

各要件には、どの Kiro についての要件かが書かれています。「Dr. Kiro」は実験者のエージェントです。「ビルダー」は、このリポジトリで作業する Kiro、またはベンチを操作する人です。

### 対象外: Dr. Kiro 自体

Dr. Kiro のエージェントプロンプト、ラボのステアリング（方法のルール、このラボが何であるか、4 つのフェーズからなるタスク）、ラボの仕様テンプレートは、`lab-bench` の後に続く別の仕様 `dr-kiro` で規定します。lab-bench の設計は、ベンチが読む機械可読な形式（仮説と予測のブロック、実験ファイル、`## Discovered spec` の表）を定義します。`dr-kiro` のテンプレートはそれらの形式を使い、再定義はしません。Dr. Kiro の権限は要件 17 に残ります。

`dr-kiro` 仕様への注記:
- Dr. Kiro は実験をまたいでパラメーター名を変えません。ベンチは条件をパラメーター名で比較します（要件 6.4）。パラメーター名を変えると予測は not comparable になり、`validated` には数えられません（要件 12.3）。
- Dr. Kiro は、仕様ファイルと実験ファイルにラボからの相対パスだけを書きます。Kiro はエージェントにラボの絶対パスを渡します（ツールが絶対パスを受け取るため）。しかしブラインドスキャンはどのレベルでも絶対パスを検出するので、Dr. Kiro のファイルに絶対パスがあるとセッションを封印できなくなります（要件 15、設計 D12）。
- compare のバリアントは、1 組の関数に渡されるパラメーター値の行です（設計 7.1）。構造が異なるバリアントには、フラグとなるパラメーターと `if` が必要です。たとえば、あるバリアントで 2 つ目のチャンネルの振幅を 0 にします。テンプレートではこの方法を示します。

## 用語集

- **ベンチ（Bench）**: ここで規定するシステムです。
- **コア（Core）**: ベンチのうち、セッション状態を保持し、ゲートを強制する部分です。ベンチ操作を、トランスポートを持たないプログラミングインターフェースとして公開します。
- **フロントエンド（Front end）**: Dr. Kiro をコアにつなぐ部分です（要件 17）。
- **ベンチ操作（Bench action）**: 次のいずれかです: セッション開始、仮説登録、実験実行、判定記録、セッション終了、セッション停止。
- **アプリケーション（Application）**: 研究対象のシステムです（body-lab、wind-tunnel、またはフェイクアプリケーション）。
- **アダプター（Adapter）**: アプリケーションがベンチに接続するために提供するコードです（要件 2）。
- **ノブ（Knob）**: アダプターが宣言する、アプリケーションの入力の 1 つです。値の範囲を持つ時間の関数（body-lab のチャンネル）か、範囲を持つ数値（wind-tunnel のノブ）のどちらかです。
- **未計測結果（Not-measured outcome）**: 試行が値を得ずに終わりうる計測項目について、アダプターが理由とともに宣言する名前付きの結果です（たとえば、計測対象を追跡できなかった場合）。これは実験の結果であり、障害ではありません。
- **ラボの仕様ファイル（Lab spec files）**: アプリケーションの `lab/` フォルダー内にある、Dr. Kiro の `requirements.md`、`design.md`、`tasks.md` です。
- **仮説（Hypothesis）**: Dr. Kiro の `requirements.md` にあるエントリーで、id `H<n>`、EARS 形式の記述、1 つ以上の構造化予測を含む予測ブロックを持ちます。
- **凍結部分（Frozen part）**: 登録済みの仮説の id、記述、予測ブロックです。
- **構造化予測（Structured prediction）**: 計測名、予測が当てはまる条件、予測範囲の組です。
- **パラメーター（Parameter）**: 試行の入力を決める名前付きの数値です。数値ノブは、そのノブ自身の名前を持つパラメーターです。実験ファイルは、ノブの式が使うパラメーターを追加で宣言できます。
- **条件（Conditions）**: 予測が参照するパラメーター値です。
- **条件クラス（Condition class）**: それまでに実行された試行に照らして、ベンチが予測の条件を分類した結果です。inside the tried range（試行済みの範囲内）、new combination（試行済みの値の新しい組み合わせ）、outside the tried range（試行済みの範囲外）、not comparable（比較不能）のいずれかです。
- **実験ファイル（Experiment file）**: Dr. Kiro がラボの実験フォルダーに書くファイルです。1 つの仮説、1 つのフェーズ、1 つのモード、そのパラメーター、各試行のパラメーター値を指定し、実験言語でノブの値を計算します（要件 4）。
- **実験（Experiment）**: 実験ファイルの、受け付けられた 1 回の実行です。1 つ以上の試行からなります。
- **試行（Trial）**: 完全に計算された入力とシードによる、アダプターの 1 回の呼び出しです。
- **計算済み入力（Computed inputs）**: ベンチが実験ファイルを評価した後の、試行のノブの値です。数値ノブでは数値、時間関数ノブではアダプターのサンプル時刻における値です。
- **予測結果（Prediction outcome）**: 構造化予測に対するベンチの結果です。hit（的中）、miss（外れ）、not checkable（確認不能: 計測項目が未計測結果だった）、not run（未実行: 条件に一致する試行がなかった）のいずれかです。
- **判定（Verdict）**: 実験の後に Dr. Kiro が下す仮説の判断です。`supported`、`partly`、`rejected` のいずれかで、Dr. Kiro 自身の言葉を伴います。
- **判定フラグ（Verdict flag）**: 判定と予測結果が食い違うときに、ベンチが記録する印です。
- **フェーズ（Phase）**: Dr. Kiro のタスクの 4 つの段階の 1 つです: システムを把握する、ルールを述べる、一度も実行していない条件でルールを検証する、最良の点を予測する。
- **ルールステータス（Rule status）**: `## Discovered spec` の表の行のステータスです: `observed`、`validated`、`partly`、`rejected` のいずれかです。
- **拒否（Refusal）**: ラボのルールによって拒否されたベンチ操作です。Dr. Kiro はこれを修正できます。実行は記録されず、予算も消費されません。
- **ベンチ障害（Bench failure）**: ベンチまたはアダプターの障害です。セッションは停止します。
- **セッション記録（Session record）**: 1 つのセッションについてベンチが書くもののすべてです。
- **封印済みセッション記録（Sealed session record）**: 封印した後のセッション記録です。変更できず、ハッシュが付き、ノートブックへの唯一の入力です。
- **ブラインドスキャン（Blind scan）**: `rules.md`（Blind scan）で定義された検査で、ここで実装します（要件 15）。

---

# コア

### 要件 1: フロントエンドなしのコア

**ユーザーストーリー:** ビルダーとして、ゲートを直接テストでき、フロントエンドを MCP スパイクの後に選べるように、フロントエンドなしでコアを使えるようにしたいです。

#### 受け入れ基準

1. THE core SHALL すべてのベンチ操作を、プログラミングインターフェースの呼び出しとして公開する。その呼び出しは操作の入力を受け取り、3 つの結果のうちちょうど 1 つを返す: 実行（その結果付き）、拒否（理由付き）、ベンチ障害（理由付き）。
2. THE core SHALL NOT いかなるフロントエンド、トランスポート、エージェントフレームワーク、フックも、インポートする、呼び出す、または前提にする。
3. THE core SHALL 設定（アダプター、ラボフォルダー、ラボの仕様ファイルのパス、実験フォルダー、ベンチ状態フォルダー、セッションシード）をセッション開始時に明示的に受け取り、いずれかが欠けている場合は、デフォルトで補わずに開始を拒否する。
4. THE core SHALL ベンチ操作を 1 つずつ適用し、セッション状態へのすべての変更がアトミックになり、重なり合う呼び出しがゲートを迂回できないようにする。

### 要件 2: アダプター契約

**ユーザーストーリー:** ビルダーとして、新しいアプリケーションのためにベンチを変更しなくて済むように、アプリケーションが小さく固定された契約を提供するだけで接続できるようにしたいです。

#### 受け入れ基準

1. THE bench SHALL アダプターを通じてアプリケーションを受け入れる。アダプターが提供するのは次のものだけである: ノブ（名前、種類、範囲。時間関数ノブではさらに、試行の長さと、制御レートから決まるサンプル時刻）、1 回の試行の実行方法、計測する項目の名前と単位および各計測項目がとりうる未計測結果、1 種類の画像、試行数で表した予算、目標（最良の点が最大化または最小化する計測項目を名指しする 1 文）、計測の方法（1 つの短いテキスト。たとえば、カメラが何を見られるか、その視野の大きさ）。
2. THE bench SHALL アダプターの宣言を、Dr. Kiro に伝えるアプリケーションの完全な記述として扱い、ブラインドスキャンの許可リストとして使う（要件 15）。
3. WHEN ベンチが試行を実行するとき、THE bench SHALL アダプターに計算済み入力と試行シードだけを渡す。
4. WHEN 試行が完了したとき、THE adapter SHALL 宣言されたすべての計測項目について、値か、その計測項目について宣言された未計測結果の 1 つとその理由のどちらかを返し、画像をちょうど 1 つ返す。
5. WHEN アダプターが宣言済みの未計測結果を返したとき、THE bench SHALL それをその未計測結果として理由とともに記録し、値で補わない。
6. IF 計測項目が宣言済みの未計測結果なしに欠けている場合、値が余分である・有限でない・型が誤っている場合、または未計測結果がその計測項目について宣言されていない場合、THEN THE bench SHALL それをベンチ障害として扱う。
7. IF アダプターが障害を報告した場合、または応答を返さない場合、THEN THE bench SHALL それをアダプターの理由付きのベンチ障害として扱い、いかなる値でも代用しない。
8. THE アダプター契約 SHALL 同じ計算済み入力とシードから、同じ計測値、同じ未計測結果、同じ画像が得られることを要求する。
9. 2 つのアプリケーション body-lab と wind-tunnel はどちらも決定的で、シードを使わない。同じ計算済み入力からは同じ結果が得られる。このため、ベンチは試行の完全な繰り返しを、再実行せずに拒否する（要件 6.5 と 7.4）。
10. THE 時間関数ノブの制御レート、試行の長さ、サンプル時刻 SHALL Dr. Kiro に伝える宣言の一部とする。これらは研究対象のシステムではなく、計測器に属する。どのチャンネルがシステムのどの部分を、どの符号で駆動するかは、宣言の一部としないものとする。

### 要件 3: セッション開始とシード

**ユーザーストーリー:** ビルダーとして、再現できるように、すべてのセッションを明示的なシードと既知の予算から開始したいです。

#### 受け入れ基準

1. WHEN ビルダーがセッションを開始したとき、THE bench SHALL アプリケーション、アダプターの宣言、セッションシード、予算を記録し、セッションに id を付ける。
2. THE bench SHALL 各試行のシードを、セッションシードとセッション内での試行番号から導出し、シードを使わないアダプターの場合も含めて、その両方を試行とともに記録する。
3. THE bench SHALL セッション記録内のすべてをシーケンス番号で順序付ける。実時間の時刻は、ハッシュ対象のセッション記録に含めないものとする。実時間の時刻はビルダー側のログにだけ書く。
4. WHEN 同じアダプター、同じシード、同じ入力によるベンチ操作の同じ並びで 2 つのセッションを実行したとき、THE bench SHALL バイト単位で同一のセッション記録を生成する。

### 要件 4: 実験言語

**ユーザーストーリー:** Dr. Kiro として、最もよく機能する入力を表現できるように、本物のプログラム構造（時間の区分関数、補間付きのキーフレーム、位相のずれ）で試行の入力を記述したいです。

#### 受け入れ基準

1. THE bench SHALL Python の制限されたサブセットで書かれたノブの値を受け付ける。このサブセットで使えるのは次のものである: 関数定義、ローカル変数、`if`/`else` と条件式、比較、リストとインデックス、リストまたは `range(...)` に対する `for` ループと `break`・`continue`、算術演算、`math` モジュールの関数と定数。`while` は使えないものとする。ループはステップ上限（4.4）で抑える。
2. THE bench SHALL 何かを評価する前に、すべての実験ファイルを構文木のノード型のホワイトリストと照合し、ホワイトリスト外のものを含む場合は、行と構文を示してファイルを拒否する。拒否される構文には、`math` 以外のインポート、`math` の関数と定数以外の属性アクセス、ファイルやネットワークへのアクセス、ホワイトリストにない組み込み関数の呼び出しが含まれる。
3. THE bench SHALL 検査済みの構文木に対して独自の評価器で実験ファイルを評価し、実行のためにファイルを `exec`、`eval`、`compile` に渡さない。
4. THE bench SHALL 実験ファイルごとの評価ステップ数に上限を設け、評価が上限を超えた場合は、上限を示してファイルを拒否する。
5. IF 評価でエラー（たとえばゼロ除算やインデックスの範囲外）が発生した場合、THEN THE bench SHALL 行とエラーを示してファイルを拒否し、値で代用しない。
6. WHEN 計算済み入力がそのノブの範囲外であるとき、または有限の数値でないとき、THE bench SHALL ノブ、試行、および時間関数ノブの場合は最初に不適合となるサンプル時刻を示して、ファイルを拒否する。THE bench SHALL NOT 値をクリップする。
7. THE bench SHALL 実験ファイルのどの試行を実行するよりも前に、そのファイルのすべての検査とすべての評価を完了する。
8. THE 実験ファイル SHALL パラメーターと各試行のパラメーター値を数値として宣言する。数値ノブは、そのノブ自身の名前を持つパラメーターである。

### 要件 5: 実験モード

**ユーザーストーリー:** Dr. Kiro として、いくつかの選択肢を比較したり、パラメーターを掃引したりできるように、2 つの実験モードが欲しいです。

#### 受け入れ基準

1. THE bench SHALL ちょうど 2 つのモードを受け付ける: 1 から 3 個のバリアントを持つ `compare` と、1 個または 2 個のパラメーターについて合計ちょうど 6 点を持つ `sweep`。
2. `sweep` モードでは、Dr. Kiro が 6 点を実験ファイルに列挙するものとする。ベンチは点を配置しないものとする。
3. IF 実験ファイルが別のモードを宣言している場合、バリアント数や点数がこれらの制限外である場合、または掃引する 1 個か 2 個のパラメーター以外のパラメーターをほかの点と異なる値に設定する掃引点がある場合、THEN THE bench SHALL 制限を示してそれを拒否する。
4. THE 実験の試行数 SHALL その実験のバリアント数または点数と等しい。

### 要件 6: 仮説の登録

**ユーザーストーリー:** Dr. Kiro として、書いた仮説を、それを検証する実験より前に凍結されるように登録したいです。

#### 受け入れ基準

1. WHEN Dr. Kiro が id を指定して仮説を登録したとき、THE bench SHALL Dr. Kiro の `requirements.md` から仮説の凍結部分（id、記述、予測ブロック）を読み取り、凍結部分の写しとそのハッシュを記録する。
2. IF id が `requirements.md` に見つからない場合、またはすでに登録済みの場合、THEN THE bench SHALL id を示して登録を拒否する。
3. IF 記述が EARS の形になっていない場合、仮説に予測ブロックがないかその中に構造化予測がない場合、または予測が、アダプターが宣言していない計測項目を指定している・範囲が空か逆転している・条件がノブの範囲外である場合、THEN THE bench SHALL 行と問題を示して登録を拒否する。THE bench SHALL 記述の内容ではなく、記述の形を検査する。
4. WHEN 仮説が登録されたとき、THE bench SHALL 各予測の条件を、それまでに実行された試行に照らして分類する。対象とするのは、予測と同じパラメーター名を宣言する実験の、それより前の試行だけである。分類は inside the tried range、a new combination of tried values、outside the tried range、または同じパラメーターを宣言する以前の試行がない場合の not comparable のいずれかである。THE bench SHALL この条件クラスを、Dr. Kiro が予測に付けたラベル（同じ 4 つのクラスのいずれか）と並べて記録する。両者の違いは記録するものとし、拒否はしないものとする。
5. IF 予測の条件が、同じパラメーターですでに実行された試行のパラメーター値とまったく同じである場合、THEN THE bench SHALL 予測と、結果が当てはまる以前の実験を示して、登録を拒否する。
6. WHILE `requirements.md` 内の登録済み仮説の凍結部分が記録された写しと異なるか欠けている間、THE bench SHALL Dr. Kiro がそれを復元するまで、仮説を示して、セッション停止以外のすべてのベンチ操作を拒否する。
7. Dr. Kiro が登録済み仮説の予測ブロックの後ろ、次の仮説までに追記したテキスト（メモ、結果）は、凍結部分に含まれないものとし、要件 6.6 を発動させないものとする。凍結部分の内側に挿入されたテキストは、要件 6.6 を発動させるものとする。
8. THE bench SHALL `requirements.md` 内の未登録の仮説を、検査せずに受け入れる。

### 要件 7: 実験の実行

**ユーザーストーリー:** Dr. Kiro として、仮説を判断できるように、登録済みの仮説を検証する実験を実行し、その計測値と画像を受け取りたいです。

#### 受け入れ基準

1. THE bench SHALL 仮説を指定していない実験ファイル、または登録されていない仮説を指定する実験ファイルの実行を、id を示して拒否する。
2. THE bench SHALL フェーズをちょうど 1 つ指定していない実験ファイルを拒否する。
3. WHILE 以前の実験に判定がない間、THE bench SHALL 判定が必要な実験を示して、別の実験の実行を拒否する。
4. THE bench SHALL ヘッダーやコメントの変更で実験が新しいものにならないように、各試行をファイルのテキストではなく計算済み入力で識別する。IF 実験のいずれかの試行が、すでに実行された試行と同じ計算済み入力を持つ場合、THEN THE bench SHALL 結果が当てはまる以前の実験を示して、その実験を拒否する。
5. IF 実験の試行数が残りの予算を超える場合、THEN THE bench SHALL 必要な試行数と残りの数を示して、それを拒否する。
6. WHEN 実験がすべての検査を通過したとき、THE bench SHALL アダプターを通じてその試行を実行し、書かれたままの実験ファイル、そのフェーズ、パラメーター、計算済み入力、シード、すべての計測値または未計測結果、すべての画像を記録し、残りの予算を試行数だけ減らし、Dr. Kiro には計測値と未計測結果、画像、残りの予算だけを返す。
7. WHEN 実験が実行されたとき、THE bench SHALL その仮説の各構造化予測について予測結果を記録する: 実験のある試行が予測のパラメーターと条件を持ち、その計測項目の値がある場合は hit または miss、その試行の計測項目が未計測結果である場合は not checkable、実験のどの試行も一致しない場合は not run。同じ仮説に対する後の実験が、not run の予測をほかの結果のいずれかに変えてもよい。それ以外の結果は、一度記録されたら変わらないものとする。
8. IF 試行がベンチ障害で終わった場合、THEN THE bench SHALL 完了した試行の記録を保持し、障害とその理由を記録し、セッションを停止する（要件 11）。

### 要件 8: 判定の記録

**ユーザーストーリー:** Dr. Kiro として、先に進む前に自分の判断が記録に含まれるように、各実験の後に仮説への判定を記録したいです。

#### 受け入れ基準

1. WHEN Dr. Kiro が判定のない実験について判定を記録したとき、THE bench SHALL 判定（`supported`、`partly`、`rejected`）と、書かれたままの Dr. Kiro の言葉を記録する。
2. IF 判定が 3 つの値のいずれでもない場合、または実験が存在しないか、すでに判定がある場合、THEN THE bench SHALL 問題を示してそれを拒否する。
3. IF 判定が `supported` で、仮説のいずれかの構造化予測の結果が miss である場合、THEN THE bench SHALL miss となった予測とその計測値を示して、それを拒否する。
4. WHEN 判定が記録されたとき、THE bench SHALL 次のいずれかの場合に、各予測結果の件数を付けて判定フラグを記録する: 判定が `supported` で hit の予測が 1 つもない場合、判定が `partly` で予測が hit と miss の混在でない場合、判定が `rejected` で miss の予測が 1 つもない場合。THE bench SHALL NOT これらの判定を拒否する。

### 要件 9: 実行と拒否の記録

**ユーザーストーリー:** ビルダーとして、記録を信頼できるように、すべての操作の記録を Dr. Kiro ではなくベンチに書かせたいです。

#### 受け入れ基準

1. THE bench SHALL すべてのベンチ操作とその結果を、理由付きのすべての拒否も含めて記録する。
2. 拒否は、記録に自身のエントリーを追加すること以外にセッション状態を変えないものとし、予算を消費しないものとする。
3. THE bench SHALL セッション記録を、すべての `lab/` フォルダーの外にあるベンチ状態フォルダーにだけ書く。
4. THE bench SHALL 記録のすべてのエントリーを追記専用にする。書かれた後に変更または削除されるエントリーはない。
5. THE bench SHALL ブラインドスキャンが適切なレベルを適用できるように（要件 15）、記録内の各テキストを誰が書いたか（ベンチか Dr. Kiro か）を記録する。
6. WHEN Dr. Kiro がラボ外のパス（絶対パス、`..` を含むパス、解決するとラボフォルダーの外になるパス、またはブラインドスキャンが検出したパス）をベンチに渡したとき、THE bench SHALL パスを返答に含めずに操作を拒否し、パスの代わりに "a path outside the lab" と書いて拒否を記録し、完全なパスはビルダー側のログにだけ書く。記録には Dr. Kiro が試みたという事実が残り、セッションは引き続き封印できる。

### 要件 10: Dr. Kiro の仕様ファイルのスナップショット

**ユーザーストーリー:** ビルダーとして、ノートブックがセッションを再生できるように、各ステップでの Dr. Kiro の 3 つの仕様ファイルの写しが欲しいです。

#### 受け入れ基準

1. WHEN 実験が実行されたとき、および WHEN 判定が記録されたとき、THE bench SHALL その時点の Dr. Kiro の `requirements.md`、`design.md`、`tasks.md` の写しを、その記録エントリーに関連付けて保存する。
2. IF スナップショットを取るべきときにラボの仕様ファイルが欠けている場合、THEN THE bench SHALL ファイルを示して操作を拒否する。
3. THE bench SHALL NOT 拒否のときにスナップショットを取る。
4. WHEN Dr. Kiro がセッションを終了し、ベンチがそれを受け付けたとき（要件 11.1）、THE bench SHALL `## Discovered spec` の表の検査に使ったのと同じ読み込みから取った、3 つの仕様ファイルの最後の写しを、封印エントリーの前に保存する。
5. WHEN セッションが「停止」として封印されるとき（要件 11.3、11.4）、THE bench SHALL NOT 仕様ファイルの最後の写しを取る。停止したセッションの最後のスナップショットは、あればその最後の実行または判定のときのものである。

### 要件 11: セッションの終了と停止

**ユーザーストーリー:** ビルダーとして、うまくいかなかったセッションも起きたとおりに保存されるように、すべてのセッションを、理由が明記された封印済み記録として終わらせたいです。

#### 受け入れ基準

1. WHEN Dr. Kiro がセッションを終了するとき、THE bench SHALL 判定のない実験がある場合、または `## Discovered spec` の表の検査（要件 12）に失敗した場合は、問題を示して拒否する。それ以外の場合、THE bench SHALL 仕様ファイルの最後のスナップショット（要件 10.4）の後に、残りの予算を記録して、セッションを「終了」として封印する。
2. WHEN 予算がゼロになったとき、THE bench SHALL それ以降の実験を拒否し、判定とセッション終了は引き続き受け付ける。
3. WHEN ベンチ障害が発生したとき、THE bench SHALL `## Discovered spec` の表の検査を行わずに、障害とその理由を付けてセッションを「停止」として封印し、そのセッションに対する以降のすべての操作を拒否する。
4. WHEN ビルダーがセッションを停止したとき、THE bench SHALL 表の検査を行わずに、ビルダーが示した理由を付けてセッションを「停止」として封印する。
5. THE bench SHALL ベンチ障害を Dr. Kiro には Dr. Kiro 向けの言葉（`rules.md`、Blind）でのみ示し、詳細のすべてをビルダー側のログに書く。

### 要件 12: Discovered spec の表

**ユーザーストーリー:** ビルダーとして、ノートブックのすべての行をたどることができ、どのルールも根拠以上のことを主張しないように、Dr. Kiro が発見した仕様では、実験で観察されただけのルールと、未試行の条件での予測によって検証されたルールを区別し、記録と一致するステータスを付けてほしいです。

#### 受け入れ基準

1. WHEN Dr. Kiro がセッションを終了するとき、THE bench SHALL `design.md` の末尾が `## Discovered spec` の表であり、1 行に 1 つのルールがあり、列が id、rule、scope、experiments、predictions、status、replaced by であることを検査する。
2. IF 表がない場合、行に必須の列が欠けている場合、または行が記録や表に存在しない実験・予測・行を引用している場合、THEN THE bench SHALL 行を示してセッションの終了を拒否する。
3. THE bench SHALL ちょうど 4 つのステータス値を受け付け、ステータスが次のとおり記録と一致しない限り、行と、引用された結果と条件クラスを示してセッションの終了を拒否する:
   - `observed`（実験で観察された）: 行が少なくとも 1 つの実験を引用し、引用された予測に miss が 1 つもない。どの条件クラスの hit も、not run と not checkable の予測も許される。ルールは根拠より少なく主張してもよいが、根拠より多く主張してはならない。
   - `validated`（引用されたすべての予測が成り立った）: 行が少なくとも 1 つの予測を引用し、引用されたすべての予測が hit であり、引用された hit の少なくとも 1 つの条件クラスが new combination または outside the tried range である。条件クラスが inside the tried range または not comparable の hit は、`validated` には数えない。
   - `partly`（引用された予測の一部が成り立った）: 行が少なくとも 1 つの hit と少なくとも 1 つの miss を引用する。
   - `rejected`: 行が少なくとも 1 つの miss を引用し、その "replaced by" 列が、その行を置き換える行の id を指定する。
4. `rejected` 以外のステータスの行は、"replaced by" を空のままにするものとする。
5. THE 表 SHALL セッション終了時に少なくとも 1 行を持つ。セッション中に取ったスナップショット（要件 10）を含め、それ以前の `design.md` のどの状態でも、空の表は許される。
6. 最後のスナップショット（要件 10.4）に記録される表 SHALL 検査に通った表と 1 バイトも違わない。

### 要件 13: 封印済みセッション記録

**ユーザーストーリー:** ビルダーとして、ノートブックがほかに何も必要としないように、ノートブックのすべての画面を再構築するのに十分な封印済み記録が欲しいです。

#### 受け入れ基準

1. WHEN セッションが封印されるとき、THE bench SHALL 記録に対してブラインドスキャンを実行する（要件 15）。IF スキャンが何かを検出した場合、THEN THE bench SHALL ファイルと行を示して失敗し、記録を `sessions/` に書かずにベンチ状態フォルダーに保持する。それ以外の場合、THE bench SHALL 封印済みセッション記録を `sessions/<application>/<session-id>/` に書く。
2. THE 封印済みセッション記録 SHALL ノートブックが表示するすべてを含む: アダプターの宣言、シードと予算、凍結部分付きのすべての登録済み仮説、条件クラス・Dr. Kiro のラベル・予測結果付きのすべての予測、フェーズ・パラメーター・計算済み入力・シード・計測値・未計測結果・画像付きの、書かれたままのすべての実験ファイル、すべての判定と判定フラグ、すべての拒否とその理由、すべてのスナップショット、終了したセッションについては終了時に検査した最後の仕様ファイル（要件 10.4。その `## Discovered spec` の表を含む）、各テキストの書き手、終了理由。
3. THE bench SHALL すべてのエントリーとファイルにわたる SHA-256 のハッシュチェーンで、署名鍵を使わずに記録を封印する。
4. THE bench SHALL 封印済み記録のハッシュチェーンを再計算し、一致しない最初のエントリーまたはファイルを示して失敗する検査を提供する。
5. IF セッションフォルダーがすでに存在する場合、THEN THE bench SHALL それを示して失敗し、上書きしない。

### 要件 14: フェイクアプリケーション

**ユーザーストーリー:** ビルダーとして、シミュレーターなしでセッション全体を実行・テストできるように、振る舞いがわかっているフェイクアプリケーションが欲しいです。

#### 受け入れ基準

1. THE bench SHALL アダプター契約を実装するフェイクアプリケーションを含める。このアプリケーションは、少なくとも 1 つの時間関数ノブと少なくとも 1 つの数値ノブ、高速で決定的な試行、少なくとも 1 つの宣言済み未計測結果、小さな画像を持つ。
2. THE フェイクアプリケーション SHALL 決まった入力値に対して失敗し、また決まった入力値に対して未計測結果を返して、その両方をテストできるようにする。そのきっかけは計算済み入力だけに依存するものとし、呼び出し回数やほかのアダプター状態には決して依存しないものとする。これにより、新しいアダプターを作る再開されたセッションでも同じように振る舞う。
3. THE フェイクアプリケーション SHALL 独自の部品名を持つモデルファイルを含め、それに対してブラインドスキャンをテストできるようにする。
4. フェイクアプリケーションに対するセッション全体が、コアのインターフェースを通じて、開始から封印まで実行できるものとする。
5. フェイクアプリケーションが生成した数値は、それを含むすべての記録でフェイクと明示するものとし、結果として提示しないものとする（`rules.md`、Honest）。

### 要件 15: ブラインドスキャン

**ユーザーストーリー:** ビルダーとして、ブラインドが構造上守られ、後のすべての部分（body-lab、wind-tunnel、ノートブック、公開）が同じ検査を再利用できるように、Dr. Kiro の視界、ベンチの出力、記録の中からモデルを明かすものを見つける 1 つの自動検査が欲しいです。

#### 受け入れ基準

1. THE bench SHALL `rules.md`（Blind scan）で定義されたブラインドスキャンを、コマンドとして、また呼び出しとして提供する。ブラインドスキャンはスキャンするパスを受け取り、見つけたすべてのファイルと行を、検出の種類とともに示して失敗する。
2. THE blind scan SHALL 禁止語を、スキャン時に各アプリケーションのモデルファイルとソルバーファイルから導出する。これらのファイルは、アプリケーションが `lab/` フォルダーの外、かつアダプター宣言の外でスキャナーに指定する。THE blind scan SHALL NOT 手作業で写した語のリストを含む。
3. THE blind scan SHALL 導出した語から、アプリケーションのアダプター宣言（許可リスト）と `.kiro/blind-scan/stop-list.txt` の語（除外リスト）を取り除き、それ以外は何も取り除かない。
4. THE blind scan SHALL ビルダーまたはベンチが書いたテキスト（ビルダーが `lab/` に置く、Dr. Kiro の仕様ファイルと実験ファイル以外のすべてのもの、ベンチの出力と記録にあるベンチ自身の文言）について、語、パスとファイル名、認証情報をスキャンする。
5. THE blind scan SHALL Dr. Kiro が書いたテキスト（Dr. Kiro の仕様ファイル、実験ファイル、それらのスナップショット、判定の言葉、ベンチがメッセージ内で引用する Dr. Kiro のファイルの行や名前）については、パスとファイル名、認証情報だけをスキャンする。
6. WHERE テキストがコピーされる場合（スナップショット、封印済み記録、ノートブックのビルド出力、公開ファイル）、THE blind scan SHALL テキストとともに記録された書き手を使って、その書き手のレベルを適用する。
7. IF ブラインドスキャンがテキストの書き手を判定できない場合、またはモデルファイル、ソルバーファイル、除外リストを読めない場合、THEN THE blind scan SHALL それを示して失敗し、レベルを推測したりファイルを飛ばしたりしない。
8. WHEN ベンチが Dr. Kiro に何かを返そうとするとき、THE bench SHALL ベンチ自身の文言をビルダーレベルで、Dr. Kiro のファイルから引用したテキストを Dr. Kiro レベルでスキャンし、IF スキャンが何かを検出した場合、THEN THE bench SHALL それをベンチ障害として扱い、その内容を何も返さない。Dr. Kiro 自身のテキストの引用は、語を含むという理由で拒否をベンチ障害に変えないものとする。
9. WHERE `lab/` フォルダー内のファイルが画像である（名前が `.png`、`.gif`、`.webp` で終わる）場合、THE blind scan SHALL それをテキストとして読む代わりに、アダプター契約の画像検査（設計のセクション 4: 形式のシグネチャー、およびテキストチャンクやメタデータチャンクがないこと）で検査し、検査に通らない画像を検出として報告する。UTF-8 テキストでないそれ以外のファイルは、引き続きスキャンを失敗させる（15.7）。
10. WHERE フォルダーに `source.json` がある（最終仕様の写し、`dr-kiro` 要件 8）場合、THE blind scan SHALL 3 つの仕様ファイルのそれぞれを、その SHA-256 が `source.json` の示すものと等しい間だけ Dr. Kiro のレベルでスキャンし、`source.json` をハッシュを除いてビルダーレベルでスキャンする。IF ファイルが一致しない、欠けている、または 4 つのどれでもない場合、THEN THE blind scan SHALL そのファイルを示して失敗する（15.7）。
11. WHERE ラボ内のファイルが、ラボの Dr. Kiro の glob に当てはまり、Dr. Kiro のテンプレート（`dr-kiro` 要件 4）のどれかとバイト単位で同じ内容を持つ場合、THE blind scan SHALL それをビルダーレベルでスキャンする: テンプレートは、Dr. Kiro が変えるまではビルダーの文章である。

### 要件 16: ゲートのプロパティベーステスト

**ユーザーストーリー:** ビルダーとして、誰も試そうと思わなかった操作に対してもゲートが守られるように、エージェントの操作のランダムな並びでゲートをテストしたいです。

#### 受け入れ基準

1. THE bench SHALL ステートフルなプロパティベーステスト（`hypothesis`）を持つ。このテストは、フェイクアプリケーションに対して、有効な入力と無効な入力によるベンチ操作のランダムな並びを生成する。これには、操作の間に行う Dr. Kiro の仕様ファイルの編集（凍結部分の内側と外側）と、未計測結果を返す試行が含まれる。
2. THE tests SHALL 各操作の後に、少なくとも次の点を検査する: 登録済みの仮説なしに実行された実験がないこと、操作が受け付けられている間に凍結部分が変わっていないこと、予測ブロックの後ろに追記したテキストが拒否を起こしていないこと、同じ計算済み入力で 2 回実行された試行がないこと、以前の実験に判定がない間に実行された実験がないこと、消費した予算が実行した試行数と等しく、予算を超えていないこと、すべての拒否が自身の記録エントリーを除いて状態を変えていないこと、未計測結果に対して値が記録されていないこと、miss に対して `supported` が記録されていないこと、判定フラグが要件 8.4 の定めるときにちょうど記録されていること、すべての実行、判定、受け付けられた終了にスナップショットがあり、停止したセッションには最後の写しがないこと、Dr. Kiro に返されたものに、計測値、未計測結果、画像、残りの予算、Dr. Kiro 向けの言葉による拒否理由以外のものが含まれていないこと。
3. THE tests SHALL セッションの終了が、`## Discovered spec` の表が要件 12 の定義どおりに記録と一致するときにちょうど受け付けられることを検査する。これには、hit が inside the tried range または not comparable のものだけである `validated` の行も含まれる。また、終了したセッションの最後のスナップショットにある `design.md` が同じ検査に通ることを検査する。
4. THE tests SHALL 封印済み記録がハッシュ検査に通ること、およびそのどの 1 バイトを変えても検査が失敗することを検査する。
5. THE tests SHALL 同じシードと同じ操作の並びから同じ封印済み記録が得られることを検査する。
6. THE tests SHALL 実験の評価器がホワイトリスト外のすべての構文ノードを拒否し、ステップ上限より長く実行されないことを検査する。
7. THE tests SHALL ブラインドスキャンが、許可リストにも除外リストにもない導出された語をビルダーレベルのテキストに仕込んだときにすべて検出し、同じ語を Dr. Kiro レベルのテキストでは無視し、仕込んだパス、ファイル名、認証情報を両方のレベルで検出することを検査する。
8. THE tests SHALL 導出された語を含む Dr. Kiro 自身のテキスト（たとえば部品名から作ったパラメーター名）をメッセージで引用する拒否は、拒否のままで Dr. Kiro に届き、一方でベンチ自身の文言に含まれる同じ語はベンチ障害になることを検査する。

---

# フロントエンド


### 要件 17: フロントエンド

**ユーザーストーリー:** Dr. Kiro として、シェルなしで実験できるように、いくつかのツールを通じてベンチを実行し、画像をファイルとして開きたいです。ビルダーとして、人を待つセッションが生じないように、確認を求める仕組みではなく拒否する仕組みによって Dr. Kiro をラボ内にとどめたいです。

MCP スパイク（`spikes/mcp/results.md`）の後にユーザーが決定した内容は次のとおりです: フロントエンドは MCP サーバーとし、Dr. Kiro はシェルを持ちません。画像はラボ内のファイルとして、そのパスとともに返します。並列の呼び出しはキューに入れて 1 つずつ実行します。スパイクの禁止ルールは禁止せずに確認を求めたため、ツール実行前フックがラボフォルダー外のファイルの読み書きをすべて拒否します。ブラインドのためにここで追加するものはありません。コアのスキャン（要件 15）が、フロントエンドが書くもの・返すもののすべてをすでに対象にしています。コアのどの部分もこの要件に依存しません。

#### 受け入れ基準

*ベンチの呼び出し*

1. THE front end SHALL stdio 上の MCP サーバーで、名前を `bench` とし、Dr. Kiro のツール呼び出しをコアの呼び出し（要件 1）に変換して、コアの結果を返す。フロントエンドは独自のゲートを追加しないものとする。
2. THE front end SHALL Dr. Kiro が使うベンチ操作ごとに 1 つのツールを公開する: 仮説登録、実験実行、判定記録、セッション終了。セッション開始とセッション停止はツールにしないものとする。これらはビルダーの操作である（要件 3.1 と 11.4）。
3. THE front end SHALL 要件 1.1 の 3 つの結果を次のように返す:
   - 実行: 計測値、未計測結果、画像のパス、残りの予算だけを保持するツール結果（要件 7.6）。
   - 拒否: Dr. Kiro が修正できるように、テキストが Dr. Kiro 向けの言葉による拒否理由であるツールエラー。
   - ベンチ障害: セッションは「停止」として封印され（要件 11.3）、理由は Dr. Kiro 向けの言葉で示され（要件 11.5）、以降のすべての呼び出しは拒否される。
4. THE ツール名、説明、入力スキーマ SHALL ビルダーが書いたものとし、アダプターが宣言するものだけを記述する（要件 2.2）。
5. THE セッションの設定（予算、シード、フォルダー） SHALL セッション開始時にビルダーから与えられる（要件 1.3）。Dr. Kiro は、ツールの入力を通じてそれを設定または変更できないものとする。

*Dr. Kiro のエージェントと権限*

6. Dr. Kiro のエージェント定義は、ファイルの読み取りツールと書き込みツール、およびベンチのツールを Dr. Kiro に与え、それ以外は何も与えないものとする: シェルなし、Web アクセスなし、ほかの MCP サーバーなし（ワークスペースの MCP 設定を含む）、パワーなし。Kiro の `read` と `write` のツール群は、ほかのツールも提供する（task 21 で観測: `code`、`delete_file`、`disclose_context`、`tool_call`）。これらは閉じ込めフックが拒否するものとする。フックは表にないツールをすべて拒否する（17.9）。
7. Dr. Kiro は、自身のエージェント定義、フック、ステアリング、設定、MCP 設定（ラボの `.kiro/agents/`、`.kiro/hooks/`、`.kiro/steering/`、`.kiro/settings/`。保護フォルダー）を変更できず、MCP サーバーを追加または起動することもできないものとする。保護フォルダーに対する禁止ルールがこれを強制するものとし、閉じ込めフックもそれらへの書き込みを拒否するものとする（17.8）。Dr. Kiro は、`.kiro/specs/` にあるラボの仕様ファイルを読み書きできるものとする。保護フォルダーの読み取りは防がれない: 検索ツールは禁止ルールで止まらず（`spikes/mcp/results.md`、Q7）、その内容はブラインドスキャン（要件 15）に通るビルダーのテキストである。
8. ラボの `.kiro/` にあるツール実行前フックは、ラボフォルダー外のパスを読み書きするすべてのツール呼び出しを拒否するものとする。THE フック SHALL 比較する前にパス（相対パス、`..` セグメント、シンボリックリンク）を解決し、権限ルールだけに頼らない。ラボ外への呼び出しは必ず拒否で終わるものとし、人への確認で終わってはならない。THE フック SHALL 17.7 の保護フォルダーへのすべての書き込みも拒否する。Kiro は既定で、`.kiro/agents/` と `.kiro/hooks/` への書き込みの前に人に確認を求めるためである。
9. IF フックが入力を読めない場合、パスを解決できない場合、または入力を分類できない呼び出しに出会った場合、THEN フックは、ブロック用の終了コードと、Dr. Kiro 向けの言葉による理由（フックの内部ではなくフォルダーのルール）を付けて、その呼び出しを拒否するものとする。フックはその呼び出しを通さないものとする。
10. THE 内容検索ツールとファイル名検索ツール（入力にパスを持たない） SHALL ワークスペースだけを検索し、ワークスペースはラボフォルダーとする（要件 17.12）。フックはそれらをそれ以上検査しないものとする。
11. 2 つ目のフックが、すべてのツール呼び出しの名前と入力を、その実行前と実行後に記録するものとする。THE ログ SHALL ビルダーのためにラボの外に保管し、封印済みセッション記録には含めない。これにはフック自身の拒否も含まれる。
12. Dr. Kiro は、ラボフォルダーを作業フォルダーとして起動した Kiro CLI の中でだけ実行するものとする。Kiro IDE はビルダー用と仕様の表示用であり、Dr. Kiro の実行には決して使わない。

*画像*

13. WHEN 実験が実行されたとき、THE front end SHALL 各試行の画像をラボ内の画像フォルダーにファイルとして書き、ラボからの相対パスを、その試行の計測値とともに返す。THE front end SHALL NOT ツール結果で画像の内容を返す。
14. THE 画像のファイル名 SHALL 実験と試行を識別する。
15. THE front end SHALL 結果を返す前に、すべての画像ファイルを書き終えている。IF ファイルを書けない場合、THEN それはベンチ障害であり、ほかのベンチ障害と同じようにセッション記録に記録される（要件 11.3）。
16. ラボ内のファイルは写しである。封印済み記録内の画像（要件 13.2）はアダプターが返したものであり、ラボの写しを変更しても記録は変わらないものとする。

*長時間の呼び出しと並列の呼び出し*

17. THE front end SHALL ベンチ操作が終わるまで呼び出しを開いたままにし、その同じ呼び出しで結果を返す。Dr. Kiro がポーリングするためのジョブ id を返さないものとする。
18. THE front end SHALL 最大 900 s の 1 回の呼び出しをサポートする。スパイクでは、Kiro CLI で 120 s、300 s、900 s の呼び出しがタイムアウトなしで返った（`spikes/mcp/results.md`、Q4）。ポーリングは使わないものとする。
19. THE front end SHALL 別の呼び出しの適用中に届いた呼び出しをキューに入れ、届いた順に 1 つずつ適用する（要件 1.4）。キューに入った各呼び出しは、直前の呼び出しが残した状態に対して検査されるものとする。たとえば、並列の `run experiment` 呼び出しのうち実行できるのは最初の 1 つだけである。残りは以前の実験に判定がないため拒否され（要件 7.3）、予算を消費しない。
20. THE セッション記録 SHALL 呼び出しが適用された順序を示す（要件 3.3）。

*テスト*

21. THE 閉じ込めフック SHALL 3 つのテストを持つ: ラボ外のパスを持つ呼び出しがブロック用の終了コードで拒否されること、不正な入力（有効な JSON でない、またはツール名が欠けている）がブロック用の終了コードで拒否されること、および保護フォルダー（17.7）への書き込みがブロック用の終了コードで拒否されること。

#### 注記

- スパイクで開いたのは PNG だけです。Dr. Kiro のファイルツールが wind-tunnel の渦度アニメーションを表示できるかは検証していません。画像の形式は、`wind-tunnel` 仕様がアダプターとともに決めます。
- スパイクでテストしていないこと: 900 s より長い呼び出し、およびラボ外への書き込み（スパイクの書き込みルールは、確認を求めた読み取りルールと同じパターンを持っています）。

---

# 改訂

### 要件 18: ノブの説明（改訂）

**改訂。** 要件 1-17 を実装しテストした後（タスク 1-22）、`wind-tunnel` spec の求め（その要件 3.2 と Decision 18）で加えました。既存の要件は番号の振り直しも書き換えもしません。この要件はノブに任意のテキストを 1 つ加え、したがって要件 2.1 のアダプターが提供するもののリストを、そのテキスト分だけ広げます。

**ユーザーストーリー:** アプリケーションのビルダーとして、ノブが宣言の一部である短い説明を持てるようにしたい。Dr. Kiro が各入力が何であるか（定義、単位、範囲の両端の意味）を、第 2 の経路なしに、宣言された 1 つの集合の中で伝えられるようにするためである。body-lab のビルダーとして、説明を与えないアプリケーションでは何も変わらないようにしたい。

**対象:** ビルダーとアダプターの作者。Dr. Kiro が説明を見るのは、ツールの説明の一部としてだけです（要件 17.4）。

#### 受け入れ基準

1. THE adapter contract SHALL let each knob, of either kind, carry a description: a text in the field `description`, whose default is the empty text。空のテキストは、そのノブに説明がないことを意味する。
2. WHEN the bench checks a declaration、THE bench SHALL refuse it, naming the knob and the problem, if a description is not text, contains a line break or any other control character, has a space or a tab at its start or end, or is longer than 800 characters。
3. THE bench SHALL NOT interpret a description。いかなるゲートも、実験ファイルの検査も、予測の検査も、それに依存してはならない。
4. WHEN a knob has a description、THE front end SHALL print it in the tool descriptions on the line of that knob, after the knob's range, with the same function that prints the rest of the declaration。WHILE a knob has no description、THE front end SHALL print the line of that knob exactly as before this amendment。
5. THE declaration SHALL remain the only source of what Dr. Kiro is told（要件 2.2）。THE description SHALL be part of the declaration and of the text that the front end builds from it (the told text)、and an application MAY export that text by calling the same function the front end uses。
6. WHEN the bench records the declaration at session start、THE bench SHALL write the key `description` for a knob whose description is not empty, and SHALL write no such key for a knob whose description is empty。したがって、説明を与えないアプリケーションの記録は、この改訂より前に作られた記録とバイト単位で同一である（要件 3.4）。
7. THE bench SHALL scan every description at the builder level, with the rest of the tool descriptions, when the front end starts (design F3), and SHALL scan the declaration in the record at the builder level when the session is sealed（要件 13.1）。THE words of a description SHALL NOT be added to the allow list; the allow list stays the declared names（要件 15.3）。
8. WHERE an application declares no description、THE bench SHALL give a told text and a session record that are byte-identical to those of the bench before this amendment。これは説明を宣言しない body-lab について成り立ち、body-lab の伝えるテキストと記録された宣言を、変更前のベンチから作ったファイルと比べるテストで SHALL be shown。
9. FOR ALL declarations, with and without descriptions, THE told text SHALL contain each non-empty description exactly as declared, on the line of its own knob, and SHALL contain no description of another knob on that line。

### 要件 19: アダプターの入力チェック（改訂）

**改訂。** 要件 1-18 を実装しテストした後に、`wind-tunnel` spec の求め（そのタスク 14.4 と要件 17.6 の選択肢 1。ユーザーが決定した: そのような値を Dr. Kiro の言葉のメッセージで拒否するベンチのルール）で加えました。既存の要件は番号の振り直しも書き換えもしません。この要件はアダプターに任意の関数を 1 つ、実行に 1 つのゲートを加えます。これは `rules.md` セクション 2 の結果 2（ラボのルールによる拒否）であり、`rules.md` のルールは何も変わりません。

**ユーザーストーリー:** アプリケーションのビルダーとして、アダプターが、アプリケーションが実行できない計算済み入力を、実験の試行が 1 つも走る前に拒否できるようにしたい。実験の途中でセッションが止まる代わりに、Dr. Kiro が何を変えるべきかを費用なしで伝えられるようにするためである。body-lab とフェイクアプリケーションのビルダーとして、そのような関数を与えないアダプターでは何も変わらないようにしたい。

**対象:** ビルダーとアダプターの作者。Dr. Kiro が見るのは拒否メッセージだけです。

#### 受け入れ基準

1. THE adapter contract SHALL let an adapter provide an optional function `check_inputs` that takes the computed inputs of one trial and returns either nothing or one refusal message。これはその入力だけの純粋関数である: 同じ入力には同じ答えを返し、アプリケーションを実行しない。An adapter without it SHALL refuse nothing。
2. WHEN an experiment has passed the gates up to and including the budget check（要件 7.5）、THE bench SHALL call `check_inputs` for the computed inputs of every trial of the experiment, in trial order (all variants of a compare, all points of a sweep), BEFORE any trial runs。
3. WHEN `check_inputs` returns a message for any trial、THE bench SHALL refuse the whole experiment with that message, naming the number of the first such trial within the experiment, and SHALL stop calling it。THE refusal SHALL run no trial, record no experiment or trial, use no budget, and change nothing but its own refusal entry（要件 9.2）。THE bench SHALL also write the refusal and the trial number to the builder-side log。
4. THE bench SHALL check the message: it is text, not empty, has no line break or other control character, has no space at its start or end, and has at most 400 characters。IF the message breaks one of these、THEN THE bench SHALL treat it as a bench failure（要件 2.6）。
5. IF `check_inputs` raises、THEN THE bench SHALL treat it as a bench failure with the bench's fixed text for an error in the application, and SHALL write the traceback to the builder-side log only。THE bench SHALL NOT go on to run the trials, and SHALL NOT substitute an answer。
6. THE refusal message SHALL be bench output: THE bench SHALL scan it at the builder level before it returns it（要件 15.8）。したがって、パス、識別子、バージョン、導出された用語を含むメッセージはベンチ障害であり、その内容は Dr. Kiro に何も示されない。アダプターの作者は、メッセージを Dr. Kiro の言葉（ノブ、範囲、実験ファイル、予算）で書く。
7. THE bench SHALL NOT change the told text, the tool descriptions, the declaration, the record's declaration or any existing refusal for an adapter that gives no `check_inputs`。これは body-lab とフェイクアプリケーションについて成り立ち、要件 18.8 の golden 比較が変更なしで通り続けることで SHALL be shown。
8. THE gate SHALL come after the budget check and before the lab spec files are read for the snapshot（設計 6.1、ステップ 9a）。これにより、先のチェックの順序とその理由は変わらない。
9. THE tests SHALL check, over random experiments and random sets of refused inputs, that: a refusal uses no budget and writes only a refusal entry; a refusal in any planned trial (first, middle or last, compare or sweep) refuses the whole experiment before any trial runs; an adapter without the function refuses nothing; a message that breaks 19.4, and a function that raises, are bench failures; a message with a derived term is a bench failure and is not shown。

### 要件 20: ファイル名のステムと除外リスト（改訂）

**改訂。** 要件 1-19 の実装とテストの後、2026-11-16 のユーザーの決定で加えた（ブラインドスキャンのファイル名の照合の変更。`rules.md` セクション 1 によりユーザーが決める）。既存の要件の番号は変えず、文言も変えない。この要件は、15.1、15.4、15.5 が「ファイル名」と呼ぶものを狭める。

**ユーザーストーリー:** ビルダーとして、Dr. Kiro の文にある単独の `P` や `U` をファイル名として指摘してほしくない。1 文字でセッションの封印が終わらないようにしつつ、ソースファイルを名指すパスやファイル名は、両方のレベルで引き続き見つけたい。

**関係者:** ビルダーとベンチ。Dr. Kiro には、スキャンがすでに返している指摘だけが見える。

#### 受け入れ基準

1. THE blind scan SHALL match the file name of every source file of an application in full, and its stem (the part before the first dot), as file-name findings（要件 15.4、15.5）。
2. THE blind scan SHALL NOT match a stem of one character as a file name。
3. THE blind scan SHALL NOT match a stem of two or more characters as a file name when it is on the stop list（`.kiro/blind-scan/stop-list.txt`）。THE comparison SHALL be the one the stop list has for terms: the stem is compared in token form, so case does not matter。
4. THE blind scan SHALL always match the full name of a file。ドットのない名前には別のステムがない: それはフルの名前であり、1 文字であっても、除外リストにあっても、照合される。
5. THE rules of 20.2-20.4 SHALL apply at both levels（ビルダーレベルと Dr. Kiro レベル）and in the same way。THE stop list SHALL still change only with the user's approval。除外リストにないステム（たとえば `mesh`）は引き続き見つかる。`geometry`、`mesh`、`constants`、`monitors` の選択はユーザーが任せ、2026-11-16 に `geometry`、`constants`、`monitors` を除外リストに入れ、`mesh` は入れなかった（`wind-tunnel` 要件の Decision 46）。
6. THE blind scan SHALL NOT change otherwise: 導出された用語（15.2、15.3）、パス、認証情報、body-lab のスキャンと golden ファイルは変わらない。
7. THE tests SHALL check, over random file names and random stop lists, at both levels, that: a one-character stem is not found; a stop-listed stem is not found in any case; a stem that is not stop-listed is found; the full name is always found; a name without a dot is found even when it is one character or is stop-listed。

#### 決定（ユーザーが承認、2026-11-16）

**ファイル名のステムと除外リスト。** ファイル名のパターン（`bench/src/bench/scan/patterns.py` の `Patterns`）は、各ソースファイルのフルの名前とそのステム（最初のドットの前の部分）を照合する。1 文字のステムはファイル名として照合しない: 情報を持たないためである（`p.in` と `U.in` のステムである `P` と `U` が、Dr. Kiro レベルのメモを通じてセッションの封印を終わらせうることが、最初に分かった）。2 文字以上のステムは、レビュー済みの除外リストにあれば照合しない。比較は、除外リストが用語に対して行う比較と同じく、大文字小文字を区別しない。ファイルのフルの名前は常に照合する。除外リストは、引き続きユーザーの承認があるときだけ変える。両方のレベルに両方の規則が適用される。body-lab のスキャンと golden ファイルは変わらない。理由: Dr. Kiro の文にある単独の `P` や `U` はファイル名として指摘され、除外リストはファイル名のパターンに適用されなかったので、それを取り除けなかった。

### 要件 21: discovered spec 表のない終了（改訂）

**改訂。** `build-from-spec` spec（その要件 12）のために加え、そのタスク 1 として実装しました。既存の要件は番号も文言も変えません。要件 11.1 と 12 は、新しい設定が表を必須と示す間、変更なしで適用されます。この要件が加えるのは、セッション設定の 1 つの設定、`end` の 1 つの分岐、`end_session` のツールの説明の 1 文です。

**ユーザーストーリー:** 読み手のビルダーとして、セッションが `## Discovered spec` の表なしで普通に終われるようにしたい。読み手が行を作り出すよう急かされず、普通の終了が停止と読まれないようにするためです。Dr. Kiro のビルダーとして、表がすべての Dr. Kiro のセッションで必須のままであるようにしたい。Dr. Kiro 自身の終了が何も変わらないようにするためです。

**関係者:** ビルダーと読み手。Dr. Kiro が見るのは `end_session` の説明だけで、それも表が必須でないと宣言したセッションに限られます。

#### 受け入れ基準

1. THE セッション設定 SHALL 必須の設定 `discovered_table` を 1 つ持つ。既定値はなく、その値は `"required"` または `"not-required"` のいずれかである。
2. WHILE 設定が `"required"` のとき、THE `end` 操作 SHALL 要件 11.1 と 12 を変更なしで適用する。
3. WHILE 設定が `"not-required"` のとき、THE `end` 操作 SHALL `## Discovered spec` の表を検査せず、判定のない実験があれば拒否し（要件 8）、3 つの仕様ファイルの最後のスナップショットを 1 回の読み込みから取り（要件 10）、セッションを `ended` として封印する。
4. 既存のすべてのセッション設定、そして `bench-new-session` が Dr. Kiro のために書くすべての設定は、`"required"` と書かれていなければならない。
5. この変更は小さいままとする: 設定、開始時の検査、開始エントリーでの値、`end` の 1 つの分岐、`end_session` の説明の 1 文（基準 9）、そして設定を述べるテストとドキュメント。
6. IF 設定がない、または許される 2 つの値以外の値である、THEN THE bench SHALL 設定の名前を示して起動を拒否する。
7. THE bench SHALL 設定の値を封印済み記録の開始エントリーに記録する。
8. この改訂の前に封印された記録（開始エントリーに `discovered_table` がないもの）は、`bench-verify` と `final_spec` にとって有効なままでなければならない（要件 10.4 と 13）。
9. WHILE 設定が `"not-required"` のとき、`bench-mcp` が組み立てる `end_session` のツールの説明は、終了には `## Discovered spec` の表が必要だと述べる文を取り除き、それ以外は変えない。WHILE 設定が `"required"` のとき、説明は変えない。THE 説明は宣言とこの設定だけに依存し、1 つの要求の 3 つの設定でバイト単位で同一になる。

### 要件 22: bench-check-discovered が飛ばす実行記録（改訂）

**改訂。** `build-from-spec` spec（その要件 13.7）のために加え、そのタスク 2 として実装しました。同 spec が求める 2 件の改訂のうちの 2 件目です。もう 1 件は要件 21 です。既存の要件は番号も文言も変えません。この要件が変えるのは要件 13 のうち `bench-check-discovered` の写しの検査だけです。

**ユーザーストーリー:** ビルダーとして、読み手の実行記録が `sessions/build-from-spec/` に生じたあとも、リポジトリで `bench-check-discovered` が通るようにしたい。実行記録が Dr. Kiro のセッション記録として扱われないようにするためです。

**関係者:** ビルダー。Dr. Kiro にはこの検査は見えません。

#### 受け入れ基準

1. THE `check_copies` 検査（`bench-check-discovered`）SHALL フォルダー `sessions/build-from-spec/` を飛ばす。そのフォルダーの中身は読み手の実行記録であり、Dr. Kiro のセッション記録ではないからである。そのような記録には `discovered/` に写しを作らない。
2. WHEN フォルダー `sessions/build-from-spec/` が存在するとき、THE 検査 SHALL 報告の行を 1 つ加える: `build-from-spec: reader run records, no copies`。飛ばしたことが見え、黙っていないようにするためである。
3. 検査の他の部分は何も変わらない: 他のどのアプリケーションのフォルダーでも `log.jsonl` のないフォルダーは引き続き失敗し、フォルダー `discovered/build-from-spec/` は、その名前の封印済みセッション記録がないものとして引き続き報告される。
4. 実行記録は、`bench-verify`、`sessions/` のブラインドスキャン、そして `build-from-spec` の実行記録の検査によって、引き続き対象となる。
5. この変更は小さいままとし、独自のテストを持つ。

#### 決定（ビルダーが、`build-from-spec` の決定に基づいて行った）

**改訂が 2 件、番号は 2 つ。** `build-from-spec` の要件 12 と要件 13.7 は、`lab-bench` への別々の 2 件の改訂なので、次の空いている 2 つの番号 21 と 22 を取る（この改訂の前の最後の番号は 20）。詳細は設計のセクション D1 と D2 にある。
