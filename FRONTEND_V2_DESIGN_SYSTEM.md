# InkSpire Frontend V2 — Design System Specification

Status: documentation only. This document defines tokens and standards for the upcoming frontend rebuild. It does not implement CSS, does not modify templates, and is not itself a build artifact — it is the reference other design and implementation work should be checked against.

## Design principles

1. Editorial typography leads. Type hierarchy, not color or decoration, is the primary way structure and importance are communicated.
2. Content is the interface. Chrome (cards, borders, shadows) should recede; article text and imagery should stand out.
3. Restraint over decoration. No gradients, no glassmorphism, no oversized rounded corners, no decorative shapes, no motion for its own sake.
4. Consistent spacing over custom spacing. Every gap, margin, and padding value comes from the spacing scale — no one-off pixel values.
5. One component, one shape. A given UI idea (card, button, empty state, table) has exactly one visual implementation reused everywhere, not a redesign per page.
6. Accessible by default. Color contrast, focus states, and semantic markup are non-negotiable baseline requirements, not later polish.
7. Dashboard is a tool, not a showcase. Editorial/admin surfaces prioritize density, scanability, and fast task completion over visual flourish.
8. Public pages are a reading experience. Article and archive pages prioritize legibility, generous line length control, and calm pacing.
9. Motion is a hint, not a performance. Transitions (where used at all) communicate state change quickly and subtly — no bouncing, no fade-heavy choreography.
10. Design tokens are the contract. Colors, spacing, and type sizes are referenced by token name in implementation, never hardcoded inline.
11. Mobile is not an afterthought. Every component is specified with its mobile behavior, not adapted after the fact.
12. Nothing is added for its own sake. If a visual element doesn't support reading, comprehension, or task completion, it doesn't belong.

## 1. Typography scale

Base font size: `16px` (`1rem`). Line-height values are unitless ratios per common CSS practice.

| Token | Use case | Font size | Line height | Weight | Font family |
|---|---|---|---|---|---|
| `type-display` | Homepage hero headline, largest marketing-style headline | `clamp(2.5rem, 6vw, 4.5rem)` (40–72px) | 1.05 | 700 (Bold) | Serif (editorial display face) |
| `type-page-title` | Page-level H1 (archive headers, dashboard page headers, account pages) | `clamp(2rem, 4vw, 2.75rem)` (32–44px) | 1.15 | 700 (Bold) | Serif |
| `type-section-title` | H2 section headings within a page ("Featured posts", "Comments", dashboard panel headers) | `1.5rem` (24px) | 1.25 | 700 (Bold) | Serif |
| `type-article-title` | Article H1 on the article detail page | `clamp(2.25rem, 5vw, 3.5rem)` (36–56px) | 1.1 | 700 (Bold) | Serif |
| `type-subhead` | Card titles (H3), author names as headings, dashboard stat labels | `1.15rem` (18.4px) | 1.35 | 700 (Bold) | Serif or Sans (component-dependent, see component spec) |
| `type-body` | Default paragraph text, form labels' associated input text, dashboard table body | `1rem` (16px) | 1.6 | 400 (Regular) | Sans |
| `type-article-body` | Long-form article reading text specifically (wider line-height for extended reading) | `1.125rem` (18px) | 1.75 | 400 (Regular) | Serif (matches editorial reading convention) |
| `type-meta` | Small/meta text — timestamps, byline secondary text, view counts, badge labels | `0.875rem` (14px) | 1.5 | 500 (Medium) | Sans |
| `type-caption` | Captions, helper text under form fields, image captions, footnotes | `0.8125rem` (13px) | 1.5 | 400 (Regular) | Sans |
| `type-eyebrow` | Small uppercase label above titles ("Featured story", "Category") | `0.75rem` (12px) | 1.4 | 700 (Bold), letter-spacing `0.08em`, uppercase | Sans |

