# 人工審查與 VPN 驗收

{% include disclaimer.md %}

## 人工審查

`clinical_review_template.csv` 為 115 欄簽核表。每欄至少需要臨床 reviewer 與 QBC／申報 reviewer 填寫姓名、決議、日期與備註。未簽核欄位維持 `pending`，不能被描述為已完成臨床驗證。

建議角色：乳癌臨床專家、QBC／癌登申報人員；病理、生物標記、藥物或放療欄位另由相應專業人員審查。

## VPN 驗收步驟

1. 在完全合成資料上通過 pytest、IG Publisher 與 mock receiver。
2. 以院內去識別測試資料完成雙人核對及 Big5 round-trip。
3. 確認正式 HOSPID、帳號權限、上傳月份與流水號規則。
4. 於健保 VPN 測試環境上傳三種 DIAG_TYPE 的 golden cases。
5. 保存原始 XML SHA-256、上傳時間、官方 receipt／錯誤碼及修正紀錄。
6. 全部測試案例被接受後，由院內權責人核准 release。

本機 mock receiver 只模擬已公開且已機器化的檢查，不冒充官方收件端。
