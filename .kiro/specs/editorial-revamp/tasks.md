# Implementation Plan: Editorial Revamp

## Overview

This plan implements three coordinated changes to the InkSpire Django platform: the Modern Editorial redesign with first-class dark mode, Follow Authors, and Scheduled Publishing. The implementation language is **Python/Django** (as established by the design), and property-based tests use **Hypothesis** with `hypothesis.extra.django`.

The three concerns are largely independent. Scheduling is built first because it changes the single `published()` choke point that every public surface depends on. Follow adds a model, views, and profile changes. The redesign is a presentation-layer concern layered on top. Each property test is annotated with its design property number and the requirement clause it validates, and every property test uses `max_examples>=100` and the tag `# Feature: editorial-revamp, Property {n}: ...`.

## Tasks

- [ ] 1. Scheduling: read-time publication filter (data layer)
  - [x] 1.1 Redefine `Blog.QuerySet.published()` and add `scheduled()` helper
    - In `blogs/models.py`, change `published()` to filter `status='published'` AND (`published_at__isnull=True` OR `published_at__lte=timezone.now()`)
    - Add `scheduled()` returning `status='published'` with `published_at__gt=timezone.now()`
    - Confirm `Blog.save()` still auto-sets `published_at` only when publishing and not already set (no change to immediate-publish path)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 14.1_

  - [x] 1.2 Write property test for read-time publication visibility
    - **Property 14: Publication visibility is a read-time comparison**
    - Parametrize/inject `now` (freezegun or injected clock); exercise boundary `published_at == now` and `now ± ε`; assert a future-dated row is excluded and becomes included at a later evaluation time with no intervening write
    - **Validates: Requirements 10.2, 10.3, 11.1**

  - [x] 1.3 Write property test for direct-publish publication-time recording
    - **Property 15: Direct publish records publication time once**
    - Assert save sets `published_at` when publishing with none set, and never overwrites an existing `published_at`
    - **Validates: Requirements 10.5**

- [x] 2. Scheduling: detail-view preview and view-count gate
  - [x] 2.1 Extend `BlogDetail` visibility and preview logic
    - In `blogs/views.py`, fetch the raw `Blog`, compute `is_public` (status published AND `published_at` null or `<= now`), set `is_preview = not is_public`
    - Compute `can_preview` = authenticated AND (author OR staff OR `blogs.change_blog`); raise `Http404` when `is_preview and not can_preview`
    - Keep view-count increment gated on `not is_preview`; leave existing `select_related`/comment prefetch untouched
    - _Requirements: 11.5, 11.6, 13.1, 13.2, 13.3_

  - [x] 2.2 Write property test for permission-gated preview access
    - **Property 16: Preview access to non-public posts is permission-gated**
    - Generate drafts and future-dated scheduled posts across the viewer permission matrix (anonymous / reader / author / staff / `change_blog`); assert viewable iff author/staff/perm, else 404
    - **Validates: Requirements 11.5, 11.6, 13.3**

  - [x] 2.3 Write property test for view-count increment behavior
    - **Property 19: View count increments once per non-preview read**
    - Assert N non-preview requests raise view count by exactly N; any authorized preview (draft or scheduled) raises it by 0, regardless of scheduling
    - **Validates: Requirements 13.1**

  - [x] 2.4 Write query-count regression tests for listing/detail views
    - Use `assertNumQueries` to hold query counts constant as row counts grow (no N+1 from scheduling filter)
    - _Requirements: 13.2_

- [~] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Scheduling: dashboard controls
  - [x] 4.1 Add publication-time control and validation to `BlogForm`
    - In `dashboard/forms.py`, bind a `publication_time` control (datetime-local widget) to the model's `published_at`
    - Reject a past Publication_Time for a not-yet-published post with a validation message naming the future-time requirement
    - When Publication_Time is cleared without status published, normalize save to `draft`
    - Preserve existing image-upload validation and sanitizer mixin
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 13.5_

  - [x] 4.2 Write property test for past-time rejection
    - **Property 17: Past publication times are rejected before publish**
    - Assert form invalid with future-time message for any past time on a not-yet-published post; form accepts any future time
    - **Validates: Requirements 12.3**

  - [x] 4.3 Write unit test for cleared-schedule-to-draft normalization
    - Assert clearing publication time without publishing saves as draft
    - _Requirements: 12.4_

  - [x] 4.4 Distinguish scheduled posts in dashboard post listing
    - In `templates/dashboard/posts.html`, classify each row as draft / scheduled / published using `scheduled()` semantics; show status pills and the Publication_Time for scheduled posts
    - _Requirements: 12.5_

  - [x] 4.5 Write property test for dashboard listing classification
    - **Property 18: Dashboard listing classifies each post by its true state**
    - Assert each post is labeled draft / scheduled / published matching its actual state and that scheduled rows show their Publication_Time
    - **Validates: Requirements 12.5**

  - [x] 4.6 Write example tests for sitemap and RSS scheduled exclusion
    - Assert `BlogSitemap` and `LatestPostsFeed` exclude scheduled posts (1-2 representative examples each)
    - _Requirements: 11.2, 11.3_

