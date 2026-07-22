"""Deterministic structural / architecture constraint tests (Editorial Revamp).

# Feature: editorial-revamp — Task 15.1 structural guardrails.

These are NOT property-based tests. They assert the *scope boundaries* the
design commits to, so a future change that quietly reintroduces forbidden
infrastructure (a task runner, a new preference model, a separate ``Author``
model, new roles/permissions) fails loudly.

Covered requirements:
  - 6.1   Follow model records follower/followed Users.
  - 10.4  Scheduling uses only a read-time queryset filter — no task runner.
  - 12.1  Dashboard add-post form exposes a Publication_Time control.
  - 12.2  Dashboard edit-post form exposes a Publication_Time control.
  - 13.8  No new roles / permission types introduced.
  - 14.1  No Celery / cron / queue dependency.
  - 14.2  Theme_Preference persisted via cookie/session (no new DB model).
  - 14.3  No separate Author model; Follow operates on the Django User model.
"""

import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User as AuthUser
from django.db import models
from django.test import SimpleTestCase

from blogs.models import Follow


BASE_DIR = Path(settings.BASE_DIR)

# Package/dist names and importable module names that indicate a background
# task runner, message queue, or periodic-job scheduler. Requirement 14.1 /
# 10.4 forbid all of these — scheduling must be a pure read-time filter.
FORBIDDEN_TASK_RUNNER_TOKENS = [
    'celery',
    'django-celery',
    'django_celery',
    'django-celery-beat',
    'django-celery-results',
    'rq',
    'django-rq',
    'django_rq',
    'rq-scheduler',
    'huey',
    'dramatiq',
    'django-q',
    'django_q',
    'django-q2',
    'apscheduler',
    'django-apscheduler',
    'kombu',
    'billiard',
    'flower',
    'crontab',
    'django-crontab',
    'django_crontab',
]


class NoBackgroundTaskRunnerTests(SimpleTestCase):
    """Requirements 10.4, 14.1 — scheduling depends only on a read-time
    queryset filter, never on Celery, a cron job, or any other background
    task runner / message queue."""

    def _read_requirements(self):
        req_path = BASE_DIR / 'requirements.txt'
        self.assertTrue(
            req_path.exists(),
            f'requirements.txt not found at {req_path}',
        )
        return req_path.read_text(encoding='utf-8')

    def test_requirements_has_no_task_runner_dependency(self):
        text = self._read_requirements()
        for line in text.splitlines():
            # Ignore comments and blank lines; only inspect real requirements.
            stripped = line.split('#', 1)[0].strip()
            if not stripped:
                continue
            # The distribution name is the part before any version specifier.
            dist = re.split(r'[<>=!~\[ ]', stripped, 1)[0].strip().lower()
            self.assertNotIn(
                dist,
                FORBIDDEN_TASK_RUNNER_TOKENS,
                msg=(
                    f'requirements.txt declares forbidden task-runner/queue '
                    f'dependency {dist!r}; scheduling must use only a '
                    f'read-time queryset filter (Requirements 10.4, 14.1).'
                ),
            )

    def test_installed_apps_has_no_task_runner_app(self):
        for app in settings.INSTALLED_APPS:
            token = app.lower()
            for forbidden in FORBIDDEN_TASK_RUNNER_TOKENS:
                self.assertNotIn(
                    forbidden,
                    token,
                    msg=(
                        f'INSTALLED_APPS contains {app!r} which looks like a '
                        f'background task runner/queue ({forbidden!r}); '
                        f'forbidden by Requirements 10.4, 14.1.'
                    ),
                )


class ThemePersistenceConstraintTests(SimpleTestCase):
    """Requirement 14.2 — Theme_Preference is persisted via cookie/session,
    NOT via a new database-backed preference model, and the theme scripts
    actually use a cookie."""

    THEME_MODEL_HINT = re.compile(r'(theme|preference)', re.IGNORECASE)

    def test_no_new_theme_or_preference_model(self):
        # Scan every model in the project for a theme/preference-style model.
        # UserProfile is the pre-existing profile model and is explicitly
        # allowed; anything named like a Theme/Preference model is not.
        offending = []
        for model in apps.get_models():
            name = model.__name__
            if name == 'UserProfile':
                continue
            if self.THEME_MODEL_HINT.search(name):
                offending.append(f'{model._meta.app_label}.{name}')
        self.assertEqual(
            offending, [],
            msg=(
                'Found model(s) that look like a theme/preference store: '
                f'{offending}. Theme_Preference must be persisted via '
                'cookie/session, not a new DB model (Requirement 14.2).'
            ),
        )

    def _theme_script(self, filename):
        path = BASE_DIR / 'blog_main' / 'static' / 'js' / filename
        self.assertTrue(path.exists(), f'{filename} not found at {path}')
        return path.read_text(encoding='utf-8')

    def test_theme_init_reads_a_cookie(self):
        source = self._theme_script('theme-init.js')
        self.assertIn(
            'document.cookie', source,
            'theme-init.js must resolve the persisted theme from a cookie '
            '(Requirement 14.2).',
        )
        self.assertIn('theme', source.lower())

    def test_theme_toggle_persists_via_cookie(self):
        source = self._theme_script('theme-toggle.js')
        self.assertIn(
            'document.cookie', source,
            'theme-toggle.js must persist the chosen theme in a cookie '
            '(Requirements 2.3, 14.2).',
        )
        self.assertIn(
            'Max-Age', source,
            'theme-toggle.js must write a long-lived cookie (Max-Age) so the '
            'preference survives across sessions (Requirement 14.2).',
        )


