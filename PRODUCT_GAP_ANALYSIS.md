# InkSpire Product Gap Analysis

Scope: portfolio-grade publishing platform, benchmarked against the practical core of Medium, Ghost, Substack, Hashnode, and WordPress. Security baseline: commit `7c532ba`; article redesign: `1280993`.

## Priority key

| Priority | Meaning |
|---|---|
| P0 | Must fix before presenting publicly |
| P1 | Important professional capability |
| P2 | Useful advanced polish |
| Avoid | Poor return for this portfolio scope |

## 1. Current pages

| Area | Pages/endpoints |
|---|---|
| Public | Home, article detail, category archive, search, about, contact, RSS, sitemap, 404 |
| Account | Register, login/logout, profile, edit profile, change password, bookmarks |
| Editorial | Dashboard overview; post/category list, add, edit, delete |
| Administration | User list/add/edit/delete; contact inbox/detail/delete; Django admin |
| Engagement | Comment/reply/edit/delete and like/bookmark actions embedded in articles |

## 2–4. Missing, weak, and incomplete pages/features

| Priority | Gap | Assessment |
|---|---|---|
| P0 | Home, archives, search | Visually dated/inconsistent; weak cards, hierarchy, responsive behavior, and empty states |
| P0 | Base layout | Bootstrap 4/5 mismatch, no mobile navigation, placeholder links/newsletter, inconsistent components |
| P0 | Password recovery | Missing forgot/reset-password pages and email flow |
| P0 | Dashboard/editor | CRUD presentation; no filtering, pagination, clear state actions, preview, or polished validation |
| P0 | SEO head architecture | Fixed titles; article metadata is emitted in body; no canonical or structured data |
| P1 | Public author page | Profile exists only for its owner; author byline has no public destination |
| P1 | Category landing | ID-based URL and basic post list; missing category slug/description |
| P1 | Editorial preview | Drafts cannot be reviewed safely in the public layout |
| P1 | Comment moderation | Replies exist, but no approval, spam handling, reporting, or moderation queue |
| P1 | Error/system pages | Only 404 exists; add consistent 403/500 and form failure states |
| P2 | Tag archive | Useful after category and search quality are complete |
| P2 | Subscriber preferences | Only relevant after a real newsletter is implemented |

Existing but incomplete: draft/publish state, rich editor, profiles, comments, likes, bookmarks, view count, related posts, contact inbox, RSS, sitemap, search, and sharing.

## 5–6. Feature scope

### Practical missing features

| Priority | Reader | Author/editor |
|---|---|---|
| P0 | Password reset, responsive navigation, reliable search/pagination, accessible feedback | Stable URLs, preview, dashboard filters/pagination, image validation/alt text |
| P1 | Public author pages, better discovery, comment moderation feedback | `published_at`, schedule/unpublish, revisions, autosave, moderation queue |
| P2 | Tags, reading progress, copy-link, theme preference | Media library, reusable drafts, basic post analytics |

### Unnecessary now

| Avoid | Reason |
|---|---|
| Paid subscriptions/paywall | Billing, tax, entitlement, and support complexity |
| Social graph, DMs, communities | Changes the product from publishing to a social network |
| Mobile app or SPA/API rewrite | No portfolio value proportional to cost |
| Multi-tenant publications/custom domains | Large authorization and deployment surface |
| AI writing, recommendation ML, real-time collaboration | Distracts from core editorial quality |
| External search cluster/data warehouse | PostgreSQL search and simple aggregates are sufficient |

## 7. Backend refactoring gaps

| Priority | Area | Required direction |
|---|---|---|
| P0 | Query behavior | Central published-post queryset; `select_related`/annotations; dashboard pagination |
| P0 | Input handling | Django forms for comments/contact; consistent validation and messages |
| P0 | Configuration | Reconcile Django version/docs; environment-driven settings; production logging/media policy |
| P0 | Tests | Add public visibility, auth, forms, SEO, query, and editor workflow coverage |
| P1 | Publishing rules | Centralize slug generation, publication transitions, preview authorization, profile creation |
| P1 | App boundaries | Move account behavior from project package; namespace URLs; remove duplicate contact route |
| P1 | Data semantics | Add stable slugs/redirects and `published_at` only in a planned migration phase |
| P1 | Counters/search | Atomic or analytics-backed views; PostgreSQL full-text search |
| P2 | Async work | Background email/image work only when those workflows exist |

