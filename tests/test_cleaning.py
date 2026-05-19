import pytest
import pandas as pd
from etl.data_cleaning import clean_orders, clean_customers, clean_sellers


def test_clean_orders_dedup():
    df = pd.DataFrame({
        "order_id": ["a", "a", "b"],
        "customer_id": ["c1","c1","c2"],
        "order_status": ["delivered","delivered","shipped"],
        "order_purchase_timestamp": ["2018-01-01","2018-01-01","2018-02-01"],
        "order_approved_at": [None, None, None],
        "order_delivered_carrier_date": [None, None, None],
        "order_delivered_customer_date": [None, None, None],
        "order_estimated_delivery_date": [None, None, None],
    })
    cleaned = clean_orders(df)
    assert len(cleaned) == 2

def test_clean_orders_datetime_parsing():
    df = pd.DataFrame({
        "order_id": ["x"],
        "customer_id": ["c"],
        "order_status": ["delivered"],
        "order_purchase_timestamp": ["2018-03-15 10:30:00"],
        "order_approved_at": [None],
        "order_delivered_carrier_date": [None],
        "order_delivered_customer_date": [None],
        "order_estimated_delivery_date": [None],
    })
    cleaned = clean_orders(df)
    assert pd.api.types.is_datetime64_any_dtype(cleaned["order_purchase_timestamp"])

def test_clean_customers_normalizes_city():
    df = pd.DataFrame({
        "customer_id": ["1"],
        "customer_unique_id": ["u1"],
        "customer_zip_code_prefix": ["12345"],
        "customer_city": ["  São Paulo  "],
        "customer_state": ["sp"],
    })
    cleaned = clean_customers(df)
    assert cleaned.iloc[0]["customer_city"] == "são paulo"
    assert cleaned.iloc[0]["customer_state"] == "SP"

def test_clean_sellers_dedup():
    df = pd.DataFrame({
        "seller_id": ["s1","s1"],
        "seller_zip_code_prefix": ["11","11"],
        "seller_city": ["campinas","campinas"],
        "seller_state": ["SP","SP"],
    })
    cleaned = clean_sellers(df)
    assert len(cleaned) == 1
