# Deployment Information

## Public URL
Đang chờ triển khai trên Render.

## Platform
Render Web Service (Docker), dùng thư mục gốc dịch vụ `06-lab-complete/` và Render Key Value nội bộ cùng vùng cho Redis.

Blueprint [06-lab-complete/render.yaml](06-lab-complete/render.yaml) khai báo hai dịch vụ gói Free ở Singapore. Khi tạo Blueprint trong Render, chọn nhánh `main` và đặt Blueprint Path là `06-lab-complete/render.yaml`. Render sinh `AGENT_API_KEY` và gắn URL nội bộ của Key Value vào `REDIS_URL`. [Tài liệu Render Blueprint](https://render.com/docs/blueprint-spec)

## Test Commands

Đặt `BASE` thành URL `onrender.com` sau khi triển khai và nạp `AGENT_API_KEY` vào môi trường shell trước khi chạy lệnh thứ tư.

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

## Kiểm thử local trước khi deploy

Ngày 2026-11-25, Dockerfile của Part 6 đã chạy với Redis và `PORT=10000`. Kết quả theo thứ tự các lệnh ở trên là `200`, `200`, `401`, `200`. Bốn mã HTTP này được đo trong Docker local. Kiểm thử từ URL Render vẫn đang chờ triển khai.

## Screenshots

Ảnh dashboard, trạng thái dịch vụ và kết quả kiểm thử sẽ được bổ sung khi deploy xong.