class FollowUsesExistingUserModelTests(SimpleTestCase):
    """Requirements 6.1, 14.3 — Follow records a follower/followed User and
    operates against the existing Django User model; no separate Author
    model is introduced."""

    def test_follow_fields_reference_the_auth_user_model(self):
        user_model = get_user_model()
        # The project uses the stock Django auth User; confirm it, then that
        # both Follow FKs point at it (equivalently settings.AUTH_USER_MODEL).
        self.assertEqual(user_model, AuthUser)
        self.assertEqual(settings.AUTH_USER_MODEL, 'auth.User')

        for field_name in ('follower', 'followed'):
            field = Follow._meta.get_field(field_name)
            self.assertIsInstance(
                field, models.ForeignKey,
                f'Follow.{field_name} must be a ForeignKey.',
            )
            self.assertEqual(
                field.related_model, user_model,
                f'Follow.{field_name} must reference the Django User model, '
                f'not a separate Author model (Requirements 6.1, 14.3).',
            )
            self.assertEqual(
                field.remote_field.on_delete, models.CASCADE,
                f'Follow.{field_name} must cascade-delete with the User '
                f'(Requirement 6.4).',
            )

    def test_no_author_model_exists(self):
        offending = [
            f'{m._meta.app_label}.{m.__name__}'
            for m in apps.get_models()
            if m.__name__ == 'Author'
        ]
        self.assertEqual(
            offending, [],
            msg=(
                f'A model named Author exists ({offending}); Follow and '
                'scheduling must operate on the existing User model, and no '
                'separate Author model may be introduced (Requirement 14.3).'
            ),
        )


class NoNewRolesOrPermissionsTests(SimpleTestCase):
    """Requirement 13.8 — the feature introduces no new roles or permission
    types. Feature models must not declare custom permissions, and feature
    migrations must not create Group/Permission rows or custom permissions."""

    FEATURE_MODELS = [Follow]

    def test_feature_models_declare_no_custom_permissions(self):
        for model in self.FEATURE_MODELS:
            self.assertEqual(
                list(model._meta.permissions), [],
                msg=(
                    f'{model.__name__} declares custom permissions '
                    f'{model._meta.permissions}; no new permission types may '
                    f'be introduced (Requirement 13.8).'
                ),
            )
            # Only the default add/change/delete/view permissions are allowed.
            self.assertEqual(
                set(model._meta.default_permissions),
                {'add', 'change', 'delete', 'view'},
                msg=(
                    f'{model.__name__} alters default_permissions; the '
                    f'feature must keep the standard permission set '
                    f'(Requirement 13.8).'
                ),
            )

    def test_follow_migration_defines_no_custom_permissions(self):
        migration = (
            BASE_DIR / 'blogs' / 'migrations' / '0018_follow.py'
        ).read_text(encoding='utf-8')
        # The Follow migration must not seed roles/permissions or attach
        # custom permission options to the model.
        self.assertNotIn("'permissions'", migration)
        self.assertNotIn('"permissions"', migration)
        self.assertNotRegex(
            migration, r'\bmodel_name=.{0,40}(group|permission)\b',
        )


class FollowModelAndMigrationExistTests(SimpleTestCase):
    """Requirements 6.1, 6.2, 6.3 — the Follow model, its fields, its
    uniqueness/self-follow constraints, and its migration all exist."""

    def test_follow_has_expected_fields(self):
        field_names = {f.name for f in Follow._meta.get_fields()}
        for expected in ('follower', 'followed', 'created_at'):
            self.assertIn(
                expected, field_names,
                f'Follow is missing the {expected!r} field (Requirement 6.1).',
            )

    def test_follow_declares_uniqueness_and_self_follow_constraints(self):
        constraint_names = {c.name for c in Follow._meta.constraints}
        self.assertIn(
            'unique_follow', constraint_names,
            'Follow must enforce a unique (follower, followed) constraint '
            '(Requirement 6.2).',
        )
        self.assertIn(
            'prevent_self_follow', constraint_names,
            'Follow must enforce a self-follow check constraint '
            '(Requirement 6.3).',
        )

    def test_follow_migration_file_exists(self):
        migration_path = (
            BASE_DIR / 'blogs' / 'migrations' / '0018_follow.py'
        )
        self.assertTrue(
            migration_path.exists(),
            f'Follow migration not found at {migration_path} '
            '(Requirement 6.1).',
        )
        source = migration_path.read_text(encoding='utf-8')
        self.assertIn("name='Follow'", source)
        # The migration must reference the swappable AUTH_USER_MODEL rather
        # than a bespoke Author model (Requirement 14.3).
        self.assertIn('settings.AUTH_USER_MODEL', source)


class DashboardPublicationTimeControlTests(SimpleTestCase):
    """Requirements 12.1, 12.2 — the dashboard add/edit post form exposes a
    control to set/view/change/clear a future Publication_Time."""

    def test_blogform_exposes_publication_time_field(self):
        from django import forms as django_forms
        from dashboard.forms import BlogForm

        form = BlogForm()
        self.assertIn(
            'publication_time', form.fields,
            'BlogForm must expose a publication_time control for scheduling '
            '(Requirements 12.1, 12.2).',
        )
        field = form.fields['publication_time']
        self.assertIsInstance(
            field, django_forms.DateTimeField,
            'publication_time must be a DateTimeField control.',
        )
        # Optional so a post can be published immediately or kept as a draft.
        self.assertFalse(
            field.required,
            'publication_time must be optional (Requirements 12.1, 12.2, 12.4).',
        )
