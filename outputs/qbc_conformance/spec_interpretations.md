# 規格疑義與本草案處理

下列項目不能冒充主管機關正式解釋，須列入 QBC reviewer 簽核：

| 項目 | 原始資料觀察 | 本草案處理 |
|---|---|---|
| 表-1 XML | 部分結束標籤錯置或遺漏 `/` | 以主表欄位與正確 well-formed XML 產生器為準 |
| `TM10` | 原文寫「不可早於 TM08 的日期」，但 TM08 是其他部位文字 | 依欄位語意暫解讀為不得早於 `TM09`，等待 QBC reviewer 確認 |
| `D058–D085` | 主表總則要求 DIAG_TYPE=3 時復發欄位必填，但 D069 等欄另有明確條件 | 採「總則必填、個別條件優先」：D068 必填；D069 只有 D068 包含 13 時必填，否則不得填。D071、D072、D074、D075、D077、D079、D081 同樣依各自條件。 |
| `P02` | 正式主表為 0男性、1女性、2其他、3未知 | FHIR gender 已依主表修正；舊程式的 1/2 對應已移除 |
| mCODE | mCODE 4.0.0 為 US Realm 且依賴 US Core | 只做 gap mapping，不以加入 dependency 冒充 TW Core/mCODE 雙重 conformance |

如果主管機關提供新版規格或正式澄清，應保留舊版 source hash、提高本套件版本並重跑完整 regression test。
