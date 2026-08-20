# -*- coding: utf-8 -*-
"""癌症登記申報 task：與 QBC 申報平級的第二個提交目標。

- `ig_export`        產生本 IG 的癌登 FHIR 資源（CodeSystem/ValueSet/
                     Questionnaire/Task）與 `data/tcr_fields.json`；未審術語
                     對應留在非 FHIR 的逐碼 backlog
- `resolution_rules` 乳癌 SSF1-10 的碼冊摘錄原則（哪份報告該採用、為什麼）
- `demo_er`          端到端示範：多份互相矛盾的 ER 報告 -> 兩份申報值

代碼表本身不在這裡：那是 `tcr-decoder` 套件的職責（14 個癌別、20,172 個
代碼、逐碼雙向驗證）。本模組只做「乳癌 IG 要怎麼用它」。
"""

from tcr_workbench.resolution_rules import BREAST_RULES, rule_for  # noqa: F401
