from datetime import date, timedelta
import requests
from bs4 import BeautifulSoup
import re

# Static Parameters
NO_OF_PAY_PERIODS = 26

def get_date_input(prompt):
    """Get date input from user and return as a datetime.date object."""
    while True:
        try:
            y, m, d = map(int, input(prompt).split('-'))
            return date(y, m, d)
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

def second_friday_of_month(year, month):
    """Calculate the date of the second Friday of a given month and year."""
    first_day = date(year, month, 1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday() + 7) % 7)
    second_friday = first_friday + timedelta(weeks=1)
    return second_friday


def calculate_amount_per_period(remaining_amount, periods_left):
    """Calculate the amount to contribute per pay period."""
    return remaining_amount / periods_left if periods_left > 0 else 0

def calculate_percentage(amount_per_period, gross_pay):
    """Calculate the percentage of gross pay to be contributed per pay period."""
    return (amount_per_period / gross_pay) * 100 if gross_pay > 0 else 0

from datetime import date, timedelta

NO_OF_PAY_PERIODS = 26

def second_friday_of_month(year, month):
    first_day = date(year, month, 1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday() + 7) % 7)
    second_friday = first_friday + timedelta(weeks=1)
    return second_friday

def calculate_pay_periods_old(start_date, num_periods):
    return [start_date + timedelta(weeks=2 * i) for i in range(num_periods)]

def calculate_pay_periods(start_date):
    """
    Generate pay periods (biweekly) starting from start_date until the end of the year.
    Returns a list of datetime.date objects.
    """
    pay_dates = []
    current_date = start_date
    year_end = date(start_date.year, 12, 31)

    while current_date <= year_end:
        pay_dates.append(current_date)
        current_date += timedelta(weeks=2)

    return pay_dates

def calculate_amount_per_period(remaining_amount, periods_left):
    return remaining_amount / periods_left if periods_left > 0 else 0

def calculate_percentage(amount_per_period, gross_pay):
    return (amount_per_period / gross_pay) * 100 if gross_pay > 0 else 0

def calculate_401k_contribution(year, month, gross_pay_biweekly,
                                contributions_so_far, annual_limit,
                                effective_periods=0):

    start_date = second_friday_of_month(year, month)
    remaining_amount_for_401k = annual_limit - contributions_so_far
    
    # Generate pay periods
    #pay_dates = calculate_pay_periods(start_date, NO_OF_PAY_PERIODS)
    pay_dates = calculate_pay_periods(start_date)

    
    # Calculate remaining pay periods
    today = date.today()
    future_pay_periods = [d for d in pay_dates if d > today]
    
    if effective_periods > len(future_pay_periods):
        print("Effective periods exceed the number of remaining pay periods. Adjusting to remaining periods.")
        effective_periods = len(future_pay_periods)
    
    if effective_periods > 0:
        # Adjust future pay periods based on effective_periods
        next_pay_period = future_pay_periods[effective_periods - 1] if len(future_pay_periods) >= effective_periods else today
        future_pay_periods = [d for d in pay_dates if d >= next_pay_period]
        no_of_pay_periods_left = len(future_pay_periods)
    else:
        # Immediate effect
        no_of_pay_periods_left = len(future_pay_periods)
    
    amount_per_pay_period = calculate_amount_per_period(remaining_amount_for_401k, no_of_pay_periods_left)
    percentage_per_pay_period = calculate_percentage(amount_per_pay_period, gross_pay_biweekly)

    remaining_amount_for_401k = max(0.0, annual_limit - contributions_so_far)
    amount_per_pay_period = calculate_amount_per_period(remaining_amount_for_401k, no_of_pay_periods_left)
    percentage_per_pay_period = calculate_percentage(amount_per_pay_period, gross_pay_biweekly)

    return {
        "annual_limit": annual_limit,
        "remaining_amount": remaining_amount_for_401k,
        "periods_left": no_of_pay_periods_left,
        "amount_per_period": amount_per_pay_period,
        "percent_per_period": percentage_per_pay_period,
        "first_future_pay_date": future_pay_periods[0] if future_pay_periods else None,
        "future_pay_periods": future_pay_periods,
        "all_pay_dates": pay_dates,

    }


def fetch_latest_401k_limit():
    """
    Fetch the most recent 401(k) contribution limit from Fidelity's page.
    It searches for the current year in the text and extracts the corresponding dollar value.
    """
    try:
        url = "https://www.fidelity.com/learning-center/smart-money/401k-contribution-limits"
        resp = requests.get(url, timeout=10)
        text = resp.text

        # Determine which year's limit to look for (current or next)
        current_year = date.today().year

        # Regex pattern to find something like:
        # 'For 2025, the most you can contribute ... is $23,500'
        pattern = rf"For {current_year}.*?\$([0-9,]+)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if not match:
            # Fallback: try next year if IRS already published it
            next_year = current_year + 1
            pattern = rf"For {next_year}.*?\$([0-9,]+)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if match:
            return int(match.group(1).replace(",", ""))

    except Exception as e:
        print("Error fetching 401k limit:", e)

    # fallback default if all else fails
    return 23500


def main():

    # Input
    year = int(input("Enter the year for the first pay period: "))
    month = int(input("Enter the month for the first pay period: "))
    start_date = second_friday_of_month(year, month)
    
    gross_pay_biweekly = float(input('Bi-weekly Gross Pay: '))
    contributions_so_far = float(input('Total Contribution so far: '))
    
    # User input for annual contribution limit
    annual_limit = float(input('Enter the annual 401(k) contribution limit for the current year: '))
    
    effective_periods = int(input('In how many pay periods should the change be effective? '))
    
    remaining_amount_for_401k = annual_limit - contributions_so_far
    
    # Generate pay periods
    #pay_dates = calculate_pay_periods(start_date, NO_OF_PAY_PERIODS)
    pay_dates = calculate_pay_periods(start_date)
    
    # Calculate remaining pay periods
    today = date.today()
    future_pay_periods = [d for d in pay_dates if d > today]
    
    if effective_periods > len(future_pay_periods):
        print("Effective periods exceed the number of remaining pay periods. Adjusting to remaining periods.")
        effective_periods = len(future_pay_periods)
    
    if effective_periods > 0:
        # Adjust future pay periods based on effective_periods
        next_pay_period = future_pay_periods[effective_periods - 1] if len(future_pay_periods) >= effective_periods else today
        future_pay_periods = [d for d in pay_dates if d >= next_pay_period]
        no_of_pay_periods_left = len(future_pay_periods)
    else:
        # Immediate effect
        no_of_pay_periods_left = len(future_pay_periods)
    
    amount_per_pay_period = calculate_amount_per_period(remaining_amount_for_401k, no_of_pay_periods_left)
    percentage_per_pay_period = calculate_percentage(amount_per_pay_period, gross_pay_biweekly)
    
    # Output
    print(f'Annual contribution limit: ${annual_limit:.2f}')
    print(f'Remaining amount you can contribute: ${remaining_amount_for_401k:.2f}')
    print(f'No of pay periods left: {no_of_pay_periods_left}')
    print(f'Amount per pay period: ${amount_per_pay_period:.2f}')
    print(f'New percentage per pay period: {percentage_per_pay_period:.2f}%')

if __name__ == "__main__":
    main()

