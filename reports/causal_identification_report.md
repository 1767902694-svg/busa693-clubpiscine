# Feature Engineering & Parameter Calibration Report

Generated: 2026-03-01 12:20:17.144511

36 monthly observations, 7 channels, target: total_all_revenue

Controls-only baseline LOOCV R²: 0.7347

## Decay Rates (Final: Multi-Channel Grid Search)

Grid search: 16,384 combinations, best R² = 0.9499

| Channel | λ (Final) | λ (Single) | λ (Industry) | Sensitivity | CI | Half-life |
|---|---|---|---|---|---|---|
| Television | 0.10 | 0.2 | 0.7 | MODERATE | [0.01, 0.20] | 0.3mo |
| Radio | 0.20 | 0.5 | 0.5 | ROBUST | [0.10, 0.30] | 0.4mo |
| Panneaux | 0.25 | 0.4 | 0.4 | ROBUST | [0.15, 0.35] | 0.5mo |
| Social Media | 0.01 | 0.1 | 0.4 | ROBUST | [0.01, 0.11] | 0.2mo |
| Preroll | 0.45 | 0.3 | 0.5 | MODERATE | [0.35, 0.45] | 0.9mo |
| Banniere Web | 0.15 | 0.2 | 0.3 | ROBUST | [0.05, 0.25] | 0.4mo |
| Circulaire Digitale | 0.01 | 0.3 | 0.3 | ROBUST | [0.01, 0.11] | 0.2mo |

## Saturation Functions

| Channel | Function | K / Scale |
|---|---|---|
| Television | log | $127,905 |
| Radio | power | $0 |
| Panneaux | power | $0 |
| Social Media | power | $0 |
| Preroll | hill | $68,771 |
| Banniere Web | log | $23,836 |
| Circulaire Digitale | log | $7,510 |