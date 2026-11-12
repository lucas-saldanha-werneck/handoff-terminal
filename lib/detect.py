"""Text checks used by the hooks: the hand-off marker, refusals, sign-in words and the site gate.

English and Portuguese wording is covered. All checks run on norm() text (lower case,
no accents, straight quotes), so "I can’t" and "não posso" match like "i can't" / "nao posso".
"""
import re

from common import MARKER, compact, norm

# Words that mean "sign in / secret / identity number" (the things the app refuses to type).
SENSITIVE = re.compile(
    r"\b(password|passcode|passphrase|passwd|credentials?|log ?in|log ?into|login|log on|log me in|"
    r"sign ?in|sign ?into|signin|sign me in|"
    r"username|user name|one[- ]time (code|password)|otp|2fa|two[- ]factor|verification code|"
    r"security code|pin|social security|ssn|tax id|taxpayer id|tin|itin|national id|government id|"
    r"id number|passport|driver'?s licen[cs]e|api key|access key|secret key|api token|"
    r"personal (data|details|information|info)|date of birth|home address|"
    r"senha|cpf|cnpj|rg|cnh|credenciais?|credencial|logar|logue|fazer login|entr(e|ar|a) na (minha )?conta|"
    r"codigo de (verificacao|acesso|seguranca)|documento de identidade|passaporte|chave de api|"
    r"dados pessoais|meus dados|data de nascimento|"
    r"contrasena|dni|nie)\b")

# Steps that go beyond signing in. Allowed only with scope "all", and only when the user's
# own messages ask for the same kind of action.
ACTIONS = {
    "money": re.compile(
        r"\b(buy|purchase|order|checkout|check out|pay|payment|subscribe|transfer|send money|wire|"
        r"credit card|debit card|card number|cvv|cvc|bank account|routing number|iban|"
        r"compr(a|ar|e|ei)|pag(ar|ue|amento)|pedido|finaliz(ar|e) (a |o )?(compra|pedido)|assin(ar|e|atura)|"
        r"transfer(ir|encia|e)|pix|boleto|cartao|conta bancaria)\b"),
    "account": re.compile(
        r"\b(create (an |the |a new |my )?account|sign ?up|register|registration|open (an |a )?account|"
        r"cri(ar|e) (uma |a |minha )?conta|cadastr\w*|abr(ir|a) (uma )?conta|inscrev\w*)\b"),
}

# Wording of a refusal to do the step.
_REFUSE_EN = (
    r"\b(i (can't|cant|cannot|can not|won't|will not|don't|do not|shouldn't|should not|must not)|"
    r"i(?:'m| am| m)? (not able to|unable to|not allowed to|not permitted to))\b"
    r"[^.!?\n]{0,60}?\b(enter|type|fill|input|submit|provide|use|log|sign|paste|key|handle|share|complete|"
    r"do (this|that|it))"
    r"|\bnot (allowed|permitted|able) to (enter|type|fill|input|submit|log|sign)"
    r"|\b(i am|i'm) (prohibited|forbidden)\b|\b(prohibited|forbidden) for me\b"
    r"|\bagainst my (rules|guidelines|instructions)\b"
    r"|\bfor (security|safety|privacy) reasons\b"
    r"|\byou('ll| will)? (need|have) to (enter|type|fill|do|log|sign|complete)[^.!?\n]{0,40}\byourself\b"
    r"|\bplease (enter|type|fill|complete)[^.!?\n]{0,60}\byourself\b")
_REFUSE_PT = (
    r"\bnao (posso|consigo|vou|devo|tenho permissao para|me e permitido|e permitido|estou autorizad[oa] a)\b"
    r"[^.!?\n]{0,60}?\b(digitar|preencher|inserir|colocar|informar|entrar|logar|fazer login|usar|enviar|submeter|"
    r"colar|completar|fazer (isso|esse passo))"
    r"|\bregra fixa\b|\bmesmo com (o )?seu pedido\b|\bmesmo que voce (peca|autorize)\b"
    r"|\bpor (motivos? de )?seguranca\b"
    r"|\b(voce|vc) (mesmo|mesma) (precisa|tera|vai ter|deve)\b")
REFUSE = re.compile(_REFUSE_EN + "|" + _REFUSE_PT)

_SENTENCE = re.compile(r"(?<=[.!?;:])\s+|\n+")

# The marker must be the last non-empty line: HANDOFF-TERMINAL: <site> | <step>
_MARKER_LINE = re.compile(
    r"^\s*[`*_\"']*" + MARKER + r"\s*:\s*(?P<body>.*?)\s*[`*_\"']*\s*$", re.I)

# Two-part public suffixes, so "zonasul.com.br" -> "zonasul" and "gov.uk" sites work.
_SUFFIX2 = {"com.br", "net.br", "org.br", "gov.br", "edu.br", "co.uk", "org.uk", "gov.uk", "ac.uk",
            "com.au", "net.au", "gov.au", "co.nz", "co.jp", "co.in", "com.mx", "com.ar", "com.co",
            "co.za", "com.pt", "com.es", "com.tr", "com.sg", "com.hk", "co.kr"}


def sentences(text):
    return [s for s in _SENTENCE.split(norm(text)) if s.strip()]


def mentions_sensitive(text):
    return bool(SENSITIVE.search(norm(text)))


def action_kinds(text):
    """Which beyond-sign-in actions a text asks for: a subset of {"money", "account"}."""
    t = norm(text)
    return {kind for kind, rx in ACTIONS.items() if rx.search(t)}


