from datetime import *

# Static parameters
max_401k_contribution = int(20500)
no_of_pay_periods = int(26)

# Input first pay date
y1, m1, d1 = [int(x) for x in input("First pay date in (YYYY-MM-DD) : ").split('-')]
d = date(y1, m1, d1)

gross_pay_biweekly = float(input('Bi-weekly Gross Pay: '))
contributions_so_far = float(input('Total Contribution so far: '))
remaining_amount_for_401k = float(max_401k_contribution - contributions_so_far)

# create empty list
pay_dates_list = []
pay_dates_list.append(d)

# Generate the pay period list
def pay_dates(d):
    for i in range(1, no_of_pay_periods):
        d = (d + timedelta(days=14))
        pay_dates_list.append(d)


# Get today's date
pay_periods_left_list = []
def pay_periods_left():
    pay_periods_left_list.append(date.today())

pay_dates(d)
pay_periods_left()

# To determine the no of pay periods left for the year
count = 0
for d in pay_dates_list:
    for dt in pay_periods_left_list:
        if d > dt:
            count = count + 1

no_of_pay_periods_left = int(count)

print('Remaining amount you can contribute:', remaining_amount_for_401k)
print('No of pay periods left:', no_of_pay_periods_left)

amount_per_pay_period = float(remaining_amount_for_401k/no_of_pay_periods_left)
percentage_per_pay_period = float((amount_per_pay_period/gross_pay_biweekly)*100)

print('Amount per pay period:', amount_per_pay_period)
print('New percentage per pay period:', percentage_per_pay_period)
