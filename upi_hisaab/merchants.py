"""Known-merchant dictionary: statement name -> (canonical name, category).

Banks print merchants under many spellings ("SWIGGY", "SWIGGY INSTAMART",
"SWIGGY*"). The dictionary matches on a normalised, upper-cased substring
of the payee text, longest key first, so "SWIGGY INSTAMART" beats plain
"SWIGGY". Anything not in here is NOT guessed — it stays uncategorised
and the report says so honestly.

Categories are the plain words a normal person uses, not accounting codes.
"""

from __future__ import annotations

# (statement spelling, canonical name, category)
MERCHANTS: tuple[tuple[str, str, str], ...] = (
    # Food delivery & quick commerce
    ("SWIGGY INSTAMART", "Swiggy Instamart", "Groceries"),
    ("SWIGGY", "Swiggy", "Food delivery"),
    ("ZOMATO", "Zomato", "Food delivery"),
    ("BLINKIT", "Blinkit", "Groceries"),
    ("ZEPTO", "Zepto", "Groceries"),
    ("BIGBASKET", "BigBasket", "Groceries"),
    ("AMAZON FRESH", "Amazon Fresh", "Groceries"),
    ("JIO MART", "JioMart", "Groceries"),
    ("JIOMART", "JioMart", "Groceries"),
    ("DMART", "DMart", "Groceries"),
    ("RELIANCE FRESH", "Reliance Fresh", "Groceries"),
    ("DOMINOS", "Domino's", "Food delivery"),
    ("PIZZA HUT", "Pizza Hut", "Food delivery"),
    ("KFC", "KFC", "Food delivery"),
    ("MCDONALD", "McDonald's", "Food delivery"),
    ("BURGER KING", "Burger King", "Food delivery"),
    # Travel & commute
    ("OLA", "Ola", "Local transport"),
    ("UBER", "Uber", "Local transport"),
    ("RAPIDO", "Rapido", "Local transport"),
    ("IRCTC", "IRCTC", "Train travel"),
    ("REDBUS", "redBus", "Bus travel"),
    ("ABHIBUS", "AbhiBus", "Bus travel"),
    ("MAKE MY TRIP", "MakeMyTrip", "Travel"),
    ("MAKEMYTRIP", "MakeMyTrip", "Travel"),
    ("GOIBIBO", "Goibibo", "Travel"),
    ("FASTAG", "FASTag", "Vehicle"),
    ("METRO", "Metro", "Local transport"),
    ("INDIGO", "IndiGo", "Flights"),
    ("AIR INDIA", "Air India", "Flights"),
    # Subscriptions (the ones people forget they pay for)
    ("NETFLIX", "Netflix", "Subscriptions"),
    ("SPOTIFY", "Spotify", "Subscriptions"),
    ("HOTSTAR", "Disney+ Hotstar", "Subscriptions"),
    ("PRIME VIDEO", "Prime Video", "Subscriptions"),
    ("YOUTUBE", "YouTube Premium", "Subscriptions"),
    ("APPLE.COM", "Apple", "Subscriptions"),
    ("APPLE", "Apple", "Subscriptions"),
    ("GOOGLE ONE", "Google One", "Subscriptions"),
    ("GOOGLE PLAY", "Google Play", "Subscriptions"),
    ("AMAZON PRIME", "Amazon Prime", "Subscriptions"),
    ("CHATGPT", "ChatGPT", "Subscriptions"),
    ("OPENAI", "OpenAI", "Subscriptions"),
    ("LINKEDIN", "LinkedIn", "Subscriptions"),
    ("JIO", "Jio", "Mobile & internet"),
    ("AIRTEL", "Airtel", "Mobile & internet"),
    ("BSNL", "BSNL", "Mobile & internet"),
    ("VODAFONE", "Vodafone Idea", "Mobile & internet"),
    ("VI ", "Vodafone Idea", "Mobile & internet"),
    # Shopping
    ("AMAZON", "Amazon", "Shopping"),
    ("FLIPKART", "Flipkart", "Shopping"),
    ("MYNTRA", "Myntra", "Shopping"),
    ("AJIO", "AJIO", "Shopping"),
    ("MEESHO", "Meesho", "Shopping"),
    ("NYKAA", "Nykaa", "Shopping"),
    ("DECATHLON", "Decathlon", "Shopping"),
    # Health
    ("APOLLO PHARMACY", "Apollo Pharmacy", "Medicines"),
    ("PHARMEASY", "PharmEasy", "Medicines"),
    ("1MG", "1mg", "Medicines"),
    ("NETMEDS", "Netmeds", "Medicines"),
    ("APOLLO", "Apollo", "Health"),
    # Bills & utilities
    ("TATA POWER", "Tata Power", "Electricity"),
    ("ADANI ELECTRICITY", "Adani Electricity", "Electricity"),
    ("ELECTRICITY", "Electricity board", "Electricity"),
    ("INDANE", "Indane LPG", "Cooking gas"),
    ("HP GAS", "HP Gas", "Cooking gas"),
    ("BHARAT GAS", "Bharat Gas", "Cooking gas"),
    ("LIC", "LIC", "Insurance"),
    ("HDFC ERGO", "HDFC ERGO", "Insurance"),
    # Money
    ("GROWW", "Groww", "Investments"),
    ("ZERODHA", "Zerodha", "Investments"),
    ("PAYTM MONEY", "Paytm Money", "Investments"),
    ("CRED", "CRED", "Credit card bill"),
)

