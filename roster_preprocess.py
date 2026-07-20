import pandas as pd
import numpy as np

df = pd.read_excel("ContingentTravelDataExport-20260709142105.xlsx")

# Drop rows where the "Type" column is "Departure"
df = df.loc[df["Type"] != "Departure"].copy()

# Create Basecamp column from Unit Number
cont = df['Contingent'].astype(str).str.strip()
df['Basecamp'] = pd.Series(np.nan, index=df.index, dtype='object')
df.loc[cont.str.startswith('3'), 'Basecamp'] = 'Charlie'
df.loc[cont.str.startswith('4'), 'Basecamp'] = 'Delta'

# Create Subcamp column by combining basecamp and the second number from Contingent
df['Subcamp'] = df['Basecamp'] + '-' + df['Contingent'].astype(str).str.strip().str[1]

df.rename(columns={'Contingent': 'Unit Number'}, inplace=True)

# Split the DateTime column into separate date and time columns
df['date'] = pd.to_datetime(df['DateTime']).dt.date
df['time'] = pd.to_datetime(df['DateTime']).dt.time

# Remove the original DateTime column if no longer needed
df.drop('DateTime', axis=1, inplace=True)
df.drop('ContingentId', axis=1, inplace=True)

# Clean and normalize values in the Carrier column
s = df['Carrier']
# Preserve NaN
mask_na = s.isna()
s = s.astype(str).str.strip()
c = s.str.lower()
personal = {'15-passenger van', 'mini-van', 'truck/car/suv', 'trailer', 'personal passenger vehicle'}
motor = {'school bus', 'charter bus', 'charter or school bus'}
new = s.copy()
new[c.isin(personal)] = 'Personal Vehicle'
new[c.isin(motor)] = 'Motor Coach'
new[mask_na] = np.nan
df['Carrier'] = new

# Save the modified DataFrame to a new Excel file
df.to_excel("ContingentTravelDataExport.xlsx", index=False)