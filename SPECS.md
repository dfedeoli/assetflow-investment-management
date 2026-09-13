# AssetFlow — Product Specifications

> This document describes **what** the product does and **why**, not how it's built.
> It is the source of truth for product decisions. Update it when intent changes.

---

## Who This Is For

A Brazilian individual investor managing a diversified portfolio across multiple asset types (Renda Fixa, Fundos, FIIs, Previdência, COE, etc.). The investor:

- Has assets spread across brokers and account types
- Wants to follow a deliberate allocation strategy (targets by category)
- Makes regular contributions, especially to PGBL for tax deduction
- Wants to see portfolio evolution over time and understand the impact of each investment decision
- Does their own tax planning (Imposto de Renda) and needs to track deductible limits

---

## Core Concepts

### Portfolio Snapshot

The portfolio is tracked through dated snapshots — a complete picture of all positions at a given moment. When you import data or register a contribution, you're recording "this is what my portfolio looked like on this date."

This model is intentional: it means every historical date is accurate on its own, without needing to reconstruct history from transactions. Comparing two dates always gives you the true state of the portfolio at each point.

### Contribution vs. Market Value Change

These are fundamentally different things and the product must never confuse them:

- **Contribution:** New money the user actively put into an asset. The user knows the exact amount and date. This is capital deployed — it matters for tax tracking (especially PGBL) and for calculating true investment returns.
- **Market value change:** The asset grew or shrank because of price movement. No money moved; the market moved.

When the user updates an asset's value after a period of time, that delta is market appreciation — not a contribution. If on top of that the user also deposited new money, those are two separate events and must be recorded separately. The product must make this distinction explicit and never silently assume a value change is a contribution or vice versa. Getting this wrong inflates gain/loss numbers and corrupts PGBL tracking.

### Categories

Every asset belongs to exactly one category. Categories are not optional or freeform — they are a fixed set defined by the user's investment strategy. Every asset must be assigned to one; nothing can be uncategorized.

The current categories are:

| Category | Role |
|---|---|
| **Estabilidade** | Low-risk, capital preservation assets |
| **Diversificação** | Broad diversification across geographies or asset classes |
| **Valorização** | Growth-oriented, higher risk/return assets |
| **Antifragilidade** | Assets that benefit from volatility or crisis (e.g., gold, crypto) |
| **Segurança** | Emergency reserve — liquid, safe, always accessible |

These same categories apply to both regular investments and Previdência investments. The distinction between regular and Previdência is tracked separately (see below), not through different category names.

Within each category, individual assets can also have a target allocation percentage (as a share of the category total). This is important for volatile assets that should be capped — for example, a speculative fund might be limited to 20% of Valorização even if Valorização as a whole is 30% of the portfolio.

### Previdência — A Separate Portfolio

Previdência assets share the same categories as regular investments (Estabilidade, Valorização, etc.), but they are managed as a completely separate portfolio. They have a 10+ year time horizon, follow different tax rules (PGBL deduction), and should never appear mixed into the regular portfolio views.

The split is:
- **Investimentos portfolio:** Regular investments. Rebalancing, allocation targets, and evolution tracked here.
- **Previdência portfolio:** Retirement investments. Entirely separate allocation targets, rebalancing, and PGBL tracking. Uses the same category taxonomy, but the percentages and targets are independent.

When the user looks at their Investimentos portfolio, Previdência is not there. When the user manages Previdência, they only see Previdência assets. History and contribution tracking can surface both, but always labeled clearly.

### Emergency Reserve (Segurança)

The "Segurança" category holds the emergency reserve. The user defines a minimum amount that must always be kept there (e.g., R$ 50,000). Any amount above that minimum is considered available for active investing and surfaced automatically in rebalancing suggestions. The reserve floor itself is never touched by rebalancing logic.

---

## Features

### 1. Tracking What You Own

The user needs to keep an up-to-date record of their portfolio. There are several situations they might be in:

