-- ============================================================
-- 20 Sample Analytical Queries for the Olist DW
-- Use these to test the warehouse and as NL2SQL benchmarks
-- ============================================================

-- 1. Total revenue by year
SELECT dt.year, SUM(fs.payment_value) AS total_revenue
FROM fact_sales fs
JOIN dim_time dt ON fs.date_key = dt.date_key
WHERE fs.order_status = 'delivered'
GROUP BY dt.year ORDER BY dt.year;

-- 2. Monthly revenue trend
SELECT dt.year, dt.month, SUM(fs.payment_value) AS revenue,
       COUNT(DISTINCT fs.order_id) AS orders
FROM fact_sales fs
JOIN dim_time dt ON fs.date_key = dt.date_key
GROUP BY dt.year, dt.month ORDER BY dt.year, dt.month;

-- 3. Top 10 cities by revenue
SELECT dc.customer_city AS city,
       SUM(fs.payment_value) AS revenue,
       COUNT(DISTINCT fs.order_id) AS order_count
FROM fact_sales fs
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
GROUP BY dc.customer_city
ORDER BY revenue DESC LIMIT 10;

-- 4. Revenue by state
SELECT dc.customer_state AS state,
       SUM(fs.payment_value) AS revenue
FROM fact_sales fs
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
GROUP BY dc.customer_state ORDER BY revenue DESC;

-- 5. Top 10 product categories by revenue
SELECT dp.product_category_name_english AS category,
       SUM(fs.payment_value) AS revenue,
       COUNT(DISTINCT fs.order_id) AS orders
FROM fact_sales fs
JOIN dim_products dp ON fs.product_id = dp.product_id
GROUP BY dp.product_category_name_english
ORDER BY revenue DESC LIMIT 10;

-- 6. Average review score by product category
SELECT dp.product_category_name_english AS category,
       AVG(fs.review_score) AS avg_score,
       COUNT(*) AS review_count
FROM fact_sales fs
JOIN dim_products dp ON fs.product_id = dp.product_id
WHERE fs.review_score IS NOT NULL
GROUP BY dp.product_category_name_english
ORDER BY avg_score DESC LIMIT 15;

-- 7. Payment type distribution
SELECT payment_type,
       COUNT(DISTINCT order_id) AS orders,
       SUM(payment_value) AS total_value,
       ROUND(SUM(payment_value) / SUM(SUM(payment_value)) OVER () * 100, 2) AS pct
FROM fact_sales
GROUP BY payment_type ORDER BY total_value DESC;

-- 8. Late order rate by state
SELECT dc.customer_state AS state,
       COUNT(*) AS total_orders,
       SUM(fs.is_late) AS late_orders,
       ROUND(SUM(fs.is_late) / COUNT(*) * 100, 2) AS late_pct
FROM fact_sales fs
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
WHERE fs.order_status = 'delivered'
GROUP BY dc.customer_state
ORDER BY late_pct DESC;

-- 9. Average delivery time by state
SELECT dc.customer_state AS state,
       AVG(fs.delivery_time_days) AS avg_delivery_days,
       MIN(fs.delivery_time_days) AS min_days,
       MAX(fs.delivery_time_days) AS max_days
FROM fact_sales fs
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
WHERE fs.delivery_time_days IS NOT NULL AND fs.order_status = 'delivered'
GROUP BY dc.customer_state ORDER BY avg_delivery_days;

-- 10. Top 10 sellers by revenue
SELECT ds.seller_id, ds.seller_city, ds.seller_state,
       SUM(fs.price) AS total_sales,
       COUNT(DISTINCT fs.order_id) AS orders
FROM fact_sales fs
JOIN dim_sellers ds ON fs.seller_id = ds.seller_id
GROUP BY ds.seller_id, ds.seller_city, ds.seller_state
ORDER BY total_sales DESC LIMIT 10;

-- 11. Order status breakdown
SELECT order_status,
       COUNT(DISTINCT order_id) AS orders,
       ROUND(COUNT(DISTINCT order_id) / SUM(COUNT(DISTINCT order_id)) OVER() * 100, 2) AS pct
FROM fact_sales
GROUP BY order_status ORDER BY orders DESC;

-- 12. Revenue in 2018 by quarter
SELECT dt.quarter, SUM(fs.payment_value) AS revenue
FROM fact_sales fs
JOIN dim_time dt ON fs.date_key = dt.date_key
WHERE dt.year = 2018
GROUP BY dt.quarter ORDER BY dt.quarter;

-- 13. Average installments by payment type
SELECT payment_type,
       AVG(payment_installments) AS avg_installments,
       MAX(payment_installments) AS max_installments
FROM fact_sales
GROUP BY payment_type ORDER BY avg_installments DESC;

-- 14. Products with highest freight cost
SELECT dp.product_category_name_english AS category,
       AVG(fs.freight_value) AS avg_freight,
       AVG(fs.price) AS avg_price
FROM fact_sales fs
JOIN dim_products dp ON fs.product_id = dp.product_id
GROUP BY dp.product_category_name_english
ORDER BY avg_freight DESC LIMIT 10;

-- 15. Weekend vs weekday order patterns
SELECT dt.is_weekend,
       COUNT(DISTINCT fs.order_id) AS orders,
       AVG(fs.payment_value) AS avg_order_value
FROM fact_sales fs
JOIN dim_time dt ON fs.date_key = dt.date_key
GROUP BY dt.is_weekend;

-- 16. Repeat customers (unique_id ordered more than once)
SELECT dc.customer_unique_id,
       COUNT(DISTINCT fs.order_id) AS order_count,
       SUM(fs.payment_value) AS lifetime_value
FROM fact_sales fs
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
GROUP BY dc.customer_unique_id
HAVING order_count > 1
ORDER BY order_count DESC LIMIT 20;

-- 17. Review score distribution
SELECT review_score, COUNT(*) AS count
FROM fact_sales
WHERE review_score IS NOT NULL
GROUP BY review_score ORDER BY review_score;

-- 18. Monthly order growth rate
SELECT year, month, orders,
       LAG(orders) OVER (ORDER BY year, month) AS prev_orders,
       ROUND((orders - LAG(orders) OVER (ORDER BY year, month)) /
              LAG(orders) OVER (ORDER BY year, month) * 100, 2) AS growth_pct
FROM (
  SELECT dt.year, dt.month, COUNT(DISTINCT fs.order_id) AS orders
  FROM fact_sales fs
  JOIN dim_time dt ON fs.date_key = dt.date_key
  GROUP BY dt.year, dt.month
) base ORDER BY year, month;

-- 19. Seller performance by state
SELECT ds.seller_state AS state,
       COUNT(DISTINCT ds.seller_id) AS sellers,
       SUM(fs.payment_value) AS total_revenue,
       AVG(fs.review_score) AS avg_rating
FROM fact_sales fs
JOIN dim_sellers ds ON fs.seller_id = ds.seller_id
GROUP BY ds.seller_state ORDER BY total_revenue DESC;

-- 20. Correlation: delivery delay vs review score
SELECT
  CASE WHEN fs.delay_days <= 0 THEN 'On Time / Early'
       WHEN fs.delay_days <= 7 THEN '1–7 days late'
       WHEN fs.delay_days <= 30 THEN '8–30 days late'
       ELSE 'Over 30 days late' END AS delay_bucket,
  COUNT(*) AS orders,
  AVG(fs.review_score) AS avg_review_score
FROM fact_sales fs
WHERE fs.delay_days IS NOT NULL AND fs.review_score IS NOT NULL
  AND fs.order_status = 'delivered'
GROUP BY delay_bucket ORDER BY avg_review_score DESC;
