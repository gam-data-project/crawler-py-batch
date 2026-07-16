from selenium import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import os
import time
from datetime import datetime, timedelta
from selenium.webdriver.chrome.options import Options
from parser import extract_order_items
#from parser import extract_deposit_date
from parser import extract_shipping_fee
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from send_to import send_to_sales, send_to_delivery
from selenium.webdriver.support.ui import Select
"""
주문최소된 주문서 확인
-주문 목록 페이지 내에서 취소된 주문을 걸러냄
-주문 목록 페이지에서 해당 주문(root_idx)이 '주문취소' 상태인지 확인
"""

# def is_canceled_order(driver, root_idx: str) -> bool:

#     try:
#         xpath = f'//*[@id="centerbody_scroll"]//div[@attr-idx="{root_idx}"]/../../..//div[contains(text(), "주문취소")]'
#         cancel_elements = driver.find_elements(By.XPATH, xpath)
#         return len(cancel_elements) > 0
#     except Exception as e:
#         print(f"❌ 주문취소 확인 중 오류 (root_idx={root_idx}):", e)
#         return False

   

CANCEL_WORDS = {"주문취소", "주문완료"}

def is_canceled_order(driver, root_idx: str) -> bool:
    """
    - '주문취소' 버튼 텍스트가 보이면 False
    - select 박스의 선택값이 '주문완료'면 False
    - 둘 다 없으면 True
    """
    try:
        base_xpath = f'//*[@id="centerbody_scroll"]//div[@attr-idx="{root_idx}"]/../../..'

        # 1) 버튼/라벨(div)에서 '주문취소' 찾기
        try:
            cancel_divs = driver.find_elements(
                By.XPATH,
                base_xpath + '//div[contains(text(), "주문취소")]'
            )
            if len(cancel_divs) > 0:
                print(f"[{root_idx}] LABEL: 주문취소")
                return True
        except Exception:
            pass

        #2) select 박스의 선택된 옵션이 '주문완료'인지 확인
        try:
            sel = driver.find_element(
                By.XPATH,
                base_xpath + '//select[contains(@class,"buys")]'
            )
            selected_text = Select(sel).first_selected_option.text.strip()
            if selected_text == "주문완료":
                print(f"[{root_idx}] SELECT: 주문완료")
                return True
        except Exception:
            pass


        # 두 조건 다 없으면 True
        return False

    except Exception as e:
        print(f"❌ 주문 상태 확인 중 오류 (root_idx={root_idx}): {e}")
        return False





# .env 로드
load_dotenv()

# 환경 변수 확인
url = os.getenv("NONGRA_URL")
login_id = os.getenv("NONGRA_LOGIN_ID")
login_pw = os.getenv("NONGRA_LOGIN_PW")

print("✅ 로그인 ID:", login_id)
print("✅ URL:", url)


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


# github actions 환경변수 로그인 정보 로드
# url = os.environ["NONGRA_URL"]
# login_id = os.environ["NONGRA_LOGIN_ID"]
# login_pw = os.environ["NONGRA_LOGIN_PW"]
# driver.get(url)


# 페이지 접속
driver.get(url)

# 로그인 여부 판단
if "로그인" in driver.page_source and "login_id" in driver.page_source:
    print("🔐 로그인 시도 중...")

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
        print("✅ 로그인 성공!")
    else:
        raise Exception("❌ 로그인 실패 또는 예상과 다른 페이지입니다.")
else:
    print("✅ 이미 로그인된 세션입니다. 로그인 생략.")



"""날짜별로 주문 리스트 페이지 방문"""


time.sleep(2)  # 로그인 대기

# 날짜 반복: 2022-01-04부터 오늘까지
#start_date = datetime(2022, 1, 4).date()
#start_date = datetime(2025, 8, 31).date()
start_date = datetime(2026, 2, 26).date()
end_date = datetime(2026, 5, 6).date()
# end_date = datetime(2025, 9, 22).date()
#end_date = datetime.today().date()

while start_date <= end_date:
    s_date = e_date = start_date.strftime("%Y-%m-%d")
    print(f"📅 [{s_date}] 주문 내역 수집 시작")

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

    # 주문취소 여부 확인
        if is_canceled_order(driver, root_idx):
            print(f"🚫 주문취소됨 (root_idx={root_idx}) → 건너뜀")
            continue

        order_ids.append(root_idx)
    
    # order_ids = [elem.get_attribute("attr-idx") for elem in order_elements]
    print(f"🧾 주문 수: {len(order_ids)}")

    for root_idx in order_ids:
        detail_url = f"https://www.farmer4989.com/html/order_show.php?root_idx={root_idx}"
        driver.get(detail_url)
        print(f"🔗 상세 주문 URL: {detail_url}")
        time.sleep(2)
        # 상세 정보 수집 로직 추가

        parsed = extract_order_items(driver)

        #date = extract_deposit_date(driver)
        date = s_date

        shipping = extract_shipping_fee(driver)

        
        if not parsed or not date:
            print("⚠️  데이터 없음 또는 구조 다름 (건너뜀)")
        else:
            for p in parsed:
                print(p)
            
            print(date)

        print("🚚 배송비:", shipping)

        ok_cnt = send_to_sales(root_idx, parsed, date, shipping)
        print("sales 전송 성공 건수:", ok_cnt)
        ok = send_to_delivery(root_idx, date, shipping)
        print("delivery 전송 성공:", ok)


    start_date += timedelta(days=1)



time.sleep(5)
driver.quit()



