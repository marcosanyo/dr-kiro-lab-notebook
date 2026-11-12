---
inclusion: fileMatch
fileMatchPattern: "docs/ja/**"
---

# Japanese reference translations of the specs

Policy (set by the user): every spec in `.kiro/specs/<spec>/` has a Japanese reference translation for the user in
`docs/ja/<spec>/` (`requirements.md`, `design.md`, `tasks.md`). The English files stay the source of truth. Kiro
reads, executes and ticks only the English files.

## When to update

- Whenever an English spec file changes, update its translation in the same change, and commit both together.
  The hook `.kiro/hooks/ja-translation-sync.json` reminds the agent after each save of a `requirements.md` or
  `design.md`. It leaves out `tasks.md`, so that ticking a task does not fire it.
- Ticking a task does not count as a change: for `tasks.md`, `scripts/ja-check.sh` hashes `- [x]` as `- [ ]`.
  So the 完了/未着手 marks in the translation may lag behind; they are as of the last translation. Any other change
  to `tasks.md` (new tasks, changed wording) makes the translation stale and needs an update.
- A new spec file gets a new translation.
- `sh scripts/ja-check.sh` lists translations that are missing or out of date, and exits 1 if there are any.
  Run it before committing a spec change, and wherever hooks do not run (for example Kiro Web).

## How to translate

- Update only the parts that changed, keeping the rest of the translation as it is.
- First lines of every translation, exactly:
  ```
  > **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/<spec>/<file>`](../../../.kiro/specs/<spec>/<file>) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
  > 原文 SHA-256: `<sha256 of the English file>`
  ```
  The hash is what `scripts/ja-check.sh` compares; set it to the hash the script computes for the English file
  (for `tasks.md`, with ticks counted as unticked).
- Keep the structure exactly: headings, numbering, order, tables, lists. Do not summarise, add or drop content.
- Copy code blocks byte for byte. Never translate text in backticks, paths, identifiers, ids (H1, E1, P1, R1, T1),
  status and verdict values, condition-class values, requirement numbers, numbers and units, or literal strings
  the bench outputs (for example "a path outside the lab").
- Acceptance criteria keep the EARS keywords in English: `WHEN …、THE bench SHALL …する。`
- Tasks: no Markdown checkboxes. Write `- **N. タイトル** — 完了` or `— 未着手`, so no tool takes the file for a
  task list. `_Requirements: …_` becomes `_要件: …_` with the same numbers.
- One Japanese term per concept: bench=ベンチ, core=コア, front end=フロントエンド, bench action=ベンチ操作,
  adapter=アダプター, knob=ノブ, hypothesis=仮説, structured prediction=構造化予測, prediction outcome=予測結果
  (hit=的中, miss=外れ, not checkable=確認不能, not run=未実行), condition class=条件クラス, frozen part=凍結部分,
  experiment=実験, trial=試行, computed inputs=計算済み入力, verdict=判定, verdict flag=判定フラグ, refusal=拒否,
  bench failure=ベンチ障害, session record=セッション記録, sealed session record=封印済みセッション記録,
  blind scan=ブラインドスキャン, not-measured outcome=未計測結果, builder=ビルダー, phase=フェーズ,
  parameter=パラメーター, budget=予算, snapshot=スナップショット, allow list=許可リスト, stop list=除外リスト,
  step bound=ステップ上限, hash chain=ハッシュチェーン, seal=封印.
- The Honest rule applies: no invented numbers, and no words that suggest human injury or disability for how the
  body moves.
