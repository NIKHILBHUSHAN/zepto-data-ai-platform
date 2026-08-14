# Module 2 — Analytics Pipeline

## Overview

This module implements an end-to-end analytics and machine-learning workflow using the Titanic dataset.

The workflow covers:

1. Dataset loading and offline storage
2. Data profiling
3. Missing-value analysis and cleaning
4. Univariate analysis
5. Bivariate and multivariate analysis
6. Feature engineering
7. Leakage-safe train/test splitting
8. Classification modeling
9. Class-imbalance handling
10. Hyperparameter tuning
11. Random Forest OOB validation
12. Regression modeling
13. Model interpretation
14. Model persistence and reload validation

The module is implemented using two notebooks:

- `01_eda.ipynb` — exploratory data analysis and cleaning
- `02_modeling.ipynb` — feature engineering, classification, regression, evaluation, and model persistence

---

## Dataset

The Titanic dataset is loaded once using:

```python
sns.load_dataset("titanic")