- [~] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Follow: data model and migration
  - [x] 6.1 Create the `Follow` model
    - In `blogs/models.py`, add `Follow` with `follower`/`followed` FKs to `User` (`on_delete=CASCADE`, related names `following`/`followers`) and `created_at`
    - Add `UniqueConstraint(follower, followed)`, `CheckConstraint(~Q(follower=F('followed')))`, and indexes on `(follower, followed)` and `(followed)`
    - Add a `clean()`/application-level guard for friendly self-follow rejection
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 14.3_

  - [x] 6.2 Generate and apply the Follow migration
    - Run `makemigrations blogs` and apply; confirm constraints/indexes are created
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 6.3 Write property test for unique idempotent following
    - **Property 5: Following is unique and idempotent**
    - Assert following a distinct pair one or more times yields exactly one Follow record
    - **Validates: Requirements 6.2, 7.3**

  - [x] 6.4 Write property test for self-follow rejection
    - **Property 6: Self-follow is rejected**
    - Assert attempting to follow oneself creates no record and is rejected
    - **Validates: Requirements 6.3**

  - [x] 6.5 Write property test for cascade deletion of follow edges
    - **Property 7: Deleting a User removes all Follow edges touching them**
    - Assert no Follow record referencing a deleted User remains as follower or followed
    - **Validates: Requirements 6.4**

- [ ] 7. Follow: follow / unfollow / following-feed views and URLs
  - [x] 7.1 Implement `follow_author` and `unfollow_author` views
    - Add POST-only, `@login_required` views in `blogs/views.py`; use `get_or_create` for follow (idempotent), guard self-follow, catch `IntegrityError` as no-op; delete on unfollow; redirect back to profile
    - _Requirements: 6.3, 7.3, 7.4, 7.5_

  - [x] 7.2 Implement `following_feed` view
    - `@login_required` GET view: query `Blog.objects.published().filter(author_id__in=followed_ids)` with `select_related('author','category')`, ordered `-published_at, -created_at`; filter at query level
    - Render a named empty-state when the Reader follows no one / no posts exist
    - _Requirements: 8.1, 8.2, 8.4, 11.4, 13.2_

  - [x] 7.3 Wire follow/unfollow/following URLs
    - Add routes in `blogs/urls.py` for `follow_author`, `unfollow_author`, and `following_feed`
    - _Requirements: 7.3, 7.4, 8.1_

  - [x] 7.4 Write property test for follow/unfollow round-trip
    - **Property 9: Follow then unfollow round-trips to the original state**
    - Assert follow-then-unfollow leaves no Follow record between the pair
    - **Validates: Requirements 7.4**

  - [-] 7.5 Write property test for anonymous follow/unfollow no-op redirect
    - **Property 10: Anonymous follow/unfollow is a no-op redirect**
    - Assert an unauthenticated submission redirects to login and leaves Follow records unchanged
    - **Validates: Requirements 7.5**

  - [-] 7.6 Write property test for the Following Feed contents
    - **Property 12: Following Feed contains exactly published-due posts by followed authors**
    - Use a plain-Python model oracle; assert the feed equals exactly published-due posts by followed authors, newest first, excluding non-followed authors and unpublished/not-yet-due posts
    - **Validates: Requirements 8.1, 8.2, 11.4**

  - [-] 7.7 Write example tests for feed redirect and empty state
    - Assert anonymous request redirects to login (8.3); Reader following no one gets the named empty-state (8.4)
    - _Requirements: 8.3, 8.4_

