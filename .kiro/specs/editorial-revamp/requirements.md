# Requirements Document

## Introduction

InkSpire is a Django 5.2.16 / Python 3.12 blogging platform (SQLite in dev, PostgreSQL in prod, Redis cache in prod, django-ratelimit, django-allauth with Google OAuth, CKEditor 5, WhiteNoise, vanilla templates + Bootstrap 5). This feature, "Editorial Revamp," delivers three coordinated changes:

1. A full visual redesign of every public-facing and dashboard template, replacing the current "Frontend V2" restrained design system (`FRONTEND_V2_DESIGN_SYSTEM.md`) with a new "Modern Editorial" direction that blends editorial-quiet restraint, modern-magazine asymmetric layout, and a first-class dark mode — explicitly avoiding generic AI-generated design tropes (gradients, glassmorphism, oversized radii, decorative shapes, scroll-triggered animation).
2. A new Follow Authors capability, letting readers follow/unfollow authors and view a feed of recent posts from followed authors.
3. A new Scheduled Publishing capability, letting editors schedule a `Blog` post to go live automatically at a future date/time using a read-time filter, with no background task runner.

This document defines WHAT the system must do. Visual direction, exact token values, and implementation approach for styling are technical decisions to be resolved in design; the acceptance criteria below define testable, observable behavior and constraints that any design/implementation must satisfy.

## Glossary

- **Site**: The InkSpire Django application as experienced through its public-facing templates and views.
- **Visitor**: An unauthenticated person browsing Site's public pages.
- **Reader**: An authenticated `User` (Django auth `User` model) browsing Site, regardless of dashboard permissions.
- **Editor**: An authenticated `User` who holds the Django permission(s) or staff/superuser status required to manage `Blog` posts in the Dashboard (matches the existing dashboard permission model; no new role concept is introduced).
- **Author**: A `User` who is set as the `author` of one or more `Blog` posts, or who is the subject of a public Author Profile Page.
- **Blog**: The existing `blogs.Blog` model representing a single post, with `status` (`draft`/`published`), `published_at`, and related fields as defined in `blogs/models.py`.
- **Published_Blog**: A `Blog` that is visible on Public_Surfaces under the rules defined in this document (see Requirement 10 and Requirement 11).
- **Public_Surface**: Any page, feed, or endpoint reachable without Editor-level draft-preview permission, including the homepage, category/search/author archive pages, the article detail page (outside of preview mode), the sitemap, and the RSS feed.
- **Theme**: One of two supported visual presentations of Site: "light" or "dark".
- **Theme_Preference**: The Theme a Visitor or Reader has explicitly selected, persisted so it is honored on subsequent requests.
- **Theme_Toggle**: The UI control that lets a Visitor or Reader switch Site's active Theme.
- **Design_System**: The set of visual tokens (color, typography, spacing, radius, shadow, motion) and reusable component patterns that govern Site's rendered appearance across all templates.
- **Follow**: A directed relationship record connecting a follower `User` to a followed `User`.
- **Follower**: A `User` who has created a Follow record targeting another `User`.
- **Following_Feed**: A page, accessible only to an authenticated Reader, listing Published_Blog posts authored by Users the Reader follows.
- **Scheduled_Blog**: A `Blog` that has been assigned a future Publication_Time and is not yet visible on any Public_Surface.
- **Publication_Time**: The date/time at or after which a Scheduled_Blog automatically becomes a Published_Blog, evaluated at read time against the current time.
- **Dashboard**: The internal editorial interface under `/dashboard`, rendered by `dashboard/views.py` and `templates/dashboard/*`.

## Requirements

### Requirement 1: Design Token Foundation

**User Story:** As a Site visitor, I want a distinctive, editorial-feeling visual foundation instead of a generic template look, so that reading InkSpire feels considered and credible rather than like a default AI-generated theme.

#### Acceptance Criteria

1. THE Design_System SHALL define fixed light-Theme color properties — an off-white background, near-black primary text color, and exactly one warm, non-purple, non-blue accent color — regardless of which Theme is currently active.
2. WHEN the dark Theme is active, THE Design_System SHALL render backgrounds as near-black, primary text as warm off-white, and accents using the same accent color defined for the light Theme.
3. THE Design_System SHALL pair exactly one serif font family for headlines and article body text with exactly one sans-serif font family for UI, navigation, and meta text.
4. THE Design_System SHALL restrict the border-radius of every rectangular container to a maximum of 8px, reserving fully circular radius values only for avatars and single-icon circular controls.
5. THE Design_System SHALL render card, panel, and section boundaries using hairline (1px) borders as the primary separation technique rather than heavy drop shadows.
6. THE Design_System SHALL restrict background fills to flat, single colors, permitting a gradient only where it is applied over photographic imagery to preserve text legibility.
7. THE Design_System SHALL NOT include glassmorphism/frosted-glass panel effects, decorative geometric shapes, fabricated statistics, or stock abstract 3D imagery in any template.
8. WHERE color contrast between text and its background is evaluated, THE Design_System SHALL meet WCAG AA contrast ratios (4.5:1 for body text, 3:1 for large text/UI elements) in both the light Theme and the dark Theme.

