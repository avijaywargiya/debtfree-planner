# DebtFree Planner

**Compare debt payoff strategies and see the smartest path to becoming debt-free.**

> **Disclaimer:** This tool is for illustration purposes only and does not constitute financial, tax, credit, lending, or investment advice.

---

## What the App Does

DebtFree Planner is a local Streamlit web app that helps individuals and families make smarter decisions about their debt. It answers six key questions:

1. Which debt payoff method works best for me?
2. How long will it take to become debt-free?
3. How much interest will I pay under different strategies?
4. Should I use extra cash to pay off debt, invest, or build emergency savings?
5. Which debt is creating the most financial pressure?
6. What monthly payment do I need to become debt-free by a target date?

All calculations run locally — no internet connection, login, database, or paid API required.

---

## File Structure

```
DebtFreePlanner/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── .streamlit/
│   └── config.toml         # Sets default port to 8513
└── utils/
    ├── __init__.py
    └── calculations.py     # Pure calculation functions (no Streamlit)
```

---

## How to Install

**Requirements:** Python 3.11 or later recommended.

```bash
# 1. Clone or download the project folder
cd DebtFreePlanner

# 2. (Optional but recommended) Create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run Locally

```bash
streamlit run app.py
```

The app will open automatically in your default browser at `http://localhost:8513`.

---

## App Sections

### 1 · Profile & Assumptions
Enter your monthly income, expenses, savings, and extra payoff budget. The app computes your cash flow summary and warns you if spending exceeds income or your emergency fund is critically low.

### 2 · Debt Entry
Use the interactive table to add, edit, or remove debts. Each debt has a name, type, balance, APR, minimum payment, and optional fields (term, promo APR, priority override). The app ships with three sample debts so you can explore it immediately.

### 3 · Payoff Strategy Comparison
Runs four simulations in parallel and shows a comparison table plus charts:
- **Minimum Payments Only** — baseline
- **Debt Avalanche** — highest APR first
- **Debt Snowball** — lowest balance first
- **Custom Priority** — respects your priority overrides, promo expirations, then APR

### 4 · Debt-Free Target Planner
Enter a target timeline in months. The app uses binary search to find the exact extra monthly payment required to hit that date, labels it Feasible / Tight / Not Feasible, and suggests specific adjustments.

### 5 · Payoff vs Invest
Compares three allocation models over your chosen horizon:
- **Model A (Debt First):** All extra cash to debt, then invest freed-up cash
- **Model B (Invest First):** Minimums only on debt, invest everything else
- **Model C (Hybrid 70/30):** Split extra cash between debt and investing

Includes debt-by-debt APR classification and a recommendation that accounts for emergency fund, employer match, and risk preference.

### 6 · Emergency Fund Check
Classifies your current savings as Dangerously Low / Starter Cushion / Adequate / Strong and tells you how much you need to reach each level before aggressive debt payoff makes sense.

### 7 · Summary Report
One-page dashboard with all key metrics, the DebtFree Score, and download buttons for a CSV report and a Markdown summary.

---

## Payoff Strategy Explanations

### Debt Avalanche
Pay minimums on all debts, then direct every extra dollar to the debt with the **highest APR**. This minimises total interest paid — the mathematically optimal strategy.

*Best for:* People motivated by numbers who want to minimise cost.

### Debt Snowball
Pay minimums on all debts, then direct extra cash to the debt with the **smallest balance**. This pays off individual debts faster, creating psychological wins.

*Best for:* People who need early momentum to stay motivated.

### Custom Priority
Combines rule-based prioritisation:
1. Debts marked "Must Pay First"
2. Promotional 0% APR debts expiring soonest
3. Highest APR
4. Lowest balance as tiebreaker

*Best for:* Users with promo debt deadlines or specific debts they want to eliminate first.

### Minimum Payments Only
No extra payment applied. Used as the baseline to measure interest savings and time savings for other strategies.

---

## DebtFree Score (0–100)

The score starts at 100 and deductions are applied for financial risk factors:

| Factor | Max Deduction |
|--------|--------------|
| Debt payment burden > 50% of income | −25 |
| Debt payment burden > 35% of income | −15 |
| Debt payment burden > 20% of income | −8 |
| Weighted APR ≥ 20% | −15 |
| Weighted APR ≥ 15% | −10 |
| Weighted APR ≥ 10% | −5 |
| Emergency fund < 1 month | −20 |
| Emergency fund < 3 months | −10 |
| Emergency fund below target | −5 |
| Negative monthly cash flow | −15 |
| Very tight cash flow (<$100/mo free) | −5 |
| Payoff timeline > 20 years | −10 |
| Payoff timeline > 10 years | −5 |
| >50% of debt is revolving credit cards | −5 |

**Score bands:**

| Score | Label |
|-------|-------|
| 80–100 | Strong / Manageable |
| 60–79 | Needs Focus |
| 40–59 | Stretched |
| 0–39 | High Risk |

---

## Key Calculation Functions (`utils/calculations.py`)

| Function | Description |
|----------|-------------|
| `calculate_monthly_interest()` | One month of interest on a balance |
| `calculate_weighted_average_apr()` | Balance-weighted APR across all debts |
| `simulate_payoff_strategy()` | Full month-by-month debt payoff simulation |
| `calculate_required_payment_for_target()` | Binary search for required extra payment |
| `calculate_future_value()` | Future value of monthly investment contributions |
| `calculate_payoff_vs_invest()` | Compares Debt-First, Invest-First, Hybrid models |
| `calculate_emergency_fund_status()` | EF coverage months, gaps, status label |
| `calculate_debtfree_score()` | Composite 0–100 financial health score |
| `generate_markdown_report()` | Full markdown export of all results |
| `debts_df_to_list()` | Converts the Streamlit DataFrame to a list of dicts |

---

## Export Options

- **CSV Report** — debt table + strategy comparison table
- **Markdown Report** — full narrative report with all sections, suitable for saving or sharing

Both are available in the Summary Report tab via download buttons.

---

## Deploying to Streamlit Community Cloud

1. Push this project to a public GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account.
3. Select the repo and set the main file to `app.py`.
4. Click Deploy.

No additional configuration is required — all dependencies are in `requirements.txt`.

---

## Future Enhancement Ideas

- [ ] Save / load profile assumptions as JSON
- [ ] Debt consolidation loan comparison
- [ ] Balance transfer calculator (0% APR promo window)
- [ ] Student loan income-driven repayment options
- [ ] Mortgage payoff accelerator module
- [ ] Credit score impact estimator
- [ ] Snowball motivation tracker (visual milestone calendar)
- [ ] Monthly payoff schedule (printable)
- [ ] Printable PDF payoff plan
- [ ] AI-generated narrative summary
- [ ] Integration with broader family financial roadmap
- [ ] Dark mode theme option
- [ ] Multi-currency support

---

## Disclaimer

This tool is for illustration purposes only and does not constitute financial, tax, credit, lending, or investment advice. Always consult a qualified financial professional before making major financial decisions.
