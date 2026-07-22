"""Deterministic stylesheet audit + WCAG contrast tests for the Editorial
Revamp Design System (Task 10.3).

# Feature: editorial-revamp

These are NOT property-based tests. They are deterministic audits that parse
``blog_main/static/css/editorial.css`` (and scan the HTML templates) to assert
the visual constraints defined by Requirements 1.1-1.8 and 4.1-4.5:

  - No rectangular container radius exceeds 8px (Requirement 1.4). The fully
    circular radius token (``--radius-full``) is reserved for avatars /
    single-icon controls and is exempt.
  - Hairline (1px) borders are declared as the separation technique
    (Requirement 1.5).
  - Flat, single-color fills only: the sole permitted gradient is the
    legibility scrim placed over photographic imagery; the underline uses a
    single-color ``linear-gradient(currentColor, currentColor)`` which is a
    solid line, not a decorative fill (Requirements 1.6, 1.7).
  - No glassmorphism / ``backdrop-filter`` and no decorative geometric shapes
    (Requirement 1.7).
  - No auto-playing load animations and no scroll-triggered content animation:
    the stylesheet declares only user-caused ``transition`` state changes, no
    ``@keyframes`` and no ``animation`` property. The reading-progress bar is
    driven by a JS-set CSS variable width, not a CSS animation
    (Requirements 4.1, 4.2, 4.3, 4.5).
  - Exactly one serif family (headlines + article body) and exactly one
    sans-serif family (UI/nav/meta) are declared (Requirement 1.3).
  - The dark-theme accent is identical to the light-theme accent
    (Requirements 1.1, 1.2).
  - Every documented resting-state text/background token pair meets WCAG AA
    contrast in both themes: 4.5:1 for body text, 3:1 for large text / UI
    element colors (Requirement 1.8).

Contrast scope note: the matrix below evaluates the *resting* (default) state
of each documented token pair, which is what WCAG SC 1.4.3 evaluates. Transient
interaction states (e.g. the ``:hover`` link color) are interaction affordances
rather than part of the documented resting palette and are not part of this
static matrix.
"""

import re

from django.conf import settings
from django.test import SimpleTestCase

CSS_PATH = settings.BASE_DIR / "blog_main" / "static" / "css" / "editorial.css"
TEMPLATES_DIR = settings.BASE_DIR / "templates"


# ---------------------------------------------------------------------------
# WCAG contrast computation helper
# ---------------------------------------------------------------------------

def _hex_to_rgb(value):
    """Parse ``#RGB`` / ``#RRGGBB`` into an (r, g, b) 0-255 tuple."""
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Not a hex color: {value!r}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _parse_rgba(value):
    """Parse ``rgb(...)`` / ``rgba(...)`` into (r, g, b, a) with a in [0, 1]."""
    nums = re.findall(r"[-+]?\d*\.?\d+", value)
    r, g, b = (float(nums[0]), float(nums[1]), float(nums[2]))
    a = float(nums[3]) if len(nums) > 3 else 1.0
    return r, g, b, a


def _to_rgba(value):
    """Normalize a hex or rgb(a) color string to (r, g, b, a)."""
    value = value.strip()
    if value.startswith("#"):
        r, g, b = _hex_to_rgb(value)
        return float(r), float(g), float(b), 1.0
    if value.startswith("rgb"):
        return _parse_rgba(value)
    raise ValueError(f"Unsupported color format: {value!r}")


def composite_over(fg, base):
    """Alpha-composite foreground color string over an opaque base color.

    Returns an opaque (r, g, b) tuple. Used to resolve translucent tint fills
    (e.g. status-pill backgrounds) onto the surface they sit on.
    """
    fr, fg_, fb, fa = _to_rgba(fg)
    br, bg_, bb, ba = _to_rgba(base)
    if ba != 1.0:  # pragma: no cover - bases used here are always opaque
        raise ValueError("Compositing base must be opaque")
    r = fr * fa + br * (1 - fa)
    g = fg_ * fa + bg_ * (1 - fa)
    b = fb * fa + bb * (1 - fa)
    return (r, g, b)


def _relative_luminance(rgb):
    """WCAG 2.x relative luminance for an opaque (r, g, b) 0-255 tuple."""

    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(rgb[0]), channel(rgb[1]), channel(rgb[2]))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color_a, color_b, base="#FFFFFF"):
    """WCAG contrast ratio between two colors.

    Either color may be translucent; it is composited over ``base`` first so
    the ratio reflects the rendered appearance.
    """
    rgb_a = composite_over(color_a, base)
    rgb_b = composite_over(color_b, base)
    la = _relative_luminance(rgb_a)
    lb = _relative_luminance(rgb_b)
    lighter, darker = (max(la, lb), min(la, lb))
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# CSS parsing helpers
# ---------------------------------------------------------------------------

