# QBC VPN 驗收清單

## Release candidate

- [ ] 正式 canonical、package ID、publisher 已設定
- [ ] `pytest` 全數通過
- [ ] IG Publisher：0 errors、0 broken links，warnings 已處理
- [ ] 三種 DIAG_TYPE golden cases 均由 mock receiver 接受
- [ ] 115 欄臨床與 QBC reviewer 已完成簽核
- [ ] 院內資安、個資與資料出境審查已通過
- [ ] HOSPID、上傳月份、流水號由正式主檔確認

## VPN 測試環境

| 測試編號 | DIAG_TYPE | XML SHA-256 | 上傳時間 | 官方 receipt／錯誤碼 | 結果 | 操作者 | 覆核者 |
|---|---|---|---|---|---|---|---|
| VPN-001 | 1 |  |  |  | pending |  |  |
| VPN-002 | 2 |  |  |  | pending |  |  |
| VPN-003 | 3 |  |  |  | pending |  |  |

## 異常與修正

每次退件須保留原 XML、SHA-256、官方完整訊息、修正 commit／版本及重送結果。未取得官方 receipt 不得標示 VPN 驗收完成。
