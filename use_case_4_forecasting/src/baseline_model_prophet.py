# =====================================
# USE CASE 4 - Franchise Demand Forecasting
# Baseline Prophet Model (pre-data access)
# =====================================

# =====================================
# 1. IMPORTS
# =====================================

import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error
import matplotlib.pyplot as plt
import os

import openmeteo_requests
import requests_cache
from retry_requests import retry

from datetime import date
from dateutil.relativedelta import relativedelta




os.makedirs("./use_case_4_forecasting/data", exist_ok=True)
os.makedirs("./use_case_4_forecasting/outputs", exist_ok=True)
os.makedirs("./use_case_4_forecasting/plots", exist_ok=True)

today = date.today()
three_years_ago = today - relativedelta(years=3)



# =====================================
# 2. SYNTHETIC DATA (until Power BI access)
# =====================================
np.random.seed(42)
dates = pd.date_range(start="2021-01-01", periods=500, freq="D")

cities = ["Montreal", "Saguenay", "Laval"]
categories = ["Hotubs", "Pools", "Backyard"]

rows = []
for city in cities:
    for category in categories:
        sales = (
            200
            + 10 * np.sin(np.arange(500) / 10)          
            + 5 * (np.arange(500) / 500)                
            + np.random.normal(0, 8, 500)                
        )
        for i, date in enumerate(dates):
            rows.append({
                "Date": date,
                "City": city,
                "Category": category,
                "Sales": max(0, sales[i])                # no negative sales
            })

df = pd.DataFrame(rows)
df.to_csv("./use_case_4_forecasting/data/weekly_sales_data.csv", index=False)
print(f"Synthetic data created: {df.shape[0]} rows across {len(cities)} cities and {len(categories)} categories")


# =====================================
# 3. LOAD & AGGREGATE TO WEEKLY
# =====================================
df = pd.read_csv("./use_case_4_forecasting/data/weekly_sales_data.csv")
df["Date"] = pd.to_datetime(df["Date"])

weekly_df = (
    df.set_index("Date")
    .groupby(["City", "Category"])["Sales"]
    .resample("W")
    .sum()
    .reset_index()
)

print(f"Weekly aggregated: {weekly_df.shape[0]} rows")


# =====================================
# 4. WEATHER REGRESSOR STUB
# Once Open-Meteo or Visual Crossing data is available,
# merge it here by City + Week before the loop.
#
# Expected schema:
#   ds (datetime) | City | avg_temp | total_precip
#
# weather_df = pd.read_csv("weather_by_city_week.csv")
# weather_df["ds"] = pd.to_datetime(weather_df["ds"])

# =====================================
# Weather Data Fetcher
# Source: Open-Meteo 
# =====================================

# pip install openmeteo-requests requests-cache retry-requests


os.makedirs("./use_case_4_forecasting/data", exist_ok=True)

# =====================================
# 1. CITY COORDINATES
# Update this dict once you see the full
# store list from Michèle's Power BI
# =====================================
CITIES = {
    "Montreal":  {"lat": 45.5017, "lon": -73.5673},
    "Laval":   {"lat": 45.6066, "lon": -73.7124},
    "Saguenay": {"lat": 48.4276, "lon": -71.0600},
  
}

# =====================================
# 2. DATE RANGES
# Historical: match your sales data range
# Forecast:   up to 16 days ahead (Open-Meteo free limit)
# =====================================



HISTORICAL_START = three_years_ago
HISTORICAL_END   = today




FORECAST_DAYS    = 16  # max on free tier (~2 weeks forward)

# =====================================
# 3. SETUP CLIENT (with caching + retry)
# Caching avoids re-fetching same data
# =====================================
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=3, backoff_factor=0.2)
client = openmeteo_requests.Client(session=retry_session)

# =====================================
# 4. WEATHER CLASSIFICATION FUNCTION
# Based on WMO weather codes:
# https://open-meteo.com/en/docs#weathervariables
# =====================================
def classify_weather(df):
    def get_condition(code):
        if code == 0:
            return "Clear"
        elif code in range(1, 4):
            return "Cloudy"
        elif code in range(45, 58):
            return "Fog"
        elif code in range(51, 68):
            return "Rain"
        elif code in range(71, 78):
            return "Snow"
        elif code in range(80, 83):
            return "Rain"       # rain showers
        elif code in range(85, 87):
            return "Snow"       # snow showers
        elif code in range(95, 100):
            return "Thunderstorm"
        else:
            return "Other"

    df["weather_condition"] = df["weathercode"].apply(get_condition)
    df["is_rain"] = (df["weather_condition"] == "Rain").astype(int)
    df["is_snow"] = (df["weather_condition"] == "Snow").astype(int)
    df["is_bad_weather"] = (
        df["weather_condition"].isin(["Rain", "Snow", "Thunderstorm", "Fog"])
    ).astype(int)
    return df


