# -*- coding: utf-8 -*-
"""Worked example: one set of ER observations -> two submissions.

Run it:

    python -m tcr_workbench.demo_er

Shows the whole point of the fact layer in one screen: several documents
disagree about ER, the code book's own rule picks one and says why the others
were rejected, and TWO encoders read that same decision to produce the TCR
code (SSF1) and the QBC codes (D014/D015). Neither submission is derived from
the other.
"""

from __future__ import annotations

import pandas as pd

from tcr_decoder.encoders import encode_er_pr
from tcr_decoder.facts import (
    DOC_PATHOLOGY, DOC_PRIOR_SUBMISSION, Evidence, HOSPITAL_EXTERNAL,
    Observation, PROCEDURE_BIOPSY, PROCEDURE_RESECTION, Resolution,
    SITE_METASTATIC, SITE_PRIMARY, SPECIMEN_IN_SITU, SPECIMEN_INVASIVE,
    TIMING_POST_NEOADJUVANT, TIMING_PRE,
)
from tcr_workbench.resolution_rules import rule_for


# ─────────────────────────────────────────────────────────────────────────────
# Encoders: both read the SAME Resolution. This is the hub-and-spoke shape --
# no QBC -> TCR conversion exists anywhere.
# ─────────────────────────────────────────────────────────────────────────────

_INTENSITY_LETTER = {'strong': 'S', 'intermediate': 'I', 'moderate': 'I',
                     'weak': 'W'}


def to_tcr_ssf1(resolution: Resolution) -> str:
    """Resolution -> TCR SSF1 code (3 characters, verified against the range)."""
    if resolution.forced_code:
        return resolution.forced_code
    observation = resolution.chosen
    if observation is None:
        return '999'
    percent = observation.value
    if not isinstance(percent, (int, float)):
        return '999'
    intensity = _INTENSITY_LETTER.get(
        str(observation.qualifiers.get('intensity', '')).lower())
    if intensity:
        # 強度 + 2 碼比例，100% 寫成 '00'（碼冊 p.121）
        return f'{intensity}{int(percent) % 100:02d}'
    if percent == 0:
        return '000'
    return f'{int(percent):03d}'


def to_qbc_d014_d015(resolution: Resolution) -> dict:
    """Resolution -> QBC D014 (X/0/1) + D015 (1-100)。

    QBC 沒有「染色強度」這個欄位，所以強度資訊在這裡被丟掉 —— 這是**降維**，
    不是資訊損失，因為它從來就不是從 TCR 碼推回來的。
    """
    if resolution.forced_code in ('121',):
        return {'D014': '0', 'D015': None}
    if resolution.forced_code in ('111', '888'):
        return {'D014': '1', 'D015': None}
    observation = resolution.chosen
    if observation is None:
        return {'D014': 'X', 'D015': None}
    percent = observation.value
    if not isinstance(percent, (int, float)):
        return {'D014': 'X', 'D015': None}
    if percent < 1:
        return {'D014': '0', 'D015': None}
    return {'D014': '1', 'D015': f'{int(percent):02d}'}


# ─────────────────────────────────────────────────────────────────────────────
# The scenario
# ─────────────────────────────────────────────────────────────────────────────

def sample_observations() -> list:
    """Five documents describing ER for one patient. They disagree."""
    return [
        Observation(
            concept='er', value=70, qualifiers={'intensity': 'strong',
                                                'representation': 'proportion'},
            specimen=SPECIMEN_INVASIVE, site=SITE_PRIMARY, timing=TIMING_PRE,
            procedure=PROCEDURE_RESECTION, specimen_volume_mm=22.0,
            tumor_id='T1', doc_type=DOC_PATHOLOGY, method='ai_extraction',
            confidence=0.94,
            evidence=[Evidence('DiagnosticReport/path-2026-1234', DOC_PATHOLOGY,
                               text='ER: 70% of tumor cells, strong intensity',
                               span=(1420, 1468), page=3)]),
        Observation(
            concept='er', value=30, qualifiers={'representation': 'proportion'},
            specimen=SPECIMEN_INVASIVE, site=SITE_METASTATIC, timing=TIMING_PRE,
            procedure=PROCEDURE_BIOPSY, tumor_id='LN1',
            doc_type=DOC_PATHOLOGY, confidence=0.9,
            evidence=[Evidence('DiagnosticReport/path-2026-1301', DOC_PATHOLOGY,
                               text='Axillary node metastasis, ER 30%')]),
        Observation(
            concept='er', value=15, qualifiers={'representation': 'proportion'},
            specimen=SPECIMEN_IN_SITU, site=SITE_PRIMARY, timing=TIMING_PRE,
            procedure=PROCEDURE_RESECTION, specimen_volume_mm=22.0,
            tumor_id='T1', doc_type=DOC_PATHOLOGY, confidence=0.88,
            evidence=[Evidence('DiagnosticReport/path-2026-1234', DOC_PATHOLOGY,
                               text='DCIS component: ER 15%')]),
        Observation(
            concept='er', value=8, qualifiers={'representation': 'proportion'},
            specimen=SPECIMEN_INVASIVE, site=SITE_PRIMARY, timing=TIMING_PRE,
            procedure=PROCEDURE_BIOPSY, specimen_volume_mm=4.0, tumor_id='T1',
            doc_type=DOC_PATHOLOGY, hospital=HOSPITAL_EXTERNAL, confidence=0.7,
            evidence=[Evidence('DocumentReference/referral-note', DOC_PATHOLOGY,
                               text='外院 core biopsy: ER 8%',
                               hospital=HOSPITAL_EXTERNAL)]),
        Observation(
            concept='er', value=70, qualifiers={'representation': 'proportion'},
            timing=TIMING_PRE, doc_type=DOC_PRIOR_SUBMISSION, confidence=1.0,
            evidence=[Evidence('QBC/2026-001', DOC_PRIOR_SUBMISSION,
                               text='既有 QBC 申報：D014=1, D015=70')]),
    ]


def run(observations=None) -> dict:
    observations = observations or sample_observations()
    resolution = rule_for('SSF1').resolve(observations)
    ssf1 = to_tcr_ssf1(resolution)
    qbc = to_qbc_d014_d015(resolution)
    # The TCR code goes back through the verified decoder as a self-check.
    from tcr_decoder.decoders import decode_er_pr
    meaning = decode_er_pr(pd.Series([ssf1]), 'ER').iloc[0]
    return {'resolution': resolution, 'SSF1': ssf1, 'QBC': qbc,
            'SSF1_meaning': meaning}


def main() -> None:
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    observations = sample_observations()
    print('═' * 72)
    print(f'輸入：{len(observations)} 筆 ER 觀察（互相不一致）')
    print('═' * 72)
    for observation in observations:
        print(f'  · {observation.describe()}')

    result = run(observations)
    print()
    print('═' * 72)
    print('碼冊規則解析')
    print('═' * 72)
    print(result['resolution'].explain())

    print()
    print('═' * 72)
    print('兩個申報目標，各自從同一個 Resolution 編碼')
    print('═' * 72)
    print(f"  癌症登記 SSF1 = {result['SSF1']}   ({result['SSF1_meaning']})")
    qbc = result['QBC']
    print(f"  QBC      D014 = {qbc['D014']}     D015 = {qbc['D015']}")
    print()
    print('  注意：QBC 沒有「染色強度」欄位，所以 strong 這個資訊只出現在癌登碼。')
    print('  這正是不能用 QBC → 癌登 轉換的原因：反過來推會得到 070，遺失強度。')


if __name__ == '__main__':
    main()
