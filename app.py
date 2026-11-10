"""Isolated dashboard for synthetic platform checks; no platform connections."""

import json
from html import escape
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

STATUSES = ("WORKING", "PARTIAL", "BROKEN", "UNAVAILABLE", "BLOCKED", "UNKNOWN")
CHECKS = (
    {"component": "Тестовый API", "status": "WORKING", "observed_at": "2026-11-10T08:00:00+00:00", "description": "Демонстрационный API отвечает", "defect": ""},
    {"component": "Очередь задач", "status": "PARTIAL", "observed_at": "2026-11-10T08:03:00+00:00", "description": "Часть демонстрационных задач ожидает", "defect": "Искусственная задержка обработки"},
    {"component": "Проверка почты", "status": "BROKEN", "observed_at": "2026-11-10T08:05:00+00:00", "description": "Тестовая почта не доставлена", "defect": "Синтетическая ошибка отправки"},
    {"component": "Тестовый шлюз", "status": "UNAVAILABLE", "observed_at": "2026-11-10T08:07:00+00:00", "description": "Демонстрационный шлюз недоступен", "defect": "Нет тестового ответа"},
    {"component": "Ручная проверка", "status": "BLOCKED", "observed_at": "2026-11-10T08:09:00+00:00", "description": "Тестовый сценарий ожидает проверки", "defect": "Ожидание тестовых данных"},
    {"component": "Неизвестный стенд", "status": "UNKNOWN", "observed_at": "2026-11-10T08:11:00+00:00", "description": "Состояние демонстрационного стенда не определено", "defect": "Нет наблюдения"},
)


def respond(start_response, status, body, content_type):
    payload = body.encode("utf-8")
    start_response(status, [
        ("Content-Type", f"{content_type}; charset=utf-8"),
        ("Content-Length", str(len(payload))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
    ])
    return [payload]


def json_response(start_response, status, data):
    return respond(start_response, status, json.dumps(data, ensure_ascii=False), "application/json")


def render_dashboard(checks, selected):
    options = ['<option value="">Все статусы</option>']
    options.extend(
        f'<option value="{status}"{" selected" if selected == status else ""}>{status}</option>'
        for status in STATUSES
    )
    rows = "\n".join(
        "<tr>" + "".join(f"<td>{escape(str(check[key]))}</td>" for key in
                          ("observed_at", "component", "status", "description", "defect")) + "</tr>"
        for check in checks
    )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nextera Platform Health Dashboard</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:3rem auto;padding:0 1rem;color:#1b2430;background:#f5f8fc}}
header,main{{background:white;padding:1.5rem;border-radius:12px;margin-bottom:1rem;box-shadow:0 1px 6px #ccd4de}}
h1{{margin:0 0 .5rem}}p{{margin:.5rem 0}}form{{margin:1rem 0}}select{{padding:.5rem;font:inherit}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:.7rem;border-bottom:1px solid #d8dfe7}}th{{background:#eaf0f8}}
.table-wrap{{overflow-x:auto}}a{{color:#17477d}}@media(max-width:650px){{body{{margin:1rem auto}}}}
</style></head><body>
<header><h1>Nextera Platform Health Dashboard</h1><p>Только синтетические данные. Состояние реальной платформы здесь не проверяется.</p></header>
<main><form method="get" action="/"><label for="status">Фильтр статуса</label>
<select id="status" name="status">{"".join(options)}</select><button type="submit">Показать</button></form>
<div class="table-wrap"><table><thead><tr><th>Дата</th><th>Компонент</th><th>Статус</th><th>Описание</th><th>Дефект</th></tr></thead>
<tbody>{rows}</tbody></table></div><p>Показано: {len(checks)}</p><a href="/api/checks">JSON API</a></main></body></html>"""


def application(environ, start_response):
    if environ.get("REQUEST_METHOD") != "GET":
        return json_response(start_response, "405 Method Not Allowed", {"error": "method not allowed"})

    path = environ.get("PATH_INFO", "")
    if path == "/health":
        return json_response(start_response, "200 OK", {"status": "ok"})
    if path not in ("/", "/api/checks"):
        return json_response(start_response, "404 Not Found", {"error": "not found"})

    params = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
    values = params.get("status")
    if values is not None and (len(values) != 1 or values[0] not in STATUSES):
        return json_response(start_response, "400 Bad Request", {"error": "invalid status", "allowed": STATUSES})
    selected = values[0] if values else ""
    checks = [check for check in CHECKS if not selected or check["status"] == selected]
    if path == "/api/checks":
        return json_response(start_response, "200 OK", checks)
    return respond(start_response, "200 OK", render_dashboard(checks, selected), "text/html")


if __name__ == "__main__":
    with make_server("127.0.0.1", 8765, application) as server:
        print("Dashboard: http://127.0.0.1:8765 (local-only; synthetic data)", flush=True)
        server.serve_forever()
