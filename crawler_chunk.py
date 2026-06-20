from selenium import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import os
import time
import logging
import argparse
from datetime import datetime, timedelta
from selenium.webdriver.chrome.options import Options
from parser import extract_order_items
from parser import extract_shipping_fee
from selenium.webdriver.support.ui import Select
from send_to_chunk import send_chunk
from send_to_chunk import notify_slack
from send_to_chunk import notify_batch_failure


# logger 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("crawler_chunk")


CANCEL_WORDS = {"주문취소", "주문완료"}


# 취소 주문 여부 확인 함수
"""
    주문 목록 페이지에서 취소 또는 완료 처리된 주문인지 확인한다.
    - '주문취소' 버튼 텍스트가 보이면 True
    - select 박스의 선택값이 '주문완료'면 True
    - 둘 다 없으면 False
    """
def is_canceled_order(driver, root_idx: str) -> bool:
    try:
        base_xpath = f'//*[@id="centerbody_scroll"]//div[@attr-idx="{root_idx}"]/../../..'
        # 1) 버튼/라벨(div)에서 '주문취소' 찾기
        try:
            cancel_divs = driver.find_elements(
                By.XPATH,
                base_xpath + '//div[contains(text(), "주문취소")]'
            )
            if len(cancel_divs) > 0:
                logger.info("취소 주문 라벨 확인: root_idx=%s", root_idx)
                return True
        except Exception:
            pass
        #2) select 박스의 선택된 옵션이 '주문완료'인지 확인 -> 미입금 주문
        try:
            sel = driver.find_element(
                By.XPATH,
                base_xpath + '//select[contains(@class,"buys")]'
            )
            selected_text = Select(sel).first_selected_option.text.strip()
            if selected_text == "주문완료":
                logger.info("주문 완료(미입금) 상태 확인: root_idx=%s", root_idx)
                return True
        except Exception:
            pass

        return False

    except Exception as e:
        logger.exception("주문 상태 확인 중 오류: root_idx=%s, error=%s", root_idx, e)
        return False


"""
주문 단위 데이터 생성 함수
상품 목록과 배송비 정보를 주문 단위 chunk 전송 데이터로 변환한다."""
def build_order_data(root_idx, parsed, date, shipping):

    sales_items = []

    # 주문 내역에 판매된 상품 정보
    for idx, item in enumerate(parsed, start=1):
        sales_items.append({
            "item_seq": idx,
            "product_name_raw": item.get("product_name_raw"),
            "quantity": item.get("quantity"),
            "product_total": item.get("product_total"),
            "unit_price": item.get("unit_price"),
            "shipping_included": shipping.get("shipping_included", False),
        })
    # 주문 정보
    total_delivery_fee = (
        shipping.get("shipping_fee") if shipping.get("shipping_included", False) else 4000
    )

    order_data = {
        "order_message_id": f"nongra-{root_idx}",
        "order_number": root_idx,
        "platform": "nongra",
        "order_date": str(date),
        "sales_items": sales_items,
        "delivery": {
            "shipping_included": shipping.get("shipping_included", False),
            "total_delivery_fee": total_delivery_fee,
            "shipping_count": 1,
            "unit_price": total_delivery_fee
        }
    }

    logger.info(
        "주문 데이터 생성 완료: root_idx=%s, sales_items=%d",
        root_idx,
        len(sales_items)
    )
    return order_data


