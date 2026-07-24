# InkSpire

InkSpire is a Django blogging and publishing platform built as a portfolio-grade project. It started as a simple blog and has been improved into a cleaner, safer publishing system with public discovery pages, author profiles, an editorial dashboard, SEO foundations, comment moderation, and a more professional writing workflow.

**Live demo: https://inkspire-blog-fqad.onrender.com**

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
- Django 5.2.16 LTS
- SQLite for local development / PostgreSQL on Render
- Custom CSS design system (Source Serif 4 + Inter, dark mode, design tokens)
- django-allauth for Google OAuth authentication
- CKEditor 5 for rich text editing
- django-crispy-forms + crispy-bootstrap5
- Cloudinary for persistent media/image storage
- Pillow for image validation
- WhiteNoise + Gunicorn for production deployment

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
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

For production (set these in your Render dashboard under Environment Variables):

```env
DEBUG=False
SECRET_KEY=your-production-secret
ALLOWED_HOSTS=your-domain.onrender.com
DATABASE_URL=your-postgres-url
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
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

### Rich-text security

Article HTML is sanitized server-side with one shared allowlist. New and edited posts are cleaned before storage, while legacy content is sanitized again when rendered. CKEditor filtering is not a security boundary; raw `safe` rendering of article content is prohibited. Any allowed-tag or attribute expansion requires security review and tests.

## Future improvements

- Dashboard filters and pagination for posts/comments/messages
- Richer author pages with selected social links
- Better image handling, thumbnails, and responsive image variants
- More accessibility pass coverage
- Deployment hardening checklist and CI pipeline

## Portfolio / CV bullet

Built InkSpire, a Django publishing platform with secure editorial workflows, public author pages, SEO-ready metadata, RSS/sitemap/robots support, image validation, comment moderation, and 26 automated tests covering security and publishing behavior.

## LinkedIn project description

InkSpire is a Django-based publishing platform I improved from a basic blog into a more professional content system. I focused on security containment, editorial dashboard UX, public reading experience, SEO metadata, RSS/sitemap/robots support, author profiles, image validation, comment moderation, and test coverage.

## 60-second interview explanation

InkSpire is a Django publishing platform that I evolved from a simple blogging app into a more complete editorial system. The main work was not just adding UI polish, but tightening the product foundations: protecting dashboard access, making state-changing actions POST-only, separating public and private profile views, adding password reset, improving SEO metadata, and ensuring drafts cannot leak into public lists, search, sitemap, RSS, or author pages.

On the publishing side, I added safer draft previews, stable slugs after editing, a `published_at` field, featured image validation, alt text, and comment moderation. I also redesigned the public reading and discovery pages and improved the dashboard overview, post list, and editor workflow. The project now has automated tests covering the important security and publishing rules, so it is a much stronger portfolio example than a normal CRUD blog.