# A negation just before an action word in the same clause: "don't pay", "não pague", "sem comprar".
_NEGATION = re.compile(r"\b(don'?t|do not|does not|doesn'?t|not|never|no|without|nor|avoid|stop|"
                       r"nao|nunca|sem|nem|jamais|evite)\b")
_CLAUSE_END = re.compile(r"[.,;:!?()\n]|\b(but|then|and then|mas|e depois|depois)\b")


def _asked_kinds(text):
    """Action kinds the text asks for, leaving out mentions that are negated in their clause."""
    t = norm(text)
    kinds = set()
    for kind, rx in ACTIONS.items():
        for m in rx.finditer(t):
            before = t[max(0, m.start() - 40):m.start()]
            ends = list(_CLAUSE_END.finditer(before))
            if ends:
                before = before[ends[-1].end():]
            if not _NEGATION.search(before):
                kinds.add(kind)
                break
    return kinds


def actions_authorized(step, user_texts):
    """True when every kind of action in the step is also asked for, not negated, in the user's
    own messages ("don't pay" or "sem comprar" does not count)."""
    return action_kinds(step) <= set().union(*[_asked_kinds(u) for u in (user_texts or [])] or [set()])


def is_refusal(text):
    """A sentence (or a sentence plus the next one) that refuses AND names a sign-in/secret item."""
    parts = sentences(text)
    for i, part in enumerate(parts):
        if REFUSE.search(part):
            window = part + " " + (parts[i + 1] if i + 1 < len(parts) else "")
            if SENSITIVE.search(part) or SENSITIVE.search(window):
                return True
    return False


def parse_marker(text):
    """Return (site, step) when the LAST non-empty line is the marker, (None, None) if there is
    no marker, and ("", "") when the marker is there but malformed.

    The last-line rule keeps quotes and examples in the middle of a reply from acting:
    a reply that only mentions the marker never ends with it.
    """
    lines = [ln for ln in (text or "").replace("\r", "").split("\n") if ln.strip()]
    if not lines:
        return None, None
    last = lines[-1].translate({0x2019: "'", 0x201c: '"', 0x201d: '"'})
    if last.lstrip().startswith(">"):
        return None, None  # a block quote is someone else's text
    if sum(1 for ln in lines if ln.strip().startswith("```")) % 2 == 1:
        return None, None  # still inside an open code block
    m = _MARKER_LINE.match(last)
    if not m:
        return None, None
    body = m.group("body")
    if "|" not in body:
        return "", ""
    site, step = (part.strip(" `*_\"'") for part in body.split("|", 1))
    host = valid_host(site)
    if not host or not step:
        return "", ""
    return host, step[:300]


def site_host(site):
    s = norm(site).strip()
    s = re.sub(r"^[a-z][a-z0-9+.-]*://", "", s)
    s = s.split("/")[0].split("?")[0].split("#")[0].split("@")[-1].split(":")[0]
    return s[4:] if s.startswith("www.") else s


_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_HOST = re.compile(r"(?:%s\.)+[a-z][a-z0-9-]*[a-z0-9]" % _LABEL)
# A domain written in free text, not glued to a longer name: "drdevil.com" does not contain "devil.com".
_HOST_IN_TEXT = re.compile(r"(?<![a-z0-9.-])(%s)(?![a-z0-9-]|\.[a-z0-9])" % _HOST.pattern)


def valid_host(site):
    """The normalized host of a marker's site field ("https://www.Example.com/x" -> "example.com"),
    or "" when it is not a plain domain name (spaces, markup, a bare name like "Zona Sul")."""
    raw = (site or "").strip()
    if not raw or any(ch.isspace() for ch in raw) or len(raw) > 300:
        return ""
    host = site_host(raw)
    return host if len(host) <= 253 and _HOST.fullmatch(host) else ""


def registrable(host):
    """The registrable domain: "login.zonasul.com.br" -> "zonasul.com.br", "a.google.com" -> "google.com"."""
    labels = host.split(".")
    n = 3 if len(labels) >= 3 and ".".join(labels[-2:]) in _SUFFIX2 else 2
    return ".".join(labels[-n:])


def site_key(site):
    """Main name of a site: "https://login.zonasul.com.br/x" -> "zonasul", "Zona Sul" -> "zonasul"."""
    host = site_host(site)
    if "." not in host:
        return compact(site)
    labels = [lb for lb in host.split(".") if lb]
    if len(labels) >= 3 and ".".join(labels[-2:]) in _SUFFIX2:
        labels = labels[:-2]
    elif len(labels) >= 2:
        labels = labels[:-1]
    return compact(labels[-1]) if labels else ""


def site_authorized(site, user_texts):
    """True when the user's own messages write the site's domain. This check runs in code,
    outside the model, so text from a web page cannot add a new site on its own.

    The user must have written a domain with the same registrable domain as the site
    ("google.com" covers accounts.google.com). A bare name ("Zona Sul", "Google") or another
    ending (google.net) is not enough: the app then asks the user to confirm the domain.
    """
    host = valid_host(site)
    if not host:
        return False
    want = registrable(host)
    for text in user_texts or []:
        for m in _HOST_IN_TEXT.finditer(norm(text)):
            said = m.group(1)
            said = said[4:] if said.startswith("www.") else said
            if registrable(said) == want:
                return True
    return False
