# crawler-py-batch 프로젝트 요약

이 문서는 Codex가 프로젝트 맥락을 빠르게 파악하기 위한 요약이다. 현재 프로젝트는 Selenium 기반 웹 크롤러로 농라 주문 데이터를 수집하고, 파싱한 주문/배송비 데이터를 외부 API로 전송하는 배치성 Python 애플리케이션이다.

## 한 줄 요약

`crawler.py`가 브라우저 자동화로 주문 목록과 주문 상세 페이지를 순회하고, `parser.py`가 상세 페이지에서 상품/배송비 정보를 추출하며, `send_to.py`가 추출 결과를 API 서버로 POST 전송한다.

## 주요 파일

| 파일 | 역할 |
| --- | --- |
| `crawler.py` | 메인 실행 파일. 로그인, 날짜 범위 순회, 주문 목록/상세 페이지 접근, 취소 주문 필터링, 파서/API 전송 호출을 담당한다. |
| `parser.py` | Selenium WebDriver로 열린 주문 상세 페이지에서 상품명, 수량, 금액, 단가, 배송비 정보를 추출한다. |
| `send_to.py` | 파싱된 데이터를 API 서버의 `/salesData`, `/deliveryFeeData` 엔드포인트로 전송한다. |
| `requirements.txt` | Python 의존성 목록. `selenium`, `python-dotenv`, `requests`, `beautifulsoup4` 사용. |
| `Dockerfile` | Python 3.9 기반 이미지, Chrome, ChromeDriver, Python 의존성 설치를 정의한다. |
| `README.md` | 간단한 프로젝트 설명만 포함한다. |

## 실행 흐름

1. `crawler.py`가 `.env`를 로드한다.
2. 환경변수에서 `NONGRA_URL`, `NONGRA_LOGIN_ID`, `NONGRA_LOGIN_PW`를 읽는다.
3. headless Chrome WebDriver를 생성한다.
4. `NONGRA_URL`에 접속해 로그인 페이지로 판단되면 로그인한다.
5. 지정된 날짜 범위를 하루씩 순회한다.
6. 날짜별 주문 목록 URL에 접속한다.
7. 주문 목록에서 `root_idx` 주문 ID를 수집한다.
8. `is_canceled_order()`로 주문 상태를 확인해 제외 대상 주문을 건너뛴다.
9. 주문 상세 URL에 접속한다.
10. `extract_order_items(driver)`로 상품 목록을 파싱한다.
11. `extract_shipping_fee(driver)`로 배송비 정보를 파싱한다.
12. `send_to_sales(root_idx, parsed, date, shipping)`로 상품별 매출 데이터를 전송한다.
13. `send_to_delivery(root_idx, date, shipping)`로 배송비 데이터를 전송한다.
14. 날짜 범위가 끝나면 WebDriver를 종료한다.

## 데이터 처리 개요

### 주문 상품 데이터

`parser.py`의 `extract_order_items()`는 주문 상세 페이지의 특정 XPath 영역에서 상품 행을 찾고, 각 행에서 다음 값을 만든다.

| 필드 | 설명 |
| --- | --- |
| `product_name_raw` | 수량 표기 제거 후의 원본 상품명 |
| `quantity` | 상품명 텍스트의 `(N개)` 패턴에서 추출한 수량. 패턴이 없으면 `1` |
| `product_total` | 상품 총액 |
| `unit_price` | `product_total / quantity`로 계산한 단가 |

### 배송비 데이터

`extract_shipping_fee()`는 주문 상세 페이지의 배송비 영역에서 `배송비` 라벨을 찾아 다음 형태의 딕셔너리를 반환한다.

```python
{
    "shipping_included": bool | None,
    "shipping_fee": int | None
}
```

현재 로직상 배송비 금액이 `0`보다 크면 `shipping_included`가 `True`로 설정된다.

### API 전송 데이터

`send_to.py`는 `.env`의 `API_BASE_URL`을 기준으로 엔드포인트를 구성한다.

