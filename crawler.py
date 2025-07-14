from selenium import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import os
import time
from datetime import datetime, timedelta
from selenium.webdriver.chrome.options import Options

#headless Chrome 
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--user-data-dir=/tmp/unique-profile') 

driver = webdriver.Chrome(options=options)

# .env 파일 로드
#load_dotenv()
#driver.get(os.getenv("NONGRA_URL"))
#login_id = os.getenv("NONGRA_LOGIN_ID")
#login_pw = os.getenv("NONGRA_LOGIN_PW")

# 로그인 정보 로드
url = os.environ["NONGRA_URL"]
login_id = os.environ["NONGRA_LOGIN_ID"]
login_pw = os.environ["NONGRA_LOGIN_PW"]
driver.get(url)
#driver = webdriver.Chrome()
#nongra_url = os.getenv("NONGRA_URL")
#driver.get(nongra_url)

# ID 입력
input_id = driver.find_element(By.ID, "login_id")
input_id.clear()
input_id.send_keys(login_id)

# PW 입력
input_pw = driver.find_element(By.ID, "login_pw")
input_pw.clear()
input_pw.send_keys(login_pw)

# 로그인 버튼 클릭
login_btn = driver.find_element(By.XPATH,"/html/body/form/div/div[2]/div/div[2]")
login_btn.click()


#---------------------------------------------
# 날짜별로 주문 리스트 페이지 방문
#---------------------------------------------

time.sleep(2)  # 로그인 대기

# 날짜 반복: 2022-01-04부터 오늘까지
start_date = datetime(2022, 1, 4).date()
end_date = datetime.today().date()

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
    order_ids = [elem.get_attribute("attr-idx") for elem in order_elements]
    print(f"🧾 주문 수: {len(order_ids)}")

    for root_idx in order_ids:
        detail_url = f"https://www.farmer4989.com/html/order_show.php?root_idx={root_idx}"
        driver.get(detail_url)
        print(f"🔗 상세 주문 URL: {detail_url}")
        time.sleep(2)
        # TODO: 여기에 상세 정보 수집 로직 추가

    start_date += timedelta(days=1)



time.sleep(5)
driver.quit()