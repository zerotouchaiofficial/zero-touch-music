# Maintenance Guide — YT Auto-Uploader

This document provides guidance for maintaining and updating the YT Auto-Uploader project.

---

## 1. Updating Dependencies
- Check `requirements.txt` for outdated packages:
- Update packages carefully, test locally before deploying.
- Ensure compatibility with Python 3.10+.

---

## 2. GitHub Actions Workflow
- Workflow file: `.github/workflows/auto_upload.yml`
- If updating cron schedule or pipeline steps:
1. Edit the YAML file in your fork.
2. Commit changes and monitor workflow logs.
- Check Actions logs regularly to ensure uploads complete successfully.

---

## 3. API Quotas & Tokens
- YouTube API has a daily quota (10,000 units/day). Monitor usage.
- Refresh tokens may expire; regenerate using `get_refresh_token.py` if errors occur.
- Keep `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, and `YT_REFRESH_TOKEN` secure in GitHub Secrets.

---

## 4. Troubleshooting
- `quotaExceeded` → Verify API usage; reduce upload frequency if needed.
- `Token refresh failed` → Re-run `get_refresh_token.py` and update secret.
- `yt-dlp: Video unavailable` → Video removed; pipeline skips automatically.
- `ffmpeg not found` → Install locally or confirm Actions environment.

---

## 5. Versioning & Changelog
- Track updates in `CHANGELOG.md`.
- Test all new features in a private/unlisted environment before going live.

---

## 6. Best Practices
- Do not commit secrets or API keys to the repo.
- Review third-party dependencies for security risks.
- Regularly monitor logs for failed uploads or errors.
- Keep documentation updated for contributors.

---

Maintained by: **zerotouchai.official@gmail.com**
