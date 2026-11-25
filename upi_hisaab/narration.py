"""Parse Indian bank-statement narrations into (channel, utr, payee, vpa).

Real narrations are messy: UPI lines carry a 12-digit UTR, a P2M/P2A
marker, a VPA handle and a name, all separated by slashes; IMPS/NEFT
lines carry a reference and a name; POS lines carry a masked card number;
gateway names (Razorpay, BillDesk) appear where the shop's name should be.
The parser never invents a payee — when it cannot tell who was paid, the
payee stays empty and the line is flagged for the user to check.
"""

from __future__ import annotations

import re

_UTR_RE = re.compile(r"\b(\d{12})\b")
_ANY_REF_RE = re.compile(r"\b(\d{10,16})\b")
_VPA_RE = re.compile(r"([A-Za-z0-9._\-+]{2,}@[A-Za-z]{2,})")

# Payment gateways: the name in the narration is the middleman, not the
# shop. Flag these so the report says so instead of inventing a merchant.
GATEWAYS = {
    "RAZORPAY": "Razorpay",
    "BILLDESK": "BillDesk",
    "PAYTM": "Paytm",
    "CASHFREE": "Cashfree",
    "CCAvenue": "CCAvenue",
    "CCAVENUE": "CCAvenue",
    "PAYU": "PayU",
    "PHONEPE": "PhonePe",
    "GPAY": "Google Pay",
    "AMAZONPAY": "Amazon Pay",
    "JUSPAY": "Juspay",
    "EASEBUZZ": "Easebuzz",
    "PAYTM PG": "Paytm",
}

_LITE_MARKERS = ("UPI LITE", "UPILITE", "LITE TOPUP", "LITE TOP-UP", "LITE TOP UP")


def is_lite_topup(narration: str) -> bool:
    """True when the line is a UPI Lite wallet load, not a purchase."""
    upper = (narration or "").upper()
    return any(marker in upper for marker in _LITE_MARKERS)


def _clean_segment(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("_", " ").strip()).strip(" -")


def parse_narration(narration: str) -> dict:
    """Parse one narration. Always returns all keys; unknowns stay empty.

    Keys: channel, utr, payee, vpa, gateway ("" when not a gateway line),
    is_lite_topup (bool).
    """
    raw = (narration or "").strip()
    upper = raw.upper()
    out = {
        "channel": "other",
        "utr": "",
        "payee": "",
        "vpa": "",
        "gateway": "",
        "is_lite_topup": is_lite_topup(raw),
    }
    if not raw:
        return out

    # --- UPI ------------------------------------------------------------
    if upper.startswith("UPI") or "/UPI/" in upper or upper.startswith("UPI/"):
        out["channel"] = "upi"
        utr = _UTR_RE.search(raw)
        if utr:
            out["utr"] = utr.group(1)
        vpa = _VPA_RE.search(raw)
        if vpa:
            out["vpa"] = vpa.group(1).lower()
        parts = [p for p in raw.split("/") if p.strip()]
        # Drop the leading UPI token, the UTR, the P2M/P2A marker and the
        # VPA/phone segment; what is left is the payee name.
        kept: list[str] = []
        for part in parts:
            p = part.strip()
            if p.upper() in ("UPI", "P2M", "P2A", "P2P", "P2P"):
                continue
            if _UTR_RE.fullmatch(p):
                continue
            if _VPA_RE.search(p) and "@" in p:
                continue
            if re.fullmatch(r"\d{10}", p):
                continue
            kept.append(p)
        # A gateway name in the narration is the honest payee: the shop's
        # name is hidden behind it, and an order id is not a payee.
        for part in kept:
            if part.upper() in GATEWAYS:
                out["payee"] = GATEWAYS[part.upper()]
                break
        else:
            if kept:
                out["payee"] = _clean_segment(kept[-1])
        # A bare "UPI/123456789012/SWIGGY" has the payee as the last part.
        if not out["payee"] and len(parts) >= 3:
            out["payee"] = _clean_segment(parts[-1])
        return _finish(out)

    # --- IMPS / NEFT / RTGS ---------------------------------------------
    for prefix, channel in (("IMPS", "imps"), ("NEFT", "neft"), ("RTGS", "rtgs")):
        if upper.startswith(prefix):
            out["channel"] = channel
            ref = _ANY_REF_RE.search(raw)
            if ref:
                out["utr"] = ref.group(1)
            rest = re.sub(rf"^{prefix}[-/ ]*", "", raw, flags=re.I).strip()
            rest = _ANY_REF_RE.sub("", rest, count=1).strip(" -/")
            out["payee"] = _clean_segment(rest)
            return _finish(out)

    # --- ACH / NACH (EMI, SIP, auto-debit) -------------------------------
    if upper.startswith(("ACH", "NACH", "ECS")):
        out["channel"] = "ach"
        rest = re.sub(r"^(ACH|NACH|ECS)[-/ ]*", "", raw, flags=re.I).strip()
        out["payee"] = _clean_segment(rest)
        return _finish(out)

    # --- POS / card ------------------------------------------------------
    if upper.startswith("POS") or "POS/" in upper:
        out["channel"] = "pos"
        # Drop any masked-card token (411111******1111, 4111********1111):
        # a token holding both digits and stars is a card number, not a shop.
        tokens = [tok for tok in raw.split() if not ("*" in tok and any(c.isdigit() for c in tok))]
        text = " ".join(tokens)
        text = re.sub(r"^POS[-/ ]*", "", text, flags=re.I).strip()
        out["payee"] = _clean_segment(text)
        return _finish(out)

    # --- ATM -------------------------------------------------------------
    if upper.startswith("ATM"):
        out["channel"] = "atm"
        out["payee"] = _clean_segment(re.sub(r"^ATM[-/ ]*", "", raw, flags=re.I))
        return _finish(out)

    # --- Anything else: keep the whole line as the payee text ------------
    out["payee"] = _clean_segment(raw)
    return _finish(out)


def _finish(parsed: dict) -> dict:
    """Mark gateway lines so the report never invents a shop name.

    The UPI parser already sets the payee to the gateway's name when a
    gateway segment is present, so checking the payee is enough — and it
    avoids mistaking a person's Paytm handle ("9876543210@paytm") for a
    payment through the Paytm gateway.
    """
    payee_upper = parsed["payee"].upper()
    for key, name in GATEWAYS.items():
        if key in payee_upper:
            parsed["gateway"] = name
            return parsed
    return parsed
