"""
DebtFree Planner
Compare debt payoff strategies and see the smartest path to becoming debt-free.
"""

import io
import sys
import os

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from utils.calculations import (
    DISCLAIMER,
    add_months,
    calculate_debtfree_score,
    calculate_emergency_fund_status,
    calculate_future_value,
    calculate_monthly_interest,
    calculate_payoff_vs_invest,
    calculate_required_payment_for_target,
    calculate_weighted_average_apr,
    debts_df_to_list,
    generate_markdown_report,
    simulate_payoff_strategy,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DebtFree Planner",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Default debt data
# ---------------------------------------------------------------------------
DEFAULT_DEBTS = pd.DataFrame(
    [
        {
            "Debt Name": "Credit Card 1",
            "Type": "Credit Card",
            "Balance ($)": 8000.0,
            "APR (%)": 22.0,
            "Min Payment ($)": 240.0,
            "Term (mo)": 0,
            "Secured": False,
            "Tax Deductible": False,
            "0% Promo": False,
            "Promo Months Left": 0,
            "Priority": "Normal",
            "Notes": "",
        },
        {
            "Debt Name": "Auto Loan",
            "Type": "Auto Loan",
            "Balance ($)": 18000.0,
            "APR (%)": 7.0,
            "Min Payment ($)": 425.0,
            "Term (mo)": 48,
            "Secured": True,
            "Tax Deductible": False,
            "0% Promo": False,
            "Promo Months Left": 0,
            "Priority": "Normal",
            "Notes": "",
        },
        {
            "Debt Name": "Student Loan",
            "Type": "Student Loan",
            "Balance ($)": 35000.0,
            "APR (%)": 5.5,
            "Min Payment ($)": 350.0,
            "Term (mo)": 120,
            "Secured": False,
            "Tax Deductible": False,
            "0% Promo": False,
            "Promo Months Left": 0,
            "Priority": "Normal",
            "Notes": "",
        },
    ]
)

DEBT_TYPES = [
    "Credit Card",
    "Personal Loan",
    "Student Loan",
    "Auto Loan",
    "Mortgage",
    "HELOC",
    "Medical Debt",
    "Other",
]
PRIORITY_OPTIONS = ["Normal", "Must Pay First", "Avoid Accelerating"]
STRATEGY_MAP = {
    "Avalanche (Highest APR First)": "avalanche",
    "Snowball (Lowest Balance First)": "snowball",
    "Custom Priority": "custom",
}

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
DEFAULTS = {
    "monthly_income": 6000,
    "monthly_essential": 2500,
    "monthly_discretionary": 800,
    "current_savings": 5000,
    "ef_target_months": 6,
    "ef_min_months": 3,
    "monthly_investing": 200,
    "extra_payment": 500,
    "inv_return": 7.0,
    "inflation": 3.0,
    "tax_rate_invest": 20.0,
    "risk_pref": "Balanced",
    "target_months": 48,
    "target_planner_months": 48,
    "investing_pref": "Continue current investing",
    "employer_match": False,
    "match_pct": 50,
    "match_contribution": 200,
    "horizon_years": 10,
    "user_psy_pref": "Balanced",
    "target_strategy_label": "Avalanche (Highest APR First)",
    "pvi_strategy_label": "Avalanche (Highest APR First)",
}

for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

if "debts_df" not in st.session_state:
    st.session_state.debts_df = DEFAULT_DEBTS.copy()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmt_usd(v: float) -> str:
    return f"${v:,.0f}"


def fmt_months(m: int | None) -> str:
    if m is None:
        return "N/A"
    yrs, mos = divmod(int(m), 12)
    parts = []
    if yrs:
        parts.append(f"{yrs}y")
    if mos:
        parts.append(f"{mos}m")
    return " ".join(parts) if parts else "0m"


def get_debts() -> list:
    return debts_df_to_list(st.session_state.debts_df)


def get_profile() -> dict:
    return {k: st.session_state.get(k, v) for k, v in DEFAULTS.items()}


def run_all_strategies(debts: list, extra: float) -> dict:
    return {
        "Minimum Payments": simulate_payoff_strategy(debts, extra, "minimum"),
        "Debt Avalanche": simulate_payoff_strategy(debts, extra, "avalanche"),
        "Debt Snowball": simulate_payoff_strategy(debts, extra, "snowball"),
        "Custom Priority": simulate_payoff_strategy(debts, extra, "custom"),
    }


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.title("DebtFree Planner")
st.markdown(
    "**Compare debt payoff strategies and see the smartest path to becoming debt-free.**"
)
st.info(f"ℹ️  {DISCLAIMER}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
(
    tab_profile,
    tab_debts,
    tab_strategy,
    tab_target,
    tab_pvi,
    tab_ef,
    tab_summary,
) = st.tabs(
    [
        "1 · Profile & Assumptions",
        "2 · Debt Entry",
        "3 · Payoff Strategies",
        "4 · Target Planner",
        "5 · Payoff vs Invest",
        "6 · Emergency Fund",
        "7 · Summary Report",
    ]
)


# ===========================================================================
# TAB 1 — Profile & Assumptions
# ===========================================================================
with tab_profile:
    st.header("Profile & Assumptions")

    col_hh, col_plan = st.columns(2, gap="large")

    with col_hh:
        st.subheader("Household Profile")
        st.number_input(
            "Monthly after-tax income ($)",
            min_value=0,
            step=100,
            key="monthly_income",
        )
        st.number_input(
            "Monthly essential expenses — excluding debt payments ($)",
            min_value=0,
            step=50,
            key="monthly_essential",
        )
        st.number_input(
            "Monthly discretionary expenses ($)",
            min_value=0,
            step=50,
            key="monthly_discretionary",
        )
        st.number_input(
            "Current liquid savings ($)",
            min_value=0,
            step=500,
            key="current_savings",
        )
        st.number_input(
            "Monthly retirement / investment contributions ($)",
            min_value=0,
            step=50,
            key="monthly_investing",
        )
        st.number_input(
            "Extra monthly cash available for debt payoff ($)",
            min_value=0,
            step=50,
            key="extra_payment",
        )
        st.number_input(
            "Expected annual investment return (%)",
            min_value=0.0,
            max_value=30.0,
            step=0.5,
            key="inv_return",
        )
        st.number_input(
            "Expected annual inflation (%)",
            min_value=0.0,
            max_value=20.0,
            step=0.5,
            key="inflation",
        )
        st.number_input(
            "Effective tax rate on investment gains (%, optional)",
            min_value=0.0,
            max_value=50.0,
            step=1.0,
            key="tax_rate_invest",
        )
        st.selectbox(
            "Risk preference",
            ["Conservative", "Balanced", "Aggressive"],
            key="risk_pref",
        )

    with col_plan:
        st.subheader("Planning Assumptions")
        st.number_input(
            "Minimum emergency fund floor (months)",
            min_value=1,
            max_value=12,
            step=1,
            key="ef_min_months",
        )
        st.number_input(
            "Full emergency fund target (months)",
            min_value=1,
            max_value=24,
            step=1,
            key="ef_target_months",
        )
        st.number_input(
            "Target debt-free timeline (months, optional — 0 = not set)",
            min_value=0,
            max_value=600,
            step=1,
            key="target_months",
        )
        st.selectbox(
            "Investing preference while paying debt",
            [
                "Pause investing temporarily",
                "Continue current investing",
                "Reduce investing",
                "Increase investing only after high-interest debt is gone",
            ],
            key="investing_pref",
        )
        st.number_input(
            "Investment comparison horizon (years)",
            min_value=1,
            max_value=40,
            step=1,
            key="horizon_years",
        )

    # --- Computed summary ---
    st.markdown("---")
    st.subheader("Cash Flow Summary")

    income = st.session_state.monthly_income
    essential = st.session_state.monthly_essential
    discr = st.session_state.monthly_discretionary
    investing = st.session_state.monthly_investing
    extra = st.session_state.extra_payment
    savings = st.session_state.current_savings
    ef_min = st.session_state.ef_min_months
    ef_target = st.session_state.ef_target_months

    debts_now = get_debts()
    total_min = sum(d["min_payment"] for d in debts_now)
    total_bal = sum(d["balance"] for d in debts_now)
    non_debt_spend = essential + discr + investing
    cash_before_debt = income - non_debt_spend
    free_cash = cash_before_debt - total_min
    monthly_obligations = essential + total_min
    ef_current_months = (savings / monthly_obligations) if monthly_obligations > 0 else 0.0

    # Store ef_current_months for score calculation
    st.session_state["ef_current_months_computed"] = ef_current_months

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monthly Income", fmt_usd(income))
    c2.metric("Total Non-Debt Spending", fmt_usd(non_debt_spend))
    c3.metric("Cash Flow Before Debt Pmts", fmt_usd(cash_before_debt))
    c4.metric("Free Cash After All Payments", fmt_usd(free_cash))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Total Minimum Payments", fmt_usd(total_min))
    c6.metric("Extra Payoff Budget", fmt_usd(extra))
    c7.metric("Emergency Fund Coverage", f"{ef_current_months:.1f} mo")
    debt_ratio = (total_min / income * 100) if income > 0 else 0
    c8.metric("Debt Payment / Income", f"{debt_ratio:.1f}%")

    # Warnings
    if income > 0 and non_debt_spend > income:
        st.warning("⚠️ Non-debt spending exceeds income. Review your budget.")
    if cash_before_debt < total_min:
        st.error("🚨 Monthly cash flow does not fully cover minimum debt payments.")
    if extra <= 0:
        st.warning("⚠️ Extra payoff amount is $0. Strategies will only show minimum-payment results.")
    if ef_current_months < 1:
        st.error("🚨 Emergency fund is below 1 month. Consider building a cushion before aggressive payoff.")
    if debt_ratio > 40:
        st.warning(f"⚠️ Debt payments are {debt_ratio:.0f}% of income — above the recommended 35–40% guideline.")


# ===========================================================================
# TAB 2 — Debt Entry
# ===========================================================================
with tab_debts:
    st.header("Debt Entry")
    st.markdown(
        "Add, edit, or remove debts below. Balances of $0 are automatically excluded from calculations."
    )

    edited = st.data_editor(
        st.session_state.debts_df,
        key="debt_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Debt Name": st.column_config.TextColumn("Debt Name", width="medium", required=True),
            "Type": st.column_config.SelectboxColumn("Type", options=DEBT_TYPES, width="medium"),
            "Balance ($)": st.column_config.NumberColumn(
                "Balance ($)", min_value=0.0, format="$%.0f", width="small"
            ),
            "APR (%)": st.column_config.NumberColumn(
                "APR (%)", min_value=0.0, max_value=100.0, format="%.2f", width="small"
            ),
            "Min Payment ($)": st.column_config.NumberColumn(
                "Min Payment ($)", min_value=0.0, format="$%.0f", width="small"
            ),
            "Term (mo)": st.column_config.NumberColumn(
                "Term (mo)", min_value=0, width="small"
            ),
            "Secured": st.column_config.CheckboxColumn("Secured", width="small"),
            "Tax Deductible": st.column_config.CheckboxColumn("Tax Ded.", width="small"),
            "0% Promo": st.column_config.CheckboxColumn("0% Promo", width="small"),
            "Promo Months Left": st.column_config.NumberColumn(
                "Promo Mo Left", min_value=0, width="small"
            ),
            "Priority": st.column_config.SelectboxColumn(
                "Priority", options=PRIORITY_OPTIONS, width="medium"
            ),
            "Notes": st.column_config.TextColumn("Notes", width="medium"),
        },
    )
    st.session_state.debts_df = edited

    # Validation and metrics
    debts_list = debts_df_to_list(edited)
    if not debts_list:
        st.info("No active debts. Add at least one debt with a balance > $0.")
    else:
        st.markdown("---")
        st.subheader("Debt Metrics")

        total_bal = sum(d["balance"] for d in debts_list)
        total_min = sum(d["min_payment"] for d in debts_list)
        wapr = calculate_weighted_average_apr(debts_list)
        highest_apr = max(debts_list, key=lambda d: d["apr"])
        lowest_bal = min(debts_list, key=lambda d: d["balance"])
        income = st.session_state.monthly_income

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Debt", fmt_usd(total_bal))
        col2.metric("Weighted Avg APR", f"{wapr:.2f}%")
        col3.metric("Total Min Payments", fmt_usd(total_min))
        col4.metric(
            "Debt Pmt / Income",
            f"{(total_min/income*100):.1f}%" if income > 0 else "N/A",
        )

        col5, col6 = st.columns(2)
        col5.info(f"🔺 Highest APR: **{highest_apr['name']}** at {highest_apr['apr']:.1f}%")
        col6.info(f"🔻 Lowest Balance: **{lowest_bal['name']}** at {fmt_usd(lowest_bal['balance'])}")

        # Per-debt warnings
        for d in debts_list:
            mi = calculate_monthly_interest(d["balance"], d["apr"])
            if d["min_payment"] < mi * 0.999 and d["apr"] > 0:
                st.warning(
                    f"⚠️ **{d['name']}**: Minimum payment ${d['min_payment']:.0f} "
                    f"< monthly interest ${mi:.0f}. Balance will grow."
                )
            if d["balance"] > 0 and d["min_payment"] == 0 and d["apr"] > 0:
                st.warning(f"⚠️ **{d['name']}**: No minimum payment set with APR > 0.")


# ===========================================================================
# TAB 3 — Payoff Strategy Comparison
# ===========================================================================
with tab_strategy:
    st.header("Payoff Strategy Comparison")

    debts = get_debts()
    extra = st.session_state.extra_payment

    if not debts:
        st.info("No active debts. Enter debts in the Debt Entry tab.")
    else:
        with st.spinner("Running simulations…"):
            results = run_all_strategies(debts, extra)

        total_min_pay = sum(d["min_payment"] for d in debts)
        min_result = results["Minimum Payments"]
        min_int = min_result["total_interest"]

        # --- Comparison table ---
        st.subheader("Strategy Comparison")
        table_rows = []
        for name, r in results.items():
            saved = max(0, min_int - r["total_interest"])
            time_saved = max(0, min_result["months"] - r["months"])
            dfd = r["debt_free_date"]
            dfd_str = dfd.strftime("%b %Y") if dfd else "Beyond cap"
            table_rows.append(
                {
                    "Strategy": name,
                    "Months": r["months"],
                    "Debt-Free Date": dfd_str,
                    "Total Interest": fmt_usd(r["total_interest"]),
                    "Total Payments": fmt_usd(r["total_payments"]),
                    "Interest Saved": fmt_usd(saved),
                    "Time Saved": fmt_months(time_saved) if time_saved > 0 else "—",
                    "First Debt Paid": r["first_paid"] or "—",
                    "Focus Debt": r["focus_debt"] or "—",
                }
            )
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        # --- Recommendation ---
        avl = results["Debt Avalanche"]
        snb = results["Debt Snowball"]
        best_interest = min(results, key=lambda k: results[k]["total_interest"])
        best_time = min(results, key=lambda k: results[k]["months"])

        st.subheader("Recommendation")
        with st.container():
            avl_saved = max(0, min_int - avl["total_interest"])
            snb_saved = max(0, min_int - snb["total_interest"])

            if avl["total_interest"] <= snb["total_interest"]:
                primary = "Debt Avalanche"
                rec_text = (
                    f"The **Avalanche** method saves the most interest — "
                    f"approximately **{fmt_usd(avl_saved)}** compared with minimum payments. "
                    f"It targets the highest APR debt first, giving you the best mathematical return."
                )
            else:
                primary = "Debt Snowball"
                rec_text = (
                    f"The **Snowball** method is competitive here and pays off your smallest "
                    f"debt faster, which can build momentum. "
                    f"It saves approximately **{fmt_usd(snb_saved)}** vs minimum payments."
                )

            interest_diff = abs(avl["total_interest"] - snb["total_interest"])
            rec_text += (
                f"\n\nThe Avalanche and Snowball strategies differ by "
                f"**{fmt_usd(interest_diff)}** in total interest. "
                "Choose Snowball if early wins matter for motivation; "
                "choose Avalanche to minimise cost."
            )
            st.info(rec_text)

        # Show per-strategy warnings
        all_warnings = []
        for name, r in results.items():
            for w in r.get("warnings", []):
                if w not in all_warnings:
                    all_warnings.append(w)
        for w in all_warnings:
            st.warning(f"⚠️ {w}")

        # --- Charts ---
        st.subheader("Balance Over Time")

        fig_bal = go.Figure()
        colors = {"Minimum Payments": "#e74c3c", "Debt Avalanche": "#2ecc71",
                  "Debt Snowball": "#3498db", "Custom Priority": "#f39c12"}
        for name, r in results.items():
            if r["history"]:
                months_x = [h["month"] for h in r["history"]]
                bal_y = [h["total_balance"] for h in r["history"]]
                fig_bal.add_trace(
                    go.Scatter(
                        x=months_x, y=bal_y, name=name,
                        line=dict(color=colors.get(name), width=2),
                    )
                )
        fig_bal.update_layout(
            xaxis_title="Month",
            yaxis_title="Total Balance ($)",
            yaxis_tickformat="$,.0f",
            legend_title="Strategy",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig_bal, use_container_width=True)

        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.subheader("Total Interest Paid")
            fig_int = go.Figure(
                go.Bar(
                    x=list(results.keys()),
                    y=[r["total_interest"] for r in results.values()],
                    marker_color=[colors[k] for k in results],
                    text=[fmt_usd(r["total_interest"]) for r in results.values()],
                    textposition="outside",
                )
            )
            fig_int.update_layout(
                yaxis_tickformat="$,.0f",
                height=340,
                margin=dict(l=10, r=10, t=30, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig_int, use_container_width=True)

        with col_c2:
            st.subheader("Months to Debt-Free")
            fig_mo = go.Figure(
                go.Bar(
                    x=list(results.keys()),
                    y=[r["months"] for r in results.values()],
                    marker_color=[colors[k] for k in results],
                    text=[fmt_months(r["months"]) for r in results.values()],
                    textposition="outside",
                )
            )
            fig_mo.update_layout(
                yaxis_title="Months",
                height=340,
                margin=dict(l=10, r=10, t=30, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig_mo, use_container_width=True)

        # --- CSV export ---
        st.subheader("Export Strategy Data")
        csv_rows = []
        for name, r in results.items():
            for h in r["history"]:
                csv_rows.append(
                    {
                        "Strategy": name,
                        "Month": h["month"],
                        "Total Balance": round(h["total_balance"], 2),
                        "Interest Paid": round(h["interest_paid"], 2),
                        "Principal Paid": round(h["principal_paid"], 2),
                    }
                )
        if csv_rows:
            csv_df = pd.DataFrame(csv_rows)
            st.download_button(
                "⬇ Download Strategy Data (CSV)",
                data=csv_df.to_csv(index=False).encode(),
                file_name="debtfree_strategy_comparison.csv",
                mime="text/csv",
            )


# ===========================================================================
# TAB 4 — Debt-Free Target Planner
# ===========================================================================
with tab_target:
    st.header("Debt-Free Target Planner")
    st.markdown(
        "Find out how much you need to pay each month to become debt-free by a specific date or timeline."
    )

    debts = get_debts()
    extra = st.session_state.extra_payment
    income = st.session_state.monthly_income

    if not debts:
        st.info("No active debts. Enter debts in the Debt Entry tab.")
    else:
        col_inp, col_out = st.columns([1, 1], gap="large")

        with col_inp:
            st.subheader("Inputs")
            target_months = st.number_input(
                "Target debt-free timeline (months)",
                min_value=1,
                max_value=600,
                step=1,
                key="target_planner_months",
            )
            target_strategy_label = st.selectbox(
                "Strategy to use",
                list(STRATEGY_MAP.keys()),
                key="target_strategy_label",
            )
            target_strat = STRATEGY_MAP[target_strategy_label]

            target_date = add_months(date.today(), int(target_months))
            st.markdown(
                f"**Target date:** {target_date.strftime('%B %Y')} "
                f"({int(target_months)} months from today)"
            )

        total_min = sum(d["min_payment"] for d in debts)

        with st.spinner("Calculating required payment…"):
            required_extra = calculate_required_payment_for_target(
                debts, int(target_months), target_strat
            )

        with col_out:
            st.subheader("Results")

            if required_extra is None:
                st.error(
                    "Target is not achievable even with a very large one-time payment. "
                    "Consider a longer timeline."
                )
            else:
                required_total = total_min + required_extra
                gap = required_extra - extra

                if gap <= 0:
                    feasibility = "✅ Feasible"
                    feas_color = "success"
                elif gap <= extra * 0.20:
                    feasibility = "⚠️ Tight"
                    feas_color = "warning"
                else:
                    feasibility = "❌ Not Feasible Without Changes"
                    feas_color = "error"

                c1, c2, c3 = st.columns(3)
                c1.metric("Required Monthly Total", fmt_usd(required_total))
                c2.metric("Required Extra Payment", fmt_usd(required_extra))
                c3.metric(
                    "Your Current Extra",
                    fmt_usd(extra),
                    delta=fmt_usd(-gap) if gap > 0 else fmt_usd(abs(gap)),
                    delta_color="inverse",
                )

                if feas_color == "success":
                    st.success(feasibility)
                elif feas_color == "warning":
                    st.warning(feasibility)
                else:
                    st.error(feasibility)

                # What happens with current extra?
                r_current = simulate_payoff_strategy(debts, extra, target_strat)
                actual_date = r_current.get("debt_free_date")
                actual_mo = r_current["months"]
                delay = max(0, actual_mo - int(target_months))

                st.markdown("---")
                st.markdown("#### With Your Current Extra Payment")
                c4, c5 = st.columns(2)
                c4.metric("Estimated Debt-Free Date", actual_date.strftime("%b %Y") if actual_date else "Beyond cap")
                c5.metric("Months (vs Target)", fmt_months(actual_mo), delta=f"+{delay} mo" if delay else "On target")

                # Interpretation
                if gap <= 0:
                    interp = (
                        f"Great news — your current extra payment of **{fmt_usd(extra)}/mo** is "
                        f"more than enough to meet your {target_months}-month target. "
                        f"You are on track to be debt-free by **{target_date.strftime('%B %Y')}**."
                    )
                else:
                    interp = (
                        f"To become debt-free in **{target_months} months**, you need to pay "
                        f"approximately **{fmt_usd(required_total)}/mo** in total — "
                        f"that is **{fmt_usd(required_extra)}/mo** in extra payments. "
                        f"You are currently short by **{fmt_usd(gap)}/mo**."
                    )
                st.info(interp)

                # Suggested adjustments
                if gap > 0:
                    st.subheader("Suggested Adjustments")
                    st.markdown(
                        f"- 💡 **Increase monthly payment** by {fmt_usd(gap)} to hit your target.\n"
                        f"- ⏱️ **Extend timeline** by ~{delay} months to fit your current budget.\n"
                        f"- ✂️ **Reduce discretionary spending** by {fmt_usd(gap)} to free up extra cash.\n"
                        "- ⏸️ **Pause or reduce optional investing** temporarily to redirect cash to debt.\n"
                        "- 🔄 **Refinance or consolidate** high-interest debt to lower the required payment.\n"
                        "- 🏦 **Build minimum emergency fund first** if savings are below 1 month."
                    )

        # Store target info for report
        st.session_state["_target_info"] = {
            "target_months": int(target_months),
            "required_extra": required_extra if required_extra is not None else 0,
            "feasibility": feasibility if required_extra is not None else "N/A",
        }


# ===========================================================================
# TAB 5 — Payoff vs Invest
# ===========================================================================
with tab_pvi:
    st.header("Payoff vs Invest")
    st.markdown(
        "Should your extra cash go toward paying off debt or investing? "
        "This section compares three models over your chosen time horizon."
    )

    debts = get_debts()
    extra = st.session_state.extra_payment

    if not debts:
        st.info("No active debts. Enter debts in the Debt Entry tab.")
    else:
        col_pvi_in, col_pvi_out = st.columns([1, 1], gap="large")

        with col_pvi_in:
            st.subheader("Inputs")
            st.caption("Investment return, tax rate, and horizon are set in **Tab 1 · Profile & Assumptions**.")
            inv_return = float(st.session_state.get("inv_return", 7.0))
            tax_rate = float(st.session_state.get("tax_rate_invest", 20.0))
            horizon_years = int(st.session_state.get("horizon_years", 10))
            st.markdown(
                f"- Expected return: **{inv_return:.1f}%** &nbsp;|&nbsp; "
                f"Tax rate: **{tax_rate:.0f}%** &nbsp;|&nbsp; "
                f"Horizon: **{horizon_years} yrs**"
            )
            pvi_strat_label = st.selectbox(
                "Debt payoff strategy",
                list(STRATEGY_MAP.keys()),
                key="pvi_strategy_label",
            )
            pvi_strat = STRATEGY_MAP[pvi_strat_label]

            st.markdown("---")
            st.subheader("Preferences")
            st.selectbox(
                "Psychological preference",
                ["Prefer certainty (debt payoff peace of mind)", "Balanced", "Prefer long-term growth"],
                key="user_psy_pref",
            )
            st.checkbox(
                "Employer retirement match available?",
                key="employer_match",
            )
            if st.session_state.employer_match:
                st.number_input("Employer match (%)", min_value=0, max_value=100, step=5, key="match_pct")
                st.number_input(
                    "Monthly contribution to receive full match ($)",
                    min_value=0, step=25, key="match_contribution",
                )

        with st.spinner("Comparing models…"):
            pvi_results = calculate_payoff_vs_invest(
                debts, extra, float(inv_return), float(tax_rate),
                int(horizon_years), pvi_strat,
            )

        wapr = calculate_weighted_average_apr(debts)
        after_tax_ret = float(inv_return) * (1 - float(tax_rate) / 100)

        with col_pvi_out:
            st.subheader(f"Results over {int(horizon_years)}-year horizon")

            rows = []
            for key in ["model_a", "model_b", "model_c"]:
                m = pvi_results[key]
                mo = m["months_to_payoff"]
                rows.append(
                    {
                        "Model": m["name"],
                        "Months to Debt-Free": fmt_months(mo) if mo else "Beyond horizon",
                        "Total Interest Paid": fmt_usd(m["total_interest"]),
                        "Investment Balance": fmt_usd(m["invest_balance"]),
                        "Remaining Debt": fmt_usd(m["debt_remaining"]),
                        "Est. Net Worth": fmt_usd(m["net_worth"]),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Net worth comparison chart
            fig_nw = go.Figure(
                go.Bar(
                    x=[pvi_results[k]["name"] for k in ["model_a", "model_b", "model_c"]],
                    y=[pvi_results[k]["net_worth"] for k in ["model_a", "model_b", "model_c"]],
                    marker_color=["#2ecc71", "#3498db", "#f39c12"],
                    text=[fmt_usd(pvi_results[k]["net_worth"]) for k in ["model_a", "model_b", "model_c"]],
                    textposition="outside",
                )
            )
            fig_nw.update_layout(
                title=f"Estimated Net Worth after {horizon_years} Years",
                yaxis_tickformat="$,.0f",
                height=340,
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig_nw, use_container_width=True)

        # Debt-by-debt classification
        st.subheader("Debt Classification")
        st.markdown(
            f"Your weighted average APR is **{wapr:.1f}%**. "
            f"Expected after-tax return: **{after_tax_ret:.1f}%**."
        )

        classify_rows = []
        for d in debts:
            apr = d["apr"]
            td = d.get("tax_deductible", False)
            eff_apr = apr * (1 - float(tax_rate) / 100) if td else apr
            if apr >= 10:
                action = "High-priority payoff"
            elif apr >= 6:
                action = "Usually prioritise payoff"
            elif apr >= 3:
                action = "Compare with investment return"
            else:
                action = "Investing may be better financially"
            classify_rows.append(
                {
                    "Debt": d["name"],
                    "APR": f"{apr:.1f}%",
                    "Eff. APR (after tax)": f"{eff_apr:.1f}%",
                    "Recommended Action": action,
                }
            )
        st.dataframe(pd.DataFrame(classify_rows), use_container_width=True, hide_index=True)

        # Recommendation logic
        st.subheader("Recommendation")
        high_apr_debts = [d for d in debts if d["apr"] >= 10]
        savings = st.session_state.current_savings
        essential = st.session_state.monthly_essential
        total_min = sum(d["min_payment"] for d in debts)
        ef_months = (savings / (essential + total_min)) if (essential + total_min) > 0 else 0
        psy = st.session_state.user_psy_pref

        if ef_months < st.session_state.ef_min_months:
            rec_label = "🏦 Build Emergency Fund First"
            rec_text = (
                f"Your emergency fund covers only {ef_months:.1f} months. "
                "Before choosing between debt payoff and investing, build at least a "
                f"{st.session_state.ef_min_months}-month cushion to avoid creating new high-interest debt."
            )
        elif st.session_state.employer_match:
            rec_label = "🤝 Capture Employer Match First"
            rec_text = (
                "Your employer offers a retirement match — this is essentially a 100% return. "
                "Capture the full match before directing extra cash elsewhere, then prioritise high-interest debt."
            )
        elif high_apr_debts:
            rec_label = "💳 Prioritise Debt Payoff"
            rec_text = (
                f"You have high-interest debt (APR ≥10%) including "
                f"{', '.join(d['name'] for d in high_apr_debts)}. "
                f"Paying these off is a guaranteed {high_apr_debts[0]['apr']:.0f}%+ return — "
                "stronger than uncertain market returns for most risk profiles."
            )
        elif after_tax_ret > wapr + 1 and psy in ["Balanced", "Prefer long-term growth"]:
            rec_label = "📈 Hybrid Approach"
            rec_text = (
                f"Your remaining debt APR ({wapr:.1f}%) is below the expected after-tax return "
                f"({after_tax_ret:.1f}%). A hybrid split (70% debt / 30% investing) balances "
                "guaranteed interest savings with long-term wealth building."
            )
        else:
            rec_label = "⚖️ Hybrid Approach"
            rec_text = (
                "Your debt rates and expected investment returns are close. "
                "A hybrid approach spreads risk and gives you both debt reduction and investing momentum."
            )

        st.success(f"**{rec_label}**\n\n{rec_text}")

        if high_apr_debts:
            st.info(
                f"💡 Because your credit card APR is "
                f"{max(d['apr'] for d in debts if d['type'] == 'Credit Card') if any(d['type'] == 'Credit Card' for d in debts) else 'high'}%, "
                "paying it off is likely stronger than investing. "
                "This is a high, guaranteed return compared with uncertain market returns."
            )


# ===========================================================================
# TAB 6 — Emergency Fund Check
# ===========================================================================
with tab_ef:
    st.header("Emergency Fund Check")
    st.markdown(
        "Should you pay debt aggressively if your cash cushion is low? "
        "This section helps you decide."
    )

    debts = get_debts()
    savings = st.session_state.current_savings
    essential = st.session_state.monthly_essential
    discr = st.session_state.monthly_discretionary
    ef_target = st.session_state.ef_target_months
    ef_min = st.session_state.ef_min_months
    total_min = sum(d["min_payment"] for d in debts)

    ef = calculate_emergency_fund_status(
        savings, essential, total_min, ef_target, ef_min
    )

    STATUS_COLORS = {
        "Dangerously Low": "error",
        "Starter Cushion": "warning",
        "Adequate": "info",
        "Strong": "success",
    }
    color_fn = getattr(st, STATUS_COLORS.get(ef["status"], "info"))

    col_ef1, col_ef2 = st.columns(2, gap="large")

    with col_ef1:
        st.subheader("Current Status")

        c1, c2, c3 = st.columns(3)
        c1.metric("Coverage", f"{ef['current_months']:.1f} mo")
        c2.metric("Monthly Obligations", fmt_usd(ef["monthly_obligations"]))
        c3.metric("Current Savings", fmt_usd(savings))

        color_fn(f"**Emergency Fund Status: {ef['status']}**\n\n{ef['recommendation']}")

    with col_ef2:
        st.subheader("Targets & Gaps")

        c4, c5 = st.columns(2)
        c4.metric(
            f"Starter Target ({ef_min} mo)",
            fmt_usd(ef["starter_target"]),
            delta=fmt_usd(-ef["gap_to_starter"]) if ef["gap_to_starter"] > 0 else "✅ Met",
            delta_color="inverse",
        )
        c5.metric(
            f"Full Target ({ef_target} mo)",
            fmt_usd(ef["full_target"]),
            delta=fmt_usd(-ef["gap_to_full"]) if ef["gap_to_full"] > 0 else "✅ Met",
            delta_color="inverse",
        )

    # Decision framework
    st.markdown("---")
    st.subheader("Decision Framework")

    framework = {
        "Dangerously Low (<1 mo)": (
            "Build a starter emergency fund first. "
            "An unexpected expense will create new high-interest debt and erase payoff progress."
        ),
        "Starter Cushion (1–3 mo)": (
            "Pay debt minimums and focus extra cash on high-interest balances "
            "while slowly building savings to 3 months."
        ),
        "Adequate (3–6 mo)": (
            "Aggressive payoff is reasonable. Focus extra cash on highest APR debt. "
            "Continue growing the fund toward your full target."
        ),
        "Strong (≥6 mo)": (
            "Strong position. Aggressive debt payoff or investing both make sense. "
            "Consider the Payoff vs Invest tab for tailored guidance."
        ),
    }

    for label, text in framework.items():
        icon = "→" if ef["status"] not in label else "**→**"
        highlight = ef["status"] in label
        if highlight:
            st.success(f"**{label}**\n\n{text}")
        else:
            with st.expander(label):
                st.write(text)

    # Plain-English summary
    st.markdown("---")
    if ef["current_months"] < ef_target:
        st.info(
            f"Your emergency fund covers **{ef['current_months']:.1f} months** of essential obligations. "
            f"Before sending all extra cash to debt, consider building at least a "
            f"**{ef_min}-month cushion** so unexpected expenses do not create new credit card debt. "
            f"You need **{fmt_usd(ef['gap_to_starter'])}** to reach your starter target "
            f"and **{fmt_usd(ef['gap_to_full'])}** to reach your full {ef_target}-month target."
        )
    else:
        st.success(
            f"Your emergency fund is solid at **{ef['current_months']:.1f} months** of coverage. "
            "You are in a strong position to pursue aggressive debt payoff or investing."
        )


# ===========================================================================
# TAB 7 — Summary Report
# ===========================================================================
with tab_summary:
    st.header("Summary Report")
    st.markdown(DISCLAIMER)
    st.markdown("---")

    debts = get_debts()
    extra = st.session_state.extra_payment
    income = st.session_state.monthly_income
    savings = st.session_state.current_savings
    essential = st.session_state.monthly_essential
    discr = st.session_state.monthly_discretionary
    investing = st.session_state.monthly_investing
    ef_target = st.session_state.ef_target_months
    ef_min = st.session_state.ef_min_months
    inv_return = st.session_state.inv_return
    tax_rate = st.session_state.tax_rate_invest
    horizon = st.session_state.horizon_years

    if not debts:
        st.info("No active debts. Enter debts in the Debt Entry tab.")
    else:
        with st.spinner("Building summary…"):
            results = run_all_strategies(debts, extra)
            total_min = sum(d["min_payment"] for d in debts)
            total_bal = sum(d["balance"] for d in debts)
            wapr = calculate_weighted_average_apr(debts)
            avl = results["Debt Avalanche"]
            min_res = results["Minimum Payments"]
            avl_saved = max(0, min_res["total_interest"] - avl["total_interest"])

            ef = calculate_emergency_fund_status(savings, essential, total_min, ef_target, ef_min)

            pvi = calculate_payoff_vs_invest(
                debts, extra, float(inv_return), float(tax_rate), int(horizon)
            )

            profile_for_score = {
                "monthly_income": income,
                "monthly_essential": essential,
                "monthly_discretionary": discr,
                "ef_current_months": ef["current_months"],
                "ef_target_months": ef_target,
                "inv_return": inv_return,
                "risk_pref": st.session_state.risk_pref,
                "extra_payment": extra,
                "current_savings": savings,
                "monthly_investing": investing,
            }
            score_data = calculate_debtfree_score(profile_for_score, debts, avl)

        # --- Score ---
        st.subheader("DebtFree Score")
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            score_val = score_data["score"]
            st.markdown(
                f"""
                <div style="text-align:center; padding: 20px; border-radius: 12px;
                     background:{score_data['color']}22; border: 2px solid {score_data['color']}">
                  <h1 style="color:{score_data['color']}; margin:0">{score_val}</h1>
                  <p style="font-size:1.2em; margin:0"><b>{score_data['band']}</b></p>
                  <p style="font-size:0.85em; color:#888">out of 100</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_s2:
            best_strat = min(results, key=lambda k: results[k]["total_interest"])
            best_r = results[best_strat]
            dfd_str = best_r["debt_free_date"].strftime("%B %Y") if best_r["debt_free_date"] else "N/A"
            st.markdown(
                f"Your **DebtFree Score is {score_val}** — *{score_data['band']}*. "
                f"Under the **{best_strat}** strategy, you could be debt-free by **{dfd_str}** "
                f"({fmt_months(best_r['months'])}), paying **{fmt_usd(best_r['total_interest'])}** in interest "
                f"— approximately **{fmt_usd(avl_saved)} less** than paying minimums only."
            )
            if score_data["deductions"]:
                with st.expander("Score breakdown"):
                    for d in score_data["deductions"]:
                        st.markdown(f"- {d}")

        st.markdown("---")

        # --- Key metrics grid ---
        st.subheader("Key Metrics")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Debt", fmt_usd(total_bal))
        c2.metric("Weighted Avg APR", f"{wapr:.1f}%")
        c3.metric("Total Min Payments", fmt_usd(total_min))
        c4.metric(
            "Debt-to-Income",
            f"{(total_min / income * 100):.1f}%" if income > 0 else "N/A",
        )

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Emergency Fund", ef["status"])
        c6.metric("Best Strategy", best_strat)
        c7.metric("Months to Debt-Free", fmt_months(best_r["months"]))
        c8.metric("Interest Saved vs Min", fmt_usd(avl_saved))

        # Strategy summary
        st.markdown("---")
        st.subheader("Strategy Comparison")
        tbl = []
        for name, r in results.items():
            saved = max(0, min_res["total_interest"] - r["total_interest"])
            dfd = r["debt_free_date"]
            tbl.append(
                {
                    "Strategy": name,
                    "Months": r["months"],
                    "Debt-Free Date": dfd.strftime("%b %Y") if dfd else "N/A",
                    "Total Interest": fmt_usd(r["total_interest"]),
                    "Interest Saved": fmt_usd(saved),
                }
            )
        st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True)

        # Target info
        target_info = st.session_state.get("_target_info")

        # Payoff vs invest summary
        st.markdown("---")
        st.subheader("Payoff vs Invest Summary")
        pvi_rows = []
        for k in ["model_a", "model_b", "model_c"]:
            m = pvi[k]
            mo = m["months_to_payoff"]
            pvi_rows.append(
                {
                    "Model": m["name"],
                    "Months to Debt-Free": fmt_months(mo) if mo else "Beyond horizon",
                    "Total Interest": fmt_usd(m["total_interest"]),
                    "Investment Balance": fmt_usd(m["invest_balance"]),
                    "Est. Net Worth": fmt_usd(m["net_worth"]),
                }
            )
        st.dataframe(pd.DataFrame(pvi_rows), use_container_width=True, hide_index=True)

        # Emergency fund
        st.markdown("---")
        st.subheader("Emergency Fund")
        c9, c10, c11 = st.columns(3)
        c9.metric("Status", ef["status"])
        c10.metric("Current Coverage", f"{ef['current_months']:.1f} mo")
        c11.metric("Gap to Full Target", fmt_usd(ef["gap_to_full"]))
        st.info(ef["recommendation"])

        # --- Exports ---
        st.markdown("---")
        st.subheader("Export")

        col_exp1, col_exp2 = st.columns(2)

        # CSV: debt table
        with col_exp1:
            debt_export = pd.DataFrame(debts)
            strat_export_rows = []
            for name, r in results.items():
                saved = max(0, min_res["total_interest"] - r["total_interest"])
                strat_export_rows.append(
                    {
                        "Strategy": name,
                        "Months": r["months"],
                        "Total Interest ($)": r["total_interest"],
                        "Total Payments ($)": r["total_payments"],
                        "Interest Saved ($)": saved,
                    }
                )
            strat_export_df = pd.DataFrame(strat_export_rows)
            csv_buf = io.StringIO()
            csv_buf.write("# DebtFree Planner Export\n")
            csv_buf.write(f"# Generated: {date.today()}\n\n")
            csv_buf.write("## Debts\n")
            debt_export.to_csv(csv_buf, index=False)
            csv_buf.write("\n## Strategy Comparison\n")
            strat_export_df.to_csv(csv_buf, index=False)
            st.download_button(
                "⬇ Download CSV Report",
                data=csv_buf.getvalue().encode(),
                file_name="debtfree_planner_report.csv",
                mime="text/csv",
            )

        # Markdown report
        with col_exp2:
            md_report = generate_markdown_report(
                profile=profile_for_score,
                debts_list=debts,
                strategy_results=results,
                ef_status=ef,
                pvi=pvi,
                score_data=score_data,
                target_info=target_info,
            )
            st.download_button(
                "⬇ Download Markdown Report",
                data=md_report.encode(),
                file_name="debtfree_planner_report.md",
                mime="text/markdown",
            )

        # Preview markdown
        with st.expander("Preview Markdown Report"):
            st.markdown(md_report)
