> **参考訳（日本語）** — 正本は英語版 [`.kiro/specs/body-lab/design.md`](../../../.kiro/specs/body-lab/design.md) です。内容が食い違う場合は英語版が優先されます。Kiro はこのファイルを読みません。
> 原文 SHA-256: `4a80cfdea790a8e8d747716ead4f1160ded672c5af4027c86b467dd58d10eab2`

# 設計: body-lab

Requirements 1-6 を扱います。設定は `body-lab/model/README.md` と配線ファイルから読み込み時に読み取ります。手で写すものは何もありません。

## 1. 構成

```
body-lab/
  model/                         given; read only
  adapter/                       uv project "body-lab-adapter"
    pyproject.toml               depends on lab-bench (path ../../bench) and mujoco
    scan_sources.toml            mjcf + wiring-json sources, lab layout
    src/body_lab/
      adapter.py                 BodyAdapter: declaration, run_trial
      sim.py                     load the model, add the camera, step a trial
      measure.py                 Measurer protocol and PoseMeasurer
      picture.py                 offscreen frames -> one PNG
      settings.py                camera and picture settings
    tests/
  lab/                           made by bench-make-lab (Dr. Kiro's lab)
  README.md                      how it measures, how to run, limits
```

## 2. シミュレーション (Req 1)

- `sim.py` は `specimen_01.xml` を `mujoco.MjSpec` で読み込み、コードでカメラを追加し（位置は視野の中心の上、真下を向き、垂直方向の視野角と画像サイズは `settings.py` から）、コンパイルします。モデルファイルは変更しません。
- 開始姿勢: ボディのフリージョイントを、x 方向に沿って視野の中心から 0.45 m 後ろに置き、+x を向けます（`body-lab/model/README.md`）。
- 静置: すべてのコマンドを 0 にして配線の静置時間だけ置き、その後 t = 0 で試行を始めます。
- 制御: 各制御ステップ k で、チャンネル i のコマンドはノブ `c<i>` のサンプル k です。配線がそれを符号とともにアクチュエーターの制御範囲に対応づけます。各サーボの目標値は、そのコマンドに向けて最大 600°/s × 制御ステップだけ動きます。制御ステップの間は、シミュレーターはモデル自体のタイムステップで進みます。
- ノブ: 配線のチャンネルに対して `c0` ... `c<n-1>`。サンプル時刻は `k = 0 .. trial_seconds × control_hz − 1` に対して `k / control_hz` です。

## 3. 計測器 (Req 2)

```python
class Measurer(Protocol):
    def measurements(self) -> tuple[Measurement, ...]: ...      # fixed names, units, not-measured outcomes
    def measured_by(self) -> str: ...                           # text for the declaration
    def measure(self, track: Track) -> Mapping[str, float | tuple[float, ...] | NotMeasured]: ...
```

`Track` は、開始時、0.1 s ごと、終了時における追跡点のワールド座標での姿勢（位置と向き）を保持します。今ある計測器は `PoseMeasurer` だけです:

- 相対姿勢: 位置から開始位置を引き、開始時の向きの符号を反転した角度だけ回転したものです。向きは、追跡されるフレームの前方軸を床に射影した角度から開始時の向きを引き、(-180, 180] に折り返したものです。
- 見える: 追跡点がカメラの画像平面の手前にあり、画像の内側に射影され、その外向き法線がカメラの方を向いている（法線とカメラへの方向の内積 > 0）ことです。しきい値はありません。
- そのサンプルで見えないときは `lost` です。スカラーは終了時のサンプルがそうであれば `lost`、系列はいずれか 1 つのサンプルでもそうであれば `lost` です。理由は、どの条件が満たされなかったかを示します（"the tracked point faced away from the camera"、"the tracked point left the camera's view"）。
- `measured_by` のテキスト: "Computed from the simulator's pose, as the quantities a camera straight above could measure; not measured from a camera image. The camera sees a floor area of <w> m by <h> m; at the start the body is at x = 0, y = 0, and the view spans x from <x0> to <x1> m and y from <y0> to <y1> m. MuJoCo <version>." 数値は設定からコードで計算します: 高さの半分 = 高さ × tan(fov / 2)、幅の半分 = 高さの半分 × 画像の幅 / 画像の高さ。README の設定では、およそ 2.59 m × 1.46 m です。