# Keyword rules for payees the dictionary does not know. Checked only
# when no dictionary entry matched. (keyword, category)
KEYWORD_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("MILK", "Groceries"),
    ("VEGETABLE", "Groceries"),
    ("SABZI", "Groceries"),
    ("KIRANA", "Groceries"),
    ("GROCER", "Groceries"),
    ("AUTO", "Local transport"),
    ("RICKSHAW", "Local transport"),
    ("PETROL", "Vehicle"),
    ("DIESEL", "Vehicle"),
    ("CNG", "Vehicle"),
    ("PARKING", "Vehicle"),
    ("TOLL", "Vehicle"),
    ("RECHARGE", "Mobile & internet"),
    ("BROADBAND", "Mobile & internet"),
    ("WIFI", "Mobile & internet"),
    ("WATER BILL", "Utilities"),
    ("GAS BILL", "Cooking gas"),
    ("ELECTRIC", "Electricity"),
    ("SCHOOL FEE", "Education"),
    ("COLLEGE FEE", "Education"),
    ("TUITION", "Education"),
    ("EXAM FEE", "Education"),
    ("HOSPITAL", "Health"),
    ("CLINIC", "Health"),
    ("DOCTOR", "Health"),
    ("PHARMACY", "Medicines"),
    ("MEDICAL", "Medicines"),
    ("SALARY", "Salary"),
    ("RENT", "Rent"),
    ("EMI", "Loan EMI"),
    ("LOAN", "Loan EMI"),
    ("INSURANCE", "Insurance"),
    ("MUTUAL FUND", "Investments"),
    ("SIP", "Investments"),
    ("RESTAURANT", "Eating out"),
    ("CAFE", "Eating out"),
    ("TEA STALL", "Tea & snacks"),
    ("CHAI", "Tea & snacks"),
)

# Merchants whose charges are subscriptions by nature. A single charge
# from one of these inside a 12-month window is flagged as a "possible
# annual subscription — check it", even before a second charge proves
# the cadence.
SUBSCRIPTION_MERCHANTS = {
    "Netflix",
    "Spotify",
    "Disney+ Hotstar",
    "Prime Video",
    "YouTube Premium",
    "Apple",
    "Google One",
    "Google Play",
    "Amazon Prime",
    "ChatGPT",
    "OpenAI",
    "LinkedIn",
}


def lookup_merchant(payee: str) -> tuple[str, str] | None:
    """Return (canonical name, category) for a payee, or None.

    Longest matching key wins, so "SWIGGY INSTAMART" beats "SWIGGY".
    """
    upper = " " + (payee or "").upper().strip() + " "
    best: tuple[str, str, str] | None = None
    for key, name, category in MERCHANTS:
        key = key.strip()
        if (" " + key + " ") in upper or upper.strip() == key:
            if best is None or len(key) > len(best[0]):
                best = (key, name, category)
    if best is not None:
        return best[1], best[2]
    return None


def lookup_keyword(payee: str, narration: str = "") -> str | None:
    """Return a category from keyword rules, or None."""
    text = f"{payee} {narration}".upper()
    for keyword, category in KEYWORD_CATEGORIES:
        if keyword in text:
            return category
    return None