| 함수 | 엔드포인트 | 설명 |
| --- | --- | --- |
| `send_to_sales()` | `{API_BASE_URL}/salesData` | 상품 행을 개별 JSON으로 POST 전송한다. |
| `send_to_delivery()` | `{API_BASE_URL}/deliveryFeeData` | 주문별 배송비 JSON을 POST 전송한다. |

## 필요한 환경변수

`.env` 또는 실행 환경에 다음 값이 필요하다.

| 변수 | 사용 위치 | 설명 |
| --- | --- | --- |
| `NONGRA_URL` | `crawler.py` | 크롤링 대상 로그인/진입 URL |
| `NONGRA_LOGIN_ID` | `crawler.py` | 농라 로그인 ID |
| `NONGRA_LOGIN_PW` | `crawler.py` | 농라 로그인 비밀번호 |
| `API_BASE_URL` | `send_to.py` | 수집 결과를 전송할 API 서버 base URL |

민감 정보가 포함되므로 `.env` 값은 문서나 로그에 그대로 남기지 않는 것이 좋다.

## Docker/실행 환경

`Dockerfile`은 다음 실행 환경을 준비한다.

- `python:3.9.23-bookworm` 기반 이미지 사용
- Chrome 실행에 필요한 Linux 패키지 설치
- Google Chrome stable 설치
- ChromeDriver `138.0.7204.94` 설치
- `requirements.txt` 기반 Python 패키지 설치
- 프로젝트 전체를 이미지에 `COPY . .`

현재 Dockerfile에는 실행 명령이 주석 처리되어 있다.

```dockerfile
#CMD ["python", "crawler.py"]
```

따라서 컨테이너 실행 시 직접 `python crawler.py`를 실행하거나, 별도 entrypoint/command 설정이 필요할 수 있다.

## 현재 코드에서 특히 봐야 할 지점

- `crawler.py`의 날짜 범위가 코드에 직접 박혀 있다.
  - 현재 시작일: `2025-08-31`
  - 현재 종료일: `2025-09-22`
- 주문 상태 필터링 함수 이름은 `is_canceled_order()`이지만, 내부에서는 `주문취소` 라벨 또는 `주문완료` 선택값을 찾으면 `True`를 반환한다.
- HTML 구조 의존도가 높다.
  - `parser.py`는 긴 XPath와 클래스명에 의존한다.
  - 대상 사이트 DOM 구조가 바뀌면 파싱 실패 가능성이 크다.
- API 전송은 각 상품 row마다 개별 POST 요청을 보낸다.
- 배송비 전송 로직은 배송비 정보가 없거나 포함 여부가 `None`일 때도 기본 배송비 `4000`을 사용할 수 있다.
- `crawler.py` 실행 중 로그인 ID와 URL을 콘솔에 출력한다.

## Codex 작업 시 주의사항

- 애플리케이션 비즈니스 로직 변경 요청이 없으면 `crawler.py`, `parser.py`, `send_to.py`는 수정하지 않는다.
- 크롤링 대상 사이트의 DOM 구조, 날짜 범위, 주문 상태 판단, 배송비 계산은 업무 규칙과 직접 연결되어 있으므로 변경 전 반드시 의도를 확인한다.
- `.env`나 인증정보는 노출하지 않는다.
- 실행 검증 시 실제 외부 사이트와 API 서버에 접근할 수 있으므로, 단순 문서/정적 분석 작업에서는 실행하지 않는 편이 안전하다.
- 현재 프로젝트는 컨테이너 내부에서 개발 중일 수 있으므로, 컨테이너 삭제 전 변경사항 백업 또는 Git 반영 여부를 확인해야 한다.

## 빠른 파악용 의존 관계

```text
crawler.py
  -> parser.extract_order_items()
  -> parser.extract_shipping_fee()
  -> send_to.send_to_sales()
  -> send_to.send_to_delivery()

parser.py
  -> Selenium WebDriver DOM 접근
  -> 정규식 기반 가격/수량/상품명 정리

send_to.py
  -> requests.post()
  -> API_BASE_URL 기반 외부 API 전송
```