後のマーカーを読み取る計測器は、レンダリングしたフレームから同じプロトコルを実装し、同じ名前と同じ `lost` の意味を持ちます。今は作りません。

## 4. 画像 (Req 4)

- 追加したカメラで `mujoco.Renderer` をオフスクリーンで使います。`MUJOCO_GL` はアダプターでは設定しません（macOS では既定のもの、Linux ではビルダーが `egl` か `osmesa` を設定します）。
- フレームは t = 0.5, 1.0, ..., 5.0 s（`settings.py`: フレーム数 10、間隔 0.5 s）で、それぞれ 320 × 180 に縮小し、2 行 5 列に並べ、`bench.pictures.encode_png` でエンコードします（メタデータなし）。

## 5. 宣言 (Req 1-5)

- ノブはセクション 2 のとおりです。計測項目は `x`、`y`、`heading`（スカラー、`lost`）と `track_x`、`track_y`、`track_heading`（系列、`lost`）です。画像は `image/png`、予算は 40、`fake = False` です。
- `goal`: "Move the body as far as possible in the direction it faces at the start: maximise x."
- `measured_by`: 計測器から（セクション 3）。

## 6. この仕様でのベンチの変更

`lab-bench` 2.1 に 2 つの宣言フィールド `goal` と `measured_by` が加わります（承認済み）。`check_declaration` は両方を空でないテキストとして必須にします。フェイクアプリケーションには独自のものを与えます。`describe.py` はそれらをツールの説明に加えます。`dr-kiro` のワークフローは、最初の 3 つのフェーズですべての計測項目を調べるよう述べます（`dr-kiro` 3.3）。

## 7. テスト (Req 6)

| テスト | Req |
|---|---|
| すべての入力が 0 の試行が、`check_result` と `check_picture` を通る結果を与える。 | 2, 4 |
| 同じ入力を 2 回与えると、計測値と画像のバイト列が等しい。 | 5.2 |
| ボディがひっくり返っている試行（開始姿勢を x 軸まわりに半回転したもの）は、すべての計測項目で `lost` を与える。 | 2.3 |
| 宣言にチャンネルの詳細がなく、ボディのソースを使った `bench-scan` を通る。 | 1.2, 5.3 |

## 8. セッションの実行

`body-lab/README.md`: ベンチと並べて `uv tool install --editable './body-lab/adapter'`、`bench-make-lab
body-lab/lab`、`--adapter body_lab.adapter:BodyAdapter` とボディのスキャンソースを付けた `bench-new-session`、その後 `bench/README.md` の「Running Dr. Kiro」の手順です。セッションの後: `bench-verify`、ラボと封印済みフォルダーに対する `bench-scan`、dr-kiro のタスク 5 の確認です。

## 9. 止めて確認すること

- MuJoCo がサンドボックスまたは Mac でオフスクリーンレンダリングできない。
- モデルファイルを編集せずに追跡点の代わりになるボディやサイトがモデルにない。
- モデルのアクチュエーターを変えずにサーボの速度制限を適用できない。

## 決定事項

1. 目標: `x` を最大化する。`goal` として宣言する（ユーザー）。
2. 計測値はシミュレーターの姿勢から計算し、交換可能な計測器の背後に置く。今はマーカーの読み取りはしない（ユーザー）。
3. 系列は 0.1 s ごと（ユーザー）。
4. 画像: 0.5 s ごとの 10 フレームからなる 1 つの PNG（ユーザー。最初のセッションの後に変わることがある）。
5. 配線から 5 つのチャンネル、[-1, 1]、50 Hz、5 s。静置は宣言しない（ユーザー）。
6. `body-lab/adapter/` は独立した uv プロジェクト（ユーザー）。
7. マシン間の違いは書面上の制限とし、MuJoCo のバージョンを記録する（ユーザー）。
8. 最低限の検証: 4 つのテストと 40 試行のセッション 1 回（ユーザー）。