- [~] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Author profile: follow state, follower count, and density branching
  - [x] 9.1 Add follow-state, follower-count, and density context to `AuthorProfile`
    - In `blogs/views.py`, compute `is_following` (authenticated, not self), `show_follow_control` (authenticated and not self), `follower_count` (Follow records where author is followed)
    - Compute `use_dashboard_density` = authenticated AND (staff OR `blogs.change_blog`) to select the density-optimized vs spacious presentation
    - Keep public post listing on `published()` so scheduled posts are excluded
    - _Requirements: 5.5, 5.6, 7.1, 7.2, 7.6, 9.1, 11.1_

  - [-] 9.2 Write property test for permission-based profile presentation
    - **Property 4: Author-profile presentation is selected by Editor permission**
    - Assert density presentation iff viewer holds Editor permission; every non-Editor (including Visitors) gets the spacious presentation
    - **Validates: Requirements 5.5, 5.6**

  - [-] 9.3 Write property test for displayed control reflecting follow state
    - **Property 8: Displayed control reflects follow state**
    - Assert unfollow control shown when a Follow record exists, follow control when it does not (authenticated viewer, other user)
    - **Validates: Requirements 7.1, 7.2**

  - [~] 9.4 Write property test for absence of control on own profile
    - **Property 11: No follow control on one's own profile**
    - Assert neither follow nor unfollow control appears on a User's own profile
    - **Validates: Requirements 7.6**

  - [~] 9.5 Write property test for follower-count accuracy
    - **Property 13: Follower count matches Follow records**
    - Assert displayed follower count equals the number of Follow records where the Author is followed
    - **Validates: Requirements 9.1**

- [x] 10. Design System: token stylesheet and dark theme
  - [x] 10.1 Create `static/css/editorial.css` token foundation
    - Declare light-theme `:root` tokens (off-white bg, near-black text, single warm non-purple/non-blue accent `#B5651D`, one serif + one sans family, `--radius-md: 6px` with no rectangle radius > 8px, hairline 1px borders, flat fills)
    - Declare `:root[data-theme="dark"]` overrides (near-black bg, warm off-white text, same accent value); avoid glassmorphism, decorative shapes, gradients outside image overlays
    - Add color transition on background/text for smooth theme change
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.5_

  - [x] 10.2 Add editorial component classes
    - Add `.hero`, `.post-grid--asymmetric`, `.post-card`, `.category-tag`, `.empty-state`, `.reading-progress`, `.data-table` (dashboard density), buttons, form controls, alerts, and status pills
    - _Requirements: 3.2, 3.3, 4.1, 4.2, 4.4, 5.4_

  - [x] 10.3 Write stylesheet audit and contrast tests
    - Scan `editorial.css`/templates for radius > 8px on rectangles, gradient/`backdrop-filter` outside image overlays, decorative assets, and disallowed load/scroll animations
    - Assert dark accent equals light accent and exactly one serif + one sans family are declared; compute WCAG contrast for every documented text/bg token pair in both themes (4.5:1 body, 3:1 large/UI)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 4.1, 4.2, 4.3, 4.5_

- [x] 11. Dark mode: theme scripts
  - [x] 11.1 Create `theme-init.js` (pre-paint theme resolver)
    - Origin-local synchronous `<head>` script: set `document.documentElement.dataset.theme` from cookie -> `prefers-color-scheme` -> light default; treat malformed cookie as "no preference"
    - _Requirements: 2.4, 14.2_

  - [x] 11.2 Create `theme-toggle.js` (toggle + persist + transition guard)
    - Deferred script wiring the Theme_Toggle: flip `data-theme` without navigation, write a long-lived `theme` cookie (`Max-Age`~1yr, `SameSite=Lax`, readable by JS)
    - Feature-detect transition support; if unsupported, decline to complete the change rather than flashing instantaneously
    - _Requirements: 2.2, 2.3, 2.5, 14.2_

  - [x] 11.3 Write behavior tests for theme init, persistence, and transition fallback
    - Test init branches with mocked `matchMedia` (dark/light/unsupported), persistence round-trip, toggle-without-navigation, and transition-unsupported fallback
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

  - [x] 11.4 Write property test for reading-progress computation
    - **Property 2: Reading-progress reflects scroll position**
    - Test the pure scroll->progress function over random offsets in `[0, max]`; assert value in `[0, 100]`, 0 at top, 100 at bottom, monotonic non-decreasing (pairwise on sorted offsets)
    - **Validates: Requirements 4.4**

