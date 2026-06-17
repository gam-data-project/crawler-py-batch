import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger("send_to_chunk")

"""URL 생성 : 환경변수에서 chunk 전송 URL을 읽어 반환한다."""
# chunk 전송 URL을 환경변수 기준으로 만든다.
def get_chunk_endpoint() -> str:
    """환경변수에서 chunk 전송 URL을 읽어 반환한다."""
    logger.info("get_chunk_endpoint started")

    chunk_endpoint = os.getenv("CHUNK_ENDPOINT", "").strip()

    if not chunk_endpoint:
        logger.error("get_chunk_endpoint failed: CHUNK_ENDPOINT is missing")
        raise ValueError("CHUNK_ENDPOINT must be set")

    logger.info("get_chunk_endpoint completed: endpoint=%s", chunk_endpoint)
    return chunk_endpoint


# 슬랙 웹훅이 있으면 실패 알림을 보낸다.
def notify_slack(message: str) -> None:
    logger.info("notify_slack started")

    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.warning("notify_slack skipped: 슬랙 웹훅 설정 안됨")
        return

    try:
        resp = requests.post(
            webhook_url,
            json={"text": message},
            timeout=10
        )
        logger.info("notify_slack completed: status_code=%s", resp.status_code)
    except Exception as e:
        logger.exception("notify_slack failed: error=%s", e)


"""응답 본문이 JSON이면 JSON으로, 아니면 문자열(text)로 반환한다."""
def parse_response_body(resp: requests.Response) -> Any:
    logger.debug("parse_response_body started: status_code=%s", resp.status_code)

    try:
        body = resp.json()
        logger.debug("parse_response_body completed: json body parsed")
        return body
    except Exception:
        logger.debug("parse_response_body completed: text body used")
        return resp.text[:500]
    

"""실패 결과를 일관된 dict 형태로 반환한다."""
def build_fail_result(
    chunk_id: str,
    status_code,
    error_type: str,
    response_body=None,
) -> Dict[str, Any]:
    """실패 결과를 공통 dict 형태로 반환한다."""
    logger.debug(
        "build_fail_result completed: chunk_id=%s status_code=%s error_type=%s",
        chunk_id,
        status_code,
        error_type,
    )

    return {
        "ok": False,
        "chunk_id": chunk_id,
        "status_code": status_code,
        "error_type": error_type,
        "response_body": response_body,
    }




# chunk payload를 API로 전송하고 재시도/실패 알림까지 처리한다.
def send_chunk(payload: Dict[str, Any]) -> Dict[str, Any]:
    """chunk payload를 API에 전송하고 결과를 dict로 반환한다."""
    logger.info("send_chunk started")

    endpoint = get_chunk_endpoint()
    chunk_id = payload.get("chunk_id", "unknown")
    chunk_seq = payload.get("chunk_seq")
    total_chunks = payload.get("total_chunks")
    orders = payload.get("orders", [])

    retry_count = int(os.getenv("CHUNK_RETRY_COUNT", "3"))
    timeout_sec = int(os.getenv("CHUNK_TIMEOUT_SEC", "30"))
    retry_delay_sec = int(os.getenv("CHUNK_RETRY_DELAY_SEC", "3"))
    total_attempts = retry_count + 1

    last_status_code = None
    last_response_body = None
    last_error_type = None

    logger.info(
        "send_chunk payload info: chunk_id=%s chunk_seq=%s total_chunks=%s order_count=%d endpoint=%s",
        chunk_id,
        chunk_seq,
        total_chunks,
        len(orders),
        endpoint,
    )

    for attempt in range(1, total_attempts + 1):
        logger.info(
            "send_chunk request started: chunk_id=%s attempt=%d/%d",
            chunk_id,
            attempt,
            total_attempts,
        )

        try:
            # API로 데이터 전송 및 반환
            resp = requests.post(endpoint, json=payload, timeout=timeout_sec)
            last_status_code = resp.status_code
            last_response_body = parse_response_body(resp)
            last_error_type = None

            logger.info(
                "send_chunk response received: chunk_id=%s attempt=%d status_code=%s",
                chunk_id,
                attempt,
                resp.status_code,
            )
            # 성공하면 재시도 안함
            if 200 <= resp.status_code < 300:
                result = {
                    "ok": True,
                    "chunk_id": chunk_id,
                    "status_code": resp.status_code,
                    "response_body": last_response_body,
                }
                logger.info("send_chunk completed successfully: chunk_id=%s", chunk_id)
                return result
            # 4xx는 보통 데이터 문제라 즉시 실패 처리 -> 재시도 안함
            if 400 <= resp.status_code < 500:
                last_error_type = "client_error"
                fail_message = (
                    f"[crawler chunk send failed] chunk_id={chunk_id}, "
                    f"chunk_seq={chunk_seq}/{total_chunks}, order_count={len(orders)}, "
                    f"status_code={resp.status_code}, error_type={last_error_type}"
                )
                logger.error(
                    "send_chunk client error: chunk_id=%s status_code=%s body=%s",
                    chunk_id,
                    resp.status_code,
                    last_response_body,
                )

                notify_slack(fail_message)

                return build_fail_result(
                    chunk_id=chunk_id,
                    status_code=resp.status_code,
                    error_type="client_error",
                    response_body=last_response_body,
                )
            # 5xx는 재시도 대상
            if 500 <= resp.status_code < 600:
                last_error_type = "server_error"
                logger.warning(
                    "send_chunk server error: chunk_id=%s attempt=%d status_code=%s",
                    chunk_id,
                    attempt,
                    resp.status_code,
                )
            else:
                last_error_type = "unexpected_status"
                logger.warning(
                    "send_chunk unexpected status: chunk_id=%s attempt=%d status_code=%s",
                    chunk_id,
                    attempt,
                    resp.status_code,
                )

        except requests.RequestException as e:
            last_status_code = None
            last_response_body = None
            last_error_type = type(e).__name__

            logger.exception(
                "send_chunk request exception: chunk_id=%s attempt=%d error=%s",
                chunk_id,
                attempt,
                e,
            )

        if attempt < total_attempts:
            logger.info(
                "send_chunk retry wait: chunk_id=%s next_attempt=%d sleep_sec=%d",
                chunk_id,
                attempt + 1,
                retry_delay_sec,
            )
            time.sleep(retry_delay_sec)

    fail_message = (
        f"[crawler chunk send failed] chunk_id={chunk_id}, "
        f"chunk_seq={chunk_seq}/{total_chunks}, order_count={len(orders)}, "
        f"status_code={last_status_code}, error_type={last_error_type}"
    )

    logger.error("send_chunk exhausted retries: %s", fail_message)
    notify_slack(fail_message)

    return build_fail_result(
        chunk_id=chunk_id,
        status_code=last_status_code,
        error_type=last_error_type or "unknown_error",
        response_body=last_response_body,
    )