# =====================================
# 5. FETCH HISTORICAL WEATHER
# Variables: temp (mean), precipitation sum
# =====================================
def fetch_historical(city, lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": HISTORICAL_START,
        "end_date": HISTORICAL_END,
        "daily": ["temperature_2m_mean", "precipitation_sum", "weathercode"],
        "timezone": "America/Toronto"
    }
    responses = client.weather_api(
        "https://archive-api.open-meteo.com/v1/archive",
        params=params
    )
    r = responses[0].Daily()
    df = pd.DataFrame({
        "date":         pd.date_range(
                            start=pd.to_datetime(r.Time(), unit="s"),
                            periods=r.Variables(0).ValuesAsNumpy().shape[0],
                            freq="D"
                        ),
        "avg_temp":     r.Variables(0).ValuesAsNumpy(),
        "total_precip": r.Variables(1).ValuesAsNumpy(),
        "weathercode":  r.Variables(2).ValuesAsNumpy().astype(int),
        "City":         city
    })
    df = classify_weather(df)
    return df


# =====================================
# 5. FETCH FORECAST WEATHER
# =====================================
def fetch_forecast(city, lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_mean", "precipitation_sum", "weathercode"],
        "timezone": "America/Toronto",
        "forecast_days": FORECAST_DAYS
    }
    responses = client.weather_api(
        "https://api.open-meteo.com/v1/forecast",
        params=params
    )
    r = responses[0].Daily()
    df = pd.DataFrame({
        "date":         pd.date_range(
                            start=pd.to_datetime(r.Time(), unit="s"),
                            periods=r.Variables(0).ValuesAsNumpy().shape[0],
                            freq="D"
                        ),
        "avg_temp":     r.Variables(0).ValuesAsNumpy(),
        "total_precip": r.Variables(1).ValuesAsNumpy(),
        "weathercode":  r.Variables(2).ValuesAsNumpy().astype(int),
        "City":         city
    })
    df = classify_weather(df)
    return df


# =====================================
# 6. LOOP THROUGH ALL CITIES & AGGREGATE
# =====================================
all_historical = []
all_forecast   = []

for city, coords in CITIES.items():
    print(f"Fetching weather for {city}...")
    try:
        hist = fetch_historical(city, coords["lat"], coords["lon"])
        fcast = fetch_forecast(city, coords["lat"], coords["lon"])
        all_historical.append(hist)
        all_forecast.append(fcast)
        print(f"  ✓ {city}: {len(hist)} historical days, {len(fcast)} forecast days")
    except Exception as e:
        print(f"  ✗ {city} failed: {e}")

hist_df  = pd.concat(all_historical, ignore_index=True)
fcast_df = pd.concat(all_forecast, ignore_index=True)

# =====================================
# 7. AGGREGATE TO WEEKLY
# Aligns with Prophet's weekly sales data
# =====================================
def aggregate_weekly(df):
    df["date"] = pd.to_datetime(df["date"])
    return (
        df.set_index("date")
          .groupby("City")
          .resample("W")
          .agg(
              avg_temp      =("avg_temp",       "mean"),
              total_precip  =("total_precip",   "sum"),
              rain_days     =("is_rain",         "sum"),  # # of rainy days that week
              snow_days     =("is_snow",         "sum"),  # # of snowy days that week
              bad_weather_days=("is_bad_weather","sum")   # combined bad weather days
          )
          .reset_index()
          .rename(columns={"date": "ds"})
    )

hist_weekly  = aggregate_weekly(hist_df)
fcast_weekly = aggregate_weekly(fcast_df)

# Combine into one table (historical + forward)
weather_df = pd.concat([hist_weekly, fcast_weekly], ignore_index=True)
weather_df = weather_df.drop_duplicates(subset=["City", "ds"]).sort_values(["City", "ds"])

