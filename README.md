# InkSpire

InkSpire is a Django blogging and publishing platform built as a portfolio-grade project. It started as a simple blog and has been improved into a cleaner, safer publishing system with public discovery pages, author profiles, an editorial dashboard, SEO foundations, comment moderation, and a more professional writing workflow.

Live demo: https://complete-blogging-system.onrender.com

## What it does

- Publishes articles with categories, featured posts, rich text content, featured images, alt text, and reading time.
- Provides public homepage, category archive, search results, article detail, author profile, about, and contact pages.
- Supports registration, username/password login, Google login, logout, profile editing, password change, and password reset.
- Includes reader engagement: comments/replies, likes, bookmarks, RSS feed, and social sharing.
- Gives staff/editor users a dashboard for posts, categories, contact messages, and comment moderation.

## Key features

### Publishing

- Draft/published workflow
- Safe draft preview for the author, staff, or users with edit permission
- Central published-query helper to avoid draft leakage
- Stable article URLs after editing
- `published_at` timestamp
- Featured image validation: JPEG, PNG, WebP only; 3 MB limit
- Featured image alt text

### Security and permissions

- Dashboard routes protected by login and permission checks
- Ordinary users blocked from dashboard/admin-like pages
- User management restricted to superusers
- Logout, delete, like/bookmark, comment delete, and moderation actions are POST-only with CSRF
- Contact messages restricted to permitted staff
- Comment reply parent validation prevents cross-post replies
- Public article pages show only visible comments

### SEO and discovery

- Reusable title, meta description, canonical, Open Graph, Twitter card, and JSON-LD blocks
- Article JSON-LD
- Public-only sitemap
- Published-only RSS feed
- `robots.txt` rules for public/private areas
- Search results marked `noindex,follow`
- Public author pages with SEO metadata

## Tech stack

- Python 3.12
- Django 5.1.4
- SQLite for local development
- Bootstrap 5
- django-allauth for Google authentication
- CKEditor 5
- django-crispy-forms + crispy-bootstrap5
- Pillow
- WhiteNoise + Gunicorn for production-style deployment

## Setup

```bash
git clone https://github.com/kushal-kc15/complete-blogging-system.git
cd complete-blogging-system
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

On macOS/Linux, activate the environment with:

```bash
source venv/bin/activate
```

## Environment variables

Create a `.env` file for local settings if needed.

```env
SECRET_KEY=replace-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

For production, set:

```env
DEBUG=False
SECRET_KEY=your-production-secret
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_SETTINGS_MODULE=blog_main.settings_prod
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Local password reset uses Django's console email backend, so reset links are printed in the terminal during development.

For Google login, create OAuth credentials in Google Cloud Console and add these authorized redirect URIs:

- `http://127.0.0.1:8000/accounts/google/login/callback/`
- `https://your-domain.com/accounts/google/login/callback/`

## Useful commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
python manage.py runserver
```

Production/static files:

```bash
python manage.py collectstatic --noinput
```

## Screenshots

Add screenshots here before sharing widely:

- Homepage / discovery page
- Article detail page
- Public author profile
- Login/register flow
- Dashboard overview
- Post editor
- Comment moderation page

## Project notes

This project focuses on practical publishing-platform fundamentals rather than oversized startup features. The current version emphasizes:

- safe role-based dashboard access;
- clean public reading experience;
- stable publishing semantics;
- SEO-ready public pages;
- minimal, test-covered moderation and editorial tooling.

## Future improvements

- Dashboard filters and pagination for posts/comments/messages
- Richer author pages with selected social links
- Better image handling, thumbnails, and responsive image variants
- Production database and media storage configuration
- More accessibility pass coverage
- Deployment hardening checklist and CI pipeline

## Portfolio / CV bullet

Built InkSpire, a Django publishing platform with secure editorial workflows, public author pages, SEO-ready metadata, RSS/sitemap/robots support, image validation, comment moderation, and 26 automated tests covering security and publishing behavior.

## LinkedIn project description

InkSpire is a Django-based publishing platform I improved from a basic blog into a more professional content system. I focused on security containment, editorial dashboard UX, public reading experience, SEO metadata, RSS/sitemap/robots support, author profiles, image validation, comment moderation, and test coverage.

## 60-second interview explanation

InkSpire is a Django publishing platform that I evolved from a simple blogging app into a more complete editorial system. The main work was not just adding UI polish, but tightening the product foundations: protecting dashboard access, making state-changing actions POST-only, separating public and private profile views, adding password reset, improving SEO metadata, and ensuring drafts cannot leak into public lists, search, sitemap, RSS, or author pages.

On the publishing side, I added safer draft previews, stable slugs after editing, a `published_at` field, featured image validation, alt text, and comment moderation. I also redesigned the public reading and discovery pages and improved the dashboard overview, post list, and editor workflow. The project now has automated tests covering the important security and publishing rules, so it is a much stronger portfolio example than a normal CRUD blog.
