## Task 03: jupyter の compose 基盤統合

### 目的
- `jupyter` を `run` と同じ compose 実行基盤に寄せて実装重複を削減する。

### 作業
- `jupyter` の docker 実行部を compose 実行へ置換
- `run` 側の共通化可能ロジックを抽出
- URL/token 表示とポートフォワード処理を維持

### 完了条件
- `jupyter` が compose 経由で起動
- 既存同等の接続案内を表示