def _strip_css_comments(css):
    """Remove /* ... */ comments so scans don't match documentation prose."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _parse_token_block(css, selector):
    """Return {token_name: value} for the ``--foo: bar;`` declarations in the
    first rule matching ``selector`` (comments already stripped)."""
    # Find the selector, then capture up to its matching closing brace. The
    # token blocks here contain no nested braces, so a non-greedy match to the
    # next '}' is sufficient.
    pattern = re.escape(selector) + r"\s*\{(.*?)\}"
    match = re.search(pattern, css, flags=re.DOTALL)
    if not match:
        raise AssertionError(f"Could not find CSS block for selector {selector!r}")
    body = match.group(1)
    tokens = {}
    for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body):
        tokens[name.strip()] = value.strip()
    return tokens


def _resolve(tokens, value, _depth=0):
    """Resolve ``var(--x[, fallback])`` references against a token map."""
    if _depth > 10:  # pragma: no cover - guards against cyclic tokens
        raise AssertionError(f"var() resolution too deep for {value!r}")
    value = value.strip()
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", value)
    if not m:
        return value
    name, fallback = m.group(1), m.group(2)
    if name in tokens:
        return _resolve(tokens, tokens[name], _depth + 1)
    if fallback is not None:
        return _resolve(tokens, fallback, _depth + 1)
    raise AssertionError(f"Unresolved token {name!r}")


class _StylesheetFixture(SimpleTestCase):
    """Shared loading of the stylesheet + parsed token maps."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.raw_css = CSS_PATH.read_text(encoding="utf-8")
        cls.css = _strip_css_comments(cls.raw_css)
        cls.light = _parse_token_block(cls.css, ":root")
        dark_overrides = _parse_token_block(cls.css, ':root[data-theme="dark"]')
        # Dark theme inherits every light token it does not explicitly override.
        cls.dark = dict(cls.light)
        cls.dark.update(dark_overrides)
        cls.dark_overrides = dark_overrides


# ---------------------------------------------------------------------------
# Structural audits
# ---------------------------------------------------------------------------

class RadiusAuditTests(_StylesheetFixture):
    """Requirement 1.4: no rectangular radius > 8px; circular radius reserved."""

    CIRCULAR_TOKENS = {"--radius-full"}

    def test_radius_tokens_within_ceiling(self):
        radius_tokens = {
            name: value
            for name, value in self.light.items()
            if name.startswith("--radius-")
        }
        self.assertTrue(radius_tokens, "Expected --radius-* tokens to be declared")
        for name, value in radius_tokens.items():
            px = re.match(r"^(\d+(?:\.\d+)?)px$", value.strip())
            if name in self.CIRCULAR_TOKENS:
                # The circular token is intentionally large (pill/avatar shape).
                continue
            self.assertIsNotNone(
                px, f"Radius token {name} has unexpected value {value!r}"
            )
            self.assertLessEqual(
                float(px.group(1)),
                8.0,
                f"Rectangular radius token {name}={value} exceeds the 8px ceiling",
            )

    def test_no_literal_border_radius_over_8px(self):
        # Any border-radius declaration that uses a literal px value (not a
        # token) must also respect the 8px rectangle ceiling.
        for decl in re.findall(r"border-radius\s*:\s*([^;]+);", self.css):
            for px in re.findall(r"(\d+(?:\.\d+)?)px", decl):
                self.assertLessEqual(
                    float(px),
                    8.0,
                    f"border-radius declaration {decl!r} exceeds 8px on a rectangle",
                )


class BorderAuditTests(_StylesheetFixture):
    """Requirement 1.5: hairline (1px) borders are the separation technique."""

    def test_hairline_border_token_declared(self):
        self.assertIn("--border-hairline", self.light)
        self.assertIn("1px", self.light["--border-hairline"])
        self.assertEqual(self.light.get("--border-width"), "1px")