- [x] 12. Templates: base layout redesign, theme toggle, and SEO preservation
  - [x] 12.1 Restyle `base.html` under the Design System
    - Apply `editorial.css`; include `theme-init.js` in `<head>` and `theme-toggle.js` deferred; add the Theme_Toggle control to the header
    - Preserve existing SEO blocks (canonical, Open Graph, Twitter Card, JSON-LD) with no functional regression; replace Bootstrap-utility layout with Design-System equivalents
    - _Requirements: 2.1, 5.1, 5.2, 5.3, 13.7_

  - [x] 12.2 Write property test for SEO metadata preservation
    - **Property 3: SEO metadata is preserved for every published post**
    - Render the article detail page and assert each of canonical URL, Open Graph, Twitter Card, and JSON-LD (where present) individually
    - **Validates: Requirements 5.2, 13.7**

- [ ] 13. Templates: homepage editorial layout
  - [x] 13.1 Rebuild the homepage with hero + asymmetric grid + category tags
    - Render exactly one hero for the primary featured Published_Blog above listings; render additional posts in a mixed-size asymmetric grid; show color-coded category tags on hero/cards
    - When no featured post exists, render a named empty-state instead of the hero (even if non-featured posts exist)
    - Apply subtle card hover lift and animated link underline; add reading-progress indicator hook for article pages
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.4_

  - [~] 13.2 Write property test for category tag rendering
    - **Property 1: Category tag is rendered on post treatments**
    - Assert rendering a published post with an assigned Category produces output containing a distinguishable category tag labeled with that Category
    - **Validates: Requirements 3.3**

  - [~] 13.3 Write example tests for hero presence and featured empty-state
    - Assert hero renders when featured posts exist (3.1); named empty-state renders when none are featured (3.4)
    - _Requirements: 3.1, 3.4_

- [ ] 14. Templates: restyle remaining public and auth pages, and dashboard density
  - [x] 14.1 Restyle article detail, archive, search, author profile, and auth pages
    - Apply the Design System to article detail (with reading-progress indicator), category archive, search results, author profile, and authentication pages (login, register, password reset)
    - Render the author profile in spacious presentation for Visitors/non-Editors and density presentation for Editors, driven by `use_dashboard_density`
    - _Requirements: 4.4, 5.1, 5.5, 5.6_

  - [x] 14.2 Restyle dashboard templates with density-optimized presentation
    - Apply the density component set (compact tables, visible row actions) distinct from public reading pages; keep existing Django-permission access model
    - _Requirements: 5.1, 5.4, 13.8_

  - [~] 14.3 Write coverage smoke tests across pages and themes
    - Render every covered page in both themes; assert each extends the themed base and renders without depending on removed Bootstrap utility classes; confirm dashboard uses the density component set
    - _Requirements: 2.1, 5.1, 5.3, 5.4_

- [ ] 15. Structural and preservation guardrails
  - [~] 15.1 Write structural/architecture constraint tests
    - Assert no Celery/cron/queue dependency, theme persisted via cookie/session (no new preference model), Follow/scheduling reference existing `User` model (no `Author` model), and no new roles/permission types
    - Assert Follow model/fields/migration exist and dashboard forms expose the publication-time control
    - _Requirements: 6.1, 10.4, 12.1, 12.2, 13.8, 14.1, 14.2, 14.3_

  - [~] 15.2 Verify existing behavior preservation suites still pass
    - Confirm existing rate-limit, image-validation, and comment/like/bookmark suites pass unchanged
    - _Requirements: 13.4, 13.5, 13.6_

- [~] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP, though property tests are strongly recommended since they validate the feature's correctness properties.
- Each task references specific requirement sub-clauses for traceability; property test tasks additionally reference their design property number.
- Property tests use Hypothesis (`hypothesis.extra.django`) with `max_examples>=100` and the tag `# Feature: editorial-revamp, Property {n}: ...`.
- Property 14 and Property 19 inject/freeze `now` to exercise boundary times deterministically.
- Checkpoints ensure incremental validation across the scheduling, follow, and redesign concerns.
- The visual/token layer (colors, radii, typography, motion) is validated by stylesheet audits, contrast enumeration, and snapshot/coverage checks rather than property-based tests.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "6.1", "10.1", "11.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1", "6.2", "10.2", "11.2", "12.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "4.1", "6.3", "6.4", "6.5", "7.1", "10.3", "11.3", "11.4", "12.2"] },
    { "id": 3, "tasks": ["4.2", "4.3", "4.4", "7.2", "7.3", "9.1", "13.1"] },
    { "id": 4, "tasks": ["4.5", "4.6", "7.4", "7.5", "7.6", "7.7", "9.2", "9.3", "9.4", "9.5", "13.2", "13.3", "14.1", "14.2"] },
    { "id": 5, "tasks": ["14.3", "15.1", "15.2"] }
  ]
}
```
