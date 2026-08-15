# 事實層重構提案：讓「不同來源互相補充」可以自動做

> **對象**：`TW-Breast-Cancer-FHIR-IG` 的 `qbc_workbench`
> **問題**：現行 `candidates: dict[qbc_tag, Candidate]` 一個欄位只能存一個值，
> 多來源在 import 當下就被迫塌縮，不同意見只能標 `CONFLICT`，落選的值消失。
> **提案**：把「觀察」與「答案」分開，答案由**碼冊規則**產生並附理由。
>
> 參考實作：`tcr_decoder/facts.py`、`tcr_decoder/resolution_rules.py`、
> `tcr_decoder/demo_er.py`（29 個測試在 `tests/test_facts.py`）

---

## 一、「互相補充」的三種意思，只有前兩種能自動做

| | 情況 | 自動？ |
|---|---|---|
| ① 填補缺漏 | A 沒有、B 有 | ✅ 碼冊本身就規定來源優先序 |
| ② 提高精度 | A「ER 陽性」、B「ER 70% 強染」，B ⊃ A | ✅ 無矛盾 |
| ③ 衝突仲裁 | A 70%、B 30% | ❌ 碼冊有規則就照規則並記理由；沒規則就人工 |

## 二、合併規則是「每個欄位一套」，不是全域一套

這是最容易做錯的地方。同樣兩份文件，對不同欄位的優先序可能相反：

| 欄位 | 碼冊規則 | 形狀 |
|---|---|---|
| 乳癌 SSF1 ER | 多顆腫瘤取**反應比例**最高 | 取極值（值） |
| 乳癌 SSF6 Nottingham | 多顆腫瘤取 **BR 分數**最高 | 取極值（分數） |
| 乳癌 SSF9 LVI | **任一份**原發部位病理報告有 LVI 即 010 | 布林 OR |
| 乳癌 SSF3 療效 | 除 pCR 外，**臨床醫師綜合判斷**優於病理報告 | 來源優先序反轉 |
| 頭頸 SSF1 淋巴結大小 | 同區域：病理 > 手術 > 影像；**不同區域取最大徑** | 條件式切換 |
| 區域淋巴結侵犯數 | 同一 chain **不可加總**，不同 chain **可加總** | 分組後聚合 |

所以不能寫一個通用 merge。`resolution_rules.py` 把這些規則寫成**資料**，每條附碼冊頁碼。

## 三、時間不是「來源」

治療前與治療後的 ER 是**兩個事實**，不是同一事實的兩個來源。癌登有專屬代碼：

- `111` / `121`：僅有前導性治療後的數值（陽性／陰性）
- `888`：治療前陰性、治療後轉陽性

若在事實層合併成「這個病人的 ER」，這三個碼就永遠編不出來。

## 四、資料模型的具體改動

### 現況

```python
class Candidate(BaseModel):
    qbc_tag: str            # ← key 是 QBC 欄位，事實層與 QBC 編碼綁死
    value: str | None
    method: Method
    status: ReviewStatus    # ← 有兩個值只能標 CONFLICT，輸的那個消失
    confidence: float
    evidence: list[Evidence]

class CaseRecord(BaseModel):
    candidates: dict[str, Candidate]    # 一個 tag 一個值
```

### 建議

```python
class Observation(BaseModel):
    """一次觀察 ≠ 一個答案。同一個 concept 可以有很多筆。"""
    concept: str                 # 'er_proportion'（臨床概念，不是欄位碼）
    value: str | float
    qualifiers: dict             # {'intensity': 'strong', 'representation': 'proportion'}
    specimen: str | None         # invasive / in_situ
    site: str | None             # primary / metastatic
    timing: str                  # pre_treatment / post_neoadjuvant
    procedure: str | None        # resection / biopsy
    specimen_volume_mm: float | None
    tumor_id: str | None
    doc_type: str                # pathology / operative / imaging /
                                 # physician_statement / prior_submission
    reporting_hospital: str      # reporting / external
    method: Method               # 沿用既有 enum
    confidence: float
    evidence: list[Evidence]     # 沿用既有型別

class Resolution(BaseModel):
    """某個申報欄位選了誰、依哪條規則、為什麼別人落選。"""
    field: str                   # 'D014' 或 'SSF1'
    chosen: Observation | None
    forced_code: str | None      # 規則直接指定代碼（888/988/111/121…）
    rule_id: str                 # 對應碼冊條文
    trace: list[str]             # 套用了哪幾條規則
    rejected: list[tuple[Observation, str]]   # 落選者＋理由
    status: ReviewStatus         # 沿用既有 enum
    review_reason: str | None

class CaseRecord(BaseModel):
    observations: list[Observation]              # 新增：所有原始觀察
    resolutions: dict[str, Resolution]           # 新增：每個申報欄位的決定
    candidates: dict[str, Candidate]             # 保留：由 resolutions 產生
```