class GradientAndGlassAuditTests(_StylesheetFixture):
    """Requirements 1.6, 1.7: flat fills only; gradients only over imagery;
    no glassmorphism / backdrop-filter; no decorative shapes."""

    def test_only_sanctioned_gradients(self):
        gradients = re.findall(
            r"(linear-gradient|radial-gradient|conic-gradient)\s*\((.*?)\)",
            self.css,
            flags=re.DOTALL,
        )
        for kind, args in gradients:
            normalized = re.sub(r"\s+", " ", args).strip().lower()
            is_solid_underline = (
                kind == "linear-gradient"
                and normalized == "currentcolor, currentcolor"
            )
            is_image_scrim = (
                kind == "linear-gradient"
                and "to top" in normalized
                and "rgba(0, 0, 0" in normalized
            )
            self.assertTrue(
                is_solid_underline or is_image_scrim,
                f"Disallowed decorative {kind} found: {args!r}. Only the "
                f"single-color underline and the over-image legibility scrim "
                f"are permitted.",
            )

    def test_no_backdrop_filter(self):
        self.assertNotRegex(
            self.css,
            r"backdrop-filter\s*:",
            "backdrop-filter (glassmorphism) is forbidden by Requirement 1.7",
        )

    def test_no_glass_blur_filter(self):
        for decl in re.findall(r"[^-\w]filter\s*:\s*([^;]+);", self.css):
            self.assertNotIn(
                "blur(",
                decl,
                f"filter: blur() (frosted-glass effect) is forbidden: {decl!r}",
            )

    def test_no_decorative_clip_path_shapes(self):
        # Decorative geometric shapes are commonly built with clip-path
        # polygons; none should exist in the editorial system.
        self.assertNotRegex(
            self.css,
            r"clip-path\s*:",
            "Decorative clip-path shapes are forbidden by Requirement 1.7",
        )


class MotionAuditTests(_StylesheetFixture):
    """Requirements 4.1, 4.2, 4.3, 4.5: only user-caused transitions; no
    auto-playing load animation and no scroll-triggered content animation."""

    def test_no_keyframes(self):
        self.assertNotRegex(
            self.css,
            r"@keyframes",
            "@keyframes implies an auto-playing animation, forbidden by "
            "Requirements 4.3 / 4.5",
        )

    def test_no_animation_property(self):
        # `transition` is allowed (user-caused state change); the `animation`
        # shorthand / longhands are not (they would play on load).
        self.assertNotRegex(
            self.css,
            r"[^-\w]animation(?:-[\w]+)?\s*:",
            "The animation property is forbidden; only transitions on "
            "user-caused state changes are permitted (Requirements 4.1-4.5)",
        )

    def test_transitions_are_declared(self):
        # Positive check: the interaction affordances (hover lift, underline)
        # are implemented as transitions.
        self.assertRegex(self.css, r"transition\s*:")


class TypographyAuditTests(_StylesheetFixture):
    """Requirement 1.3: exactly one serif family and one sans family."""

    def test_exactly_one_serif_and_one_sans_family(self):
        self.assertIn("--font-serif", self.light)
        self.assertIn("--font-sans", self.light)

        font_family_tokens = {
            name: value
            for name, value in self.light.items()
            if name.startswith("--font-") and (
                "serif" in value.lower() or "sans-serif" in value.lower()
            )
        }
        # Only two font-family stacks may be declared.
        self.assertEqual(
            set(font_family_tokens),
            {"--font-serif", "--font-sans"},
            f"Expected exactly two font-family tokens, found {set(font_family_tokens)}",
        )

        serif_stack = self.light["--font-serif"].lower()
        sans_stack = self.light["--font-sans"].lower()
        # The serif stack terminates in the generic `serif` family and the sans
        # stack in `sans-serif`; neither must claim the other generic family.
        self.assertTrue(serif_stack.rstrip().endswith("serif"))
        self.assertNotIn("sans-serif", serif_stack)
        self.assertTrue(sans_stack.rstrip().endswith("sans-serif"))


class AccentParityTests(_StylesheetFixture):
    """Requirements 1.1, 1.2: the dark accent equals the light accent."""

    def test_dark_accent_equals_light_accent(self):
        light_accent = _resolve(self.light, self.light["--color-accent"])
        dark_accent = _resolve(self.dark, self.dark["--color-accent"])
        self.assertEqual(
            _to_rgba(light_accent),
            _to_rgba(dark_accent),
            "Dark theme accent must be identical to the light theme accent",
        )
        # And it must not be redeclared to a different value in the dark block.
        if "--color-accent" in self.dark_overrides:
            self.assertEqual(
                _to_rgba(self.dark_overrides["--color-accent"]),
                _to_rgba(light_accent),
            )

    def test_accent_is_warm_non_purple_non_blue(self):
        r, g, b, _ = _to_rgba(_resolve(self.light, self.light["--color-accent"]))
        # Warm accent: red dominates, blue is the weakest channel (rules out
        # blue and purple hues).
        self.assertGreater(r, b, "Accent must be warm (red > blue)")
        self.assertGreater(g, b, "Accent must be warm (green > blue), ruling out purple/blue")


# ---------------------------------------------------------------------------
# WCAG contrast matrix (Requirement 1.8)
# ---------------------------------------------------------------------------

