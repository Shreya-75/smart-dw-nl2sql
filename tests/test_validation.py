import pytest
from agents.validation_agent import validate_sql


def test_valid_select():
    sql = "SELECT customer_city, SUM(payment_value) FROM fact_sales JOIN dim_customers ON fact_sales.customer_id = dim_customers.customer_id GROUP BY customer_city"
    result = validate_sql(sql)
    assert result.is_valid

def test_blocks_delete():
    result = validate_sql("DELETE FROM fact_sales WHERE 1=1")
    assert not result.is_valid
    assert any("DELETE" in e for e in result.errors)

def test_blocks_drop():
    result = validate_sql("DROP TABLE fact_sales")
    assert not result.is_valid

def test_blocks_update():
    result = validate_sql("UPDATE fact_sales SET price = 0")
    assert not result.is_valid

def test_blocks_insert():
    result = validate_sql("INSERT INTO fact_sales VALUES (1,2,3)")
    assert not result.is_valid

def test_must_start_with_select():
    result = validate_sql("SHOW TABLES")
    assert not result.is_valid

def test_unknown_table_flagged():
    result = validate_sql("SELECT * FROM nonexistent_table")
    assert not result.is_valid

def test_warns_on_high_join_count():
    sql = ("SELECT * FROM fact_sales fs "
           "JOIN dim_customers dc ON fs.customer_id = dc.customer_id "
           "JOIN dim_products dp ON fs.product_id = dp.product_id "
           "JOIN dim_sellers ds ON fs.seller_id = ds.seller_id "
           "JOIN dim_time dt ON fs.date_key = dt.date_key "
           "JOIN dim_time dt2 ON dt2.date_key = 20180101 "
           "JOIN dim_customers dc2 ON dc2.customer_id = fs.customer_id")
    result = validate_sql(sql)
    assert any("JOIN" in w for w in result.warnings)
