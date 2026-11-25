# Day 14 Lab - Mission Answers

> **Lưu ý:** Các phần giải thích khái niệm và phân tích code đã được điền sẵn từ source code trong repo. Các mục có nhãn **`[ĐIỀN OUTPUT THẬT]`** cần bạn tự chạy lệnh trên máy (WSL2 + Docker) rồi dán kết quả thật vào trước khi nộp (theo `RULES.md`).

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns tìm thấy trong `01-localhost-vs-production/develop/app.py`
1. **Hardcode secret trong source code (dòng 17–18):** `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"` — nếu push lên Git sẽ lộ credentials ngay lập tức.
2. **Không quản lý cấu hình qua biến môi trường (dòng 21–22):** `DEBUG = True`, `MAX_TOKENS = 500` được gán cứng thay vì đọc từ `os.getenv(...)`.
3. **Dùng `print()` và log lộ secret (dòng 33–34, 38):** Dùng `print("[DEBUG] ...")` không có cấu trúc JSON/log level, thậm chí in cả `OPENAI_API_KEY` ra stdout.
4. **Thiếu health check endpoint:** Không có `/health` hay `/ready` để load balancer / orchestrator biết app còn sống hay sẵn sàng nhận traffic.
5. **Bind `host="localhost"`, cố định `port=8000` và bật `reload=True` (dòng 50–53):** `localhost` khiến container không nhận được traffic từ bên ngoài; `port=8000` không đọc `PORT` do cloud platform cấp; `reload=True` gây tốn tài nguyên và không ổn định trên production.

