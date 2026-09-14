import os
import httpx
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

BASE_URL = "https://api-call.visitseoul.net/api/v1"
API_KEY = os.getenv("VISITSEOUL_API_KEY")


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
    headers = {
        "VISITSEOUL-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "keyword": keyword,
        "page_no": page_no,
        "lang_code_id": lang_code_id
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, headers=headers, json=payload)

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
    headers = {
        "VISITSEOUL-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "cid": cid
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, headers=headers, json=payload)

    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}

    return {
        "request_url": url,
        "status_code": resp.status_code,
        "response": data
    }
