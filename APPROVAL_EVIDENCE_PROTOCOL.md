# 發布核准證據規範

本規範適用於 RC-07 與 RC-08 的人工核准。姓名、日期、路徑文字及 64 碼字串只能表示一項宣告；除非稽核能讀取該證據並重算出相同 SHA-256，否則不得計為已核准。

## 必要條件

每筆 `approved / approve` 決定必須同時符合：

1. `evidence_uri_path`（QBC 清冊為 `Evidence URI/path`）必須位於 `mappings/publication/evidence/` 下；不可使用 URL、其他目錄、絕對路徑或 `..`。
2. 檔案實際存在、可由 Git 保存、會被 publication privacy scan 檢查，且可隨 Publisher evidence 追溯。
3. 稽核以原始 bytes 重算 SHA-256，結果必須等於清冊值；只檢查 64 碼格式不算通過。
4. 檔案變更後，原核准立即失效，必須由具權責者重新審查及簽署。
5. 證據不得用來覆蓋仍存在的 CQL、FHIR、來源資料或規格矛盾；所有技術與資料 gate 仍須獨立通過。

## 各類核准的額外要求

- QBC 與作業核准：保留經去識別化的決議或簽署包，並使 hash 與清冊一致。
- 20 個 Measure：證據 bundle 必須精確綁定當次 Measure FSH、CQL、生成 Measure JSON、catalog row、該 Measure 與共用 population criteria、measure audit row 及 approval context；每個 criterion 至少要有 true/false 各一個 truth assertion，20 個 Measure 合計最低 208 筆，且所有已知問題均須有非空 resolution 與 evidence。詳細格式見 [`MEASURE_SPECIFICATION_APPROVAL_PROTOCOL.md`](MEASURE_SPECIFICATION_APPROVAL_PROTOCOL.md)。
- 48 個 StructureDefinition：這是唯一的目錄例外；`evidence_uri_path` 必須直接指向當次 SUSHI／手寫來源聯集中的實際 `StructureDefinition-*.json`，hash 必須等於該 JSON。CI 會把這些生成 JSON 另外上傳為 Publisher evidence。這確保審查不會在 artifact 變更後仍被沿用。
- 15 個 criterion resolution：證據檔 hash 必須相符，而且 live crosscheck 必須已變成 aligned、publication disposition 必須允許 production；簽名不能覆蓋未解矛盾。
- 10 個 scope decision：簽署證據檔 hash 必須相符，approved role 必須等於鎖定的 proposed role，normative scope 仍須具備 formal-release-ready 證據。

目前所有相關正式核准仍為 pending；新增規範不會把缺少的人工作業自動視為完成。
