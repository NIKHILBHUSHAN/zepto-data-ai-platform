-- Query 1: SELECT + WHERE
SELECT title, rating, price_gbp
FROM books
WHERE rating >= 4;


-- Query 2: ORDER BY + LIMIT
SELECT title, price_gbp, price_inr
FROM books
ORDER BY price_gbp DESC
LIMIT 10;


-- Query 3: DISTINCT
SELECT DISTINCT category_name
FROM categories
ORDER BY category_name;


-- Query 4: BETWEEN
SELECT title, price_gbp, rating
FROM books
WHERE price_gbp BETWEEN 20 AND 40
ORDER BY price_gbp;


-- Query 5: IN
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
);


-- Query 6: JOIN
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
LIMIT 10;