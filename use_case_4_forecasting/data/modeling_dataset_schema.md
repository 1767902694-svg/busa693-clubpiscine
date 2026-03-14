# Use Case 4 — Modeling Dataset Schema

## Forecast Definition

- **Target**: `units` (weekly net units sold, clipped at 0)
- **Alternative target**: `log_units` (log1p transform)
- **Granularity**: `store_code` x `division_code` x `week_ending`
- **Forecast Horizon**: 4-8 weeks ahead

## Primary Keys

| Column | Type | Description |
|--------|------|-------------|
| `week_ending` | date | Sunday week-ending date |
| `store_code` | string | Store identifier (e.g., CP01 - Quebec) |
| `city` | string | Store city |
| `province` | string | Province (QC or ON) |
| `division_code` | string | Product division code |
| `fiscal_year` | int | Fiscal year (Nov 1 - Oct 31). FY2024 = Nov 2023 - Oct 2024. |

## Target Variables

| Column | Type | Description |
|--------|------|-------------|
| `units` | float | Net units sold (clipped at 0) |
| `gross_units` | float | Units sold before returns |
| `returns` | float | Units returned |
| `n_transactions` | int | Transaction count |
| `sales` | float | Revenue (if available) |
| `log_units` | float | log(units + 1) |

## Feature Groups

### Seasonality (Fourier Terms)
| Column | Description |
|--------|-------------|
| `sin_week_1`, `cos_week_1` | Annual Fourier, 1st harmonic (period=52) |
| `sin_week_2`, `cos_week_2` | Annual Fourier, 2nd harmonic |
| `sin_month_1`, `cos_month_1` | Monthly Fourier (period=12) |

### Calendar
| Column | Description |
|--------|-------------|
| `year_idx` | Integer year index (0, 1, 2, ...) |
| `quarter` | Quarter (1-4) |
| `week_of_yr` | ISO week number |
| `month` | Month (1-12) |
| `year` | Calendar year |
| `has_holiday` | Binary: week contains a statutory holiday |
| `n_holidays` | Count of holidays in week |
| `is_summer_peak` | Jun-Aug flag |
| `is_spring_opening` | Apr-May flag |
| `is_fall_closing` | Sep-Oct flag |
| `is_winter_off` | Nov-Mar flag |

### Quebec-Specific Holidays
| Column | Description |
|--------|-------------|
| `is_construction_holiday` | Last 2 weeks of July (ISO 29-30) |
| `is_st_jean_week` | Week containing June 24 |
| `is_victoria_day_week` | Week of Victoria Day (late May) |
| `is_labour_day_week` | First week of September |
| `is_pool_season` | May-September flag |

### Division Seasonality
| Column | Description |
|--------|-------------|
| `is_pool_div` | Pool-related divisions (PC, CH, LO, AP, SEC, DO) |
| `is_outdoor_div` | Outdoor divisions (ME, GA, BQ, PA) |
| `is_fitness_div` | Fitness divisions (FI, CR) |
| `pool_div_x_summer` | Pool division x summer interaction |
| `pool_div_x_spring` | Pool division x spring interaction |
| `outdoor_div_x_summer` | Outdoor division x summer interaction |
| `fitness_div_x_winter` | Fitness division x winter interaction |

### Weather (Raw)
| Column | Description |
|--------|-------------|
| `avg_temp` | Weekly mean temperature (C) |
| `max_temp` | Weekly mean of daily max temperature (C) |
| `total_precip` | Weekly total precipitation (mm) |
| `sunshine_hours` | Weekly sunshine hours |
| `rain_days` | Rain days in week |
| `snow_days` | Snow days in week |
| `bad_weather_days` | Rain + Thunderstorm + Snow days |
| `max_wind` | Weekly max wind speed (km/h) |
| `feels_like_max` | Weekly mean apparent temperature max (C) |
| `weekend_avg_temp` | Weekend-only average temperature |
| `weekend_bad_weather` | Weekend bad weather day count |

### Weather (Derived)
| Column | Description |
|--------|-------------|
| `*_dev` | Deviation from city-year-month mean |
| `*_dev_z` | Z-score of deviation |
| `temp_above_20` | Binary: avg_temp > 20C |
| `temp_above_25` | Binary: avg_temp > 25C |
| `temp_below_0` | Binary: avg_temp < 0C |
| `cooling_degree_days` | max(avg_temp - 18, 0) |
| `heating_degree_days` | max(18 - avg_temp, 0) |
| `heavy_rain` | Binary: total_precip > 10mm |
| `very_hot` | Binary: avg_temp > 30C |

### Weather x Season Interactions
| Column | Description |
|--------|-------------|
| `temp_x_summer` | avg_temp x is_summer_peak |
| `temp_x_spring` | avg_temp x is_spring_opening |
| `sunshine_x_summer` | sunshine_hours x is_summer_peak |
| `bad_weather_x_summer` | bad_weather_days x is_summer_peak |
| `temp_x_pool_season` | avg_temp x is_pool_season |

### Weather Lags
| Column | Description |
|--------|-------------|
| `temp_lag1` | avg_temp shifted 1 week |
| `temp_lag2` | avg_temp shifted 2 weeks |
| `precip_lag1` | total_precip shifted 1 week |

### Sales Lag & Rolling Features
| Column | Description |
|--------|-------------|
| `units_lag_1w` | Units shifted 1 week |
| `units_lag_2w` | Units shifted 2 weeks |
| `units_lag_4w` | Units shifted 4 weeks |
| `units_lag_8w` | Units shifted 8 weeks |
| `units_lag_52w` | Units shifted 52 weeks (YoY) |
| `units_yoy_change` | Year-over-year change rate |
| `units_roll4_mean` | 4-week rolling mean (shifted) |
| `units_roll4_std` | 4-week rolling std (shifted) |
| `units_roll12_mean` | 12-week rolling mean (shifted) |

## Notes
- All lag/rolling features use `shift(1)` before rolling to prevent leakage
- Weather deviation z-scores use per-city-year-month norms
- NaN values in lag features are expected at series start
- Data grows over time via Power BI API connection
