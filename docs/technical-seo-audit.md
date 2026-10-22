# Technical SEO audit

**Status:** Initial local-demo audit only; it is not an audit of a public WordPress site.

| Check | Local demo result | Evidence |
|---|---|---|
| Titles and meta descriptions | Present on content pages | `website/*.html` |
| H1 hierarchy | One clear H1 per page | `website/*.html` |
| Internal navigation | Present | local crawler output during testing |
| Canonical URLs | Present, localhost values | `website/*.html` |
| robots.txt and sitemap | Present | `website/robots.txt`, `website/sitemap.xml` |
| HTTPS / public indexing | Not tested or claimed | Requires deployed domain |
| Schema, Core Web Vitals, GA4, GSC | Not implemented | Pending WordPress site |
