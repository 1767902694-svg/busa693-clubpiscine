# Feature Engineering & Parameter Calibration Report

Generated: 2026-02-13 18:22:15.293959

36 monthly observations, 7 channels, target: total_all_revenue

Controls-only baseline LOOCV R²: 0.7347

## Decay Rates

| Channel | Lambda | Source | CI | Half-life |
|---|---|---|---|---|
| Television | 0.2 | data | [0.10, 0.30] | 0.4mo |
| Radio | 0.5 | industry | [0.40, 0.60] | 1.0mo |
| Panneaux | 0.4 | industry | [0.30, 0.50] | 0.8mo |
| Social Media | 0.1 | data | [0.10, 0.20] | 0.3mo |
| Preroll | 0.4 | data | [0.30, 0.40] | 0.8mo |
| Banniere Web | 0.3 | industry | [0.20, 0.40] | 0.6mo |
| Circulaire Digitale | 0.3 | industry | [0.20, 0.40] | 0.6mo |

## Saturation Functions

| Channel | Function | K / Scale |
|---|---|---|
| Television | log | $146,394 |
| Radio | power | $0 |
| Panneaux | power | $0 |
| Social Media | power | $0 |
| Preroll | log | $37,881 |
| Banniere Web | hill | $32,834 |
| Circulaire Digitale | power | $0 |