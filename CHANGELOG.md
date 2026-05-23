# Changelog

All notable changes to this project. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 2026-05-20 → 2026-05-23 — Audit cleanup pass

A multi-session code review and follow-through. Every public-facing item
the audit surfaced (P0–P2) was either resolved or explicitly deferred with
rationale. The site picked up a 85-test regression suite and a `ruff`
lint config along the way.

### Security
- HTTP Basic Auth on `/analytics` via `ANALYTICS_USER` / `ANALYTICS_PASSWORD`
  env vars; route 404s when unset, 401s for bad creds. (`55860f1`)
- Boot-time fail-fast: app refuses to start when `FLASK_DEBUG` is not True
  and `SECRET_KEY` is unset or still the placeholder. (`55860f1`)
- Defense-in-depth security headers via `@app.after_request`: CSP
  (with `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`),
  X-Frame-Options: DENY, X-Content-Type-Options: nosniff,
  Referrer-Policy, Permissions-Policy; HSTS only in non-debug mode. (`5dd41a7`)
- Session cookie hardening: `HTTPONLY`, `SAMESITE=Lax`, `SECURE` in prod,
  30-day `PERMANENT_SESSION_LIFETIME`. (`5dd41a7`)
- Rate limiting via `flask-limiter`: 5/hour per IP on both form endpoints,
  60/minute on `/api/pageview`. (`5dd41a7`)
- Honeypot fields on both forms — bots that fill the hidden `website`
  input are silently dropped (contact) or 404'd (checklist). (`5dd41a7`)
- Server-side input bounds: names 100, email 200, country 100, message
  2000 chars. JS `maxlength` was client-only and trivially bypassed. (`5dd41a7`)
- `/api/pageview` validates `path` against `^/[A-Za-z0-9/_.\-]{0,200}$`
  and rejects unsupported lang codes so spammers can't pollute
  `/analytics` with arbitrary strings. (`5dd41a7`)
- `staging.db` untracked from git; previous committed contact submissions
  were test data but should never have been in the repo. (`55860f1`)
- `/analytics` added to `robots.txt` disallow list. (`55860f1`)

### Added
- **Lead notifications** (`notifications.py`): SMTP via env vars sends an
  email per submission with the lead's address in Reply-To. Falls back to
  a clearly-bracketed stderr block when SMTP isn't configured, so lead
  capture is never silently broken. Applies to both `/submit_contact_form`
  and `/download-checklist`. (`5dd41a7`)
- **Full bilingual coverage** — 250+ new translation keys across every
  public template. Site is now actually German when `?lang=de` is set
  (services, process, calculator, FAQs, case studies, blog, privacy,
  search, error pages, cookie banner). Swiss numeric formatting
  (`CHF 2'000`). (`d9fbfeb`)
- **Open Graph + PWA assets**: 1200×630 OG image, 192/512/maskable square
  PWA icons, 180px apple-touch-icon. Generated from existing brand
  elements (database glyph, profile photo) on the brand colour palette.
  Wired into `<head>` (og:image, twitter:card upgraded to
  `summary_large_image`) and `manifest.json`. (`6572a59`)
- **Per-post blog OG images**: optional `cover:` frontmatter field
  overrides the site-wide OG image. (`1796f4f`)
- **No-JS fallbacks**: pages remain readable without JavaScript;
  calculator shows a "JavaScript Required" CTA banner; carousel
  prev/next/dots hidden when scripts are off. (`c0d8bd8`)
- **Country datalist** on contact form (~50 countries, DACH first). (`4e3f31a`)
- **Distinct 500 page** (`templates/500.html`) with its own copy. (`4e3f31a`)
- **Smoke test suite** (`tests/`): 85 tests, ~0.15s. Covers public routes,
  legacy redirects, security headers, cookie flags, honeypot drops,
  input bounds, rate-limit ceiling, SMTP fallback, sitemap `<lastmod>`,
  font preload pattern, theme bootstrap, DE coverage on every page, blog
  cache + thread safety, db indexes + retention + UTC timestamps,
  `?lang=invalid` fallback, blog posts without frontmatter date. (`b7638eb`,
  `5dd41a7`, `7b53bc4`, `d9fbfeb`, `1796f4f`, `a3d981b`)
- **Ruff lint config** (`pyproject.toml`) with E/F/W/I/B/UP rules + format
  style. `ruff check .` is clean. (`a3d981b`)
