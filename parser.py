from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By

def parse_price(text: str) -> int:
    """가격 문자열에서 숫자 추출"""
    cleaned = text.strip().replace(',', '').replace('원', '')
    return int(cleaned) if cleaned.isdigit() else 0


def parse_quantity(text: str) -> int:
    """텍스트에서 '(숫자개)' 패턴 찾아 수량 반환. 없으면 1"""
    match = re.search(r'\((\d+)개\)', text)
    return int(match.group(1)) if match else 1


def parse_product_name(name: str) -> str:
    """상품명에서 수량 부분 제거"""
    return re.sub(r'\(\d+개\)', '', name).strip()


def extract_order_items(driver) -> list[dict]:
    result = []

    #제품 정보 추출
    products_div = driver.find_element(By.XPATH, '//*[@id="f_order"]/div/div/div/div[1]/div[7]/div[1]/div[1]')

    with open(f"debug_xpath.html", "w", encoding="utf-8") as f:
        f.write(products_div.get_attribute("outerHTML"))
    print("💾 debug_xpath.html 저장 완료")

    # products_div 내부 요소 파싱
    items = products_div.find_elements(By.CLASS_NAME, "clfix")

    for item in items:
        try:
            name_elem = item.find_element(By.CLASS_NAME, "fl")
            price_elem = item.find_element(By.CLASS_NAME, "fr")

            full_text = name_elem.text.strip()
            price_text = price_elem.text.strip()

            quantity = parse_quantity(full_text)
            product_total = parse_price(price_text)
            unit_price = int(product_total / quantity) if quantity else 0
            product_name = parse_product_name(full_text)

            result.append({
                "product_name_raw": product_name,
                "quantity": quantity,
                "product_total": product_total,
                "unit_price": unit_price,
                #"is_shipping_included": False  # 배송비는 이 구조에선 없음
            })
        except Exception as e:
            print(f"⚠️ 파싱 실패: {e}")
            continue

    return result


"""
    입금완료일을 추출하여 딕셔너리로 반환
    - 입금완료 상태가 아닐 경우 {'order_date': None}
    - 입금완료일이 존재할 경우 {'order_date': 'YYYY-MM-DD HH:MM:SS'}
    """
def extract_deposit_date(driver) -> dict:
    
    result = {'order_date': None}

    try:
        rows = driver.find_elements(By.XPATH, '//*[@id="_ACCOUNT_LOG_"]/tbody/tr')
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) >= 2:
                status_text = cells[0].text.strip()
                if "입금완료" in status_text:
                    date_text = cells[1].text.strip()
                    match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', date_text)
                    if match:
                        result['order_date'] = match.group(0)
                        break
    except Exception as e:
        print("❌ 입금일자 추출 오류:", e)

    return result


