from datetime import date, timedelta

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

def calculate_pay_periods(start_date, num_periods):
    """Generate a list of pay periods starting from start_date."""
    return [start_date + timedelta(weeks=2 * i) for i in range(num_periods)]

def calculate_amount_per_period(remaining_amount, periods_left):
    """Calculate the amount to contribute per pay period."""
    return remaining_amount / periods_left if periods_left > 0 else 0

def calculate_percentage(amount_per_period, gross_pay):
    """Calculate the percentage of gross pay to be contributed per pay period."""
    return (amount_per_period / gross_pay) * 100 if gross_pay > 0 else 0

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
    pay_dates = calculate_pay_periods(start_date, NO_OF_PAY_PERIODS)
    
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

