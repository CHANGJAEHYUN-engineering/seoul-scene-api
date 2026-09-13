from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


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
                max-width: 720px;
                margin: 80px auto;
                padding: 20px;
                line-height: 1.7;
            }
            h1 {
                margin-bottom: 8px;
            }
        </style>
    </head>
    <body>
        <h1>서울 한 장면</h1>
        <p>서울 관광 콘텐츠의 일정과 세부 프로그램 정보를 분석하여
        관광객의 방문 의사결정을 지원하는 관광정보 서비스 프로토타입입니다.</p>

        <p>현재 비짓서울 API 연동을 준비하고 있습니다.</p>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}