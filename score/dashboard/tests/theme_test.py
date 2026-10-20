"""The cockpit's one theme: every colour of a template or static file comes from the design tokens
(design/tokens/colours.css), every token a page names is defined, and the text tokens hold WCAG AA."""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[3]
PAGES = REPO / "score" / "dashboard" / "pages"
TOKENS = REPO / "design" / "tokens"
SOURCES = [*sorted((PAGES / "templates").rglob("*.html")),
           *sorted(path for path in (PAGES / "static").rglob("*") if path.suffix in (".css", ".js"))]

HEX = re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
NUMBER_HEX = re.compile(r"\b0x[0-9a-fA-F]{6}\b")
FUNCTION = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(\s*[\d.]")
NAMED = ("black|white|red|green|blue|yellow|orange|purple|gray|grey|pink|silver|navy|teal|maroon|olive|lime|aqua|"
         "fuchsia|cyan|magenta|gold|brown")
# a named colour in a CSS value: after a declaration's colon (a css file, a style attribute), never in a selector
CSS_NAMED = re.compile(rf":[^;{{}}\"]*(?<![\w-])(?:{NAMED})(?![\w-])")
STYLE = re.compile(r"style=\"([^\"]*)\"")
USED = re.compile(r"var\(\s*(--[\w-]+)|[tT]oken\(\"(--[\w-]+)\"\)")  # token(...), designToken(...)
DEFINED = re.compile(r"(--[\w-]+)\s*:")


def literal_colours(path):
    """Each hard-coded colour in one template or static file, as (line number, the literal)."""
    found = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        declarations = [line] if path.suffix == ".css" else [f":{value}" for value in STYLE.findall(line)]
        literals = [*HEX.findall(line), *FUNCTION.findall(line), *NUMBER_HEX.findall(line),
                    *(named for value in declarations for named in CSS_NAMED.findall(value))]
        found += [(number, literal) for literal in literals]
    return found


def test_no_template_or_static_file_hard_codes_a_colour():
    found = {str(path.relative_to(REPO)): hits for path in SOURCES if (hits := literal_colours(path))}
    assert not found, f"colours outside design/tokens/colours.css: {found}"


def test_the_check_finds_each_kind_of_literal(tmp_path):
    css, js = tmp_path / "a.css", tmp_path / "a.js"
    css.write_text(".x { color: #abc; } .y { background: rgba(0, 0, 0, .5); } .film-black { border-color: white; }\n")
    js.write_text("new THREE.Color(0xffd400);\n")
    assert [literal for _, literal in literal_colours(css)] == ["#abc", "rgba(0", ": white"]
    assert literal_colours(js) == [(1, "0xffd400")]


def test_every_token_a_page_names_is_defined():
    defined = {name for path in (TOKENS / "colours.css", TOKENS / "scale.css", *SOURCES)
               for name in DEFINED.findall(path.read_text())}
    used = {name for path in SOURCES for pair in USED.findall(path.read_text()) for name in pair if name}
    assert not used - defined, f"tokens named but never defined: {sorted(used - defined)}"


def test_the_tokens_and_font_are_served():
    from fastapi.testclient import TestClient

    from score.dashboard.site.asgi import app
    client = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    links = re.findall(r'href="([^"]+)"', (PAGES / "templates/pages/tokens.html").read_text())
    for url in [*links, "/static/design/fonts/poppins/poppins-400-latin.woff2", "/static/pages/tokens.js"]:
        assert client.get(url).status_code == 200, url


def hex_of(name, text):
    return re.search(rf"{name}:\s*(#[0-9a-fA-F]{{6}})\b", text).group(1)


def contrast(one, other):
    """WCAG 2 contrast ratio of two #rrggbb colours."""
    def luminance(colour):
        channels = [int(colour[at:at + 2], 16) / 255 for at in (1, 3, 5)]
        red, green, blue = [part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4 for part in channels]
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue
    light, dark = sorted((luminance(one), luminance(other)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_text_holds_wcag_aa_on_every_surface():
    text = (TOKENS / "colours.css").read_text()
    pairs = [(ink, ground) for ink in ("--color-primary", "--color-text-body", "--color-text-light",
                                       "--color-text-faint", "--color-accent")
             for ground in ("--color-bg", "--color-bg-section", "--color-bg-raised")]
    pairs += [("--color-accent-ink", "--color-accent")]
    pairs += [("--color-on-status", status) for status in ("--color-idle", "--color-gap-missing", "--color-gap-gate",
                                                          "--color-gap-route", "--color-gap-lost")]
    ratios = {(ink, ground): contrast(hex_of(ink, text), hex_of(ground, text)) for ink, ground in pairs}
    low = {pair: round(ratio, 2) for pair, ratio in ratios.items() if ratio < 4.5}
    assert not low, f"under WCAG AA 4.5:1: {low}"


def test_gap_colours_stay_told_apart():
    text = (TOKENS / "colours.css").read_text()
    kinds = [hex_of(f"--color-gap-{kind}", text) for kind in ("missing", "gate", "route", "lost")]
    assert len(set(kinds)) == 4 and hex_of("--color-accent", text) not in kinds
