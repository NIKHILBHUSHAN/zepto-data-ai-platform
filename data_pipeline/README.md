# Module 1 — Data Pipeline

## Overview

This module implements an end-to-end data pipeline using Books to Scrape as the public data source.

The pipeline performs:

1. Web scraping using `requests` and `BeautifulSoup`
2. Data cleaning and type conversion using pandas
3. Fixed-rate GBP to INR currency conversion
4. Normalized SQLite database creation
5. SQL querying
6. pandas `read_sql` analysis
7. pandas `merge` validation of the SQL JOIN

## Data Source

The data source is:

https://books.toscrape.com/

The pipeline scrapes the first five pages of the All Products catalogue.

Each catalogue page contains up to 20 books, producing 100 scraped book records.

The resulting dataset contains more than the required three categories.

## Raw Fields

The scraper collects:

- `title`
- `price`
- `star_rating`
- `availability`
- `category`

## Cleaning Decisions

### Price

The pound currency symbol is removed from the raw price.

The result is converted to a floating-point `price_gbp` column.

If a price cannot be parsed, the median valid price is used for imputation.

### Rating

The text ratings are mapped as follows:

| Text | Integer |
|---|---:|
| One | 1 |
| Two | 2 |
| Three | 3 |
| Four | 4 |
| Five | 5 |

If an unexpected rating cannot be mapped, the median valid rating is used.

### Availability

`In stock` is converted to `True`.

Other availability states, including `Out of stock`, are converted to `False`.

The comparison is performed against the complete normalized availability value so that `Out of stock` is not incorrectly classified as in stock.

### Currency Conversion

The required project-defined fixed conversion rate is:

**1 GBP = 105.50 INR**

Therefore:

`price_inr = price_gbp × 105.50`

No external currency API is used.

This is intentionally the required fixed-rate baseline specified by the assignment.

## Database Design

The SQLite database contains two normalized tables.

### categories

- `category_id` — primary key
- `category_name` — unique category name

### books

- `book_id` — primary key
- `title`
- `price_gbp`
- `price_inr`
- `rating`
- `in_stock`
- `category_id` — foreign key referencing `categories.category_id`

The category information is normalized into a separate table to avoid repeatedly storing the category name in every book record.

Foreign-key enforcement is enabled using SQLite's:

`PRAGMA foreign_keys = ON`

## SQL Queries

Six SQL queries are included in `queries.sql`.

They demonstrate:

- `SELECT`
- `WHERE`
- `ORDER BY`
- `LIMIT`
- `DISTINCT`
- `BETWEEN`
- `IN`
- `JOIN`

The executed query outputs are stored in:

`sql_outputs/`

## pandas Validation

The pipeline uses `pd.read_sql()` to read multiple SQL query results into pandas DataFrames.

The JOIN result is independently reproduced using:

`pd.merge()`

The SQL JOIN result and pandas merge result are sorted using the same ordering and compared using pandas.

The pipeline raises an error if the results are not equivalent.

The comparison output is saved as:

`sql_outputs/join_comparison.csv`

## Running the Module

From the project root:

```bash
python data_pipeline/pipeline.py

## Validation Summary

The completed pipeline successfully produced 100 cleaned book records across 29 categories.

The required fields were stored using the following types:

- `price_gbp`: float
- `rating`: integer
- `in_stock`: boolean
- `price_inr`: float

The SQLite database contains the normalized `categories` and `books` tables connected through a primary-key/foreign-key relationship.

Six SQL queries were executed covering SELECT/WHERE, ORDER BY, LIMIT, DISTINCT, BETWEEN, IN, and JOIN.

The SQL JOIN was independently reproduced using `pd.merge()`, and both results were equivalent.