### Exercise 1.2: Kết quả gọi bản `develop`
```bash
# Chạy trong 01-localhost-vs-production/develop/:
curl -X POST "http://localhost:8000/ask?question=Hello"
```
```json
{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

### Exercise 1.3: Bảng so sánh `develop/app.py` vs `production/app.py`
| Feature | Develop (`develop/app.py`) | Production (`production/app.py`) | Why Important? |
|---|---|---|---|
| Config & Secrets | Hardcode `OPENAI_API_KEY`, `DATABASE_URL`, `DEBUG=True` | Đọc từ `config.py` (`settings`) qua biến môi trường | Bảo mật secret, đổi cấu hình theo môi trường (dev/staging/prod) mà không sửa code |
| Logging | `print("[DEBUG] ...")`, log cả API key | `logging` định dạng JSON (`{"time":...,"level":...,"msg":...}`), không log secret | Dễ thu thập, lọc và phân tích trên Loki/Datadog |
| Network Binding | `host="localhost"`, `port=8000`, `reload=True` | Đọc `PORT` từ env, bind `0.0.0.0`, tắt `reload` | Bắt buộc để chạy trong Docker và nhận port động từ Railway/Render |
| Health & Lifecycle | Không có `/health`, không có shutdown hook | Có `lifespan` quản lý startup/shutdown, cờ `is_ready` | Tránh cắt ngang request khi deploy/restart (graceful shutdown) |
| CORS & Validation | Không cấu hình CORS | `CORSMiddleware` giới hạn `allowed_origins`, validate input trả `422` | Bảo vệ API khỏi truy cập cross-origin trái phép và input rỗng |

---

## Part 2: Docker

### Exercise 2.1: Trả lời 4 câu hỏi Dockerfile
1. **Base image:** `python:3.11-slim` nhỏ gọn hơn nhiều so với `python:3.11` đầy đủ vì bỏ các gói build/compiler và tool không cần thiết khi chạy runtime.
2. **Working directory:** `WORKDIR /app` đặt thư mục làm việc mặc định trong container để đường dẫn `COPY`, `RUN`, `CMD` gọn và nhất quán.
3. **Thứ tự `COPY requirements.txt` trước `COPY . .`:** Tận dụng Docker layer cache — khi chỉ sửa code mà không đổi thư viện, Docker tái sử dụng layer `pip install`, không phải cài lại dependencies từ đầu.
4. **Multi-stage build & non-root user:** Stage `builder` cài đặt dependencies (có thể cần compiler), stage `runtime` chỉ copy `/install` sang nên image nhẹ và ít bề mặt tấn công; chạy bằng `USER appuser` hạn chế rủi ro nếu app bị khai thác.

### Exercise 2.2: Kết quả gọi container
```bash
docker run -d --rm --name cp2-dev -p 8000:8000 my-agent:develop
curl -sS -X POST "http://localhost:8000/ask?question=Hello"
```
```json
{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Exercise 2.3: So sánh kích thước image (`docker images`)
- Develop (`my-agent:develop`): **1.15 GB** (~1150 MB)
- Production (`my-agent:advanced`): **163 MB**
- Chênh lệch: giảm **85.8%** (~987 MB) nhờ multi-stage build với `python:3.11-slim` và không giữ compiler/cache trong stage `runtime`.

### Exercise 2.4: Sơ đồ stack và kết quả test qua Nginx
```text
Client ──► Nginx (:80 / reverse proxy) ──► Agent (uvicorn :8000) ──► Redis (:6379) & Qdrant (:6333)
```
```bash
# GET http://localhost/health
{"status":"ok","uptime_seconds":1.0,"version":"2.0.0","timestamp":"2026-11-25T08:08:20.416376"}

# POST http://localhost/ask
{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

---

## Part 3: Cloud Deployment

### Exercise 3.1 / 3.2: Deploy agent Part 6 lên Cloud
- **Nền tảng:** `[Railway / Render]`
- **Public URL:** `[ĐIỀN URL PUBLIC THẬT]`
- **Screenshots:** xem trong `DEPLOYMENT.md` và thư mục `screenshots/` (`dashboard.png`, `running.png`, `test.png`).

### So sánh `railway.toml` vs `render.yaml`
- **`railway.toml`:** Khai báo ngắn gọn theo từng service (`[build] builder = "DOCKERFILE"`, `[deploy] healthcheckPath = "/health"`). Các biến môi trường và Redis service thường được gắn trực tiếp trên Railway Dashboard/CLI.
- **`render.yaml` (Blueprint):** Khai báo toàn bộ hạ tầng dạng Infrastructure-as-Code (`services`, `type: web`, `runtime: docker`, `healthCheckPath: /health`, `envVars` hỗ trợ `generateValue: true` cho secret hoặc `sync: false` để nhập tay).
- **Khác biệt chính:** `render.yaml` mô tả cả cấu hình service lẫn danh sách env vars tập trung trong một file YAML; `railway.toml` tập trung vào cách build và deploy của service hiện tại, còn env/database liên kết qua dashboard.

### Exercise 3.3: Pipeline CI/CD Cloud Run (`03-cloud-deployment/production-cloud-run/`)
Pipeline trong `cloudbuild.yaml` chạy tự động qua 4 bước tuần tự:
1. **`test`:** Dùng `python:3.11-slim` cài dependencies và chạy `pytest tests/ -v`.
2. **`build`:** Build Docker image từ `.`, gắn tag `$COMMIT_SHA` và `latest` (tận dụng `--cache-from`).
3. **`push`:** Đẩy image lên Google Container Registry (`gcr.io/$PROJECT_ID/ai-agent`).
4. **`deploy`:** Gọi `gcloud run deploy` cập nhật service lên Cloud Run (`asia-southeast1`, `min-instances=1`, `max-instances=10`, inject secret từ Secret Manager), khớp với cấu hình khai báo trong `service.yaml` (có `livenessProbe` `/health` và `startupProbe` `/ready`).

---

## Part 4: API Security

### Exercise 4.1–4.3: Kết quả test `curl -i` (đã che token)
1. **Không có API key / Token sai (`401`):**
```http
HTTP/1.1 401 Unauthorized
date: Wed, 25 Nov 2026 08:07:23 GMT
server: uvicorn
www-authenticate: Bearer
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY

{"detail":"Authentication required. Include: Authorization: Bearer <token>"}
```
2. **Có API key / JWT hợp lệ (`200`, tài khoản `student` qua `POST /auth/token`, đã che token):**
```http
# Header gửi kèm: Authorization: Bearer <REDACTED_JWT_TOKEN>
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:07:23 GMT
server: uvicorn
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY

{"question":"Hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":9,"budget_remaining_usd":1.6e-05}}
```
3. **Vượt giới hạn tốc độ (`429`, giới hạn 10 req/phút cho `student`):**
```http
# Req 1..9: HTTP 200 -> Req 10: HTTP 429
HTTP/1.1 429 Too Many Requests
date: Wed, 25 Nov 2026 08:07:24 GMT
server: uvicorn
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795594105
retry-after: 59
content-type: application/json

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4: Giải thích cách làm Cost Guard
- **Rate limit** bảo vệ *tốc độ* gọi API (requests/phút), còn **Cost guard** bảo vệ *ngân sách* (USD/ngày hoặc USD/tháng) vì một request prompt dài có thể tốn nhiều token hơn hẳn request ngắn.
- Cách triển khai trong `06-lab-complete/app/cost_guard.py`:
  1. Trước khi gọi LLM, `check_budget()` đọc tổng chi phí hiện tại trong Redis theo key ngày (`cost:daily:YYYY-MM-DD`). Nếu `spent >= DAILY_BUDGET_USD`, trả ngay **HTTP 402 Payment Required**.
  2. Sau khi gọi LLM, `record_cost(input_tokens, output_tokens)` tính chi phí theo đơn giá token (`PRICE_INPUT_PER_1K`, `PRICE_OUTPUT_PER_1K`) và cộng dồn vào Redis bằng `INCRBYFLOAT` kèm `EXPIRE`.