- **Sitemap `<lastmod>`** per URL (post date for blog, file mtime for
  templates, latest-post-date for home/blog index). (`1796f4f`)
- **Apple touch icon** and **square PWA icons** (192/512/maskable). (`6572a59`)

### Changed
- **Page rendering without JS**: scroll-reveal opacity-0 default scoped to
  `html.js` so pages are visible when scripts fail or load slowly. Stats
  counters render real numbers from the template and reset to zero only
  if JS will animate them. Reduced-motion preference now skips the
  hero typing animation and stats count-up, with `aria-label` /
  `aria-live="off"` so screen readers get the final value once. (`c0d8bd8`,
  `1796f4f`)
- **Theme flash fix**: localStorage read inlined into the same `<head>`
  script that flags `.js`, so light-mode users no longer see a
  single-frame dark flash. (`1796f4f`)
- **Heading hierarchy** cleaned across every template: h3/h5 misused for
  taglines/body text → semantic `<p>`; card titles under section headers
  demoted to `<h3>`. Roughly 80 `<br>` ladders replaced with margin
  tokens. Inline `height: 400px` removed from non-home hero containers. (`8583bb3`)
- **Case studies** reframed from "real client" copy to "Project Scenarios"
  with a visible "Sample scenario" callout on each detail page. Specific
  fabricated impact numbers softened to typical/illustrative language. (`aabb83e`)
- **URLs**: `/projects/case-study-foo.html` → `/projects/foo`; old URLs
  301-redirect to the new clean ones. Sitemap emits only new URLs. (`b7638eb`)
- **CSS architecture**: the 2,517-line `styles.css` monolith split into 4
  focused files (`base.css`, `layout.css`, `components.css`, `pages.css`).
  22 dead classes (`.about__*`, `.layout-box*`, `.page-title*`,
  `.project-hero-text`, `.github-button`, etc.) removed. (`cf105a2`)
- **Case study templates** collapsed into one shared
  `_case_study.html` driven by `t.case_study.details[slug]`. Adding a
  scenario is now a JSON-only change. (`d9fbfeb`)
- **matrix.js**: was running `setInterval(draw, 50)` on every page,
  reading `getComputedStyle` per frame. Now rAF-throttled, pauses via
  `IntersectionObserver` when off-screen and via the browser when the
  tab is hidden; theme colors cached and refreshed only on
  `data-theme` mutation; respects `prefers-reduced-motion`; uses a
  katakana charset instead of random control characters. (`eceb4b7`)
- **Logo regenerated**: wordmark "Clasen / Data / Science" replaced
  with "Niklas / Clasen / Consulting" matching the current brand.
  Nav-bar logo now flips to white in dark mode (was effectively
  invisible). (`c271c1c`)
- **Backend perf**: `get_blog_posts()` is mtime-cached with
  thread-safe double-checked locking. `_translations_cache` same.
  `datetime.utcnow()` (deprecated) → `datetime.now(timezone.utc)`. (`b7638eb`,
  `7b53bc4`)
- **Database hardening**: all timestamps stored as UTC ISO strings.
  Indexes on `pageviews(timestamp)`, `pageviews(path)`,
  `contactRequests(submission)`, `leads(submission)`. New
  `prune_old_pageviews(days)` function; `insert_pageview` opportunistically
  prunes (1% probability) so the table stays bounded without requiring
  a cron. (`7b53bc4`)
- **Hero typing animation** decoupled from literal text — driven by a
  `data-typed` attribute so renaming "NIK" doesn't silently disable
  the effect. (`4e3f31a`)
- **Stats bar**: fake "15+ Happy Clients" removed; "3+ Years Experience"
  corrected to "6+ Years in BI & Data Science". (`aabb83e`)
- **Google Fonts** loaded via `<link rel="preload" as="style">` +
  media-print swap pattern; the `@import` was render-blocking. (`1796f4f`)
- **Footer contrast**: body text 0.5 → 0.7 white (9.14:1, was 5.27:1);
  copyright 0.3 → 0.55 white (6.22:1, was 2.66:1 — failed WCAG AA). (`5284932`)
- **Service worker**: HTML cache no longer unbounded — skips `/analytics`,
  `/sitemap.xml`, `/robots.txt`, `/blog/feed.xml`, `/api/*` and applies
  a soft 30-entry cap. CACHE_NAME bumped to v4. (`a3d981b`)
- **Analytics dashboard**: heavy inline styles extracted to
  `.analytics-*` CSS classes; now themeable. (`a3d981b`)
