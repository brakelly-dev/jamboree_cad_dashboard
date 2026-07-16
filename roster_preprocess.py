import pandas as pd
import numpy as np

df = pd.read_excel("ContingentTravelDataExport-20260709142105.xlsx")

# Drop rows where the "Type" column is "Departure"
df = df.loc[df["Type"] != "Departure"].copy()

# Create Basecamp column from Contingent
cont = df['Contingent'].astype(str).str.strip()
df['Basecamp'] = pd.Series(np.nan, index=df.index, dtype='object')
df.loc[cont.str.startswith('3'), 'basecamp'] = 'Charlie'
df.loc[cont.str.startswith('4'), 'basecamp'] = 'Delta'

# Create Subcamp column by combining basecamp and the second number from Contingent
df['Subcamp'] = df['basecamp'] + '-' + df['Contingent'].astype(str).str.extract(r'(\d)$')[0]

# Split the DateTime column into separate date and time columns
df['date'] = pd.to_datetime(df['DateTime']).dt.date
df['time'] = pd.to_datetime(df['DateTime']).dt.time

# Remove the original DateTime column if no longer needed
df.drop('DateTime', axis=1, inplace=True)

df.to_excel("ContingentTravelDataExport.xlsx", index=False)