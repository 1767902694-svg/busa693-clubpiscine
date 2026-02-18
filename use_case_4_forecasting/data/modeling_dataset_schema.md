# Use Case 4 – Modeling Dataset Schema

## Forecast Definition

Target:
- weekly_sales_volume

Granularity:
- week_start_date
- region
- product_category

Forecast Horizon:
- 4–8 weeks ahead

---

## Modeling Dataset Structure

### Primary Keys
- week_start_date (date)
- region (store region or aggregated geographic level)
- product_category

### Target Variable
- weekly_sales_volume

---

## Feature Groups

### 1. Time Features
- week_of_year
- month
- year
- holiday_flag

### 2. Weather Features
- avg_temperature
- total_precipitation

### 3. Lag Features
- sales_lag_1 (previous week)
- sales_lag_4 (previous 4 weeks)
- rolling_mean_4

### 4. Optional Features
- promo_flag (if available)
- marketing_spend (if available)