- **Profile image**: 192 KB PNG → 158 KB via 96-color palette
  quantization; WebP fallback re-exported at 22 KB. (`a3d981b`)
- **Search route**: page titles/descriptions now pulled from
  translations so search results localise too. (`d9fbfeb`)
- **Project URLs in `app.py`**: `project_slugs` hardcoded since all
  scenarios render from one template; no longer derived from
  `os.listdir`. (`d9fbfeb`)

### Removed
- **Fake testimonials** — five named placeholder testimonials
  ("Sarah M. - FinEdge AG", etc.) deleted from the home page along
  with the carousel widget, `carousel.js`, ~90 lines of `.carousel-*`
  CSS, and the `sections.testimonials` translation key. (`aabb83e`)
- **`form_submitted.html`**, **`admin.html`**, **`wrong-credentials.html`**
  — orphan templates referencing no routes. (`55860f1`, `4e3f31a`)
- **`TODO.md`** — 2023, referenced pre-rebrand items, all done. (`a3d981b`)
- **`logo-old-data-science.png`** — pre-rebrand logo backup. (`a3d981b`)
- **`linkedin-seeklogo.com.svg`** — precached but never used. (`a3d981b`)
- **`styles.css`** — split into four files; the monolith no longer
  exists. (`cf105a2`)

### Fixed
- **WCAG AA failure** in the footer copyright (was 2.66:1). (`5284932`)
- **Stale brand**: nav-bar logo said "Clasen Data Science" while
  site copy said "Niklas Clasen Consulting / Technology Consultant". (`c271c1c`)
- **`thank_you.html`** still referencing "Case Studies" after the
  "Project Scenarios" rename — fixed via translation key. (`d9fbfeb`)
- **404.html "Home" description** read `t.hero.greeting` = "Hello World,"
  out of context; now uses a real description string. (`d9fbfeb`)
- **`.modular-container-services-one/two`** were near-duplicates;
  `-two` was missing `backdrop-filter` and `transition`. Merged into
  one rule. (`cf105a2`)
- **`.container`** had `padding-left/right: var(--space-6)` immediately
  overridden by `padding-left/right: 0`. Dead override removed. (`cf105a2`)
- **`.card-hr` / `.card-hr-dark`** were identical; merged. (`cf105a2`)
- **`.service-list`** defined twice with different properties; merged. (`cf105a2`)
- **`make_response`** imported but never used. Removed. (`5dd41a7`)
- **`datetime.utcnow()`** deprecation. (`b7638eb`)
- **`_translations_cache` / `_blog_cache`** were not thread-safe; could
  race under threaded gunicorn workers. (`7b53bc4`)
- **CSP `:not(.js)` selector bug**: `:not(.js) .calc-container` matched
  any element without `.js` as ancestor (including `<body>`), so it
  always fired. Scoped to `html:not(.js)`. (`c0d8bd8`)
- **Jinja `.items` shadowing**: `t.services_page.items[key]` invoked
  `dict.items()` instead of subscripting. Renamed JSON keys to
  `packages` / `scenarios` / `bullets`. (`d9fbfeb`)

### Build & DX
- **`tests/`** harness with `conftest.py` that sets a tempfile
  `DATABASE_PATH` and disables WTF-CSRF and the rate limiter by default.
  Tests that need them re-enable locally. (`b7638eb`)
- **`pyproject.toml`** with ruff config. (`a3d981b`)
- **`requirements.txt`** gains `flask-limiter>=3.5`, `pytest>=8.0`,
  `ruff>=0.6`.
- **`.gitignore`** gains `.venv/`, `.claude/`, `.pytest_cache/`. (`55860f1`,
  `b7638eb`)
- **`.env` template** in `readme.md` documents `SMTP_*`, `NOTIFY_EMAIL`,
  `ANALYTICS_USER` / `ANALYTICS_PASSWORD`, `RATELIMIT_STORAGE_URI`,
  the `SECRET_KEY` generation command, and the fail-fast behaviour. (`5dd41a7`)

### Intentionally not done
- **Blueprint split of `app.py`**. File is 444 lines after all changes;
  the original audit said "not urgent until ~500 lines". Splitting
  would add churn without clear value at this size.
- **Type hints across the codebase**. Worth doing if the project grows;
  high effort, low marginal value at current size.
- **German tone review**. Translations were authored mechanically from
  the English copy and standard B2B/consulting German conventions —
  worth a human pass before relying on them for client conversations.