**遷移策略**：`candidates` 不刪，改成由 `resolutions` 投影出來——

```python
def project_candidates(case: CaseRecord, encoder) -> dict[str, Candidate]:
    """Resolution -> 既有的 Candidate，維持 exporter/web/validation 不動。"""
    out = {}
    for field, resolution in case.resolutions.items():
        out[field] = Candidate(
            qbc_tag=field,
            value=encoder(resolution),
            method=resolution.chosen.method if resolution.chosen else Method.RULE_DERIVED,
            status=resolution.status,
            confidence=resolution.chosen.confidence if resolution.chosen else 1.0,
            evidence=resolution.chosen.evidence if resolution.chosen else [],
            rule_id=resolution.rule_id,
            notes=[*resolution.trace,
                   *(f'排除 {o.value}：{why}' for o, why in resolution.rejected)],
        )
    return out
```

這樣 **exporter.py、web.py、xml_validation.py 完全不用改**，既有 60 個測試也不會破。

## 五、`validation.py` 的 CONFLICT 邏輯要跟著調

現在：只要來源不一致就擋。
之後：**碼冊有規則能判的，自動判並記理由；只有規則判不出來才擋。**

```python
# 之前
if len({c.value for c in candidates_for(tag)}) > 1:
    _issue(issues, tag, 'QBC-SOURCE-CONFLICT', '來源衝突')

# 之後
resolution = case.resolutions[tag]
if resolution.status is ReviewStatus.CONFLICT:
    _issue(issues, tag, 'QBC-SOURCE-CONFLICT',
           f'{resolution.review_reason}（已套用：{"、".join(resolution.trace)}）')
```

實測影響：ER 這個欄位，5 筆互相矛盾的觀察在現行邏輯下會擋下來人工處理；
套規則後 4 筆有明確碼冊理由被排除，直接產出 `S70`，不需要人工。

## 六、對兩個 task 的意義

```
                     Observation[]（抽一次、審一次）
                            │
        ┌───────────────────┴───────────────────┐
   QBC Resolution                        癌登 Resolution
   （QBC 規則）                          （癌登碼冊規則）
        │                                       │
   D014=1, D015=70                         SSF1=S70
```

同一批觀察、兩套規則、兩份申報。**沒有 QBC → 癌登 的轉換**，因為那個方向會捏造
它沒有的精度（QBC 沒有「染色強度」欄位，ER 408 個癌登碼裡有 305 個推不出來）。

## 七、落地順序（可以分批，不必一次到位）

1. **只加不改**：`Observation` / `Resolution` 加進 `models.py`，`CaseRecord` 多兩個
   欄位，`candidates` 照舊。既有測試不動。
2. **一個欄位先走通**：ER（D014/D015 ↔ SSF1）。抽取層產 `Observation`，
   `project_candidates` 產回 `Candidate`，前後端無感。
3. **審核 UI 加一段**：顯示 `trace` 與 `rejected`，讓複核的人看到「為什麼是 70%
   不是 30%」。這一步的價值最高，因為它把人工時間從「重讀報告」變成「確認理由」。
4. **其餘欄位逐步接上**：乳癌 SSF1–10 的規則已在
   `tcr_decoder/resolution_rules.py`，QBC 的 115 欄規則同樣可以照抄碼冊寫成資料。
5. **一致性檢查器**：兩份申報都產生後互相比對（QBC 說陰性、癌登卻是 S70 → 抽取
   有錯）。這是「task 對 task」真正該做的東西，不是互相轉換。