Rules:
- Exactly two font families system-wide: one serif (headings, article body) and one sans (UI text, meta, forms, dashboard).
- No more than 3 font weights total: 400, 500, 700. No italics except inline emphasis within article body copy.
- Article body text max width is governed by the reading-width container (see §6), not by font size adjustments.

## 2. Spacing scale (4px base)

All spacing values are multiples of 4px. Components reference these tokens by name, never raw pixel values.

| Token | Value | Typical use |
|---|---|---|
| `space-1` | 4px | Icon-to-text gaps, tight inline spacing |
| `space-2` | 8px | Form field internal spacing, small gaps between meta items |
| `space-3` | 12px | Button internal padding (vertical), compact card padding |
| `space-4` | 16px | Standard component padding, gap between form fields |
| `space-5` | 20px | Gap between related inline elements (badge groups, action button rows) |
| `space-6` | 24px | Card padding, standard gap between stacked components |
| `space-8` | 32px | Section-internal spacing, gap between a heading and its content |
| `space-10` | 40px | Gap between major page sections |
| `space-12` | 48px | Large section separation on desktop |
| `space-16` | 64px | Page-top spacing, hero section padding |
| `space-20` | 80px | Maximum section spacing, used sparingly on wide desktop layouts |

Rule: components must not introduce spacing values outside this scale. If a gap "almost" fits an existing token, it should be redesigned to fit the token, not given a new custom value.

## 3. Color palette

An editorial, restrained, mostly neutral palette with one accent color. All colors must meet WCAG AA contrast (4.5:1 for body text, 3:1 for large text/UI) against their intended background.

| Token | Hex (reference) | Use case |
|---|---|---|
| `color-background` | `#FAFAF8` | Page background (warm off-white, not pure white — reduces glare for long-form reading) |
| `color-surface` | `#FFFFFF` | Cards, panels, form containers, dashboard tables |
| `color-surface-muted` | `#F2F1ED` | Secondary surfaces — empty states, disabled inputs, subtle section backgrounds |
| `color-text-primary` | `#1A1A18` | Headings, body text, primary content |
| `color-text-secondary` | `#5C5A54` | Meta text, captions, secondary descriptions, placeholder text |
| `color-border` | `#E3E1DA` | Card borders, table borders, input borders, dividers |
| `color-accent` | `#B5651D` | Links, primary buttons, active states, focus rings (warm editorial amber/rust — replaces the current bright yellow-warning accent with something more restrained) |
| `color-accent-hover` | `#8F4F16` | Hover/active state of accent-colored elements |
| `color-success` | `#2E6B3E` | Success alerts, "published" status pill, confirmation states |
| `color-warning` | `#8A6D1B` | Warning alerts, "draft" status pill — muted gold rather than bright yellow |
| `color-danger` | `#A3342A` | Destructive actions, error alerts, "hidden"/error status pills |

Rules:
- No gradients anywhere in the palette usage — every fill is a flat, single color.
- The accent color is used sparingly: primary CTAs, links, active nav/tab states, and focus rings only. It should never be used as a large background fill.
- Status pills (published/draft/hidden) each pair a muted background tint (10–15% opacity of the corresponding token) with the full-strength token as text color, not the current bright badge-style fills.

## 4. Border-radius tokens

Minimal rounding. No pill-shaped cards, no heavily rounded panels.

| Token | Value | Use case |
|---|---|---|
| `radius-none` | 0px | Tables, dividers, full-bleed images |
| `radius-sm` | 4px | Buttons, form inputs, small tags/badges |
| `radius-md` | 6px | Cards, panels, modals |
| `radius-full` | 999px | Reserved only for true circular elements (avatars, single-icon circular buttons) — never used for cards or badges |

Rule: `radius-md` (6px) is the maximum rounding for any rectangular container. Nothing in the system should look like a rounded "bubble."

## 5. Shadow tokens

Very subtle, used only to establish stacking order — never for decoration.

