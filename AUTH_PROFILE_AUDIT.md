# Auth and Profile Audit

## Current setup summary

| Area | Current state |
|---|---|
| Login | Custom function view using `AuthenticationForm`; username/password only |
| Register | Custom `UserCreationForm`; requires unique email; creates `UserProfile` after signup |
| Logout | POST-only custom view with CSRF form in templates |
| Password reset | Django built-in reset views with custom templates; console email backend locally |
| Private profile | `/profile/`, `/profile/edit/`, `/profile/change-password/` require login |
| Public profile | Separate `/authors/<username>/` public author page |
| Profile data | `bio`, `avatar`, `website`, `location`; first/last name stored on `User` |
| Settings | `LOGIN_URL`, redirects, password validators, console email backend |
| Tests | Good security/publishing coverage; little direct auth/profile flow coverage |

## Problems found

| Priority | Issue | Notes |
|---|---|---|
| P0 | Password reset template has mojibake | `weâ€™ll` visible in `password_reset_form.html` |
| P0 | Login does not honor `next` redirect | Protected pages redirect to login, but successful login always goes home |
| P0 | Profile avatar upload lacks validation | No file type/size checks like article images |
| P1 | Register email uniqueness is case-sensitive | `User@x.com` and `user@x.com` can both register |
| P1 | No direct auth/profile tests | Password reset, login next, profile edit, avatar validation are not covered |
| P1 | Password reset URLs use hardcoded success paths | Works, but `reverse_lazy` would be safer |
| P1 | Authenticated users can still visit login/register | Minor UX polish issue |
| P1 | Profile creation is view-dependent | Safer to centralize with `get_or_create` helper or signal |
| P2 | Profile edit page still has older card styling | Functional, but behind newer page quality |
| P2 | No email verification | Acceptable for portfolio unless adding email-dependent features |

## Missing modern auth/profile features

| Priority | Feature |
|---|---|
| P0 | Login `next` support |
| P0 | Avatar upload validation |
| P1 | Case-insensitive email uniqueness |
| P1 | Auth/profile tests |
| P1 | Clearer profile edit UX and form errors |
| P1 | Email change flow with confirmation |
| P2 | Remember-me session option |
| P2 | Account deletion/export |
| P2 | Login rate limiting / lockout |
| P2 | Two-factor authentication |
| Avoid | Social login for now unless specifically needed |

## Recommended changes

| Priority | Change |
|---|---|
| P0 | Fix password reset text encoding |
| P0 | Preserve and validate `next` during login |
| P0 | Add avatar type/size validation |
| P1 | Normalize/check email case-insensitively in registration |
| P1 | Add tests for login, logout POST, reset pages, profile edit, avatar validation |
| P1 | Use `reverse_lazy` in password reset URL config |
| P1 | Redirect authenticated users away from login/register |
| P2 | Polish edit profile/change password templates to match newer UI |

## Safe implementation phases

| Phase | Scope |
|---|---|
| 1 | Fix mojibake, login `next`, avatar validation, direct tests |
| 2 | Case-insensitive email handling and safer profile creation helper |
| 3 | Profile/edit/change-password UI polish |
| 4 | Optional account settings improvements |

## Risks to avoid

- Do not replace the `User` model at this stage.
- Do not add Google/social auth before basic auth is fully tested.
- Do not expose private profile data on public author pages.
- Do not weaken POST-only logout.
- Do not add real SMTP credentials to the repo.
- Do not add email verification unless email delivery is configured properly.
