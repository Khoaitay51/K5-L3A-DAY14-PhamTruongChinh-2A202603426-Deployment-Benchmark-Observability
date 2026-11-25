# Deployment Information

## Public URL
[https://day14-k5-chinh-agent.onrender.com](https://day14-k5-chinh-agent.onrender.com)

## Platform
Render Free, vùng Singapore. Web Service Docker `day14-k5-chinh-agent` lấy mã nguồn từ repo GitHub public, nhánh `main`, thư mục `06-lab-complete/`. Dịch vụ dùng `day14-agent-redis` qua mạng nội bộ để lưu trạng thái và dùng `/health` làm health check.

Lượt deploy này dùng tùy chọn Public Git Repository. [Blueprint Render](06-lab-complete/render.yaml) lưu cấu hình tương đương để tái triển khai. [Tài liệu Render](https://render.com/docs/web-services)

## Test Commands

Nạp `AGENT_API_KEY` từ cấu hình Render vào môi trường shell trước khi chạy lệnh thứ tư.

```bash
BASE=https://day14-k5-chinh-agent.onrender.com
```

### 1. Health Check (expected: 200)
```bash
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
```

### 2. Readiness Check (expected: 200)
```bash
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
```

### 3. API Test without key (expected: 401)
```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Hello"}'
```

### 4. API Test with API key (expected: 200)
```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

## Environment Variables
- `PORT` (do nền tảng tự cấp)
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`
- `REDIS_URL` (trỏ tới Redis service trên nền tảng)
- `AGENT_API_KEY` (secret đặt trên dashboard)
- `RATE_LIMIT_PER_MINUTE=10`
- `DAILY_BUDGET_USD=1.0`
- `MONTHLY_BUDGET_USD=10.0`

## Kết quả kiểm thử public

Kiểm thử lúc 16:55 GMT+7 ngày 25/11/2026. Render đã deploy commit `fc002c2`.

| Kiểm thử | HTTP thực tế |
|---|---:|
| `GET /health` | 200 |
| `GET /ready` với Redis sẵn sàng | 200 |
| `POST /ask` thiếu API key | 401 |
| `POST /ask` có API key hợp lệ | 200 |

## Screenshots

- [Dashboard Render](screenshots/dashboard.png)
- [Deploy thành công](screenshots/running.png)
- [Kết quả kiểm thử public](screenshots/test.png)
