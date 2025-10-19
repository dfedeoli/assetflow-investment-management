# Security Audit Command

You are a security audit agent tasked with scanning this codebase for exposed credentials, sensitive data, and security vulnerabilities.

## Your Mission

Perform a comprehensive security scan of the entire codebase focusing on:
1. **Exposed API Keys and Tokens** - Find any hardcoded secrets
2. **Sensitive Data Exposure** - Detect financial data, personal information, or credentials in code/comments

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

### Step 5: Generate Detailed Report

For each finding, provide:

1. **Severity Level:**
   - 🔴 **CRITICAL**: Real API keys, passwords, or tokens found
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
- [ ] [Failed checks appear here]

---

## 🔧 Recommended Actions

### Immediate (Within 24 hours)
1. Revoke any exposed API keys
2. Remove committed .env files from git history
3. Update .gitignore

### Short-term (Within 1 week)
1. Review all configuration files
2. Implement secret scanning in CI/CD
3. Set up pre-commit hooks

### Long-term (Ongoing)
1. Regular security audits
2. Developer security training
3. Automated secret scanning

---

## 📝 Notes

- This scan focused on exposed credentials and sensitive data
- For comprehensive security, consider: dependency vulnerabilities, code injection, XSS, CSRF
- Re-run this audit after making changes: `/security-audit`

```

## Important Guidelines

1. **Be Thorough:** Scan every file, even seemingly harmless ones
2. **Check Context:** Don't flag .env.example or documented placeholders
3. **Real vs Placeholder:** Distinguish between:
   - `OPENAI_API_KEY=sk-proj-123abc` (REAL - flag it!)
   - `OPENAI_API_KEY=your_openai_api_key_here` (placeholder - OK)
4. **No False Positives:** If you're unsure, mark as WARNING instead of CRITICAL
5. **Actionable Advice:** Always provide clear remediation steps

## Files to Explicitly Check

1. `.env` - Should NOT exist (only .env.example should)
2. All `**/*.py` files - Look for hardcoded secrets
3. `.gitignore` - Verify it excludes sensitive patterns
4. `*.db` files - Should be in .gitignore
5. Any `credentials.json`, `token.pickle`, or similar
6. Configuration files in project root

## Start Your Audit Now

Begin by saying:

"🔍 Starting comprehensive security audit..."

Then systematically scan the codebase and generate the detailed report above.