class ContrastMatrixTests(_StylesheetFixture):
    """Requirement 1.8: every documented resting text/bg token pair meets WCAG
    AA in both themes (4.5:1 body text, 3:1 large text / UI elements)."""

    BODY_THRESHOLD = 4.5
    UI_THRESHOLD = 3.0

    # (label, fg_token, bg_token) — opaque reading-text pairs (4.5:1).
    BODY_PAIRS = [
        ("primary text on background", "--color-text-primary", "--color-background"),
        ("primary text on surface", "--color-text-primary", "--color-surface"),
        ("primary text on muted surface", "--color-text-primary", "--color-surface-muted"),
        ("secondary text on background", "--color-text-secondary", "--color-background"),
        ("secondary text on surface", "--color-text-secondary", "--color-surface"),
        ("secondary text on muted surface", "--color-text-secondary", "--color-surface-muted"),
    ]

    # (label, fg_token, bg_token, composite_base_token) — UI / accent / large
    # text pairs (3:1). Where the bg token is a translucent tint it is
    # composited over the given opaque base.
    UI_PAIRS = [
        ("accent-contrast on accent (primary button)",
         "--color-accent-contrast", "--color-accent", None),
        ("accent link/tag on background", "--color-accent", "--color-background", None),
        ("accent link/tag on surface", "--color-accent", "--color-surface", None),
        ("success text on success tint", "--color-success", "--color-success-tint", "--color-surface"),
        ("warning text on warning tint", "--color-warning", "--color-warning-tint", "--color-surface"),
        ("danger text on danger tint", "--color-danger", "--color-danger-tint", "--color-surface"),
    ]

    def _themes(self):
        return (("light", self.light), ("dark", self.dark))

    def test_body_text_pairs_meet_4_5(self):
        for theme_name, tokens in self._themes():
            for label, fg, bg in self.BODY_PAIRS:
                fg_c = _resolve(tokens, tokens[fg])
                bg_c = _resolve(tokens, tokens[bg])
                ratio = contrast_ratio(fg_c, bg_c, base=bg_c)
                self.assertGreaterEqual(
                    round(ratio, 2),
                    self.BODY_THRESHOLD,
                    f"[{theme_name}] {label}: {fg_c} on {bg_c} = {ratio:.2f}:1 "
                    f"(< {self.BODY_THRESHOLD}:1 body-text minimum)",
                )

    def test_ui_and_large_text_pairs_meet_3(self):
        for theme_name, tokens in self._themes():
            for label, fg, bg, base_tok in self.UI_PAIRS:
                fg_c = _resolve(tokens, tokens[fg])
                bg_raw = _resolve(tokens, tokens[bg])
                base_c = (
                    _resolve(tokens, tokens[base_tok]) if base_tok else bg_raw
                )
                ratio = contrast_ratio(fg_c, bg_raw, base=base_c)
                self.assertGreaterEqual(
                    round(ratio, 2),
                    self.UI_THRESHOLD,
                    f"[{theme_name}] {label}: {fg_c} on {bg_raw} (over {base_c}) "
                    f"= {ratio:.2f}:1 (< {self.UI_THRESHOLD}:1 UI/large-text minimum)",
                )


# ---------------------------------------------------------------------------
# Template scan (Requirements 1.7, 4.3, 4.5)
# ---------------------------------------------------------------------------

class TemplateAssetAuditTests(SimpleTestCase):
    """Scan HTML templates for decorative assets, gradients/backdrop-filter in
    inline styles, and scroll-triggered animation libraries."""

    SCROLL_ANIMATION_MARKERS = [
        "data-aos",            # Animate On Scroll
        "aos-init",
        "animate-on-scroll",
        "scrollreveal",
        "wow.js",
        "sal.js",
        "data-sr",
    ]
    INLINE_STYLE_FORBIDDEN = [
        "backdrop-filter",
        "linear-gradient",
        "radial-gradient",
        "conic-gradient",
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.templates = list(TEMPLATES_DIR.rglob("*.html"))

    def test_templates_present(self):
        self.assertTrue(self.templates, "Expected HTML templates to scan")

    def test_no_scroll_animation_libraries(self):
        for path in self.templates:
            text = path.read_text(encoding="utf-8").lower()
            for marker in self.SCROLL_ANIMATION_MARKERS:
                self.assertNotIn(
                    marker,
                    text,
                    f"{path.name} references scroll-animation marker {marker!r}; "
                    f"scroll-triggered content animation is forbidden "
                    f"(Requirements 4.3, 4.5)",
                )

    def test_no_inline_gradient_or_glass(self):
        for path in self.templates:
            text = path.read_text(encoding="utf-8").lower()
            for forbidden in self.INLINE_STYLE_FORBIDDEN:
                self.assertNotIn(
                    forbidden,
                    text,
                    f"{path.name} uses inline {forbidden!r}; flat fills only, "
                    f"no glassmorphism (Requirements 1.6, 1.7)",
                )
