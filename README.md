# upi-hisaab

**Give it your bank statement file. It tells you, in plain words, where your money actually went.**

Free. Offline. No accounts, no uploads, no bank login. Your statement never leaves your computer.

## The problem

Your bank statement shows payments as cryptic codes and personal names — `UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY`, `RAMESH KUMAR`, `RAZORPAY`. At month-end you cannot tell where your money went. As one guide puts it: *"When you look back two weeks later and see five payments of ₹60, ₹140, ₹210, ₹85, and ₹320 to unfamiliar names, it is almost impossible to remember which payment was for morning milk."* ([ExpenseBook](https://expensebook.codewebtechnologies.com/guides/find-and-review-upi-transaction-history), Nov 2026)

The usual fixes don't work for a normal person:

- **Expense-tracker apps** (Walnut, ExpenseBook) need you to log every payment by hand, the same day, forever. The moment you stop logging, the picture dies.
- **Statement-analysis websites** (e.g. StatementIQ) are paid services that want your full bank statement uploaded to their servers.
- **Your UPI app's history** only shows one app, and it mixes real spending with self-transfers, refunds and failed payments — so the totals never match your bank balance.

upi-hisaab does the job from the statement file itself, on your own computer.

## What it does

1. **Reads your statement** — a CSV export from net banking (SBI, HDFC, ICICI and generic layouts; it works out the columns itself). Comma, semicolon, tab and pipe separators all work, dates with a time of day (`01/11/2026 14:32`) are fine, and files saved in Windows-1252/Latin-1 encoding are read instead of crashing.
2. **Decodes every line** — the 12-digit UPI reference, the shop or person, the channel (UPI / IMPS / NEFT / card / ATM).
3. **Sorts real spending from money that only looks spent:**
   - the same payment listed twice (UPI app + bank statement) is counted **once**,
   - money moved between **your own accounts** is not spending,
   - a **refund** days later is matched back to the payment it returns,
   - a **failed payment that was reversed** is not spending at all,
   - a **UPI Lite top-up** is not spending — counting the ₹1,000 top-up *and* the ten ₹100 Lite purchases would double-count ₹1,000.
4. **Finds the subscriptions you forgot** — the same charge every month (Netflix ₹199 → ₹2,388 a year), and flags a single charge from a known subscription service as worth checking.
5. **Prints a report in plain words** — what it went on, who got the most, and exactly how much money you still cannot account for.

It never guesses. A payee it cannot identify stays **Uncategorised** and the report says so, with the amount.

## Setup — one command

You need Python 3.10 or newer. Nothing to install — it uses only Python's standard library.

```bash
git clone https://github.com/shouvikkkk/upi-hisaab.git
cd upi-hisaab
```

## Use it

**Step 1.** Export your statement as a **CSV** from your bank's net banking or mobile app (not a PDF — this tool cannot read PDFs).

**Step 2.** Run it:

```bash
python -m upi_hisaab report statement.csv
```

**Step 3 (worth doing once).** Tell it who the personal QR names really are, in a small text file — your bank shows "Ramesh Kumar" where you mean "the milkman", and nobody else can know that:

```
# nicknames.txt
Ramesh Kumar = Milkman, Groceries
9876543210@okaxis = Milkman, Groceries
own: SBI SAVINGS = My SBI savings
```

Then:

```bash
python -m upi_hisaab report statement.csv --nicknames nicknames.txt --month 2026-11
```

Add `--format json` for a machine-readable report instead of plain words.

`--month` shows one month, but refunds and subscriptions are still matched across the whole file — buy in September, refund in October, and October's report shows the refund as money back (not as new income), while September's still calls Netflix a monthly subscription.

## A worked example

Asha earns ₹25,000 a month. Her statement for September–November 2026 is in `examples/sample-statement.csv`, with `examples/sample-nicknames.txt`. Run:

```bash
python -m upi_hisaab report examples/sample-statement.csv --nicknames examples/sample-nicknames.txt
```

You get:

```
Your money in September 2026 – November 2026
============================================

Money in:  ₹75,000 (3 credits)
Money out: ₹8,405.70 (26 payments)
Moved between your own accounts: ₹7,000 (not counted as spending)
Refunds that came back: ₹1,499

What it went on:
  Groceries                    ₹3,617  (43%)
  Shopping                     ₹2,398  (29%)
  Food delivery                  ₹987  (12%)
  Subscriptions                  ₹716  (9%)
  Medicines                      ₹420  (5%)
  Uncategorised                  ₹250  (3%)
  Bank charges                 ₹17.70  (0%)

Biggest payees:
  Milkman                                  ₹1,517
  Flipkart                                 ₹1,499
  DMart                                    ₹1,240
  Amazon                                     ₹899
  BigBasket                                  ₹860
  Swiggy                                     ₹698
  Netflix                                    ₹597
  Apollo Pharmacy                            ₹420

Repeats every month (check these — subscriptions hide here):
  Netflix — ₹199 monthly (3 charges, ₹2,388/year, next around 02 Dec 2026)
  Spotify — ₹119 possible annual (1 charge, ₹119/year)

Money you still cannot account for: ₹250 across 1 payment. Add nicknames for those payees and run it again.

Removed 1 duplicate line(s) — the same payment listed twice (UPI app + bank statement).
```

Three things to notice in Asha's report:

- **₹1,499 came back** — her September Flipkart order was refunded in October. The tool matched the refund to the original payment instead of calling it new income.
- **₹7,000 is not spending** — two ₹1,000 UPI Lite top-ups and a ₹5,000 move to her own SBI account. Without this, her "spending" would be overstated by ₹7,000.
- **Netflix costs ₹2,388 a year**, not ₹199 — the monthly figure hides the yearly one.

## One line you don't understand?

```bash
python -m upi_hisaab decode "UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY"
```

```
Narration: UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY
Channel:   upi
Reference: 412345678901 (use this 12-digit number to find the payment in your UPI app)
UPI ID:    9876543210@okhdfcbank
Paid to:   SWIGGY
```

## Honest limitations

- **PDF statements are not supported.** Export CSV from net banking. (If your bank only gives PDFs, the file will say so instead of failing silently.) CSV files with semicolon, tab or pipe separators, dates that include a time of day, and Windows-1252/Latin-1 encodings are all read fine.
- **It knows who you paid, not what you bought.** The 12-digit UPI reference identifies the payment, not the items in the bag. A ₹250 payment to "Some Random Shop" stays uncategorised until you add a nickname for it.
- **A payment gateway hides the shop.** When the narration says RAZORPAY or BILLDESK, the real shop's name is not in the statement at all — the report says "paid via Razorpay" instead of inventing a merchant.
- **Recurring detection needs history.** A subscription is only "monthly" after three charges about a month apart. With one charge, a known subscription is flagged as "possible annual — check it", not proven.
- **Rows it cannot read are reported, not dropped.** A bad date or a bad amount prints a warning naming the line, so you can check nothing real was lost.
- **This is not financial advice.** It adds up your own statement; it does not tell you what to spend.

## Tests

```bash
python3 -m unittest discover -s tests
```

82 tests, covering date/amount formats (including dates with a time of day), narration grammar, all three bank layouts plus semicolon/tab/pipe separators, de-duplication, refunds (including one purchase matching only one refund), reversals, self-transfers, the UPI Lite trap, recurring detection, cross-month refunds and subscriptions in `--month` reports, Latin-1-encoded files, and the full end-to-end report on the sample statement.

## License

MIT — see [LICENSE](LICENSE).
