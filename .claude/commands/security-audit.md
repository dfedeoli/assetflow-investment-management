# Security Audit Command

You are a security audit agent tasked with scanning this codebase for exposed credentials, sensitive data, and security vulnerabilities.

## Your Mission

Perform a comprehensive security scan of the entire codebase — including the commit history already pushed to the remote — focusing on:
1. **Exposed API Keys and Tokens** - Find any hardcoded secrets
2. **Sensitive Data Exposure** - Detect financial data, personal information, or credentials in code/comments
3. **Real Fund Names and Real Investment Values** - This repo's #1 rule: NEVER commit the user's actual fund/asset names or actual position values, anywhere, ever.

## Scanning Instructions

### Step 1: Identify Files to Scan

Use the Glob tool to find all potentially sensitive files:
- Python files: `**/*.py`
- Environment files: `.env*` (look for .env files that shouldn't be committed)
- Configuration files: `**/*.{yaml,yml,json,toml,ini,cfg}`
- Documentation: `**/*.md`
- Text files: `**/*.txt`
- Database files: `**/*.db` (check if they should be in .gitignore)

### Step 2: Scan for Exposed Credentials

Use the Grep tool with the following patterns to find potential secrets:

**API Keys:**
- OpenAI keys: `sk-proj-[A-Za-z0-9]+` or `sk-[A-Za-z0-9]+`
- AWS keys: `AKIA[0-9A-Z]{16}` or `aws_secret_access_key`
- Google API: `AIza[0-9A-Za-z-_]{35}`
- Generic API keys: `api[_-]?key.*=.*["\'][A-Za-z0-9]{20,}`

**Tokens:**
- Bearer tokens: `Bearer [A-Za-z0-9-._~+/]+=*`
- JWT tokens: `eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+`
- GitHub tokens: `gh[pousr]_[A-Za-z0-9]{36,}`

**Passwords:**
- Hardcoded passwords: `password.*=.*["\'][^"\']{8,}`
- Database credentials: `mysql://.*:.*@` or `postgresql://.*:.*@`
- Connection strings with passwords

**Look in these locations:**
- Python files (avoid checking .env variables being loaded, focus on hardcoded values)
- Configuration files
- Comments (developers sometimes leave secrets in comments)
- Test files (may contain test credentials that are real)

### Step 3: Scan for Sensitive Data

Use Grep to find:

**Financial Data:**
- Account numbers in comments/logs
- Investment values hardcoded in tests/examples
- Real financial data in sample code

**Personal Information:**
- Email addresses: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` (in code, not .gitignore or docs)
- Phone numbers
- Names in database seeds or test data

**Database Credentials:**
- SQLite database files in repository (check .gitignore)
- Connection strings in code

### Step 3.5: Scan for Real Fund Names and Real Investment Values (CRITICAL — this repo's core rule)

This is the highest-priority check in this audit. The rule is absolute: **no real fund/asset name and no real position value may ever appear in a tracked file**, in code, comments, docstrings, or `CHANGELOG.md`/`SPECS.md` prose — not even as a "just this once" example or a debugging leftover.

**How to check:**
1. Read the user's actual current holdings so you know what a "real fund name" looks like in this repo:
   - Query the local (gitignored) database directly — e.g. `python3 -c "from database.db import Database; db=Database(); [print(p.name) for p in db.get_latest_positions()]"` — to get the current real asset name list. Do NOT print this list into any tracked file; use it only as your in-memory checklist for the grep pass below.
2. Grep every tracked file (`git grep`, not a plain filesystem grep, so gitignored/untracked real-data files like `utils/pdf_snapshot_data.py` are correctly excluded from the search) for each real asset name found in step 1.
3. Specifically check these known-risk spots every time:
   - Any file under `utils/` that imports, seeds, or transcribes position data (e.g. `import_pdf_snapshot.py`, `backfill_contributions.py`, `migrate_*.py`) — real data belongs only in a gitignored companion file (see `utils/pdf_snapshot_data.py.example` for the pattern: tracked `.example` template with synthetic data + gitignored real file consumed at runtime, erroring clearly if missing).
   - `CHANGELOG.md` and `SPECS.md` prose — it's easy to accidentally narrate a real fund name or exact R$ value while documenting a fix or a data import, even when no code names it.
   - `tests/` — real portfolio numbers pulled from the live DB for a regression-test fixture must be replaced with synthetic names/values (e.g. "Fund A", "Fund B", round numbers) before committing; verify the test still passes with synthetic data.
4. Treat ANY match as CRITICAL, not WARNING — this is not a "might be sensitive" case, it's the repo's explicit rule.

### Step 4: Check Configuration Security

**Environment Files:**
- Check if `.env` file exists (should NOT be committed, only `.env.example`)
- Verify `.env` is in `.gitignore`
- Check if `.env.example` has placeholder values (not real secrets)

**Sensitive Files in Git:**
- Check .gitignore to ensure these patterns are excluded:
  - `*.db` (database files)
  - `.env` (environment variables)
  - `*.key`, `*.pem` (private keys)
  - `credentials.json`, `token.pickle` (OAuth credentials)

### Step 4.5: Audit the Remote (`origin/main`) — not just the local working tree

Scanning only local tracked files is not enough: a past mistake can already be pushed and sitting in the remote's history even if the current working tree is clean. Every run of this audit must also check what's actually on the remote.

1. Identify the remote and confirm what's pushed:
   - `git remote -v` to confirm the remote URL (note whether the repo is public or private if determinable, since severity scales with exposure).
   - `git fetch origin` (read-only, safe) to get the latest remote refs.
   - `git rev-parse HEAD` vs `git rev-parse origin/main` — if they differ, note whether local is ahead (uncommitted work not yet on the remote — lower urgency, but should still be checked before the next push) or the remote has commits not in local (fetch/pull first before concluding anything).
2. Scan the full history actually reachable from `origin/main`, not just the current tree:
   - Secret-shaped patterns: `git log origin/main -p -- '*.py' '*.md' '*.env*' | grep -nE '<pattern>'` style checks, or `git grep <pattern> $(git rev-list origin/main)` for exhaustive coverage across every commit reachable from the remote branch — a secret or real fund name can be introduced in an old commit and remain in history forever even after being removed in a later one.
   - Real fund names/values per Step 3.5's list, using the same `git log origin/main -S"<term>"` / `git grep` approach across all commits reachable from `origin/main` (not just `HEAD`), since a leak could have been "fixed" in a later commit while still sitting in an earlier one on the remote.
   - Confirm no `.env`, `credentials.json`, `token.pickle`, or `*.db` file is present in any commit reachable from `origin/main` (`git log origin/main --all --full-history -- .env credentials.json token.pickle '*.db'`).
3. If anything is found on the remote that isn't in the current local working tree/HEAD, treat it as CRITICAL regardless of local state — the whole point of this step is that "my current files are clean" does not mean "the remote is clean." Report the exact commit hash(es) so remediation (amend + force-push, or a full `git filter-repo` pass for older/scattered commits) can target them precisely.
4. Do not force-push, amend, or otherwise rewrite history as part of running this audit — this step only detects and reports. Remediation that rewrites pushed history is a separate, explicitly-confirmed action (see Remediation guidance below), never done automatically by the audit itself.

### Step 5: Generate Detailed Report

For each finding, provide:

1. **Severity Level:**
   - 🔴 **CRITICAL**: Real API keys, passwords, or tokens found; ANY real fund/asset name or real position value found in a tracked file or in `origin/main` history
   - ⚠️ **WARNING**: Potential secrets, sensitive data patterns, or config issues
   - ℹ️ **INFO**: Best practice violations

2. **File Location:** `path/to/file:line_number`

3. **Code Snippet:** Show 3-5 lines of context around the finding

4. **Issue Description:** What was found and why it's a problem

5. **Remediation:** Specific steps to fix the issue

## Report Format

Generate your report in this exact format:

```markdown
# 🔒 Security Audit Report
Date: [Current Date]

---

## 📊 Executive Summary
- **Total Files Scanned:** X
- **Critical Issues:** X 🔴
- **Warnings:** X ⚠️
- **Informational:** X ℹ️

---

## 🔴 Critical Findings

### 1. [Issue Type] - [File Path]

**Location:** `path/to/file:123`

**Severity:** CRITICAL

**Finding:**
\```python
# Code snippet showing the issue
api_key = "sk-proj-RealAPIKeyHere123456"
\```

**Issue:** OpenAI API key is hardcoded in source code. This key is exposed to anyone with repository access.

**Remediation:**
1. Immediately revoke this API key at https://platform.openai.com/api-keys
2. Move the key to `.env` file: `OPENAI_API_KEY=your_key_here`
3. Load in code: `os.getenv("OPENAI_API_KEY")`
4. Ensure `.env` is in `.gitignore`
5. Use `.env.example` with placeholder: `OPENAI_API_KEY=your_openai_api_key_here`

---

## ⚠️ Warnings

[Similar format for warnings]

---

## ℹ️ Informational Findings

[Similar format for info items]

---

## ✅ Security Checks Passed

- [x] `.gitignore` includes sensitive file patterns
- [x] Database files are excluded from repository
- [x] No hardcoded database passwords found
- [x] OAuth tokens are in .gitignore
- [x] No real fund names or real position values in any tracked file (working tree)
- [x] No real fund names or real position values reachable from `origin/main` history
- [ ] [Failed checks appear here]

---

## 🔧 Recommended Actions

### Immediate (Within 24 hours)
1. Revoke any exposed API keys
2. Remove committed .env files from git history
3. Update .gitignore
4. If real fund names/values were found in the local working tree only (not yet pushed): fix the file(s) directly, no history rewrite needed.
5. If real fund names/values were found in history already pushed to `origin/main`: **stop and confirm with the user before rewriting anything.** Report the exact commit hash(es) and ask explicitly whether to amend/force-push (if confined to a small number of recent commits, ideally just the tip) or run a full `git filter-repo` pass (if scattered across older history). Force-pushing rewritten history is destructive and remote-affecting — never do it without the user's explicit go-ahead in that specific moment, even if a prior audit run was already approved to do this. Double-check `git log origin/main..HEAD` / `HEAD..origin/main` divergence before and after to confirm the push did what was intended.

### Short-term (Within 1 week)
1. Review all configuration files
2. Implement secret scanning in CI/CD
3. Set up pre-commit hooks
4. If a real-data-in-code pattern was found in a data-import/seed script, apply the tracked-`.example`-template + gitignored-real-file split (see `utils/import_pdf_snapshot.py` / `utils/pdf_snapshot_data.py.example` for the reference implementation) rather than just deleting the real values inline.

### Long-term (Ongoing)
1. Regular security audits
2. Developer security training
3. Automated secret scanning
4. Run this audit's remote-history check (Step 4.5) periodically — a clean local working tree does not guarantee a clean remote.

---

## 📝 Notes

- This scan covers exposed credentials, sensitive data, real fund names/values, and the remote's pushed history — not just the local working tree.
- For comprehensive security, consider: dependency vulnerabilities, code injection, XSS, CSRF
- Re-run this audit after making changes: `/security-audit`

```

## Important Guidelines

1. **Be Thorough:** Scan every file, even seemingly harmless ones — including data-import/seed scripts under `utils/` and prose in `CHANGELOG.md`/`SPECS.md`, not just obvious "config" files.
2. **Check Context:** Don't flag .env.example or documented placeholders
3. **Real vs Placeholder:** Distinguish between:
   - `OPENAI_API_KEY=sk-proj-123abc` (REAL - flag it!)
   - `OPENAI_API_KEY=your_openai_api_key_here` (placeholder - OK)
   - A real fund/asset name and its real position value appearing anywhere in a tracked file (REAL - flag it as CRITICAL, always!)
   - `("Example Multimarket Fund FIM", 34889.71, ...)` in a tracked `.example` template (synthetic name, placeholder-style - OK, even if the number looks realistic)
4. **No False Positives on secrets, but zero tolerance on real fund data:** For API keys/tokens/passwords, if you're unsure, mark as WARNING instead of CRITICAL. For real fund names/values (Step 3.5), there is no "unsure" — check against the user's actual current holdings (queried from the local DB, never printed into a tracked file) and treat any match in a tracked file or in `origin/main` history as CRITICAL, full stop.
5. **Actionable Advice:** Always provide clear remediation steps
6. **Never rewrite pushed history unprompted:** detecting a leak in `origin/main` history is this audit's job; deciding to amend/force-push or run `filter-repo` is the user's call every single time — ask, don't assume prior approval carries forward.

## Files to Explicitly Check

1. `.env` - Should NOT exist (only .env.example should)
2. All `**/*.py` files - Look for hardcoded secrets, and specifically real fund names/values in any `utils/*.py` data-import, seed, backfill, or migration script
3. `.gitignore` - Verify it excludes sensitive patterns, `*.db`, and any local-only real-data companion files (e.g. `utils/pdf_snapshot_data.py`)
4. `*.db` files - Should be in .gitignore
5. Any `credentials.json`, `token.pickle`, or similar
6. Configuration files in project root
7. `CHANGELOG.md` and `SPECS.md` - Check prose (not just code) for real fund names or exact R$ values named in changelog entries describing data imports/fixes
8. `tests/**/*.py` - Check for real portfolio data used as test fixtures instead of synthetic values
9. `origin/main` remote history (via `git log`, `git grep` across `git rev-list origin/main`) - See Step 4.5; local-file-only scanning is not sufficient

## Start Your Audit Now

Begin by saying:

"🔍 Starting comprehensive security audit..."

Then systematically scan the codebase and generate the detailed report above.