# =====================================
# 8. SAVE
# =====================================
weather_df.to_csv("./use_case_4_forecasting/data/weather_by_city_week.csv", index=False)
print(f"\nWeather data saved: {weather_df.shape[0]} rows")
print(weather_df.head(10).to_string(index=False))




# =====================================


# =====================================
# 5. FORECASTING LOOP
# =====================================
FORECAST_HORIZON = 8   # weeks ahead
MIN_HISTORY = 20       # minimum weeks required to fit

results_list = []
forecast_output = []

for (city, category), group in weekly_df.groupby(["City", "Category"]):

    group = group.sort_values("Date").rename(columns={"Date": "ds", "Sales": "y"})

    if len(group) < MIN_HISTORY:
        print(f"Skipping {city} - {category}: not enough history ({len(group)} weeks)")
        continue

    # --- Train / Test Split ---
    train = group.iloc[:-FORECAST_HORIZON]
    test  = group.iloc[-FORECAST_HORIZON:]

    # --- Build Model ---
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95           # 95% confidence intervals
    )

    # STUB: Add weather regressors when data is available
    # model.add_regressor("avg_temp")
    # model.add_regressor("total_precip")

    try:
        model.fit(train)

        # --- Evaluation: predict over test period ---
        test_future = model.make_future_dataframe(periods=FORECAST_HORIZON, freq="W")
        test_forecast = model.predict(test_future)

        eval_preds = test_forecast.tail(FORECAST_HORIZON)["yhat"].values
        actuals     = test["y"].values

        mape = mean_absolute_percentage_error(actuals, eval_preds)
        mae  = mean_absolute_error(actuals, eval_preds)

        results_list.append({
            "City": city,
            "Category": category,
            "MAPE": round(mape, 4),
            "MAE": round(mae, 2),
            "Train_Weeks": len(train),
            "Test_Weeks": FORECAST_HORIZON
        })

        # --- True Forward Forecast: beyond available data ---
        # Refit on ALL available data, then forecast forward
        full_model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95
        )
        full_model.fit(group)

        full_future = full_model.make_future_dataframe(periods=FORECAST_HORIZON, freq="W")
        full_forecast = full_model.predict(full_future)

        forward_forecast = full_forecast.tail(FORECAST_HORIZON)

        for _, row in forward_forecast.iterrows():
            forecast_output.append({
                "City": city,
                "Category": category,
                "Week": row["ds"],
                "Forecast_Sales": round(max(0, row["yhat"]), 2),
                "Lower_CI": round(max(0, row["yhat_lower"]), 2),
                "Upper_CI": round(max(0, row["yhat_upper"]), 2)
            })

        # --- Plot: one per city/category ---
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(train["ds"], train["y"], label="Train", color="steelblue")
        ax.plot(test["ds"], test["y"], label="Actual", color="green")
        ax.plot(test["ds"], eval_preds, label="Forecast (eval)", color="orange", linestyle="--")
        ax.fill_between(
            eval_preds_dates := pd.to_datetime(test_forecast.tail(FORECAST_HORIZON)["ds"]),
            test_forecast.tail(FORECAST_HORIZON)["yhat_lower"],
            test_forecast.tail(FORECAST_HORIZON)["yhat_upper"],
            alpha=0.2, color="orange", label="95% CI"
        )
        ax.set_title(f"{city} – {category} | MAPE: {mape:.1%} | MAE: {mae:.1f}")
        ax.legend()
        ax.set_xlabel("Week")
        ax.set_ylabel("Weekly Sales")
        plt.tight_layout()
        plt.savefig(f"./use_case_4_forecasting/plots/{city}_{category}_forecast.png", dpi=150)
        plt.close()

    except Exception as e:
        print(f"  ⚠ Skipping {city} - {category}: {e}")


# =====================================
# 6. OUTPUT TABLES
# =====================================
accuracy_df  = pd.DataFrame(results_list)
forecast_df  = pd.DataFrame(forecast_output)

accuracy_df.to_csv("./use_case_4_forecasting/outputs/model_accuracy.csv", index=False)
forecast_df.to_csv("./use_case_4_forecasting/outputs/forecast_output.csv", index=False)

print("\n--- Model Accuracy Summary ---")
print(accuracy_df.sort_values("MAPE").to_string(index=False))

print("\n--- Forecast Output Sample (first 10 rows) ---")
print(forecast_df.head(10).to_string(index=False))
print(f"\nTotal forecast rows: {len(forecast_df)}")
print("Plots saved to ./use_case_4_forecasting/plots/")