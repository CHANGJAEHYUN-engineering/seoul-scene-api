import os
import re
import html
import httpx
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

BASE_URL = "https://api-call.visitseoul.net/api/v1"
API_KEY = os.getenv("VISITSEOUL_API_KEY")


def _headers():
    return {
        "VISITSEOUL-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>서울 한 장면</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 760px;
                margin: 60px auto;
                padding: 20px;
                line-height: 1.7;
            }
            h1 { margin-bottom: 8px; }
            code {
                background: #f3f3f3;
                padding: 2px 6px;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <h1>서울 한 장면</h1>
        <p>비짓서울 API 기반 관광정보 서비스 프로토타입입니다.</p>
        <p>테스트 엔드포인트:</p>
        <ul>
            <li><code>/health</code></li>
            <li><code>/api/visitseoul/list</code></li>
            <li><code>/api/visitseoul/info?cid=콘텐츠ID</code></li>
            <li><code>/api/visitseoul/scene-candidates?limit=5</code></li>
        </ul>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok", "api_key_loaded": bool(API_KEY)}


@app.get("/api/visitseoul/list")
async def visitseoul_list(
    keyword: str = Query("", description="검색어"),
    page_no: int = Query(1, description="페이지 번호"),
    lang_code_id: str = Query("ko", description="언어 코드")
):
    if not API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "VISITSEOUL_API_KEY 환경변수가 설정되지 않았습니다."}
        )

    url = f"{BASE_URL}/contents/list"
    payload = {
        "keyword": keyword,
        "page_no": page_no,
        "lang_code_id": lang_code_id
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, headers=_headers(), json=payload)

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}

    return {
        "request_url": url,
        "status_code": resp.status_code,
        "response": data
    }


@app.get("/api/visitseoul/info")
async def visitseoul_info(
    cid: str = Query(..., description="콘텐츠 ID")
):
    if not API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "VISITSEOUL_API_KEY 환경변수가 설정되지 않았습니다."}
        )

    url = f"{BASE_URL}/contents/info"

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, headers=_headers(), json={"cid": cid})

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}

    return {
        "request_url": url,
        "status_code": resp.status_code,
        "response": data
    }


@app.get("/api/visitseoul/scene-candidates")
async def scene_candidates(
    limit: int = Query(5, ge=1, le=10, description="반환할 후보 수")
):
    """
    C01 '한 장면 시간표' 추가 검증용 보조 엔드포인트.
    최신 콘텐츠 목록에서 축제/공연/행사 후보를 찾고,
    상세 API를 다시 호출하여 서울 소재 + 세부 날짜/시간 조건이 있는 사례를 요약한다.

    주의: scene_candidate는 규칙 기반 '추가 검토 후보'일 뿐,
    실제 장면-날짜 정답 판정 결과가 아니다.
    """
    if not API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "VISITSEOUL_API_KEY 환경변수가 설정되지 않았습니다."}
        )

    list_url = f"{BASE_URL}/contents/list"
    info_url = f"{BASE_URL}/contents/info"

    async with httpx.AsyncClient(timeout=25.0) as client:
        list_resp = await client.post(
            list_url,
            headers=_headers(),
            json={"page_no": 1, "lang_code_id": "ko"}
        )

        try:
            list_json = list_resp.json()
        except Exception:
            return JSONResponse(
                status_code=502,
                content={"error": "목록 응답 JSON 파싱 실패", "raw_text": list_resp.text}
            )

        items = list_json.get("data") or []
        festival_items = [
            item for item in items
            if "축제/공연/행사" in (item.get("cate_depth") or "")
        ]

        results = []
        scanned = 0

        for item in festival_items:
            if len(results) >= limit:
                break

            scanned += 1
            cid = item.get("cid")
            if not cid:
                continue

            detail_resp = await client.post(
                info_url,
                headers=_headers(),
                json={"cid": cid}
            )

            try:
                detail_json = detail_resp.json()
            except Exception:
                continue

            data = detail_json.get("data") or {}
            traffic = data.get("traffic") or {}
            extra = data.get("extra") or {}

            address_text = " ".join([
                str(traffic.get("adres") or ""),
                str(traffic.get("new_adres") or "")
            ]).strip()

            # 비짓서울 목록에는 타지역 콘텐츠도 포함될 수 있으므로 서울 주소만 남긴다.
            if "서울" not in address_text:
                continue

            important = str(extra.get("cmmn_important") or "").strip()
            post_desc_text = _strip_html(str(data.get("post_desc") or ""))

            # 날짜/시간 조건이 실제로 보이는지 빠르게 찾는 휴리스틱.
            has_date_or_time = bool(
                re.search(r"\b\d{1,2}/\d{1,2}\b", important)
                or re.search(r"\b\d{1,2}:\d{2}\b", important)
                or re.search(r"\b\d{4}\.\d{1,2}\.\d{1,2}\b", important)
            )

            # 세부 조건이 없으면 C01 증거 후보로는 약하므로 제외.
            if not important or not has_date_or_time:
                continue

            results.append({
                "cid": data.get("cid"),
                "title": data.get("post_sj"),
                "category": data.get("cate_depth"),
                "festival_start": data.get("schdul_info_bgnde"),
                "festival_end": data.get("schdul_info_endde"),
                "place": data.get("place"),
                "use_time": extra.get("cmmn_use_time"),
                "important": important,
                "address": traffic.get("new_adres") or traffic.get("adres"),
                "post_desc_preview": post_desc_text[:500],
                "scene_candidate": True,
                "note": "자동 정답이 아니라 C01의 장면-날짜 범위 차이를 사람이 추가 검토할 후보입니다."
            })

    return {
        "status": "ok",
        "purpose": "C01 추가 사례 탐색",
        "list_call_status": list_resp.status_code,
        "festival_items_in_first_page": len(festival_items),
        "festival_items_scanned": scanned,
        "returned_candidates": len(results),
        "candidates": results
    }