| Token | Value | Use case |
|---|---|---|
| `shadow-none` | none | Default state for most flat content (article body, plain sections) |
| `shadow-xs` | `0 1px 2px rgba(20, 20, 18, 0.05)` | Cards at rest, table rows on hover |
| `shadow-sm` | `0 2px 6px rgba(20, 20, 18, 0.08)` | Dropdowns, popovers, sticky editor action bar |
| `shadow-focus` | `0 0 0 3px rgba(181, 101, 29, 0.25)` | Focus ring for interactive elements (derived from `color-accent`) |

Rule: no shadow may exceed `shadow-sm` in blur/spread. Modal/dialog surfaces use `shadow-sm` at most, not a heavy drop shadow.

## 6. Container widths

| Token | Value | Use case |
|---|---|---|
| `container-reading` | 680px | Article body text column — optimized line length for long-form reading |
| `container-standard` | 960px | Standard page content (forms, account pages, single-column dashboard panels) |
| `container-wide` | 1200px | Archive/listing grids, homepage sections, article page including sidebar |
| `container-dashboard` | 1320px | Dashboard layout (sidebar + main content), wider to accommodate tables |

Rule: article body text never exceeds `container-reading` width even inside a wider page container — the article column itself is capped independently of the outer page width.

## 7. Responsive breakpoints

| Token | Min-width | Target |
|---|---|---|
| `bp-sm` | 480px | Large phones |
| `bp-md` | 768px | Tablets, dashboard sidebar collapses below this |
| `bp-lg` | 1024px | Small laptops, standard desktop layout begins |
| `bp-xl` | 1280px | Wide desktop, dashboard sidebar + full table width comfortable |

Rule: mobile-first. Base styles target the smallest viewport; each breakpoint adds layout complexity (multi-column grids, sidebars), never removes core functionality.

## 8. Button variants

All buttons share: `radius-sm`, `type-body` at `0.9375rem` (15px) for standard size, 700 weight, no shadow at rest, `shadow-focus` on keyboard focus, no scale/transform animation on hover (color/border change only, ≤150ms transition).

| Variant | Background | Text color | Border | Hover state |
|---|---|---|---|---|
| Primary | `color-accent` | `#FFFFFF` | none | Background → `color-accent-hover` |
| Secondary | `color-surface` | `color-text-primary` | 1px `color-border` | Border → `color-accent`, text unchanged |
| Ghost | transparent | `color-text-primary` | none | Background → `color-surface-muted` |
| Danger | `color-danger` | `#FFFFFF` | none | Background darkens ~15% (fixed reference value, not a token — define exact hex at implementation time) |

Sizing:

| Size | Padding (vertical / horizontal) | Font size |
|---|---|---|
| Standard | `space-3` / `space-6` (12px / 24px) | 15px |
| Small | `space-2` / `space-4` (8px / 16px) | 13px (`type-caption` size) |

Rule: icon-only buttons (dashboard row actions) must always carry an `aria-label` regardless of size, and must meet a minimum 32×32px hit area even if the visual button is smaller — this addresses a known accessibility gap in the current dashboard.

## 9. Form control standards

| Property | Value |
|---|---|
| Input height (standard) | 40px |
| Input height (textarea) | minimum 96px, user-resizable vertically only |
| Padding | `space-2` vertical / `space-3` horizontal (8px / 12px) |
| Border (default) | 1px `color-border` |
| Border (hover) | 1px, color unchanged (no hover state on inputs — only focus signals interactivity) |
| Border (focus) | 1px `color-accent` + `shadow-focus` ring, outline removed only when the ring fully replaces it |
| Border (error) | 1px `color-danger`, no ring color change (ring stays neutral/absent to avoid conflicting signals with focus) |
| Background | `color-surface`; `color-surface-muted` when disabled |
| Label | `type-body` at 14px, weight 700, positioned above the input with `space-1` gap |
| Helper/caption text | `type-caption`, `color-text-secondary`, positioned below the input with `space-1` gap |
| Error text | `type-caption`, `color-danger`, replaces helper text position when present, prefixed with a text label ("Error:") readable by screen readers even if visually implied by color alone |

