# Changelog

## 0.2.0 — 2026-11-27

Real statement files are messier than the clean sample. This release
fixes five ways a real file could crash the tool, lose rows, or produce
wrong totals. Every fix was reproduced against the old code first.

- **`--month` no longer breaks refunds and subscriptions.** Matching now
  runs on the whole file and `--month` only windows the report. Before,
  a September purchase refunded in October showed up in October's
  report as new income, and Netflix was demoted from "₹199 monthly"
  to "possible annual" in single-month reports.
- **Dates with a time of day are read.** `01/11/2026 14:32`,
  `01-Nov-2026 10:00:00` and `2026-11-01T14:32:00` used to be skipped
  as unreadable, silently removing that money from the totals. The
  time is now ignored (the report works in whole days). Two-digit-year
  dates like `01 Nov 26` and `01-11-26` are also read.
- **Semicolon, tab and pipe exports are read.** Only comma-separated
  files worked before; other separators failed with "Could not find a
  header row". The separator is now detected automatically.
- **Windows-1252 / Latin-1 files no longer crash.** A statement saved
  in those encodings (common for Indian bank exports) died with a raw
  `UnicodeDecodeError` traceback. The file is now read with an
  encoding fallback.
- **One purchase cannot refund two credits.** Refund matching now uses
  each purchase at most once (nearest date wins). Before, one ₹1,499
  purchase plus two ₹1,499 credits marked both credits as refunds, and
  the second — real money in — vanished from income.

## 0.1.0 — 2026-11-25

- First release: SBI/HDFC/ICICI/generic CSV reading, UPI narration
  decoding, de-duplication, self-transfer and UPI Lite handling,
  refund matching, subscription detection, plain-language text and
  JSON reports.
