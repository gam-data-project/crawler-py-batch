import requests
import os
from dotenv import load_dotenv


def send_to_sales(root_idx, parsed, date, shipping):
    """
    입력값
    root_idx: 주문 번호 (str)
    parsed: 상품 목록 (list[dict])
    date: 주문 날짜 (YYYY-MM-DD 문자열)
    shipping: 배송비 (int)

    출력값
    order_number(str)
    platform(str)
    product_name_raw(str)
    quantity(int)
    product_total(int)
    unit_price(int)
    is_shipping_included(bool)
    order_date(str)
    """

     # 1. sales_data 테이블 전송
    sales_payload = []
    for item in parsed:
        sales_payload.append({
            "order_number": root_idx,
            "platform": "nongra",
            "product_name_raw": item.get("product_name_raw"),
            "quantity": item.get("quantity"),
            "product_total": item.get("product_total"),
            "unit_price": item.get("unit_price"),
            "is_shipping_included": shipping.get("shipping_included", False),
            "order_date": str(date)
        })
    
    
    
def send_to_delivery(root_idx, date, shipping):
    """
    입력값
    root_idx: 주문 번호 (str)
    date: 주문 날짜 (YYYY-MM-DD 문자열)
    shipping: 배송비 (int)

    출력값
    order_number(str)
    platform(str)
    is_shipping_included(bool)
    total_delivery_fee(int)
    shipping_count(int)
    order_date(str)
    """

    # 2. delivery_fee 테이블 전송
    delivery_payload = {
        "order_number": root_idx,
        "platform": "nongra",
        "is_shipping_included": shipping.get("shipping_included", False),
        #배송비가 따로 청구 되면 수집한 배송비 데이터를 넣지만 
        #배송비가 제품 금액에 포함되면 배송비 테이터를 따로 책정해서 넣어준다.
        "total_delivery_fee": (
        shipping.get("shipping_fee") if shipping.get("shipping_included", False) else 4000
        ),
        #모든 제품은 배송비가 반드시 한 개 이상 있다.
        "shipping_count": 1,
        "order_date": str(date)

    }        