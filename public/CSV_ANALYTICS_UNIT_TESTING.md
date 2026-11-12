# 5.6 Unit Testing: CSV Analytics & Tabular Intelligence Engine

### Testing Objective
To thoroughly evaluate and verify the functional correctness, multi-tenant security isolation, tabular data parsing, and statistical calculation accuracy of the **DataSpeakAI CSV Analytics & Tabular Intelligence Engine**.

Testing validates the entire **Tabular Analytics & Ingestion Lifecycle**:
1. **Dataset Upload & Format Whitelist** — Strict file format validation permitting only tabular spreadsheet extensions (`.csv`, `.xlsx`, `.xls`) with a 25 MB file size boundary.
2. **Tabular Extraction & Schema Inference** — Accurate parsing of row structures, data types (numeric, categorical, temporal), and column names via high-performance Pandas routines.
3. **Descriptive Statistical Profiling** — Calculation of central tendencies and distributions: Mean, Standard Deviation, Median, Quartiles (Q25, Q75), Min, and Max.
4. **Categorical Cardinality & Value Counts** — Discrete frequency distribution analysis, uniqueness checks, and mode identification.
5. **Statistical Outlier Detection (IQR Technique)** — Identification of extreme data anomalies beyond the upper/lower bounds ($Q3 + 1.5 \times IQR$).
6. **AutoML Problem Classification Engine** — Dynamic detection of target variable characteristics classifying datasets as Regression, Binary/Multiclass Classification, or Unsupervised Clustering.
7. **Multi-Tenant Access Isolation** — Scoped dataset persistence in SQLite preventing cross-tenant data leaks and unauthorized query access.

---

### Table 5.6: CSV Analytics & Tabular Intelligence Unit Test Cases

| No. | Test case / Test script | Attribute and value | Expected result | Actual Result |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Check CSV datasets catalog listing and tenant scoping | `endpoint: 'GET /api/files/datasets'`<br>`tenant_id: 1` | Returns HTTP 200 with list of tenant CSV datasets, file types, and sizes. | **Pass** |
| **2** | Check dataset metadata profile retrieval | `endpoint: 'GET /api/files/{id}'`<br>`dataset_id: 4` (`covid19_analytics.csv`) | Returns HTTP 200 with dataset columns, row count (`2,500`), file type, and timestamps. | **Pass** |
| **3** | Check tabular row extraction and query pagination | `endpoint: 'GET /api/files/{id}/data?limit=25'`<br>`limit: 25` | Returns HTTP 200 with JSON row records bounded strictly by requested pagination limit. | **Pass** |
| **4** | Check cross-tenant dataset isolation & access denial | `dataset_id: 999999`<br>`tenant_id: 1` (unowned ID) | Blocks cross-tenant enumeration and returns HTTP 404 Not Found without leaking metadata. | **Pass** |
| **5** | Check CSV parsing, column mapping, and schema type inference | `schema: [order_id, customer, revenue, status]`<br>`engine: pandas.read_csv` | Accurately maps numeric and categorical column datatypes without type corruption. | **Pass** |
| **6** | Check numerical statistical metrics calculation | `metrics: [mean, median, std, min, max]`<br>`data: distribution [10.0 ... 100.0]` | Calculates accurate descriptive statistics across numerical columns. | **Pass** |
| **7** | Check categorical cardinality & frequency distribution | `column: 'status'` with 3 distinct categories<br>`values: ['completed', 'shipped', 'pending']` | Calculates correct category counts, cardinalities, and frequency percentages. | **Pass** |
| **8** | Check statistical anomaly and outlier detection via IQR bounds | `data: [10..14, outlier=1000]`<br>`method: IQR (Q75 + 1.5*IQR)` | Correctly flags statistical outlier 1000 beyond the upper interquartile ceiling. | **Pass** |
| **9** | Check AutoML problem type inference engine | `target: binary 'Yes'/'No' labels`<br>`fn: detect_problem_type` | Accurately detects classification problem type based on target cardinality. | **Pass** |
| **10** | Check file format extension whitelist validation | `extensions: ['.csv', '.xlsx', '.xls']`<br>`disallowed: ['.py', '.zip', '.exe']` | Restricts file uploads strictly to supported tabular formats and blocks executable files. | **Pass** |
| **11** | Check missing value imputation pipeline | `strategy: 'mean'`<br>`model: sklearn.impute.SimpleImputer` | Fills missing NaN records with computed column mean without data loss. | **Pass** |
| **12** | Check dataset database persistence and tenant association | `dataset_id: 4`<br>`models.Dataset.tenant_id == 1` | Confirms dataset metadata persistence and tenant scoping in SQLite. | **Pass** |

---

### Test Execution Summary
* **Total Unit Tests Executed:** 12
* **Passed:** 12 (100%)
* **Failed:** 0 (0%)
* **Average Execution Latency:** 24.6 ms
* **Test Stack:** Python 3.10+ / FastAPI / Pandas / NumPy / Scikit-Learn / SQLite / SQLAlchemy 2.0 / Pydantic v2
* **Target CSV Datasets Verified:** `Churn_Modelling.csv` (10,000 rows, 14 columns), `covid19_healthcare_hospital_analytics.csv` (2,500 rows) & `movies.csv` (146 rows)

---

### Visual Proof & Automated Execution Screenshots

#### Figure 5.6.1: DataSpeakAI CSV Analytics Hub & Dataset Selector
Verified dashboard interface displaying the dataset catalog (`Select Existing Dataset`), showing uploaded tabular files, file size metadata, upload timestamps, delete triggers, and the drag-and-drop upload zone supporting up to 25MB spreadsheet files.

![CSV Analytics Hub and Dataset Selector](assets/csv_analytics/csv_analytics_hub_overview.png)

---


#### Figure 5.6.2: Live Populated CSV Analytics Dashboard & KPI Cards (`Churn_Modelling.csv`)
Verified live rendering of 10,000 loaded customer records, trained ML classification model (`Decision Tree · 85.3%`, `F1: 83.6%`), AI-selected 7 interactive analytics charts, live business KPI metric cards (`Churn Rate: 0.2%`, `Average Balance: $76.5K`, `Average Estimated Salary: $100.1K`, `Active Member Rate: 0.5%`), and interactive multidimensional filter selectors (`Geography`, `Gender`).

![Live Populated CSV Analytics Dashboard](assets/csv_analytics/csv_analytics_dataset_loaded.png)

---

#### Figure 5.6.3: AI-Selected Categorical & Numerical Visualization Charts
Verified dynamic chart suite displaying churn distribution across Customer Age segments, Account Balance tiers, Geographic regions (Germany, France, Spain), and Active Membership status.

![AI Selected Analytics Charts](assets/csv_analytics/csv_analytics_charts_view.png)

---

#### Figure 5.6.4: Tabular Data Preview & Pagination Table
Verified client-side pagination and raw tabular row browser inspecting the 10,000 record dataset across CreditScore, Geography, Gender, Age, Tenure, Balance, NumOfProducts, HasCrCard, IsActiveMember, EstimatedSalary, and Exited columns.

![Tabular Data Preview Table](assets/csv_analytics/csv_analytics_data_table.png)
