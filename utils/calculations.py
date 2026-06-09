"""
DebtFree Planner — calculation engine.
All pure functions; no Streamlit imports.
"""

import copy
import calendar
import math
from datetime import date

DISCLAIMER = (
    "This tool is for illustration purposes only and does not constitute "
    "financial, tax, credit, lending, or investment advice."
)
MAX_SIM_MONTHS = 600


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_months(source_date: date, months: int) -> date:
    """Return source_date + N calendar months."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return source_date.replace(year=year, month=month, day=day)


def calculate_monthly_interest(balance: float, apr: float) -> float:
    """One month of interest on balance at given annual APR (percent)."""
    return balance * (apr / 100.0 / 12.0)


def calculate_weighted_average_apr(debts: list) -> float:
    """Balance-weighted average APR across active debts."""
    total = sum(d["balance"] for d in debts if d["balance"] > 0)
    if total == 0:
        return 0.0
    return sum(d["apr"] * d["balance"] for d in debts if d["balance"] > 0) / total


def calculate_future_value(monthly_pmt: float, annual_rate_pct: float, n_months: int) -> float:
    """Future value of level monthly contributions (ordinary annuity)."""
    if n_months <= 0:
        return 0.0
    if annual_rate_pct == 0:
        return monthly_pmt * n_months
    r = annual_rate_pct / 100.0 / 12.0
    return monthly_pmt * ((1 + r) ** n_months - 1) / r


def debts_df_to_list(df) -> list:
    """Convert the debt entry DataFrame to a list of dicts for calculations."""
    debts = []
    for _, row in df.iterrows():
        balance = float(row.get("Balance ($)", 0) or 0)
        if balance <= 0:
            continue
        promo_months_raw = row.get("Promo Months Left", 0)
        debts.append(
            {
                "name": str(row.get("Debt Name", "Unknown")),
                "type": str(row.get("Type", "Other")),
                "balance": balance,
                "apr": float(row.get("APR (%)", 0) or 0),
                "min_payment": float(row.get("Min Payment ($)", 0) or 0),
                "remaining_term": row.get("Term (mo)", None),
                "secured": bool(row.get("Secured", False)),
                "tax_deductible": bool(row.get("Tax Deductible", False)),
                "promo_apr": bool(row.get("0% Promo", False)),
                "promo_months_left": int(promo_months_raw) if promo_months_raw else 0,
                "priority_override": str(row.get("Priority", "Normal")),
                "notes": str(row.get("Notes", "") or ""),
            }
        )
    return debts


# ---------------------------------------------------------------------------
# Payoff order
# ---------------------------------------------------------------------------

def _get_payoff_order(active_debts: list, strategy: str) -> list:
    if strategy == "avalanche":
        return sorted(active_debts, key=lambda d: (-d["apr"], -d["balance"]))
    if strategy == "snowball":
        return sorted(active_debts, key=lambda d: (d["balance"], -d["apr"]))
    if strategy == "custom":
        def ckey(d):
            p = 0 if d.get("priority_override") == "Must Pay First" else 1
            promo = d.get("promo_months_left", 9999) if d.get("promo_apr") else 9999
            return (p, promo, -d["apr"], d["balance"])
        return sorted(active_debts, key=ckey)
    # minimum — no ordering needed
    return list(active_debts)


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def simulate_payoff_strategy(
    debts_input: list,
    extra_payment: float,
    strategy: str = "avalanche",
    max_months: int = MAX_SIM_MONTHS,
) -> dict:
    """
    Simulate monthly debt payoff.

    Returns dict:
        months, total_interest, total_payments, history (list of monthly dicts),
        warnings, first_paid, last_paid, focus_debt, reached_cap, debt_free_date
    """
    debts = copy.deepcopy(debts_input)
    active = [d for d in debts if d.get("balance", 0) > 0.01]

    empty = {
        "months": 0,
        "total_interest": 0.0,
        "total_payments": 0.0,
        "history": [],
        "warnings": [],
        "first_paid": None,
        "last_paid": None,
        "focus_debt": None,
        "reached_cap": False,
        "debt_free_date": date.today(),
    }
    if not active:
        return empty

    warnings = []
    for d in active:
        mi = calculate_monthly_interest(d["balance"], d["apr"])
        if d["apr"] > 0 and d["min_payment"] < mi * 0.999 and d["min_payment"] >= 0:
            warnings.append(
                f"'{d['name']}': min payment ${d['min_payment']:.0f} is less than "
                f"monthly interest ${mi:.0f}. Balance will grow."
            )

    available_extra = max(0.0, float(extra_payment))
    total_interest = 0.0
    total_payments = 0.0
    history = []
    first_paid = None
    last_paid = None
    reached_cap = False

    # Initial focus debt
    focus_debt_name = None
    if strategy != "minimum" and active:
        order0 = _get_payoff_order(active, strategy)
        focus = next(
            (d for d in order0 if d.get("priority_override") != "Avoid Accelerating"), None
        )
        focus_debt_name = focus["name"] if focus else None

    for month in range(1, max_months + 1):
        if not active:
            break

        month_interest = 0.0
        month_paid = 0.0

        # 1. Accrue interest
        for d in active:
            interest = calculate_monthly_interest(d["balance"], d["apr"])
            d["balance"] += interest
            month_interest += interest

        # 2. Apply minimum payments
        for d in active:
            pay = min(float(d["min_payment"]), d["balance"])
            d["balance"] = max(0.0, d["balance"] - pay)
            month_paid += pay

        # 3. Apply extra payment (not in minimum-only mode)
        if strategy != "minimum" and available_extra > 0.001:
            order = _get_payoff_order(active, strategy)
            extra_pool = available_extra
            for d in order:
                if d["balance"] <= 0.001:
                    continue
                if d.get("priority_override") == "Avoid Accelerating":
                    continue
                pay = min(extra_pool, d["balance"])
                d["balance"] = max(0.0, d["balance"] - pay)
                month_paid += pay
                extra_pool -= pay
                if extra_pool < 0.001:
                    break

        # 4. Identify paid-off debts; roll their minimums forward
        newly_paid = [d for d in active if d["balance"] <= 0.01]
        active = [d for d in active if d["balance"] > 0.01]

        for d in newly_paid:
            available_extra += float(d["min_payment"])
            if first_paid is None:
                first_paid = d["name"]
            last_paid = d["name"]

        total_interest += month_interest
        total_payments += month_paid

        history.append(
            {
                "month": month,
                "total_balance": sum(d["balance"] for d in active),
                "interest_paid": month_interest,
                "principal_paid": max(0.0, month_paid - month_interest),
            }
        )

        if month == max_months and active:
            reached_cap = True
            warnings.append(
                f"Simulation reached {max_months}-month cap. "
                "Increase payments or review minimum amounts."
            )

    months_to_payoff = len(history)
    debt_free_date = (
        add_months(date.today(), months_to_payoff) if not reached_cap else None
    )

    return {
        "months": months_to_payoff,
        "total_interest": round(total_interest, 2),
        "total_payments": round(total_payments, 2),
        "history": history,
        "warnings": warnings,
        "first_paid": first_paid,
        "last_paid": last_paid,
        "focus_debt": focus_debt_name,
        "reached_cap": reached_cap,
        "debt_free_date": debt_free_date,
    }


# ---------------------------------------------------------------------------
# Target planner
# ---------------------------------------------------------------------------

def calculate_required_payment_for_target(
    debts_list: list, target_months: int, strategy: str
) -> float | None:
    """
    Binary search for the extra monthly payment required to pay off
    all debts within target_months under the given strategy.
    Returns None if not feasible even with a single-month lump-sum payment.
    """
    if not debts_list:
        return 0.0

    # Can minimum payments alone meet the target?
    r0 = simulate_payoff_strategy(debts_list, 0.0, "minimum", max_months=target_months + 1)
    if r0["months"] <= target_months and not r0["reached_cap"]:
        return 0.0

    total_balance = sum(d["balance"] for d in debts_list)
    lo, hi = 0.0, total_balance  # worst case: pay everything month 1

    # Confirm hi is feasible
    r_hi = simulate_payoff_strategy(debts_list, hi, strategy, max_months=target_months + 1)
    if r_hi["months"] > target_months:
        return None

    for _ in range(60):
        if hi - lo < 0.50:
            break
        mid = (lo + hi) / 2.0
        r = simulate_payoff_strategy(debts_list, mid, strategy, max_months=target_months + 1)
        if r["months"] <= target_months and not r["reached_cap"]:
            hi = mid
        else:
            lo = mid

    return round(hi, 2)


# ---------------------------------------------------------------------------
# Payoff vs Invest
# ---------------------------------------------------------------------------

def calculate_payoff_vs_invest(
    debts_list: list,
    extra_payment: float,
    inv_return_pct: float,
    inv_tax_rate_pct: float,
    horizon_years: int,
    strategy: str = "avalanche",
) -> dict:
    """Compare Debt-First, Invest-First, and Hybrid (70/30) over a horizon."""
    horizon_months = horizon_years * 12
    after_tax_return = inv_return_pct * (1.0 - inv_tax_rate_pct / 100.0)
    total_min = sum(d["min_payment"] for d in debts_list)

    # --- Model A: Debt First ---
    r_a = simulate_payoff_strategy(debts_list, extra_payment, strategy, max_months=horizon_months)
    payoff_mo_a = r_a["months"]
    remaining_a = max(0, horizon_months - payoff_mo_a)
    # After payoff, invest freed cash (extra + all minimums)
    freed_a = extra_payment + total_min
    invest_a = calculate_future_value(freed_a, after_tax_return, remaining_a)
    debt_remain_a = 0.0 if not r_a["reached_cap"] else sum(d["balance"] for d in debts_list)
    net_a = invest_a - debt_remain_a

    # --- Model B: Invest First (minimums only on debt) ---
    r_b = simulate_payoff_strategy(debts_list, 0.0, "minimum", max_months=horizon_months)
    debt_remain_b = r_b["history"][-1]["total_balance"] if r_b["history"] else 0.0
    invest_b = calculate_future_value(extra_payment, after_tax_return, horizon_months)
    net_b = invest_b - debt_remain_b

    # --- Model C: Hybrid 70% debt / 30% invest ---
    debt_extra_c = extra_payment * 0.70
    invest_pmt_c = extra_payment * 0.30
    r_c = simulate_payoff_strategy(debts_list, debt_extra_c, strategy, max_months=horizon_months)
    payoff_mo_c = r_c["months"]
    remaining_c = max(0, horizon_months - payoff_mo_c)
    invest_c = calculate_future_value(invest_pmt_c, after_tax_return, horizon_months)
    # After debt payoff, redirect freed cash to investing
    freed_c = debt_extra_c + total_min
    invest_c += calculate_future_value(freed_c, after_tax_return, remaining_c)
    debt_remain_c = 0.0 if not r_c["reached_cap"] else sum(d["balance"] for d in debts_list)
    net_c = invest_c - debt_remain_c

    return {
        "model_a": {
            "name": "Debt First",
            "months_to_payoff": payoff_mo_a if not r_a["reached_cap"] else None,
            "total_interest": round(r_a["total_interest"], 2),
            "invest_balance": round(invest_a, 2),
            "debt_remaining": round(debt_remain_a, 2),
            "net_worth": round(net_a, 2),
        },
        "model_b": {
            "name": "Invest First",
            "months_to_payoff": r_b["months"] if not r_b["reached_cap"] else None,
            "total_interest": round(r_b["total_interest"], 2),
            "invest_balance": round(invest_b, 2),
            "debt_remaining": round(debt_remain_b, 2),
            "net_worth": round(net_b, 2),
        },
        "model_c": {
            "name": "Hybrid (70% Debt / 30% Invest)",
            "months_to_payoff": payoff_mo_c if not r_c["reached_cap"] else None,
            "total_interest": round(r_c["total_interest"], 2),
            "invest_balance": round(invest_c, 2),
            "debt_remaining": round(debt_remain_c, 2),
            "net_worth": round(net_c, 2),
        },
    }


# ---------------------------------------------------------------------------
# Emergency fund
# ---------------------------------------------------------------------------

def calculate_emergency_fund_status(
    current_savings: float,
    monthly_essential: float,
    monthly_debt_min: float,
    target_months: int = 6,
    min_months: int = 3,
) -> dict:
    monthly_obligations = monthly_essential + monthly_debt_min
    current_months = (current_savings / monthly_obligations) if monthly_obligations > 0 else 0.0

    starter_amt = monthly_obligations * min_months
    full_amt = monthly_obligations * target_months
    gap_starter = max(0.0, starter_amt - current_savings)
    gap_full = max(0.0, full_amt - current_savings)

    if current_months < 1.0:
        status, approach = "Dangerously Low", "starter"
        rec = (
            "Build a starter emergency fund before accelerating debt payoff. "
            "An unexpected expense could force new high-interest debt."
        )
    elif current_months < min_months:
        status, approach = "Starter Cushion", "hybrid"
        rec = (
            "Hybrid approach recommended: pay debt minimums plus any high-interest balance "
            "while steadily building savings to 3 months."
        )
    elif current_months < target_months:
        status, approach = "Adequate", "payoff"
        rec = (
            "Aggressive payoff is reasonable, especially for high-interest debt. "
            "Continue building toward your full target."
        )
    else:
        status, approach = "Strong", "invest"
        rec = "Strong cushion. Aggressive payoff or investing both make sense."

    return {
        "current_months": round(current_months, 2),
        "monthly_obligations": round(monthly_obligations, 2),
        "starter_target": round(starter_amt, 2),
        "full_target": round(full_amt, 2),
        "gap_to_starter": round(gap_starter, 2),
        "gap_to_full": round(gap_full, 2),
        "status": status,
        "recommendation": rec,
        "approach": approach,
    }


# ---------------------------------------------------------------------------
# DebtFree Score
# ---------------------------------------------------------------------------

def calculate_debtfree_score(profile: dict, debts_list: list, strategy_result: dict) -> dict:
    score = 100
    deductions = []

    monthly_income = max(profile.get("monthly_income", 1), 1)
    monthly_expenses = profile.get("monthly_essential", 0) + profile.get("monthly_discretionary", 0)
    total_min = sum(d["min_payment"] for d in debts_list)
    wapr = calculate_weighted_average_apr(debts_list)
    ef_months = profile.get("ef_current_months", 0)
    ef_target = profile.get("ef_target_months", 6)
    cash_flow = monthly_income - monthly_expenses - total_min
    months = strategy_result.get("months", 0)

    # Debt-to-income burden
    debt_ratio = total_min / monthly_income
    if debt_ratio > 0.50:
        score -= 25; deductions.append("Very high debt payment burden (>50% of income): -25")
    elif debt_ratio > 0.35:
        score -= 15; deductions.append("High debt payment burden (>35% of income): -15")
    elif debt_ratio > 0.20:
        score -= 8;  deductions.append("Moderate debt payment burden (>20% of income): -8")

    # Weighted APR
    if wapr >= 20:
        score -= 15; deductions.append("Very high weighted APR (≥20%): -15")
    elif wapr >= 15:
        score -= 10; deductions.append("High weighted APR (≥15%): -10")
    elif wapr >= 10:
        score -= 5;  deductions.append("Elevated weighted APR (≥10%): -5")

    # Emergency fund
    if ef_months < 1:
        score -= 20; deductions.append("Emergency fund critically low (<1 month): -20")
    elif ef_months < 3:
        score -= 10; deductions.append("Emergency fund below 3 months: -10")
    elif ef_months < ef_target:
        score -= 5;  deductions.append(f"Emergency fund below target ({ef_target} mo): -5")

    # Cash flow
    if cash_flow < 0:
        score -= 15; deductions.append("Negative monthly cash flow: -15")
    elif cash_flow < 100:
        score -= 5;  deductions.append("Very tight monthly cash flow (<$100): -5")

    # Payoff timeline
    if months > 240:
        score -= 10; deductions.append("Payoff timeline >20 years: -10")
    elif months > 120:
        score -= 5;  deductions.append("Payoff timeline >10 years: -5")

    # High revolving share
    revolving = sum(d["balance"] for d in debts_list if d.get("type") == "Credit Card")
    total_bal = sum(d["balance"] for d in debts_list)
    if total_bal > 0 and revolving / total_bal > 0.50:
        score -= 5; deductions.append("High share of revolving credit card debt: -5")

    score = max(0, min(100, score))

    if score >= 80:
        band, color = "Strong / Manageable", "#2ecc71"
    elif score >= 60:
        band, color = "Needs Focus", "#f39c12"
    elif score >= 40:
        band, color = "Stretched", "#e74c3c"
    else:
        band, color = "High Risk", "#922b21"

    return {"score": score, "band": band, "color": color, "deductions": deductions}


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def generate_markdown_report(
    profile: dict,
    debts_list: list,
    strategy_results: dict,
    ef_status: dict,
    pvi: dict,
    score_data: dict,
    target_info: dict | None = None,
) -> str:
    today = date.today().strftime("%B %d, %Y")
    lines = []

    def h(n, text): lines.append(f"{'#' * n} {text}")
    def blank(): lines.append("")
    def para(t): lines.append(t); blank()

    h(1, "DebtFree Planner — Summary Report")
    para(f"*Generated: {today}*")
    para(f"> **Disclaimer:** {DISCLAIMER}")

    # --- Profile ---
    h(2, "Financial Profile")
    lines += [
        f"- Monthly After-Tax Income: **${profile.get('monthly_income', 0):,.0f}**",
        f"- Monthly Essential Expenses: ${profile.get('monthly_essential', 0):,.0f}",
        f"- Monthly Discretionary: ${profile.get('monthly_discretionary', 0):,.0f}",
        f"- Monthly Investing Contributions: ${profile.get('monthly_investing', 0):,.0f}",
        f"- Extra Monthly Payoff Budget: **${profile.get('extra_payment', 0):,.0f}**",
        f"- Current Liquid Savings: ${profile.get('current_savings', 0):,.0f}",
        f"- Expected Investment Return: {profile.get('inv_return', 7):.1f}%",
        f"- Risk Preference: {profile.get('risk_pref', 'Balanced')}",
    ]
    blank()

    # --- Debts ---
    h(2, "Debt Overview")
    total_bal = sum(d["balance"] for d in debts_list)
    total_min = sum(d["min_payment"] for d in debts_list)
    wapr = calculate_weighted_average_apr(debts_list)
    lines += [
        f"- **Total Debt Balance:** ${total_bal:,.0f}",
        f"- **Weighted Average APR:** {wapr:.2f}%",
        f"- **Total Monthly Minimums:** ${total_min:,.0f}",
    ]
    blank()
    lines.append("| Debt | Type | Balance | APR | Min Payment |")
    lines.append("|------|------|---------|-----|-------------|")
    for d in debts_list:
        lines.append(
            f"| {d['name']} | {d['type']} | ${d['balance']:,.0f} "
            f"| {d['apr']:.1f}% | ${d['min_payment']:,.0f} |"
        )
    blank()

    # --- Strategy comparison ---
    h(2, "Payoff Strategy Comparison")
    min_result = strategy_results.get("Minimum Payments", {})
    min_int = min_result.get("total_interest", 0)
    lines.append("| Strategy | Months | Debt-Free Date | Total Interest | Interest Saved |")
    lines.append("|----------|--------|----------------|----------------|----------------|")
    for name, r in strategy_results.items():
        saved = max(0, min_int - r.get("total_interest", 0))
        dfd = r.get("debt_free_date")
        dfd_str = dfd.strftime("%b %Y") if dfd else "Beyond cap"
        lines.append(
            f"| {name} | {r.get('months','?')} | {dfd_str} "
            f"| ${r.get('total_interest',0):,.0f} | ${saved:,.0f} |"
        )
    blank()

    # --- Target planner ---
    if target_info:
        h(2, "Debt-Free Target Planner")
        lines += [
            f"- Target Timeline: {target_info.get('target_months', '?')} months",
            f"- Required Extra Payment: ${target_info.get('required_extra', 0):,.0f}/mo",
            f"- Feasibility: **{target_info.get('feasibility', '?')}**",
        ]
        blank()

    # --- Emergency fund ---
    h(2, "Emergency Fund Check")
    lines += [
        f"- Status: **{ef_status['status']}**",
        f"- Current Coverage: {ef_status['current_months']:.1f} months",
        f"- Gap to Full Target: ${ef_status['gap_to_full']:,.0f}",
        f"- Recommendation: {ef_status['recommendation']}",
    ]
    blank()

    # --- Payoff vs Invest ---
    h(2, "Payoff vs Invest Comparison")
    lines.append("| Model | Months to Debt-Free | Total Interest | Invest Balance | Net Worth |")
    lines.append("|-------|---------------------|----------------|----------------|-----------|")
    for key in ["model_a", "model_b", "model_c"]:
        m = pvi.get(key, {})
        mo = m.get("months_to_payoff")
        mo_str = str(mo) if mo else "Beyond horizon"
        lines.append(
            f"| {m.get('name','?')} | {mo_str} | ${m.get('total_interest',0):,.0f} "
            f"| ${m.get('invest_balance',0):,.0f} | ${m.get('net_worth',0):,.0f} |"
        )
    blank()

    # --- DebtFree Score ---
    h(2, "DebtFree Score")
    para(f"**Score: {score_data['score']}/100 — {score_data['band']}**")
    if score_data["deductions"]:
        lines.append("Score deductions:")
        for d in score_data["deductions"]:
            lines.append(f"- {d}")
        blank()

    lines.append("---")
    para(f"*{DISCLAIMER}*")

    return "\n".join(lines)
