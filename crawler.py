from selenium import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import os
import time

# .env 파일 로드
load_dotenv()

# 로그인 정보 로드
login_id = os.getenv("NONGRA_LOGIN_ID")
login_pw = os.getenv("NONGRA_LOGIN_PW")

print("ID:", login_id)
print("PW:", login_pw)

driver = webdriver.Chrome()
nongra_url = os.getenv("NONGRA_URL")
driver.get(nongra_url)

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

time.sleep(5)
# driver.quit()