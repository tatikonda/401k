import streamlit as st
from k401 import calculate_401k_contribution, fetch_latest_401k_limit

st.title("💼 401(k) Contribution Calculator")
st.write("Use this app to estimate how much you should contribute per pay period to hit your 401(k) target.")



@st.cache_data(ttl=86400)
def get_dynamic_limit():
    return fetch_latest_401k_limit()
limit = get_dynamic_limit()
st.info(f"IRS 401(k) contribution limit for this year: **${limit:,}**")

# Input fields
col1, col2 = st.columns(2)
with col1:
    year = st.number_input("Year of First Pay Period", min_value=2020, max_value=2100, value=2025)
    month = st.number_input("Month of your First Paycheck(1–12)", min_value=1, max_value=12, value=1)
with col2:
    gross_pay = st.number_input("Bi-weekly Gross Pay ($)", min_value=0.0, value=5000.0, step=100.0)
    contributions_so_far = st.number_input("Total Contribution So Far ($)", min_value=0.0, value=10000.0, step=100.0)


annual_limit = st.number_input(
    "Annual 401(k) Limit ($)",
    min_value=0.0,
    value=float(limit),
    step=100.0
)
effective_periods = st.number_input("Effective After How Many Pay Periods?", min_value=0, max_value=26, value=0)

if st.button("Calculate"):
    result = calculate_401k_contribution(
        year,
        month,
        gross_pay,
        contributions_so_far,
        annual_limit,
        effective_periods
    )

    st.subheader("📊 Results")
    st.write(f"**Annual Limit:** ${result['annual_limit']:.2f}")
    st.write(f"**Remaining Amount:** ${result['remaining_amount']:.2f}")
    st.write(f"**Pay Periods Left:** {result['periods_left']}")
    st.write(f"**Amount per Pay Period:** ${result['amount_per_period']:.2f}")
    st.success(f"✅ New Contribution Percentage: **{result['percent_per_period']:.2f}%**")
    result = calculate_401k_contribution(
    year, month, gross_pay, contributions_so_far, annual_limit, effective_periods
    )