### Requirement 2: Dark Mode as a First-Class Theme

**User Story:** As a reader, I want a fully realized dark mode, so that I can read comfortably in low light without the site feeling like it has an afterthought dark skin.

#### Acceptance Criteria

1. THE Site SHALL provide a dark Theme that restyles every template covered by this feature (base layout, homepage, article detail, category/search/author archive pages, authentication pages, and Dashboard), not a partial subset of pages.
2. WHEN a Visitor or Reader activates the Theme_Toggle, THE Site SHALL switch the active Theme between light and dark without requiring a full page navigation.
3. WHEN a Visitor or Reader has an active Theme_Preference, THE Site SHALL persist that Theme_Preference across subsequent page loads within the same browser without requiring the person to authenticate.
4. WHEN a Visitor or Reader has no previously stored Theme_Preference, THE Site SHALL determine the initial active Theme from the visitor's operating-system or browser color-scheme preference where available, and SHALL default to the light Theme when no such preference is available.
5. WHEN the active Theme changes, THE Site SHALL transition background and text colors smoothly rather than switching instantaneously with a visible flash, and IF the smooth transition cannot be applied due to a browser limitation, THEN THE Site SHALL NOT complete the Theme change rather than applying it instantaneously.

### Requirement 3: Editorial Homepage Layout

**User Story:** As a visitor, I want the homepage to highlight one lead story and present other posts in a visually varied layout, so that the homepage feels curated rather than like a repeating list of identical cards.

#### Acceptance Criteria

1. WHEN the homepage is requested and at least one featured Published_Blog exists, THE Site SHALL render exactly one large hero treatment for the primary featured Published_Blog above all other post listings.
2. WHEN the homepage renders additional featured or recent Published_Blog posts below the hero, THE Site SHALL present them in a mixed-size, asymmetric grid rather than a uniform grid of identically sized cards.
3. THE Site SHALL display each Published_Blog's assigned Category as a distinguishable color-coded tag on homepage card and hero treatments.
4. WHEN the homepage is requested and no Published_Blog is marked as featured, THE Site SHALL NOT render the hero treatment and SHALL instead render an empty-state message that names what is missing, regardless of whether other non-featured Published_Blog posts exist.

### Requirement 4: Site-Wide Interaction and Motion Constraints

**User Story:** As a visitor, I want subtle, purposeful interactions instead of decorative animation, so that the site feels polished without feeling gimmicky or slow.

#### Acceptance Criteria

1. WHEN a Visitor or Reader hovers over a post card on a pointer-capable device, THE Site SHALL apply a subtle lift/elevation change to that card.
2. WHEN a Visitor or Reader hovers over an inline text link within article or UI content, THE Site SHALL animate the link's underline rather than showing or hiding it instantly.
3. THE Site SHALL NOT trigger any content animation based on scroll position, including fade-ins, parallax effects, or animated gradients, EXCEPT for the reading-progress indicator described in Requirement 4.4, which is the sole scroll-driven visual update permitted by this feature.
4. WHERE an article detail page is being read, THE Site SHALL display a reading-progress indicator that reflects scroll position within the article body.
5. THE Site SHALL limit all transition and animation effects defined by this feature to state changes the person directly causes (hover, focus, Theme toggle, scroll-position reading progress), and SHALL NOT play an animation automatically on page load beyond the initial Theme determination in Requirement 2.4.

### Requirement 5: Redesigned Page Templates

**User Story:** As a visitor or editor, I want every page of the site to reflect the new editorial design consistently, so that no page feels visually inconsistent with the rest of the site.

#### Acceptance Criteria

1. THE Site SHALL apply the Design_System defined in Requirement 1 to `base.html` and every template that extends it, including the homepage, article detail page, category archive page, search results page, author profile page, authentication pages (login, register, password reset), and Dashboard templates.
2. THE Site SHALL retain, on every redesigned page, the existing SEO metadata blocks (canonical URL, Open Graph tags, Twitter Card tags, and JSON-LD where present) without functional regression.
3. WHERE a page previously relied on Bootstrap 5 utility classes for layout, THE Site SHALL render an equivalent layout under the new Design_System without depending on the removed classes.
4. THE Dashboard SHALL explicitly require a density-optimized presentation (compact tables, visible row actions) that is distinct from the more spacious presentation used on public reading pages.
5. WHEN a Visitor or a Reader without Editor permissions views an Author Profile Page, THE Site SHALL render that page using the spacious public-page presentation defined in this requirement.
6. WHEN a Reader with Editor permissions views an Author Profile Page, THE Site SHALL render that page using the density-optimized Dashboard presentation defined in this requirement rather than the spacious public-page presentation.

