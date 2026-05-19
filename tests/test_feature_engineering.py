import pytest
import pandas as pd
from etl.feature_engineering import engineer_features


def _base_orders():
    return pd.DataFrame({
        "order_id": ["o1", "o2"],
        "customer_id": ["c1", "c2"],
        "order_status": ["delivered", "delivered"],
        "order_purchase_timestamp": pd.to_datetime(["2018-01-01", "2018-02-01"]),
        "order_approved_at": pd.to_datetime(["2018-01-01 02:00", "2018-02-01 01:00"]),
        "order_delivered_carrier_date": pd.to_datetime(["2018-01-05", "2018-02-06"]),
        "order_delivered_customer_date": pd.to_datetime(["2018-01-10", "2018-02-20"]),
        "order_estimated_delivery_date": pd.to_datetime(["2018-01-08", "2018-02-15"]),
    })

def _base_items():
    return pd.DataFrame({
        "order_id": ["o1", "o2"],
        "order_item_id": [1, 1],
        "product_id": ["p1","p2"],
        "seller_id": ["s1","s2"],
        "price": [100.0, 200.0],
        "freight_value": [10.0, 20.0],
    })

def _base_payments():
    return pd.DataFrame({
        "order_id": ["o1","o2"],
        "payment_sequential": [1, 1],
        "payment_type": ["credit_card","boleto"],
        "payment_installments": [1, 1],
        "payment_value": [110.0, 220.0],
    })

def _base_reviews():
    return pd.DataFrame({
        "order_id": ["o1","o2"],
        "review_score": [5, 3],
        "review_creation_date": pd.to_datetime(["2018-01-12","2018-02-22"]),
    })


def test_delivery_time_days():
    df = engineer_features(_base_orders(), _base_items(), _base_payments(), _base_reviews())
    # o1: Jan 10 - Jan 1 = 9 days
    assert abs(df.loc[df.order_id=="o1", "delivery_time_days"].values[0] - 9.0) < 0.1

def test_delay_days_positive_means_late():
    df = engineer_features(_base_orders(), _base_items(), _base_payments(), _base_reviews())
    # o1: delivered Jan 10, estimated Jan 8 → delay = +2 (late)
    assert df.loc[df.order_id=="o1", "delay_days"].values[0] > 0
    assert df.loc[df.order_id=="o1", "is_late"].values[0] == 1

def test_total_order_value():
    df = engineer_features(_base_orders(), _base_items(), _base_payments(), _base_reviews())
    # o1: price=100 + freight=10 = 110
    assert df.loc[df.order_id=="o1", "total_order_value"].values[0] == 110.0

def test_review_score_merged():
    df = engineer_features(_base_orders(), _base_items(), _base_payments(), _base_reviews())
    assert df.loc[df.order_id=="o1", "review_score"].values[0] == 5
