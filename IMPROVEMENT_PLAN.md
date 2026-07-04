# InkSpire Improvement Plan

## Product weaknesses

- Publishing is limited to draft/published; slugs change on edit and there is no preview, revision, scheduling, or moderation workflow.
- The custom dashboard is CRUD-oriented, lacks filters/pagination, and overlaps Django admin.
- Public navigation, article typography, forms, empty states, and mobile behavior are inconsistent.
- Bootstrap 4 assets are mixed with Bootstrap 5 markup; interactive Bootstrap JavaScript is absent.
- Search is basic, view counts are inaccurate under concurrency, and automated coverage is security-focused only.
- Production configuration, media handling, database strategy, monitoring, and deployment documentation need consolidation.

## UI redesign order

1. Base layout: responsive header/navigation, search, messages, footer, accessibility, and one Bootstrap version.
2. Article detail: reading layout, metadata, media, actions, comments, and related posts.
3. Home and category/search listings: consistent cards, hierarchy, pagination, and empty states.
4. Editorial dashboard and post editor: role-aware navigation, clear actions, filters, confirmations, and form feedback.
5. Authentication, profile, bookmarks, contact, and error pages.

Define design tokens and reusable template components before redesigning individual pages. Preserve existing URL names and secured POST forms during visual work.

## Backend cleanup

- Centralize dashboard authorization helpers and add permission tests for every management route.
- Move account behavior out of project-level views into a focused app when migration risk is acceptable.
- Add forms for comments/contact input and remove raw POST parsing.
- Centralize published-post queries, slug creation, and profile provisioning.
- Introduce stable slugs and redirect history before changing public URLs.
- Separate `published_at` from creation/update timestamps and define author/category deletion policy.
- Add pagination and query optimization to dashboard lists.
- Reconcile documented and pinned Django versions; consolidate environment settings and logging.
- Stop tracking runtime database/uploads and document local seed data separately.

## SEO

- Add template head blocks with unique title, description, canonical URL, Open Graph, and Twitter metadata.
- Move article metadata from the body into `<head>` and add Article/Breadcrumb JSON-LD.
- Add category slugs, stable post URLs, and permanent redirects for previous slugs.
- Add `robots.txt`; define indexing rules for search, pagination, drafts, and account pages.
- Extend sitemap coverage to categories and validate absolute production URLs.
- Add explicit image alt text/social image fields later; optimize preview dimensions.

## Performance

- Use `select_related`, `prefetch_related`, annotations, and indexed publication/category/date queries.
- Make view counting atomic, then replace it with bot/repeat-aware analytics if needed.
- Cache navigation categories, home sections, feeds, and sitemap where measurements justify it.
- Move production data to PostgreSQL and media to object storage/CDN.
- Generate responsive image variants, compress uploads, and lazy-load noncritical images.
- Upgrade search to PostgreSQL full-text search before considering an external engine.
- Measure query counts and response times in tests before adding broad caching.

## Features for later

- Preview, autosave, revisions, scheduled publishing, archive/unpublish, and editorial review.
- Media library with alt text, captions, credits, cropping, and reuse.
- Comment moderation, reporting, spam controls, and notifications.
- Public author pages, tags, reading history, and improved bookmark organization.
- Newsletter, subscriptions, analytics, and social features only after core publishing is mature.

## Safe development phases

1. **Quality baseline:** broaden tests, reconcile dependencies/settings, add CI, document roles, and preserve the security contract.
2. **Data correctness:** publication timestamps, stable slugs/redirects, constraints, deletion policy, and migrations with rollback plans.
3. **Backend reliability:** forms, query services/managers, pagination, validation, search, and performance tests.
4. **SEO foundation:** head architecture, canonical metadata, structured data, robots, sitemap, and redirect verification.
5. **Design system:** unify Bootstrap, accessibility standards, tokens, components, and responsive base layout.
6. **Public redesign:** article first, then home/archive/search, followed by secondary pages.
7. **Editorial workflow:** focused dashboard/editor, preview, revisions, scheduling, media, and moderation.
8. **Production scale:** PostgreSQL, object storage, caching, background jobs, monitoring, backups, and load testing.
9. **Growth features:** newsletter, notifications, analytics, discovery, and social features based on evidence.

Each phase should ship with migrations reviewed, permission regressions tested, accessibility checked, and deployment rollback documented.

## Do not change yet

- Do not rename models or replace Django's user model during UI work.
- Do not rewrite the project, introduce an API/SPA, or split into services.
- Do not weaken dashboard permissions, CSRF-protected POST actions, or rich-text trust boundaries.
- Do not change public URLs until redirect support exists.
- Do not add tags, follows, newsletters, notifications, or complex analytics before phases 1–7.
- Do not optimize without measurements or add infrastructure that the current traffic does not require.
