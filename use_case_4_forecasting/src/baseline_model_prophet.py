# =====================================
# 1. Import Libraries
# =====================================
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error
import matplotlib.pyplot as plt


# =====================================
# Temp. Creating a quick synthetic file until model access is fixed
# =====================================

dates = pd.date_range(start="2021-01-01", periods=200)

df = pd.DataFrame({
    "Date": dates,
    "City": "Montreal",
    "Category": "PC",
    "Sales": 200 + 10*np.sin(np.arange(200)/5) + np.random.normal(0,5,200)
})

df.to_csv("./use_case_4_forecasting/data/weekly_sales_data.csv", index=False)


# =====================================
# 1. LOAD DATA
# =====================================
df = pd.read_csv("./use_case_4_forecasting/data/weekly_sales_data.csv") 



df_vente = pd.read_csv("./use_case_4_forecasting/data/Exemple_Table_Vente.csv") 
print(df_vente.head())
print(df_vente["Division Code"].unique())
print(df_vente["Division Code"].value_counts())

df["Date"] = pd.to_datetime(df["Date"])

# =====================================
# 2. AGGREGATE TO WEEKLY 
# =====================================
df = df.set_index("Date")
weekly_df = (
    df.groupby(["City", "Category"])["Sales"]
      .resample("W")
      .sum()
      .reset_index()
)

# =====================================
# 3. PREPARE STORAGE
# =====================================
results_list = []
forecast_output = []

forecast_horizon = 8

# =====================================
# 4. LOOP THROUGH CITY + CATEGORY
# =====================================
for (city, category), group in weekly_df.groupby(["City", "Category"]):

    group = group.sort_values("Date")

    # Skip if not enough history
    if len(group) < 10:  
        continue

    group = group.rename(columns={
        "Date": "ds",
        "Sales": "y"
    })

    train = group[:-forecast_horizon]
    test = group[-forecast_horizon:]

    # =====================================
    # Build Prophet Baseline
    # =====================================
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False
    )

    try:
        model.fit(train)

        future = model.make_future_dataframe(
            periods=forecast_horizon,
            freq="W"
        )

        forecast = model.predict(future)

        forecast_test = forecast.tail(forecast_horizon)

        predictions = forecast_test["yhat"].values
        actuals = test["y"].values

        mape = mean_absolute_percentage_error(actuals, predictions)

        # Store model accuracy
        results_list.append({
            "City": city,
            "Category": category,
            "MAPE": mape
        })

        # Store 8-week forward forecast
        future_forecast = forecast.tail(forecast_horizon)

        for i in range(len(future_forecast)):
            forecast_output.append({
                "City": city,
                "Category": category,
                "Date": future_forecast.iloc[i]["ds"],
                "Forecast": future_forecast.iloc[i]["yhat"],
                "Lower_CI": future_forecast.iloc[i]["yhat_lower"],
                "Upper_CI": future_forecast.iloc[i]["yhat_upper"]
            })

    except Exception as e:
        print(f"Skipping {city} - {category} due to error:", e)


# =====================================
# 5. FINAL OUTPUT TABLES
# =====================================
accuracy_df = pd.DataFrame(results_list)
forecast_df = pd.DataFrame(forecast_output)

print("Model Accuracy Summary:")
print(accuracy_df.sort_values("MAPE").head())

print("Forecast Output Sample:")
print(forecast_df.head())

plt.figure(figsize=(10,5))

plt.plot(train["ds"], train["y"], label="Train")
plt.plot(test["ds"], test["y"], label="Actual")
plt.plot(test["ds"], predictions, label="Forecast")

plt.title(f"{city} - {category} Weekly Forecast")
plt.legend()
plt.show()