# 실행 인자 파싱
def parse_args():
    parser = argparse.ArgumentParser(description="날짜 범위 주문 데이터를 chunk 단위로 수집/전송한다.")
    parser.add_argument("--start-date", required=True, help="수집 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="수집 종료일 (YYYY-MM-DD)")
    return parser.parse_args()


"""
데이터 수집
"""
def get_data(driver, start_date, end_date):
    # 전체 주문 데이터를 누적할 리스트
    all_orders = []

    current_date = start_date

    while current_date <= end_date:
        s_date = e_date = current_date.strftime("%Y-%m-%d")
        logger.info("주문 내역 수집 시작: %s", s_date)

        # 주문 목록 페이지 접속
        list_url = (
            f"https://www.farmer4989.com/html/mypage_buy_log.php"
            f"?is_first=N&s_date={s_date}&e_date={e_date}"
        )
        driver.get(list_url)
        time.sleep(2)

        # 주문 ID 추출
        order_elements = driver.find_elements(By.CSS_SELECTOR, "div.btn_all.do_show.order_view.ir")
        order_ids = []

        for elem in order_elements:
            root_idx = elem.get_attribute("attr-idx")

            if is_canceled_order(driver, root_idx):
                logger.info("취소 주문 제외: root_idx=%s", root_idx)
                continue

            order_ids.append(root_idx)

        logger.info("주문 수집 완료: date=%s, count=%d", s_date, len(order_ids))

        for root_idx in order_ids:
            try:
                detail_url = f"https://www.farmer4989.com/html/order_show.php?root_idx={root_idx}"
                driver.get(detail_url)
                logger.info("상세 주문 페이지 진입: %s", detail_url)
                time.sleep(2)

                # 상품 정보 추출
                parsed = extract_order_items(driver)
                # 날짜
                date = s_date
                # 배송비 정보 추출
                shipping = extract_shipping_fee(driver)

                # 주문 내역 데이터 생성
                if not parsed or not date:
                    logger.warning("파싱 실패 또는 데이터 없음: root_idx=%s", root_idx)
                else:
                    order_data = build_order_data(root_idx, parsed, date, shipping)
                    all_orders.append(order_data)
                    logger.info("전체 주문 리스트 적재 완료: cumulative_count=%d", len(all_orders))
            except Exception as e:
                logger.exception("주문 상세 크롤링 실패: root_idx=%s, error=%s", root_idx, e)
                notify_batch_failure(
                    stage="crawling_failed",
                    root_idx=root_idx,
                )
                raise

        current_date += timedelta(days=1)

    logger.info("데이터 수집 완료: total_orders=%d", len(all_orders))
    return all_orders


# 성공 요약 슬랙 알림 사용 여부를 제어
def should_notify_success_slack():
    """환경변수 기준으로 성공 요약 슬랙 알림 사용 여부를 반환한다."""
    logger.info("should_notify_success_slack started")

    value = os.getenv("SLACK_NOTIFY_SUCCESS", "false").strip().lower()
    enabled = value in {"1", "true", "y", "yes", "on"}

    logger.info("should_notify_success_slack completed: enabled=%s", enabled)
    return enabled


# 배치 전체 성공 시 슬랙 요약 알림을 1회 전송
def notify_batch_success_summary(total_orders, total_chunks, success_chunks):
    """전체 chunk 전송이 모두 성공했을 때 슬랙 요약 알림을 1회 전송한다."""
    logger.info(
        "notify_batch_success_summary started: total_orders=%d, total_chunks=%d, success_chunks=%d",
        total_orders,
        total_chunks,
        success_chunks
    )

    if not should_notify_success_slack():
        logger.info("notify_batch_success_summary skipped: success slack disabled")
        return

    message = (
        f"[SUCCEED] "
        f"total_orders={total_orders}, "
        f"total_chunks={total_chunks}, "
        f"success_chunks={success_chunks}"
    )

    notify_slack(message)
    logger.info("notify_batch_success_summary completed")




"""
chunk 생성 및 전송
"""
def send_data(all_orders):
    if not all_orders:
        logger.warning("전송할 주문 데이터가 없습니다.")
        return {
            "total_orders": 0,
            "total_chunks": 0,
            "success_chunks": 0,
            "failed_chunks": 0,
            "stopped_on_chunk_seq": None,
            "last_result": None,
        }

    # 수집 완료 후 chunk 생성
    chunk_size = int(os.getenv("CHUNK_SIZE", "50"))
    if chunk_size <= 0:
        raise ValueError("CHUNK_SIZE must be greater than 0")

    total_chunks = (len(all_orders) + chunk_size - 1) // chunk_size
    success_chunks = 0
    failed_chunks = 0

    # chunk 전송
    for idx, start_idx in enumerate(range(0, len(all_orders), chunk_size), start=1):
        chunk = all_orders[start_idx:start_idx + chunk_size]

        payload = {
            "chunk_id": f"chunk-{idx}",
            "chunk_seq": idx,
            "total_chunks": total_chunks,
            "orders": chunk,
        }

        logger.info("chunk 전송 시작: chunk_seq=%d, order_count=%d", idx, len(chunk))
        result = send_chunk(payload)
        logger.info("chunk 전송 결과: chunk_seq=%d, result=%s", idx, result)

        if result.get("ok"):
            success_chunks += 1
            continue

        failed_chunks += 1

        logger.error(
            "chunk 전송 실패로 배치를 중단합니다: chunk_seq=%d, result=%s",
            idx,
            result
        )

        return {
            "total_orders": len(all_orders),
            "total_chunks": total_chunks,
            "success_chunks": success_chunks,
            "failed_chunks": failed_chunks,
            "stopped_on_chunk_seq": idx,
            "last_result": result,
        }

    return {
        "total_orders": len(all_orders),
        "total_chunks": total_chunks,
        "success_chunks": success_chunks,
        "failed_chunks": failed_chunks,
        "stopped_on_chunk_seq": None,
        "last_result": None,
    }


"""
페이지 접속 및 로그인
"""
def main():
    args = parse_args()

    # .env 로드
    load_dotenv()

    # 환경변수 확인
    url = os.getenv("NONGRA_URL")
    login_id = os.getenv("NONGRA_LOGIN_ID")
    login_pw = os.getenv("NONGRA_LOGIN_PW")

    logger.info("환경변수 로드 완료: url=%s, login_id=%s", url, login_id)

    # 날짜 범위
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    if start_date > end_date:
        raise ValueError("start_date must be less than or equal to end_date")

    # headless Chrome
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--user-data-dir=/tmp/unique-profile')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    logger.info("Chrome driver 실행 완료")

    try:
        # 페이지 접속
        driver.get(url)
        logger.info("초기 페이지 접속 완료: %s", url)

        # 로그인 여부 판단
        if "로그인" in driver.page_source and "login_id" in driver.page_source:
            logger.info("로그인 필요 - 로그인 진행")

            input_id = driver.find_element(By.ID, "login_id")
            input_id.clear()
            input_id.send_keys(login_id)

            input_pw = driver.find_element(By.ID, "login_pw")
            input_pw.clear()
            input_pw.send_keys(login_pw)

            login_btn = driver.find_element(By.XPATH, "/html/body/form/div/div[2]/div/div[2]")
            login_btn.click()
            time.sleep(2)

            if "로그아웃" in driver.page_source or "마이페이지" in driver.page_source:
                logger.info("로그인 성공")
            else:
                raise Exception("로그인 실패 또는 예상과 다른 페이지")
        else:
            logger.info("이미 로그인된 세션입니다. 로그인 생략.")

        time.sleep(2)

        all_orders = get_data(driver, start_date, end_date)
        summary = send_data(all_orders)

        logger.info("배치 전송 요약: %s", summary)

        if summary["total_chunks"] > 0 and summary["failed_chunks"] == 0:
            notify_batch_success_summary(
                total_orders=summary["total_orders"],
                total_chunks=summary["total_chunks"],
                success_chunks=summary["success_chunks"]
            )

    except Exception as e:
        logger.exception("크롤러 실행 중 치명적 오류 발생: error=%s", e)
        raise

    finally:
        time.sleep(5)
        driver.quit()
        logger.info("크롤러 종료")



if __name__ == "__main__":
    main()