### Requirement 6: Follow Relationship Model

**User Story:** As a platform, I need a data model for follow relationships, so that readers can follow authors and the system can prevent invalid follow states.

#### Acceptance Criteria

1. THE Site SHALL provide a Follow model recording a follower `User` and a followed `User`.
2. THE Site SHALL enforce a uniqueness constraint preventing more than one Follow record for the same follower/followed `User` pair.
3. IF a `User` attempts to create a Follow record where the follower and the followed `User` are the same `User`, THEN THE Site SHALL reject the attempt and SHALL NOT create a self-follow record.
4. WHEN a followed `User` account is deleted, THE Site SHALL remove all Follow records referencing that `User` as either follower or followed.

### Requirement 7: Follow and Unfollow Controls

**User Story:** As a reader, I want to follow or unfollow an author from their profile page, so that I can curate whose work I keep up with.

#### Acceptance Criteria

1. WHERE a Reader is viewing an Author Profile Page for a `User` other than themselves, THE Site SHALL display a control to follow that Author when no Follow record exists between them.
2. WHERE a Reader is viewing an Author Profile Page for a `User` other than themselves, THE Site SHALL display a control to unfollow that Author when a Follow record already exists between them.
3. WHEN an authenticated Reader submits the follow control for an Author, THE Site SHALL create a Follow record from that Reader to that Author and SHALL update the page to reflect the followed state.
4. WHEN an authenticated Reader submits the unfollow control for an Author, THE Site SHALL delete the corresponding Follow record and SHALL update the page to reflect the unfollowed state.
5. IF an unauthenticated Visitor attempts to submit the follow or unfollow control, THEN THE Site SHALL redirect the Visitor to the login page rather than creating or deleting a Follow record.
6. THE Site SHALL NOT display a follow or unfollow control on a `User`'s own Author Profile Page.

### Requirement 8: Following Feed

**User Story:** As a reader, I want a feed of recent posts from authors I follow, so that I can catch up on their new work in one place.

#### Acceptance Criteria

1. WHEN an authenticated Reader requests the Following_Feed, THE Site SHALL query only Published_Blog posts authored by Users the Reader follows, ordered by most recently published first, filtering unpublished and not-yet-due Scheduled_Blog posts out at the query level rather than after retrieval.
2. THE Following_Feed SHALL NOT include any `Blog` post whose status is not published or whose Publication_Time has not yet passed, regardless of who authored it.
3. IF an unauthenticated Visitor requests the Following_Feed, THEN THE Site SHALL redirect the Visitor to the login page.
4. WHEN an authenticated Reader who follows no Users requests the Following_Feed, THE Site SHALL render an empty-state message that explains no followed authors have published posts yet, rather than an empty or broken listing.

### Requirement 9: Follower Count Display (Optional)

**User Story:** As an author, I want visitors to see how many people follow me, so that my profile conveys reach and credibility.

#### Acceptance Criteria

1. WHERE follower-count display is enabled for an Author Profile Page, THE Site SHALL display a count of Follow records where that Author is the followed `User`.

### Requirement 10: Scheduled Blog Field and State

**User Story:** As an editor, I need a way to mark a post to go live at a future date/time, so that I can prepare content in advance without publishing it immediately.

#### Acceptance Criteria

1. THE Blog model SHALL support recording a future Publication_Time for a post that has not yet been published.
2. IF a `Blog` has a recorded future Publication_Time that has not yet passed, THEN THE Site SHALL treat that `Blog` as a Scheduled_Blog and SHALL NOT treat it as a Published_Blog.
3. WHEN a Scheduled_Blog's recorded Publication_Time passes, THE Site SHALL treat that `Blog` as a Published_Blog on its next read, without any manual publish action or background task being required.
4. THE Site SHALL determine whether a `Blog` is a Published_Blog using only a read-time comparison against the current time within the existing `Blog.objects.published()` queryset, without introducing a scheduled task runner, message queue, or periodic job.
5. WHEN an Editor sets a `Blog`'s status to published directly (not scheduled), THE Site SHALL preserve the existing behavior of recording `published_at` at save time when it is not already set.

