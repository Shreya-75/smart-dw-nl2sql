-- ============================================================
-- Olist Smart Data Warehouse — Star Schema DDL
-- Run against: olist_dw database
-- ============================================================

USE olist_dw;

-- ── Dimension: Time ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_time (
    date_key     INT PRIMARY KEY COMMENT 'YYYYMMDD format',
    full_date    DATE NOT NULL,
    day          TINYINT UNSIGNED NOT NULL,
    month        TINYINT UNSIGNED NOT NULL,
    year         SMALLINT UNSIGNED NOT NULL,
    quarter      TINYINT UNSIGNED NOT NULL,
    day_of_week  VARCHAR(10) NOT NULL,
    is_weekend   TINYINT(1) NOT NULL DEFAULT 0,
    week_of_year TINYINT UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_time_year_month ON dim_time(year, month);

-- ── Dimension: Customers ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id            VARCHAR(36) PRIMARY KEY,
    customer_unique_id     VARCHAR(36),
    customer_city          VARCHAR(100),
    customer_state         CHAR(2),
    customer_zip_code_prefix VARCHAR(10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_cust_state      ON dim_customers(customer_state);
CREATE INDEX idx_cust_state_city ON dim_customers(customer_state, customer_city);

-- ── Dimension: Products ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_products (
    product_id                   VARCHAR(36) PRIMARY KEY,
    product_category_name        VARCHAR(100),
    product_category_name_english VARCHAR(100),
    product_name_length          INT,
    product_description_length   INT,
    product_weight_g             DECIMAL(8,2),
    product_length_cm            DECIMAL(6,2),
    product_height_cm            DECIMAL(6,2),
    product_width_cm             DECIMAL(6,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_prod_cat_english ON dim_products(product_category_name_english(50));

-- ── Dimension: Sellers ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_sellers (
    seller_id              VARCHAR(36) PRIMARY KEY,
    seller_city            VARCHAR(100),
    seller_state           CHAR(2),
    seller_zip_code_prefix VARCHAR(10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_seller_state ON dim_sellers(seller_state);

-- ── Fact Table: Sales ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_sales (
    fact_id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id             VARCHAR(36) NOT NULL,
    order_item_id        INT,
    customer_id          VARCHAR(36),
    product_id           VARCHAR(36),
    seller_id            VARCHAR(36),
    date_key             INT,
    order_status         VARCHAR(20),
    payment_type         VARCHAR(20),
    payment_installments INT,
    payment_value        DECIMAL(10,2),
    price                DECIMAL(10,2),
    freight_value        DECIMAL(10,2),
    total_order_value    DECIMAL(10,2),
    review_score         TINYINT,
    delivery_time_days   DECIMAL(6,2),
    delay_days           DECIMAL(6,2),
    is_late              TINYINT(1) DEFAULT 0,
    approval_time_hours  DECIMAL(8,2),

    CONSTRAINT fk_fact_customer FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    CONSTRAINT fk_fact_product  FOREIGN KEY (product_id)  REFERENCES dim_products(product_id),
    CONSTRAINT fk_fact_seller   FOREIGN KEY (seller_id)   REFERENCES dim_sellers(seller_id),
    CONSTRAINT fk_fact_time     FOREIGN KEY (date_key)    REFERENCES dim_time(date_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_fact_date     ON fact_sales(date_key);
CREATE INDEX idx_fact_customer ON fact_sales(customer_id);
CREATE INDEX idx_fact_product  ON fact_sales(product_id);
CREATE INDEX idx_fact_seller   ON fact_sales(seller_id);
CREATE INDEX idx_fact_status   ON fact_sales(order_status);
CREATE INDEX idx_fact_date_cust ON fact_sales(date_key, customer_id);
