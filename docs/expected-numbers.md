# Expected numbers

What Power BI must show when the model is loaded with the files of `data/`. Every number here was worked out by `src/labtrack_bi/engine.py` (a second, hand-written version of the measures), never typed in, and the tests fail when this file is out of date.

**How to check.** Open `model/check.dax` in the DAX query view of Power BI Desktop, select one query, press Run, and compare the result with the table of the same number below. Numbers are shown with six significant digits; Power BI shows more. Rows may come in another order.

`(blank)` means that the measure is blank for that row: Power BI leaves the cell empty.

## 1. Every measure with no filter

Query 1 of `model/check.dax` (`overall`).

The three measures of time intelligence are left out: they only make sense by year or month (checks by_year, by_month).

| Measure | Value |
|---|---:|
| [Sessions] | 909 |
| [Participants Enrolled] | 200 |
| [Participants Attended] | 199 |
| [Recordings] | 1634 |
| [Trials] | 45806 |
| [Hours Recorded] | 154.502 |
| [Data Volume GB] | 10.5025 |
| [Devices Used] | 11 |
| [Sessions Completed] | 817 |
| [Sessions Cancelled] | 54 |
| [Sessions No Show] | 23 |
| [Sessions Scheduled] | 15 |
| [Sessions Closed] | 894 |
| [Completion Rate] | 0.91387 |
| [No Show Rate] | 0.0257271 |
| [Cancellation Rate] | 0.0604027 |
| [Avg Session Minutes] | 81.8421 |
| [Last Completed Session Date] | 2026-10-29 |
| [Completed Sessions Running Total] | 817 |
| [Participants Attended Running Total] | 199 |
| [Target N] | 231 |
| [Recruitment Progress] | 0.861472 |
| [Participants Withdrawn] | 6 |
| [Withdrawal Rate] | 0.03 |
| [Visit Retention] | (blank) |
| [Recordings Passed QC] | 1423 |
| [QC Pass Rate] | 0.877312 |
| [Uncalibrated Recordings] | 162 |
| [Uncalibrated Rate] | 0.0991432 |
| [Valid Trials] | 42052 |
| [Rejected Trials] | 3754 |
| [Trial Rejection Rate] | 0.0819543 |
| [Avg Trials per Recording] | 28.033 |
| [Mean Force CV] | 4.27909 |
| [Mean Force CV Feedback On] | 4.04247 |
| [Mean Force CV Feedback Off] | 4.52644 |
| [Feedback Effect on Force CV] | -0.483969 |
| [Mean MDF] | 67.8664 |
| [Mean RMS] | 120.33 |
| [Mean Alpha Power] | 24.4263 |
| [MDF Change After Fatigue] | -11.0094 |
| [RMS Change After Fatigue] | 15.2528 |
| [Alpha Change Large vs Small Stimulus] | -3.91764 |

## 2. By study

Query 2 of `model/check.dax` (`by_study`).

Participants Attended adds up to 211 here but is 199 in the check overall: 12 people took part in two studies.

| Study[Study Code] | [Sessions] | [Sessions Completed] | [Participants Attended] | [Target N] | [Recruitment Progress] | [Completion Rate] | [Avg Session Minutes] | [Participants Withdrawn] | [Hours Recorded] | [Recordings] | [Trials] | [QC Pass Rate] | [Trial Rejection Rate] | [Uncalibrated Recordings] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EEG-02 | 291 | 265 | 67 | 81 | 0.82716 | 0.910653 | 80.8491 | 2 | 50.2656 | 530 | 14903 | 0.881132 | 0.0819969 | 25 |
| EMG-03 | 201 | 168 | 46 | 46 | 1 | 0.903226 | 82.875 | 2 | 31.5833 | 336 | 9363 | 0.895062 | 0.0697426 | (blank) |
| FFB-01 | 417 | 384 | 98 | 104 | 0.942308 | 0.920863 | 82.0755 | 2 | 72.6533 | 768 | 21540 | 0.867188 | 0.0872331 | 137 |