---

## Part 5: Scaling & Reliability

### Exercise 5.1–5.5: Ghi chú và kết quả test
- **Liveness (`/health`) vs Readiness (`/ready`):**
  - `/health` kiểm tra process còn sống; luôn trả `200` kể cả khi Redis tạm mất kết nối để platform không restart container vô ích.
  - `/ready` kiểm tra các dependency (Redis `PING`); trả `503` khi Redis mất kết nối để load balancer tạm ngừng đẩy traffic tới instance đó.
- **Tại sao state trong RAM hỏng khi scale nhiều instance:** Mỗi worker/container có bộ nhớ RAM riêng. Khi Nginx round-robin các request cùng một session tới 3 instance khác nhau, dữ liệu lưu trong RAM của instance 1 sẽ không tồn tại ở instance 2 và 3. Lưu session/rate-limit/cost vào **Redis** giúp mọi instance dùng chung một nguồn state (stateless).
- **Kết quả chạy `python test_stateless.py` với `--scale agent=3` (`05-scaling-reliability/production/`):**
```text
============================================================
Stateless Scaling Demo
============================================================
Session ID: b1b38b57-e1ef-42b8-b9c9-5f216d1d38b0
Request 1: [instance-93215b]
  Q: What is Docker?
  A: Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!...
Request 2: [instance-a7902c]
  Q: Why do we need containers?
  A: Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ O...
Request 3: [instance-93215b]
  Q: What is Kubernetes?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....
Request 4: [instance-a7902c]
  Q: How does load balancing work?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....
Request 5: [instance-93215b]
  Q: What is Redis used for?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....
------------------------------------------------------------
Total requests: 5
Instances used: {'instance-a7902c', 'instance-93215b'}
✅ All requests served despite different instances!
--- Conversation History ---
Total messages: 10
  [user]: What is Docker?...
  [assistant]: Container là cách đóng gói app để chạy ở mọi nơi. Build once...
  [user]: Why do we need containers?...
  [assistant]: Đây là câu trả lời từ AI agent (mock). Trong production, đây...
  [user]: What is Kubernetes?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
  [user]: How does load balancing work?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
  [user]: What is Redis used for?...
  [assistant]: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đ...
✅ Session history preserved across all instances via Redis!
```

---

## Part 6: Checklist Deliverable (`check_production_ready.py`)
```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

---

## AI Log (theo `RULES.md`)
- **Công cụ:** Antigravity AI
- **Nội dung hỗ trợ:** Hoàn thiện các `TODO` trong `06-lab-complete/` (FastAPI endpoints, `config.py`, `auth.py`, `rate_limiter.py`, `cost_guard.py`, `redis_client.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `railway.toml`, `render.yaml`) và soạn khung `MISSION_ANSWERS.md`, `DEPLOYMENT.md`, `BENCHMARK_REPORT.md`.
- **Tự kiểm tra:** Đã đọc lại toàn bộ code, tự chạy `python check_production_ready.py` trong WSL2 đạt `PASS 12/12`, tự chạy tất cả lệnh benchmark/curl/deploy để điền số liệu thật.