### Requirement 11: Scheduled Content Exclusion from Public Surfaces

**User Story:** As an editor, I need scheduled posts to stay completely invisible to the public until their scheduled time, so that I don't accidentally leak unfinished or time-sensitive content early.

#### Acceptance Criteria

1. THE Site SHALL exclude every Scheduled_Blog from the homepage, category archive pages, search results, and the author profile page's public post listing.
2. THE Site SHALL exclude every Scheduled_Blog from the sitemap generated by `BlogSitemap`.
3. THE Site SHALL exclude every Scheduled_Blog from the RSS feed generated by `LatestPostsFeed`.
4. THE Site SHALL exclude every Scheduled_Blog from the Following_Feed.
5. IF a Visitor or a Reader without draft-preview permission requests the article detail page for a Scheduled_Blog directly by URL, THEN THE Site SHALL respond as if the post does not exist, consistent with existing draft-preview permission handling.
6. WHERE the existing author/staff/`change_blog`-permission preview capability applies to draft posts, THE Site SHALL extend that same preview capability to Scheduled_Blog posts, so only a `User` who already holds one of those existing draft-preview permissions can view a scheduled post before its Publication_Time; scheduled status alone SHALL NOT grant preview access to any other `User`.

### Requirement 12: Dashboard Scheduling Controls

**User Story:** As an editor, I want to set or change a post's scheduled publish time from the dashboard, so that I can plan a publishing calendar.

#### Acceptance Criteria

1. THE Dashboard's add-post form SHALL provide a control for an Editor to set a future Publication_Time for a new `Blog`.
2. THE Dashboard's edit-post form SHALL provide a control for an Editor to view, change, or clear a `Blog`'s scheduled Publication_Time.
3. IF an Editor submits a Publication_Time that is in the past for a `Blog` that is not already published, THEN THE Dashboard SHALL reject the submission and SHALL display a validation message explaining the Publication_Time must be in the future.
4. WHEN an Editor clears a `Blog`'s scheduled Publication_Time without setting status to published, THE Dashboard SHALL save the `Blog` as a draft rather than leaving it in an ambiguous scheduled state.
5. THE Dashboard's post listing SHALL visually distinguish Scheduled_Blog posts from draft and published posts, showing the scheduled Publication_Time.

### Requirement 13: Preservation of Existing Behavior

**User Story:** As the product owner, I need this redesign and these new features to avoid regressing existing functionality, so that current readers and editors keep a working site throughout the change.

#### Acceptance Criteria

1. THE Site SHALL continue to increment a `Blog`'s view count exactly once per non-preview article detail request, unaffected by the introduction of Scheduled_Blog handling.
2. THE Site SHALL continue to apply existing `select_related`/`annotate`-based query optimizations on listing and detail views without introducing additional per-row queries as a result of Scheduled_Blog filtering or Follow-related additions.
3. THE Site SHALL continue to enforce existing draft-preview permissions (post author, staff, or `blogs.change_blog` permission holder) unchanged, extended only as described in Requirement 11.6.
4. THE Site SHALL continue to apply existing rate limiting on comment submission, login attempts, and contact form submission unchanged.
5. THE Site SHALL continue to apply existing image upload validation on featured images and CKEditor-uploaded images unchanged.
6. THE Site SHALL continue to support existing comment, like, and bookmark functionality unchanged for Published_Blog posts.
7. THE Site SHALL continue to expose, for every Published_Blog post, each of the following unchanged: canonical URL metadata, Open Graph tags, Twitter Card tags, JSON-LD structured data, and existing sitemap/RSS/`robots.txt` behavior, with each metadata type verified individually rather than as a single combined check.
8. THE Dashboard SHALL continue to enforce its existing Django-permission-based access model (no new roles or permission types introduced by this feature).

### Requirement 14: Scope Boundaries

**User Story:** As the product owner, I want the scope of backend changes limited to what Follow Authors and Scheduled Publishing require, so that the project avoids unnecessary new infrastructure.

#### Acceptance Criteria

1. THE Site SHALL implement Scheduled_Blog visibility using only a read-time queryset filter, and SHALL NOT depend on Celery, a cron job, or any other background task runner.
2. WHERE a Theme_Preference must be persisted for a Visitor or Reader, THE Site SHALL persist it via session or cookie storage, and SHALL NOT introduce a new database-backed user-preference model unless every reasonable session/cookie-based optimization technique (e.g., long-lived cookie expiry, client-side storage fallback) has been exhausted and determined insufficient during design.
3. THE Site SHALL NOT introduce a separate Author model; Follow, Scheduled Publishing, and profile-related behavior SHALL continue to operate against the existing Django `User` model and `UserProfile` model.