## 3. By year (time intelligence)

Query 3 of `model/check.dax` (`by_year`).

2027 is listed with blank sessions only because its previous year (2026) has sessions, so [Sessions YoY] is -1 there. Power BI leaves out a year when every measure is blank: that is why 2023 and 2028 are not here.

| 'Calendar'[Year] | [Sessions] | [Sessions Completed] | [Sessions YTD] | [Sessions Previous Year] | [Sessions YoY] |
|---|---:|---:|---:|---:|---:|
| 2024 | 235 | 216 | 235 | (blank) | (blank) |
| 2025 | 469 | 431 | 469 | 235 | 0.995745 |
| 2026 | 205 | 170 | 205 | 469 | -0.5629 |
| 2027 | (blank) | (blank) | (blank) | 205 | -1 |

## 4. By month (running totals)

Query 4 of `model/check.dax` (`by_month`).

The running totals are blank after the last completed session, so the last two months (2026-11 and 2026-12) show a blank in those two columns. A month in which every measure is blank is not listed.

| 'Calendar'[Year-Month] | [Sessions Completed] | [Completed Sessions Running Total] | [Participants Attended Running Total] | [Sessions YTD] |
|---|---:|---:|---:|---:|
| 2024-03 | 8 | 8 | 5 | 9 |
| 2024-04 | 31 | 39 | 14 | 42 |
| 2024-05 | 26 | 65 | 20 | 71 |
| 2024-06 | 25 | 90 | 28 | 99 |
| 2024-07 | 32 | 122 | 35 | 134 |
| 2024-08 | 18 | 140 | 37 | 153 |
| 2024-09 | 11 | 151 | 41 | 165 |
| 2024-10 | 12 | 163 | 45 | 178 |
| 2024-11 | 21 | 184 | 53 | 201 |
| 2024-12 | 32 | 216 | 59 | 235 |
| 2025-01 | 26 | 242 | 66 | 28 |
| 2025-02 | 25 | 267 | 73 | 55 |
| 2025-03 | 34 | 301 | 79 | 89 |
| 2025-04 | 37 | 338 | 89 | 127 |
| 2025-05 | 33 | 371 | 99 | 165 |
| 2025-06 | 36 | 407 | 108 | 204 |
| 2025-07 | 36 | 443 | 117 | 244 |
| 2025-08 | 34 | 477 | 127 | 284 |
| 2025-09 | 56 | 533 | 137 | 342 |
| 2025-10 | 49 | 582 | 144 | 396 |
| 2025-11 | 26 | 608 | 150 | 425 |
| 2025-12 | 39 | 647 | 159 | 469 |
| 2026-01 | 37 | 684 | 166 | 40 |
| 2026-02 | 19 | 703 | 170 | 63 |
| 2026-03 | 22 | 725 | 175 | 88 |
| 2026-04 | 13 | 738 | 178 | 102 |
| 2026-05 | 20 | 758 | 183 | 124 |
| 2026-06 | 16 | 774 | 187 | 142 |
| 2026-07 | 12 | 786 | 191 | 155 |
| 2026-08 | 9 | 795 | 191 | 164 |
| 2026-09 | 8 | 803 | 195 | 173 |
| 2026-10 | 14 | 817 | 199 | 190 |
| 2026-11 | (blank) | (blank) | (blank) | 203 |
| 2026-12 | (blank) | (blank) | (blank) | 205 |

## 5. Sessions by status

Query 5 of `model/check.dax` (`by_status`).

| Session[Status] | [Sessions] |
|---|---:|
| Cancelled | 54 |
| Completed | 817 |
| No Show | 23 |
| Scheduled | 15 |

## 6. Participants and retention by visit

Query 6 of `model/check.dax` (`by_visit`).

Visits 5 to 7 are extra visits; the visual of the report is filtered to visits 1 to 4.

