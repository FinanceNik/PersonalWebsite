# Niklas Clasen Consulting - Website

Personal website and blog for a technology consultant specializing in Microsoft Fabric, Power BI, and data platform strategy. Built with Flask.

## Prerequisites

- Python 3.10+
- pip

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/FinanceNik/PersonalWebsite.git
   cd PersonalWebsite
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root:
   ```
   FLASK_DEBUG=False
   SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
   DATABASE_PATH=staging.db
   SITE_URL=https://yourdomain.example
   ANALYTICS_USER=admin
   ANALYTICS_PASSWORD=<a strong password>

   # Lead notifications — leave blank to log to stderr instead.
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=you@example.com
   SMTP_PASSWORD=<app password>
   SMTP_FROM=you@example.com
   NOTIFY_EMAIL=you@example.com

   # Multi-worker only — defaults to in-memory.
   RATELIMIT_STORAGE_URI=memory://
   ```

   Notes:
   - `FLASK_DEBUG=True` enables Werkzeug's interactive debugger, which is an RCE vector. Only use it on your local machine.
   - When `FLASK_DEBUG` is not `True`, the app refuses to start unless `SECRET_KEY` is set to a non-placeholder value.
   - `ANALYTICS_USER` / `ANALYTICS_PASSWORD` gate the `/analytics` dashboard via HTTP Basic Auth. If either is unset, the route returns 404.
   - **Lead notifications**: when SMTP env vars are set, every `/submit_contact_form` and `/download-checklist` submission emails `NOTIFY_EMAIL` with the lead's details (Reply-To set to their address). When SMTP is unset, the submission is logged to stderr in a clearly-bracketed block so it shows up in `journalctl` or `docker logs` — lead capture is never silently broken.
   - **Rate limits**: form submits capped at 5/hour per IP; `/api/pageview` at 60/minute. Both forms include a hidden honeypot field that silently drops bot submissions.
   - **Security headers** (CSP, X-Frame-Options: DENY, Referrer-Policy, Permissions-Policy) are set on every response. HSTS is added only when `FLASK_DEBUG` is False.

## Usage

```bash
python app.py
```

The site will be available at `http://localhost:5000`.

## Blog

Blog posts are markdown files in the `blog_posts/` directory. Each post uses frontmatter for metadata:

```markdown
---
title: Your Post Title
date: 2026-04-01
summary: A short summary of the post.
---

Your markdown content here...
```

New posts are automatically picked up when the page loads.

## Project Structure

```
PersonalWebsite/
  app.py                  # Flask application and routes
  database_helper.py      # SQLite database helpers
  blog_posts/             # Markdown blog posts
  templates/              # Jinja2 HTML templates
    global-templates/     # Shared nav, footer, pre-footer
    projects/             # Case study detail pages
  static/
    css_components/       # Modular CSS (colors, sizes, nav, footer, main styles)
    js_components/        # Theme toggler, FAQ accordion, matrix animation
    image_assets/         # Logos, profile image, icons
```
