# Investigating the Relationship Between Operational Performance and Customer Repeat Purchasing in an E-commerce Marketplace

A Data Analytics BYOC (Bring Your Own Capstone) project diagnosing whether
first-order delivery performance and shipping charges are associated with
customer repeat purchasing, using the Olist Brazilian E-Commerce dataset.

## Business Problem

Repeat purchase is the clearest signal of customer satisfaction and
long-term value in an e-commerce marketplace, but only ~3% of Olist's
customers place a second order. This project investigates whether two
observable, first-order operational experiences — **delivery lateness**
and **shipping (freight) burden** — are statistically associated with
whether a customer returns to buy again, and translates the findings into
prioritised, evidence-bounded business recommendations.

## Dataset

- **Source:** [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle)
- **License:** CC BY-NC-SA 4.0
- **Scope:** ~99,441 orders / ~96,000 unique customers, Sep 2016–Oct 2018
- **PII:** None — all identifiers are anonymised/hashed by the original publisher

## Methodology Summary

1. **Data validation & cleaning** (Notebooks 01–02) — DuckDB-based ingestion,
   type casting, and construction of a customer-level analytical table using
   each customer's **first order** (temporal precedence, avoids reverse
   causality between repeat and non-repeat customers).
2. **Feature engineering** (Notebook 03) — delivery lateness flag, both a
   freight-to-price ratio band and a corrected absolute-freight-value band
   (see Known Issue below), customer value tiers, winsorized outlier-robust
   variants.
3. **Diagnostic analysis** (Notebook 04) — pre-registered hypothesis tests:
   - **H1** (delivery lateness): chi-square test, odds ratio + 95% CI
   - **H2** (freight burden): Mann-Whitney U, Cliff's delta, two-proportion z-test
   - Multicollinearity check (Spearman correlation, VIF) before modeling
   - Confirmatory logistic regression (inferential) **plus** a held-out
     train/test predictive baseline (ROC-AUC, confusion matrix) evaluating
     the same predictors' out-of-sample performance
4. **Business analysis** (Notebook 05) — segment-level exposure, Recoverable
   Revenue-at-Risk and Segment Expected Repeat Revenue (AOV × historical
   repeat rate — deliberately simple, not a CLV/DCF model), sensitivity
   scenarios in place of an unavailable intervention-effectiveness figure.
5. **Business recommendations & final report** (Notebook 06) — findings
   translated into prioritised, resource-allocation recommendations, with
   an explicit limitations section.

## Key Findings

| Hypothesis | Result | Effect size |
|---|---|---|
| **H1** — Late first-order delivery is associated with lower repeat purchase | **Significant** (χ², p = 0.0059) | Odds ratio = 0.811 (late vs. on-time/early) |
| **H2** — Higher first-order freight burden is associated with lower repeat purchase | **Not significant** on the corrected (value-based) measure (p = 0.968) | Effectively zero (+0.01pp) |
| Does the delivery effect differ by customer-value tier? | **Not significant** (likelihood-ratio test, p = 0.341) | — |
| Predictive baseline (train/test, same 4 predictors) | ROC-AUC = 0.5466 (weak, barely above random) | Consistent with the small inferential effect sizes above |

**A methodological correction is a deliberate part of this project's
narrative:** the original freight-to-price *ratio* metric showed a
significant effect, but was found to be a mechanical artifact — the ratio
is inherently confounded with order value. Rebuilding the metric on
absolute freight value (order value held as a separate control) made the
effect disappear entirely. Both versions are shown side by side in
Notebook 04, Section 11b, with the correction fully documented rather than
silently applied.

## Primary Recommendation

Prioritise **first-order delivery reliability** as the main retention-related
operational focus, ranking segments by exposure (late-order volume) and
customer value — not by a differential effect, since none was found to be
statistically significant across value tiers. Freight is not recommended as
a retention lever. A controlled operational test is recommended before
committing a large intervention budget, since the current analysis is
observational (association, not causation).

## Repository Structure

```
Final_Project_Olist_BYOC_Capstone/
├── 01_Proposal/              Problem statement & proposal form
├── 02_Data/
│   ├── 01_Raw/               Original Olist CSVs (not committed — see Setup)
│   ├── 02_Processed/         Cleaned order-level exports
│   ├── 03_Analytical/        Customer-level analytical exports
│   ├── 04_Diagnostic/        Diagnostic-analysis exports (Notebook 04)
│   ├── 05_Business_Analysis/ Business-analysis exports (Notebook 05)
│   └── 06_Final_Report/      Final report tables (Notebook 06)
├── 03_Notebooks/
│   ├── 01_Data_Inventory_and_Validation.ipynb
│   ├── 02_Data_Cleaning_and_Transformation.ipynb
│   ├── 03_EDA_and_Feature_Engineering.ipynb
│   ├── 04_Diagnostic_Analysis.ipynb
│   ├── 05_Business_Analysis_and_Revenue_at_Risk.ipynb
│   └── 06_Business_Recommendations_and_Final_Report.ipynb
├── 04_DuckDB/                Persistent DuckDB database (olist_capstone.duckdb)
├── 05_Dashboard/             Live/exported dashboard
├── 06_Report/                Final written report
├── 07_Presentation/          Presentation deck
├── src/
│   ├── __init__.py
│   └── config.py             Config-driven path resolution (no hardcoded paths)
├── tests/
│   └── test_pipeline.py       Pytest reproducibility/integrity checks
├── config.yaml                Local data-directory / DuckDB-path settings
├── requirements.txt
└── README.md                  This file
```

## Setup

1. Download the [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
   and place the 9 CSV files in `02_Data/01_Raw/` (not committed to this
   repo due to size/license — see `.gitignore`).
2. Create and activate a Python environment, then install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set the data directory either via `config.yaml` (`data_dir:` key) or an
   environment variable:
   ```
   export OLIST_DATA_DIR=/path/to/02_Data/01_Raw
   ```
4. Run the notebooks in order (01 → 06) from `03_Notebooks/`. Each notebook
   persists its outputs to the shared DuckDB database at `04_DuckDB/olist_capstone.duckdb`,
   which downstream notebooks read from directly.
5. Optionally, run the reproducibility checks:
   ```
   pytest tests/
   ```

## Tech Stack

DuckDB (primary analytical engine) · pandas · NumPy · SciPy · statsmodels ·
scikit-learn · Matplotlib · PyYAML · pytest

## Limitations

- Observational data — association, not causation.
- The analytical population excludes customers whose first order was never
  delivered (n=2,842); this exclusion is disclosed and shown to be
  conservative (Notebook 02, Section 10a), not inflationary.
- Revenue-opportunity figures are scenario estimates, not guaranteed
  forecasts, since intervention effectiveness is not observable in the
  source data.
- Segment-level prioritisation (by customer value) is a resource-allocation
  choice, not evidence that the delivery effect itself differs by segment
  (Notebook 04, Section 11a: p = 0.341).

## Author

Brijesh Arora