## 8. Frontend/template cleanup

- **P0:** Standardize one Bootstrap version and load required JavaScript.
- **P0:** Add reusable head, alerts, pagination, form errors, cards, empty states, and destructive-action components.
- **P0:** Remove inline styles, duplicate layout markup, placeholder links, and fake newsletter UI.
- **P0:** Fix accessibility: labels/IDs, icon names, focus states, contrast, keyboard navigation.
- **P1:** Split article/sidebar/comment partials and use consistent naming/formatting.
- **P1:** Add responsive images and deliberate missing-image fallbacks.

## 9. SEO gaps

| Priority | Missing/weak item |
|---|---|
| P0 | Unique page titles/descriptions and extensible `<head>` blocks |
| P0 | Canonical URLs; Open Graph URL/type; Twitter Cards |
| P0 | Article, author, publisher, and breadcrumb JSON-LD |
| P0 | `robots.txt`; noindex policy for search/account/dashboard/drafts |
| P1 | Stable category/post slugs and permanent old-slug redirects |
| P1 | Category/author sitemap coverage and production absolute-URL validation |
| P1 | Explicit social image/alt text and `published_at`/modified semantics |

## 10–14. Audience-specific gaps

| Audience | P0 | P1 | P2 |
|---|---|---|---|
| Reader | Mobile nav, password reset, search quality, accessibility | Author pages, discovery, moderated comments | Tags, reading progress, theme preference |
| Writer | Stable slug, preview, usable editor/dashboard | Autosave, revisions, schedule/unpublish, media metadata | Draft organization, writing stats |
| Editor/admin | Filters/pagination, clear permissions, form feedback | Moderation queue, editorial states, audit trail | Bulk actions, content calendar |
| Subscriber | Remove fake signup until real | Confirmed signup, unsubscribe, consent, delivery integration | Preferences, digest frequency, import/export |
| Analytics | Accurate views and basic query efficiency | Per-post views/likes/comments/bookmarks with date range | Referrers, reading completion, subscriber conversion |

Analytics should be privacy-conscious and portfolio-sized; do not build a bespoke event warehouse.

## 15. Build order

| Order | Priority | Deliverable |
|---|---|---|
| 1 | P0 | Quality baseline: dependency/settings consistency, broader tests, Bootstrap alignment, shared components |
| 2 | P0 | Public credibility: base layout, home/archive/search, auth recovery, accessibility, SEO head foundation |
| 3 | P0/P1 | Publishing correctness: stable URLs/redirects, `published_at`, preview, dashboard/editor usability |
| 4 | P1 | Professional workflow: revisions/autosave, scheduling, media metadata, comment moderation |
| 5 | P1 | Discovery/operations: author pages, PostgreSQL search, query tuning, production media/monitoring |
| 6 | P2 | Portfolio polish: tags, basic analytics, optional newsletter, reading preferences |

## 16. Recommended MVP

- Secure role-based dashboard and Django admin.
- Professional responsive base, home, archive/search, article, auth, and dashboard/editor pages.
- Registration/login/logout/password reset/profile.
- Draft/publish, preview, stable slug, featured image with alt text, category, rich text.
- Search, pagination, author page, comments with moderation, likes, bookmarks, RSS.
- Canonical metadata, social cards, JSON-LD, sitemap, robots rules.
- PostgreSQL-ready queries, reliable tests, deployment docs, monitoring/error logging.

## 17. Recommended advanced set

- Revisions/autosave, scheduled publishing, media library, tags.
- Basic per-post analytics and privacy-conscious referrer summaries.
- Confirmed newsletter subscriptions with unsubscribe/preferences.
- Reading progress/theme preference and improved discovery.

## 18. Risky changes to avoid now

- Do not rename `Blog`, replace the user model, or restructure apps during page redesign.
- Do not change public URLs before redirect history exists.
- Do not weaken POST/CSRF/permission boundaries or re-enable raw source editing.
- Do not combine a framework upgrade, schema redesign, and UI redesign in one release.
- Do not introduce a SPA, microservices, paid subscriptions, multi-tenancy, or real-time systems.
- Do not add newsletter/analytics UI without functional privacy, consent, and data flows.
