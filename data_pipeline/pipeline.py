import os
import sqlite3
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"
GBP_TO_INR = 105.50
DATABASE_PATH = "data_pipeline/zepto_books.db"
OUTPUT_DIR = "data_pipeline/sql_outputs"

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def scrape_book(book, session, page_url):
    """Extract raw fields from one book."""

    title = book.h3.a["title"]

    price = book.select_one(".price_color").get_text(strip=True)

    star_rating = book.select_one("p.star-rating")["class"][1]

    availability = book.select_one(
        ".availability"
    ).get_text(" ", strip=True)

    book_url = book.h3.a["href"]

    full_book_url = urljoin(
        page_url,
        book_url
    )

    response = session.get(
        full_book_url,
        timeout=10
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    breadcrumb = soup.select(
        "ul.breadcrumb li a"
    )

    category = breadcrumb[-1].get_text(
        strip=True
    )

    return {
        "title": title,
        "price": price,
        "star_rating": star_rating,
        "availability": availability,
        "category": category,
    }


def scrape_catalogue(session, max_pages=5):
    """Scrape the first five catalogue pages."""

    books_data = []

    current_url = BASE_URL
    page_number = 1

    while current_url and page_number <= max_pages:

        print(
            f"Scraping catalogue page {page_number}: "
            f"{current_url}"
        )

        response = session.get(
            current_url,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        books = soup.select(
            "article.product_pod"
        )

        print(
            f"Books found: {len(books)}"
        )

        for book in books:

            books_data.append(
                scrape_book(
                    book,
                    session,
                    current_url
                )
            )

        next_button = soup.select_one(
            "li.next a"
        )

        if next_button and page_number < max_pages:

            current_url = urljoin(
                current_url,
                next_button["href"]
            )

            page_number += 1

        else:
            current_url = None

    return books_data


def clean_data(books):
    """Clean and enrich the scraped records."""

    df = pd.DataFrame(books)

    # Price: remove currency/encoding artifacts
    # and convert to numeric.
    df["price_gbp"] = (
        df["price"]
        .astype(str)
        .str.replace("£", "", regex=False)
        .str.replace("Â", "", regex=False)
        .str.strip()
    )

    df["price_gbp"] = pd.to_numeric(
        df["price_gbp"],
        errors="coerce"
    )

    # Median imputation for invalid numeric prices.
    price_median = df["price_gbp"].median()

    df["price_gbp"] = df["price_gbp"].fillna(
        price_median
    )

    # Convert text rating to integer.
    df["rating"] = df["star_rating"].map(
        RATING_MAP
    )

    # Median imputation for invalid ratings.
    rating_median = int(
        df["rating"].median()
    )

    df["rating"] = (
        df["rating"]
        .fillna(rating_median)
        .astype(int)
    )

    # Parse availability exactly.
    # This avoids incorrectly treating
    # "Out of stock" as "In stock".
    df["in_stock"] = (
        df["availability"]
        .str.strip()
        .str.lower()
        .eq("in stock")
        .astype(bool)
    )

    # Required fixed project conversion.
    df["price_inr"] = (
        df["price_gbp"] * GBP_TO_INR
    )

    return df


def create_database(
    df,
    database_path=DATABASE_PATH
):
    """Create normalized SQLite database."""

    connection = sqlite3.connect(
        database_path
    )

    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA foreign_keys = ON"
    )

    cursor.execute(
        "DROP TABLE IF EXISTS books"
    )

    cursor.execute(
        "DROP TABLE IF EXISTS categories"
    )

    cursor.execute(
        """
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price_gbp REAL NOT NULL,
            price_inr REAL NOT NULL,
            rating INTEGER NOT NULL,
            in_stock INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (category_id)
                REFERENCES categories(category_id)
        )
        """
    )

    categories = sorted(
        df["category"].unique()
    )

    cursor.executemany(
        """
        INSERT INTO categories (category_name)
        VALUES (?)
        """,
        [
            (category,)
            for category in categories
        ]
    )

    cursor.execute(
        """
        SELECT category_id, category_name
        FROM categories
        """
    )

    category_map = {
        name: category_id
        for category_id, name in cursor.fetchall()
    }

    rows = []

    for _, row in df.iterrows():

        rows.append(
            (
                row["title"],
                float(row["price_gbp"]),
                float(row["price_inr"]),
                int(row["rating"]),
                int(row["in_stock"]),
                category_map[row["category"]],
            )
        )

    cursor.executemany(
        """
        INSERT INTO books (
            title,
            price_gbp,
            price_inr,
            rating,
            in_stock,
            category_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    connection.commit()
    connection.close()

    print(
        f"Database created: {database_path}"
    )


def run_sql_queries(
    database_path=DATABASE_PATH
):
    """Execute required SQL queries and save outputs."""

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    connection = sqlite3.connect(
        database_path
    )

    queries = {
        "query_01_where": """
            SELECT title, rating, price_gbp
            FROM books
            WHERE rating >= 4
        """,

        "query_02_order_limit": """
            SELECT title, price_gbp, price_inr
            FROM books
            ORDER BY price_gbp DESC
            LIMIT 10
        """,

        "query_03_distinct": """
            SELECT DISTINCT category_name
            FROM categories
            ORDER BY category_name
        """,

        "query_04_between": """
            SELECT title, price_gbp, rating
            FROM books
            WHERE price_gbp BETWEEN 20 AND 40
            ORDER BY price_gbp
        """,

        "query_05_in": """
            SELECT title, rating, category_id
            FROM books
            WHERE category_id IN (
                SELECT category_id
                FROM categories
                WHERE category_name IN (
                    'Fiction',
                    'Poetry',
                    'Mystery'
                )
            )
        """,

        "query_06_join": """
            SELECT
                b.book_id,
                b.title,
                c.category_name,
                b.rating,
                b.price_gbp,
                b.price_inr,
                b.in_stock
            FROM books b
            JOIN categories c
                ON b.category_id = c.category_id
            ORDER BY
                b.rating DESC,
                b.price_gbp DESC
            LIMIT 10
        """,
    }

    print()
    print("=" * 60)
    print("SQL QUERY RESULTS")
    print("=" * 60)

    for query_name, query in queries.items():

        print()
        print(query_name)
        print("-" * 60)

        result = pd.read_sql(
            query,
            connection
        )

        print(result.to_string(index=False))

        output_path = os.path.join(
            OUTPUT_DIR,
            f"{query_name}.csv"
        )

        result.to_csv(
            output_path,
            index=False
        )

    connection.close()

    return queries


def validate_with_pandas(
    database_path=DATABASE_PATH
):
    """
    Validate SQL results using pd.read_sql
    and reproduce the join using pd.merge.
    """

    connection = sqlite3.connect(
        database_path
    )

    # First query result using pd.read_sql.
    where_query = """
        SELECT title, rating, price_gbp
        FROM books
        WHERE rating >= 4
    """

    where_df = pd.read_sql(
        where_query,
        connection
    )

    where_df.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "pandas_read_sql_where.csv"
        ),
        index=False
    )

    # Second query result using pd.read_sql.
    between_query = """
        SELECT title, price_gbp, rating
        FROM books
        WHERE price_gbp BETWEEN 20 AND 40
        ORDER BY price_gbp
    """

    between_df = pd.read_sql(
        between_query,
        connection
    )

    between_df.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "pandas_read_sql_between.csv"
        ),
        index=False
    )

    # SQL JOIN result.
    join_query = """
        SELECT
            b.book_id,
            b.title,
            c.category_name,
            b.rating,
            b.price_gbp,
            b.price_inr,
            b.in_stock
        FROM books b
        JOIN categories c
            ON b.category_id = c.category_id
        ORDER BY
            b.rating DESC,
            b.price_gbp DESC
        LIMIT 10
    """

    sql_join_df = pd.read_sql(
        join_query,
        connection
    )

    # Read the two tables into pandas.
    books_df = pd.read_sql(
        "SELECT * FROM books",
        connection
    )

    categories_df = pd.read_sql(
        "SELECT * FROM categories",
        connection
    )

    connection.close()

    # Reproduce the SQL JOIN using pandas only.
    pandas_join_df = pd.merge(
        books_df,
        categories_df,
        on="category_id",
        how="inner"
    )

    pandas_join_df = pandas_join_df[
        [
            "book_id",
            "title",
            "category_name",
            "rating",
            "price_gbp",
            "price_inr",
            "in_stock",
        ]
    ]

    pandas_join_df = pandas_join_df.sort_values(
        by=["rating", "price_gbp"],
        ascending=[False, False]
    ).head(10)

    # Reset indexes before comparison.
    sql_compare = sql_join_df.reset_index(
        drop=True
    )

    pandas_compare = pandas_join_df.reset_index(
        drop=True
    )

    equivalent = sql_compare.equals(
        pandas_compare
    )

    # Save both outputs side by side.
    comparison = pd.concat(
        [
            sql_compare.add_suffix("_sql"),
            pandas_compare.add_suffix("_pandas"),
        ],
        axis=1
    )

    comparison.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "join_comparison.csv"
        ),
        index=False
    )

    print()
    print("=" * 60)
    print("PANDAS VALIDATION")
    print("=" * 60)

    print(
        "\npd.read_sql() WHERE result:"
    )

    print(
        where_df.head().to_string(
            index=False
        )
    )

    print(
        "\npd.read_sql() BETWEEN result:"
    )

    print(
        between_df.head().to_string(
            index=False
        )
    )

    print(
        "\nSQL JOIN result:"
    )

    print(
        sql_compare.to_string(
            index=False
        )
    )

    print(
        "\nEquivalent pd.merge() result:"
    )

    print(
        pandas_compare.to_string(
            index=False
        )
    )

    print(
        "\nJOIN results equivalent:",
        equivalent
    )

    if not equivalent:
        raise ValueError(
            "SQL JOIN and pandas merge results "
            "are not equivalent."
        )


def main():

    session = requests.Session()

    # 1. Scrape.
    books = scrape_catalogue(
        session,
        max_pages=5
    )

    print()
    print(
        "Total raw books scraped:",
        len(books)
    )

    # 2. Clean and enrich.
    df = clean_data(books)

    print(
        "Cleaned rows:",
        len(df)
    )

    print(
        "Categories:",
        df["category"].nunique()
    )

    print()
    print("Final data types:")

    print(
        df[
            [
                "price_gbp",
                "rating",
                "in_stock",
                "price_inr",
            ]
        ].dtypes
    )

    # 3. Create database.
    create_database(df)

    # 4. Execute SQL queries.
    run_sql_queries()

    # 5. Validate using pandas.
    validate_with_pandas()

    print()
    print("=" * 60)
    print("DATA PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()