Rules:
- Every form field's error state must be conveyed through text, not color alone (color-blind and screen-reader accessibility).
- Placeholder text must never be the only label for a field — every input has a persistent visible `<label>`.
- File inputs (image uploads) use the same border/focus/error treatment as text inputs, with an additional inline preview treated as a separate sub-component, not baked into the input itself.

## 10. Table standards (dashboard)

| Property | Value |
|---|---|
| Row height | minimum 48px (comfortable click/tap target for row actions) |
| Header background | `color-surface-muted` |
| Header text | `type-meta` size, weight 700, uppercase, letter-spacing `0.04em`, `color-text-secondary` |
| Body text | `type-body` |
| Row border | 1px `color-border`, bottom only (no vertical column borders) |
| Row hover | background → `color-surface-muted` (desktop only; no hover state needed on touch) |
| Zebra striping | not used — rely on row borders and hover state for scanability instead |
| Status indicator | status pill component (muted background tint + full-strength text color per §3), never a raw colored table cell background |
| Action buttons | Ghost or Secondary small buttons, right-aligned in a dedicated actions column, each with `aria-label` |
| Empty state | table is replaced entirely by the empty-state component (§11), not rendered as a table with a single "no results" row |
| Pagination | shared pagination component (same one used on public archive pages — see migration map), not a dashboard-specific variant |
| Responsive behavior | horizontal scroll container below `bp-lg`; columns are not hidden/dropped, to avoid silently hiding data |

## 11. Empty-state standards

A single empty-state component used everywhere (public archive pages, dashboard tables, comment sections, search results).

| Element | Specification |
|---|---|
| Container | `color-surface` background, 1px `color-border`, `radius-md`, padding `space-8` |
| Icon/illustration | optional, single-color line icon only if used — no decorative illustrations, no stock imagery |
| Heading | `type-subhead`, `color-text-primary` |
| Description | `type-body`, `color-text-secondary`, max width ~40 characters per line for readability |
| Primary action | Primary or Secondary button, present when a clear next action exists (e.g., "Create post", "Back to homepage") |
| Alignment | center-aligned text and action within the container |

Rule: every list, table, or grid in the system must define its own empty-state copy — a generic "No results" is not acceptable; copy should name what's missing (e.g., "No comments yet", "No published posts yet").

## 12. Alerts and status feedback

For completeness alongside forms/tables (referenced by §9 and §10):

| Type | Background | Border | Text | Icon color |
|---|---|---|---|---|
| Success | tint of `color-success` (10%) | 1px `color-success` | `color-text-primary` | `color-success` |
| Warning | tint of `color-warning` (10%) | 1px `color-warning` | `color-text-primary` | `color-warning` |
| Danger/error | tint of `color-danger` (10%) | 1px `color-danger` | `color-text-primary` | `color-danger` |
| Info (neutral) | `color-surface-muted` | 1px `color-border` | `color-text-primary` | `color-text-secondary` |

Rule: alert text color is always `color-text-primary`, never the status color itself, to preserve contrast and readability — only the border, background tint, and icon carry the status color.

## 13. Non-negotiable constraints (from project brief)

- No gradients anywhere (backgrounds, buttons, hero sections, badges).
- No glassmorphism (no backdrop blur, no translucent frosted panels).
- No oversized rounded cards — 6px (`radius-md`) is the ceiling for rectangular containers.
- No decorative shapes (no floating blobs, abstract SVG backgrounds, or purely ornamental graphics).
- No unnecessary animation — transitions are limited to ≤150ms color/border changes on interactive elements; no entrance animations, parallax, or scroll-triggered effects.
- No more than one accent color system-wide.
- No component may introduce a spacing, color, radius, or shadow value outside the tokens defined in this document.
