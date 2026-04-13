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
   FLASK_DEBUG=True
   SECRET_KEY=your-secret-key-here
   DATABASE_PATH=staging.db
   ```

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
