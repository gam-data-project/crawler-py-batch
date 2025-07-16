from bs4 import BeautifulSoup
import re


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


def extract_order_items(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    result = []

    divs = soup.select('div.lf.clfix')
    if len(divs) < 3:
        return result  # 구조 예상과 다르면 빈 리스트 반환

    # 1번째: 상품 목록
    product_div = divs[0]
    product_items = product_div.select('div.clfix[style*="height: 40px"]')

    # 3번째: 결제 요약 (배송비 판단용)
    summary_div = divs[2]
    total_elem = summary_div.select_one('span.fr')
    delivery_fee = parse_price(total_elem.text) if total_elem else 0
    is_shipping_included = delivery_fee > 0

    for div in product_items:
        name_elem = div.select_one('span.fl')
        price_elem = div.select_one('span.fr')
        if not name_elem or not price_elem:
            continue

        full_text = name_elem.text.strip()
        product_total = parse_price(price_elem.text)
        quantity = parse_quantity(full_text)
        unit_price = int(product_total / quantity) if quantity else 0
        product_name_raw = parse_product_name(full_text)

        result.append({
            'product_name_raw': product_name_raw,
            'quantity': quantity,
            'product_total': product_total,
            'unit_price': unit_price,
            'is_shipping_included': is_shipping_included,
        })

    return result
