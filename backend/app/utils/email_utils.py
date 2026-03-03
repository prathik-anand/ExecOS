"""
Email utilities — detect personal vs. business email domains.

A business email uses a custom domain (e.g. user@acmecorp.com).
A personal email uses a well-known free provider (gmail, outlook, etc.).
"""

# Common free / personal email providers
FREE_EMAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "yahoo.com", "ymail.com", "yahoo.co.uk", "yahoo.co.in",
    "icloud.com", "me.com", "mac.com",
    "aol.com",
    "protonmail.com", "proton.me", "pm.me",
    "mail.com", "email.com",
    "zoho.com",
    "tutanota.com", "tuta.io",
    "fastmail.com", "fastmail.fm",
    "gmx.com", "gmx.net", "gmx.de",
    "web.de", "t-online.de",
    "inbox.com",
    "yandex.com", "yandex.ru",
    "qq.com", "163.com", "126.com",
})


def get_email_domain(email: str) -> str:
    return email.split("@")[-1].lower().strip()


def is_personal_email(email: str) -> bool:
    return get_email_domain(email) in FREE_EMAIL_DOMAINS


def is_business_email(email: str) -> bool:
    return not is_personal_email(email)


def domain_to_org_name(domain: str) -> str:
    """Convert 'acmecorp.com' → 'Acmecorp'."""
    base = domain.split(".")[0]
    return base.replace("-", " ").replace("_", " ").title()