- **Regular broker export:** The broker provides an XLSX or PDF file with all positions. User imports it and gets a full snapshot. Value changes from the previous snapshot are treated as market movement — not contributions.
- **AI-extracted statement:** When only a PDF statement is available (not a clean export), the user uploads it and an AI model reads the positions. Multi-page PDFs are supported, with the ability to select which pages to process (for cost control).
- **Single asset:** User manually types in one new position or corrects a value.
- **Updating values:** User focuses on one asset at a time, entering the current market value. The product shows the asset's last known value for context and records the delta as market movement. This should never feel like scrolling through a list of 20+ assets — the workflow is focused, one asset at a time.
- **Editing a past snapshot:** User loads a previous date and corrects mistakes, saving back to the same date.

Regardless of method, the result is the same: a complete portfolio snapshot at a specific date.

---

### 2. Recording Contributions

When the user puts new money into an investment, they record a contribution separately from any value update. This is distinct from a market value change: a contribution is capital the user chose to deploy on a specific date.

The user records: the asset, the amount added, and the date. The product adds that amount to the last known value, updates the cost basis, and creates a new snapshot — carrying all other positions forward unchanged.

Multiple contributions on the same date can be batched.

**Why keeping this separate matters:** If a PGBL fund went from R$ 100k to R$ 120k and the user also deposited R$ 15k, the true market return was only R$ 5k. If contributions and market changes are conflated, gain/loss analysis is wrong and PGBL tracking becomes unreliable. The product must make it easy to record contributions explicitly and must never infer a contribution from a value change.

A contribution can also create a new asset that didn't exist in the last snapshot (first-time purchase).

---

### 3. Classifying Assets

Every asset must be assigned to one of the fixed categories. This is not optional — uncategorized assets are flagged prominently and excluded from all analysis until classified.

The mapping is permanent: once classified, an asset keeps its category across all future snapshots. The user only does this once per asset.

Within each category, the user can also set a target allocation for individual assets (as a percentage of the category total). This matters for volatile assets that should be capped — e.g., a speculative fund limited to 20% of Valorização even if Valorização itself is 30% of the portfolio.

---

### 4. Setting Allocation Targets

The user defines target percentages for each category — separately for the Investimentos portfolio and for Previdência, since they are independent portfolios with different time horizons.

**Investimentos portfolio targets** (Estabilidade, Diversificação, Valorização, Antifragilidade) must sum to 100%, excluding Segurança. The Segurança category is managed by a minimum reserve amount (R$), not a percentage.

**Previdência targets** are set independently and must also sum to 100% within Previdência. They do not interact with Investimentos portfolio targets.

Within each category, individual assets can have their own target weight (% of the category). These are optional but recommended for volatile positions.

---

### 5. Rebalancing Analysis

Rebalancing runs independently for the Investimentos portfolio and for Previdência.

**For the Investimentos portfolio**, the user sees:
- Current vs. target allocation per category, with status: balanced (±0.5%), overweight, or underweight.
- How much to invest or reallocate to reach target.
- If the user enters additional cash to deploy, the product shows exactly how to split it across underweight categories.
- Within each category, how to distribute the investment across individual assets — proportionally to current weights, or equally.
- Segurança excess (above the reserve minimum) is surfaced automatically as available capital.

**For Previdência**, the same logic runs independently using Previdência-only positions and Previdência-only targets.

The two analyses are never mixed.

---

### 6. Previdência as a Separate Portfolio

Previdência investments are managed entirely apart from the Investimentos portfolio. They share the same category taxonomy (Estabilidade, Diversificação, Valorização, Antifragilidade) but have their own allocation targets, their own rebalancing view, and their own contribution history tied to PGBL tracking.

The user never sees Previdência assets in the Investimentos portfolio view, and vice versa. History and totals can optionally show a combined net worth view, but the two portfolios are always clearly separated.

---

### 7. PGBL Tax Planning

Brazilian investors who contribute to INSS (or public pension) can deduct up to **12% of their taxable annual income** from their tax return by investing in PGBL plans. The deduction must be made by December 31st and claimed in the following year's IR filing.

The product helps the user track this limit throughout the year:

