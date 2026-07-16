import requests
import os
from dotenv import load_dotenv


load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")  # 예: http://localhost:8080
SALES_ENDPOINT = f"{API_BASE_URL}/salesData"
DELIVERY_ENDPOINT = f"{API_BASE_URL}/deliveryFeeData"


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
def send_to_sales(root_idx, parsed, date, shipping):

    if not API_BASE_URL:
        print("❌ API_BASE_URL이 설정되지 않았습니다 (.env 확인).")
        return 0

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
            "shipping_included": shipping.get("shipping_included", False),
            "order_date": str(date)
        })
    
    # 디버그: 타입/값 확인
    print("\n[DEBUG] sales_payload:", type(sales_payload))
    for i, row in enumerate(sales_payload):
        print(f" └─[{i}] {row}")

    # 리스트 각 요소를 개별 전송
    ok = 0
    for row in sales_payload:
        try:
            resp = requests.post(SALES_ENDPOINT, json=row, timeout=10)
            print(f"📤 [sales] {resp.status_code} {resp.text[:200]}")
            if 200 <= resp.status_code < 300:
                ok += 1
        except Exception as e:
            print("❌ [sales] 전송 실패:", e)
    return ok  # 성공 건수 반환
    
    

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
    unit_price(int)
    order_date(str)
    """
def send_to_delivery(root_idx, date, shipping):
    
    if not API_BASE_URL:
        print("❌ API_BASE_URL이 설정되지 않았습니다 (.env 확인).")
        return False

    # 2. delivery_fee 테이블 전송

    total_delivery_fee = (
        shipping.get("shipping_fee") if shipping.get("shipping_included", False) else 4000
    )
    shipping_count = 1
    unit_price = int(total_delivery_fee / shipping_count) if shipping_count else 0


    delivery_payload = {
        "order_number": root_idx,
        "platform": "nongra",
        "shipping_included": shipping.get("shipping_included", False),
        #배송비가 따로 청구 되면 수집한 배송비 데이터를 넣지만 
        #배송비가 제품 금액에 포함되면 배송비 테이터를 따로 책정해서 넣어준다.
        "total_delivery_fee": total_delivery_fee,
        #모든 제품은 배송비가 반드시 한 개 이상 있다.
        "shipping_count": shipping_count,
        "unit_price": unit_price,
        "order_date": str(date)
    }
    # 디버그: 타입/값 확인
    print("\n[DEBUG] delivery_payload:", type(delivery_payload))
    for k, v in delivery_payload.items():
        print(f" {k}: {v} ({type(v)})")

    try:
        resp = requests.post(DELIVERY_ENDPOINT, json=delivery_payload, timeout=10)
        print(f"📤 [delivery] {resp.status_code} {resp.text[:200]}")
        return 200 <= resp.status_code < 300
    except Exception as e:
        print("❌ [delivery] 전송 실패:", e)
        return False        