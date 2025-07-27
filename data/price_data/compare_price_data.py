import pandas as pd

df1 = pd.read_csv("bitcoin_data.csv")
df2 = pd.read_csv("bitcoin_2021_2024.csv")

df1.columns = df1.columns.str.lower()
df2.columns = df2.columns.str.lower()

df1.rename(columns={"date": "date", "close": "close"}, inplace=True)
df2.rename(columns={"date": "date", "close": "close"}, inplace=True)

df1["date"] = pd.to_datetime(df1["date"])
df2["date"] = pd.to_datetime(df2["date"])

merged = pd.merge(df1[["date", "close"]], df2[["date", "close"]], on="date", suffixes=('_df1', '_df2'))

# Convert close columns to numeric
merged["close_df1"] = pd.to_numeric(merged["close_df1"], errors="coerce")
merged["close_df2"] = pd.to_numeric(merged["close_df2"], errors="coerce")

# Drop rows with NaNs
merged.dropna(subset=["close_df1", "close_df2"], inplace=True)

# Correlation
corr = merged["close_df1"].corr(merged["close_df2"])
print(f"Correlation of daily close prices: {corr:.4f}")

# Percentage error
merged["pct_error"] = ((merged["close_df1"] - merged["close_df2"]).abs() / merged["close_df2"]) * 100

print(f"Mean % error: {merged['pct_error'].mean():.4f}")
print(f"Median % error: {merged['pct_error'].median():.4f}")

merged.to_csv("bitcoin_comparison.csv", index=False)
