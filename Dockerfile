# 베이스 이미지
FROM python:3.9.23-bookworm

# 작업 디렉토리
WORKDIR /home/crawler-py-batch

# 필수 패키지 설치
RUN apt update && apt install -y \
    wget curl unzip gnupg2 \
    fonts-liberation libappindicator3-1 libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libcups2 \
    libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 \
    libnss3 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 xdg-utils


# # Chrome/ChromeDriver를 같은 버전으로 고정해 브라우저-드라이버 불일치 방지
ARG CHROME_VERSION=138.0.7204.94

# Chrome for Testing 브라우저 설치
RUN wget -q -O /tmp/chrome-linux64.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip" && \
    unzip /tmp/chrome-linux64.zip -d /opt && \
    ln -s /opt/chrome-linux64/chrome /usr/local/bin/google-chrome && \
    rm /tmp/chrome-linux64.zip

# 같은 버전의 ChromeDriver 설치
RUN wget -q -O /tmp/chromedriver-linux64.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver-linux64.zip -d /opt && \
    ln -s /opt/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /opt/chromedriver-linux64/chromedriver && \
    rm /tmp/chromedriver-linux64.zip

# 코드 가져오기
WORKDIR /home
RUN rm -rf crawler-py-batch && \
    git clone https://github.com/gam-data-project/crawler-py-batch.git

# requirements 설치
WORKDIR /home/crawler-py-batch
RUN pip install --no-cache-dir -r requirements.txt

# 전체 코드 복사
COPY . .

# 실행 명령 (원할 경우)
#CMD ["python", "crawler.py"]