**What the user does:**
- Confirms they contribute to INSS for that year (required for eligibility)
- Records monthly income entries by type (salary, vacation pay, rental income, pension, etc.)
- Views how much they've already invested in PGBL (tracked from contributions to Previdência assets)

**What the user sees:**
- Total taxable income for the year
- PGBL deduction limit (12% of taxable income)
- How much has already been invested in PGBL
- How much remains to invest to maximize the deduction
- A progress percentage and countdown to December 31st
- An annual income projection if the user doesn't yet have a full year of data

**Income rules (Brazilian tax law):**
- Taxable (counts toward the 12% limit): salary, vacation pay, vacation bonus (1/3), pension, rental income, other regular income
- Non-taxable (excluded): 13th salary and PLR (profit sharing) — these have separate taxation at source and do not count

---

### 8. Portfolio History & Evolution

The user can view how their portfolio has evolved over time:

- **Overall timeline:** Total portfolio value across all snapshot dates. Shows growth in absolute and percentage terms.
- **Period comparison:** Pick two specific dates and compare the portfolio state — value changes, new positions added, positions that disappeared.
- **Category evolution:** Track how each category's value and allocation percentage changed over a date range.
- **Contribution history:** See all recorded contributions, filtered by asset or time period, with aggregations by month, quarter, or year. See the gain/loss per asset: how much value is from market appreciation vs. capital invested.

---

## Business Rules Summary

| Rule | Detail |
|---|---|
| Snapshot model | Every date stores the complete portfolio, not diffs |
| Categories | Fixed set: Estabilidade, Diversificação, Valorização, Antifragilidade, Segurança |
| Every asset must be categorized | Uncategorized assets are flagged and excluded from all analysis |
| Asset category | One asset → one category; applied retroactively to all snapshots |
| Investimentos portfolio targets | Must sum to 100% across Estabilidade, Diversificação, Valorização, Antifragilidade |
| Previdência targets | Independent from Investimentos portfolio; must sum to 100% within Previdência |
| Asset-level targets | Optional % of the parent category; recommended for volatile positions |
| Rebalancing tolerance | ±0.5% is considered balanced |
| Rebalancing scope | Investimentos portfolio and Previdência are rebalanced independently, never mixed |
| Emergency reserve | Segurança managed by minimum R$ amount, not %; excess surfaces as available capital |
| Contribution vs. market change | Value updates from imports = market movement; explicit contribution entries = capital deployed |
| Contribution math | new_total = last_known_value + contribution_amount |
| New asset via contribution | A contribution can create an asset not in the last snapshot (first purchase) |
| Gain calculation | gain = current_value − invested_value (invested_value = sum of all contributions) |
| PGBL limit | 12% of taxable income (13th salary and PLR excluded) |
| PGBL eligibility | Requires INSS or public pension contribution |
| PGBL deadline | December 31st to claim in following year's IR |
| PGBL tracking | Based on contribution entries to Previdência assets, not on value snapshots |

---

## Input & UX Principles

### Numeric Input

All currency and percentage fields must behave like a calculator or ATM, not like a text box:

- The field starts at `0,00` (or `0%`).
- As the user types digits, they fill in from the right: typing `1` gives `0,01`, typing `5` gives `0,15`, typing `0` gives `1,50`.
- The user never needs to position a cursor, type a comma, or clear a field before entering a value.
- Backspace removes the last digit, shifting right.
- No thousand separators in the input field — `12345,67` not `12.345,67`. Separators add visual noise and make editing harder; the comma-separated decimal is sufficient.
- This applies everywhere: contribution amounts, position values, target percentages, reserve amounts.

The goal is that entering a value feels instant and error-free, especially on a touchscreen or when updating many fields in sequence.

---

## What This Product Is Not

- Not a brokerage or execution platform — it tracks and analyzes, never executes trades
- Not multi-user — it's a personal tool for one investor
- Not connected to broker APIs — data comes in via file import or manual entry
- Not a tax calculator — PGBL planning helps with deduction tracking, but does not file returns
