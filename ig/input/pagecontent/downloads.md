# 下載與驗證

{% include disclaimer.md %}

建置後可從網站下載本 IG 的 FHIR package，或使用套件識別碼載入驗證工具。

本草案預定 package ID：`io.github.ericeric777777.qbc#0.1.0`。

> 對外發布前必須把範例 package ID 與 canonical URL 換成發布者實際控制的值。

## 驗證要求

驗證時應同時載入：

1. `hl7.fhir.r4.core#4.0.1`
2. `tw.gov.mohw.twcore#1.0.0`
3. 本 QBC IG package

公開 release 的 `qa.html` 必須為 0 errors、0 broken links。Warnings 必須修正，或在 release notes 中記錄其原因與影響。QBC 業務規則、Big5 XML 與 VPN 驗收屬於 package 之外的獨立驗證層。

## Dependency 與智慧財產資訊

{% include dependency-table.xhtml %}

{% include ip-statements.xhtml %}

## 版本與全域設定分析

{% include cross-version-analysis.xhtml %}

{% include globals-table.xhtml %}