| Session[Visit No] | [Participants Attended] | [Visit Retention] |
|---|---:|---:|
| 1 | 189 | 1 |
| 2 | 181 | 0.957672 |
| 3 | 175 | 0.925926 |
| 4 | 175 | 0.925926 |
| 5 | 45 | 0.238095 |
| 6 | 6 | 0.031746 |
| 7 | 1 | 0.00529101 |

## 7. Participants by age band and sex

Query 7 of `model/check.dax` (`by_age_sex`).

| Participant[Age Band] | Participant[Sex] | [Participants Attended] |
|---|---|---:|
| 30-44 | F | 25 |
| 30-44 | M | 29 |
| 45-59 | F | 22 |
| 45-59 | M | 20 |
| 60+ | F | 39 |
| 60+ | M | 29 |
| Under 30 | F | 19 |
| Under 30 | M | 16 |

## 8. Data quality by modality

Query 8 of `model/check.dax` (`by_modality`).

| Recording[Modality] | [Recordings] | [Trials] | [QC Pass Rate] | [Uncalibrated Recordings] | [Uncalibrated Rate] | [Trial Rejection Rate] |
|---|---:|---:|---:|---:|---:|---:|
| EEG | 265 | 7374 | 0.875472 | 25 | 0.0943396 | 0.0804177 |
| EMG | 985 | 27746 | 0.882837 | 64 | 0.0649746 | 0.083075 |
| Force | 384 | 10686 | 0.864583 | 73 | 0.190104 | 0.0801048 |

## 9. Recordings by quality-control result

Query 9 of `model/check.dax` (`by_qc`).

| Recording[QC] | [Recordings] |
|---|---:|
| Flagged | 137 |
| Passed | 1423 |
| Pending | 12 |
| Rejected | 62 |

## 10. Rejected trials by reason

Query 10 of `model/check.dax` (`by_reason`).

| Trial[Reject Reason] | [Rejected Trials] |
|---|---:|
| Electrode Noise | 941 |
| Force Overshoot | 1000 |
| Late Onset | 904 |
| Movement Artifact | 909 |

## 11. Devices

Query 11 of `model/check.dax` (`by_device`).

| Device[Serial No] | [Recordings] | [Uncalibrated Recordings] | [Uncalibrated Rate] |
|---|---:|---:|---:|
| SN-DYN-03 | 273 | 73 | 0.267399 |
| SN-DYN-04 | 111 | (blank) | (blank) |
| SN-EEG-01 | 193 | (blank) | (blank) |
| SN-EEG-02 | 72 | 25 | 0.347222 |
| SN-EMG-01 | 166 | (blank) | (blank) |
| SN-EMG-02 | 72 | (blank) | (blank) |
| SN-EMG-03 | 273 | 64 | 0.234432 |
| SN-EMG-04 | 111 | (blank) | (blank) |
| SN-EMG-05 | 256 | (blank) | (blank) |
| SN-EMG-06 | 80 | (blank) | (blank) |
| SN-EMG-07 | 27 | (blank) | (blank) |

## 12. Force variability by group (study FFB-01)

Query 12 of `model/check.dax` (`feedback_by_group`).
Only `Study[Study Code]` = FFB-01.

| Session[Group] | [Mean Force CV] | [Mean Force CV Feedback On] | [Mean Force CV Feedback Off] | [Feedback Effect on Force CV] |
|---|---:|---:|---:|---:|
| Control | 4.426 | 4.32664 | 4.52885 | -0.202216 |
| Intervention | 4.1077 | 3.71445 | 4.5236 | -0.809157 |

## 13. The three effects

Query 13 of `model/check.dax` (`findings`).

| Measure | Value |
|---|---:|
| [Mean MDF] | 67.8664 |
| [Mean RMS] | 120.33 |
| [Mean Alpha Power] | 24.4263 |
| [MDF Change After Fatigue] | -11.0094 |
| [RMS Change After Fatigue] | 15.2528 |
| [Alpha Change Large vs Small Stimulus] | -3.91764 |
