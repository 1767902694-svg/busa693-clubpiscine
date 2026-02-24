# Feature Engineering & Parameter Calibration Report

Generated: 2026-02-23 21:11:10.192699

36 monthly observations, 7 channels, target: total_all_revenue

Controls-only baseline LOOCV R²: 0.7347

## Decay Rates

| Channel | Lambda | Source | CI | Half-life |
|---|---|---|---|---|
| Television | 0.2 | data | [0.10, 0.30] | 0.4mo |
| Radio | 0.5 | industry | [0.40, 0.60] | 1.0mo |
| Panneaux | 0.4 | industry | [0.30, 0.50] | 0.8mo |
| Social Media | 0.1 | data | [0.10, 0.20] | 0.3mo |
| Preroll | 0.3 | data | [0.20, 0.40] | 0.6mo |
| Banniere Web | 0.2 | data | [0.10, 0.30] | 0.4mo |
| Circulaire Digitale | 0.3 | industry | [0.20, 0.40] | 0.6mo |

## Saturation Functions

| Channel | Function | K / Scale |
|---|---|---|
| Television | log | $146,394 |
| Radio | power | $0 |
| Panneaux | power | $0 |
| Social Media | power | $0 |
| Preroll | log | $32,335 |
| Banniere Web | log | $25,147 |
| Circulaire Digitale | power | $0 |