> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/dr-kiro/tasks.md`](../../../.kiro/specs/dr-kiro/tasks.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `7a11f5e04f6eb42fd7ea819934171aae7420b2d7b47a550cf2818ca87e4382f7`

# タスク: dr-kiro

要件 1〜8（設計セクション 1〜9）のタスクです。各タスクは `sh bench/scripts/check.sh` が通る（テスト、ruff check、ruff format）ことで終わります。検証は要件 7 の最低限にとどめ、設計セクション 9 の 4 つ以外のテストは作りません。

- **1. ビルダーのファイルとテンプレート** — 完了
  - `bench/src/bench/drkiro/files/` を書く: `dr-kiro.json`（設計 3）、`dr-kiro-prompt.md`（設計 4）、`inclusion: always` のフロントマターと、空欄付きのフェンス内の例を持つ `method.md` と `workflow.md`（設計 5）、そして 3 つのテンプレート（設計 6）。英語で書き、パス、部位の名前、実行から得た数字を含めない。
  - これらのファイルをパッケージデータに含める。
  - テスト: フェンス内の各例について、空欄をフェイクの宣言に合うテスト値で置き換えたものが、`parse_hypothesis`、`prepare`/`compute`、`parse_table` に受け付けられること。エージェントのファイルが、`lab-bench` 設計 F10 に設計 3 のフィールドを足したものと一致すること。
  - _要件: 1.1, 1.2, 2, 3, 4, 7.2_

- **2. `bench-make-lab`** — 完了
  - `lab.py` とコンソールスクリプト（設計 7.1）: ビルダーのファイルをコピーし、`bench-lab-hooks` のインストーラーを実行し、`experiments/` を作り、ラボの `.gitignore` を書く。上書きするのはビルダーのファイルだけで、Dr. Kiro のファイルには決して触れない。
  - テスト: `bench-make-lab` で作ったラボが、フェイクアプリケーションに対する `bench-scan` を通ること。
  - _要件: 1.3, 5.1, 5.4, 7.1_

- **3. `bench-new-session`** — 完了
  - `session.py` とコンソールスクリプト（設計 7.2）: 手順 1〜7 をこの順に行う。引数はすべて必須で、確認に失敗したときは手順 4 より前に何も変更しない。
  - テスト: 状態フォルダーに封印されていないセッションがある間は拒否すること。実行後、ラボにはビルダーのファイルとテンプレートだけがあり、セッションは開いていて、設定ファイルに `resume = true` があること。
  - _要件: 5.2, 5.3, 7.3_

- **4. Dr. Kiro の実行** — 完了
  - `bench/README.md` に「Running Dr. Kiro」の節を加える（設計 8）: コマンド、開始の一文と再開の一文、対話ありとヘッドレスの実行、タスク 5 のフェイクセッションの手順。
  - _要件: 6_

- **5. 最初の `body-lab` セッションで Dr. Kiro を確認する（後回し）** — 完了
  - ユーザーの判断で後回しにした: フェイクセッションは別に行わない。Kiro CLI での最初の `body-lab` セッションで同じ点を確認し、`body-lab` のタスクからこのタスクを参照する。
  - 合格: 記録が `ended` の封印で終わること。封印済みフォルダーに対する `bench-scan` が何も報告しないこと。`method.md` と `workflow.md` 以外のステアリングが Dr. Kiro の文脈に現れないこと（設計 11）。必要だった再開の一文の回数を記録する。
  - 失敗した場合は `bench-stop` でセッションを停止し、修正後に新しいセッションを始める。ここではそれ以外を評価しない。失敗は報告し、回避しない（`rules.md` 2）。
  - フェイクセッションの手順は、ビルダーのファイルを変えた後の簡単な確認用として `bench/README.md` に残す。
  - 最初の実行の結果（body-1、macOS、2026-11-13）: 再開の一文なしで、予算の残り 0 で `ended` として封印された。`bench-verify` は 117 件を検証した。ラボと封印済みフォルダーに対する `bench-scan` は、フックを `python -B` で起動するよう変えた後に、検出なしと報告した（ラボ内の `.pyc` がスキャンを止めていた）。Dr. Kiro が挙げたステアリングは `method` と `workflow` だけだった。
  - _要件: 7.4_

- **6. 最終仕様の写し** — 完了
  - `bench/src/bench/record/spec_copy.py` と、コンソールスクリプト `bench-export-spec` と `bench-check-discovered`（設計 7.3）。`bench-make-lab` はラボの `.gitignore` を `.kiro/specs/` なしで書く。2 つのラボの `.gitignore` もそれに合わせ、ラボは `.kiro/specs/lab/` の 3 つのテンプレートを追跡する。
  - ブラインドスキャン: `source.json` のあるフォルダーは写しであり、ラボの中のテンプレートはビルダーの文章である（`lab-bench` 15.10、15.11、タスク 35）。
  - 作者サイドカー付きの `discovered/README.md` と、`bench-export-spec` で書いた `wt-004` の写し。
  - `bench/README.md`、`body-lab/README.md`、`wind-tunnel/README.md`: セッションが終わった後の 2 つのコマンド。
  - テスト: `bench/tests/unit/test_spec_copy.py`、および `body-lab` と `wind-tunnel` のアダプターの `tests/test_templates.py`。
  - _要件: 5.4, 7.5, 8_
- **7. 全体の確認、スキャン、リハーサル** — 完了
  - `sh bench/scripts/check.sh`。`body-lab` のアダプターのテストと、`wind-tunnel` のモデルとアダプターのテスト、ruff。封印済みのすべてのフォルダーに対する `bench-verify`。`bench-check-discovered sessions discovered`。両方のラボ、`sessions/`、`discovered/` に対する `bench-scan`。本物の Docker での `wind-tunnel/rehearse_session.py`（そのセッションの写しを書き、確認し、スキャンするようになった）。
  - _要件: 7.5, 8_
