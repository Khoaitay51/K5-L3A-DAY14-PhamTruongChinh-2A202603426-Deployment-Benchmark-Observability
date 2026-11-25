# Benchmark & Observability Report — Day 14

> Mọi con số trong báo cáo này phải lấy từ file JSON/CSV và screenshot thật bạn đã chạy.

**Họ tên:** Phạm Trường Chinh
**MSSV:** 2A202603426
**Ngày chạy:** 2026-11-25
**Môi trường:** WSL2 Ubuntu 24.04, Python 3.12.3, Docker 29.1.3

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | `< 1000 ms` | Đảm bảo 95% request trả lời dưới 1 giây trong điều kiện tải bình thường |
| Error rate `/ask` | `< 2 %` | Cho phép một phần nhỏ lỗi upstream (mặc định `MOCK_ERROR_RATE=0.01`) nhưng không ảnh hưởng trải nghiệm chung |
| Accuracy trên golden dataset | `≥ 100 %` | Đảm bảo mọi câu hỏi chuẩn trong golden dataset đều trả lời đúng, không regression |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.29 | 190.6 | 219.6 | 1701.7 | 1.33% | PASS |
| 10 | 37.01 | 193.9 | 223.5 | 1696.4 | 0.67% | PASS |
| 50 | 104.55 | 193.6 | 280.2 | 1700.8 | 1.00% | PASS |
| 100 | 144.46 | 207.3 | 356.0 | 1753.4 | 0.67% | PASS |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?
- RPS tăng gần tuyến tính ở mức thấp (`c=1` → `4.29 req/s`, `c=10` → `37.01 req/s`), sau đó tăng chậm dần và bắt đầu bão hoà ở mức cao (`c=50` → `104.55 req/s`, `c=100` → `144.46 req/s`) trong khi `p95` tăng từ `219.6 ms` lên `356.0 ms` do giới hạn xử lý đồng thời của một process uvicorn + event loop/client connection pool.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 190.2 | 215.6 | 226.0 |
| 0.03 (mặc định) | 238.9 | 222.8 | 1684.3 |
| 0.1 | 354.6 | 1697.8 | 1710.1 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?
- `p99` (và `p95` khi `MOCK_SLOW_RATE=0.1`) nhạy nhất với các request chậm bất thường. Giá trị trung bình (`avg`) bị kéo thấp xuống bởi đa số request nhanh nên che giấu trải nghiệm tệ của nhóm người dùng gặp tail latency.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.35% (1/23) | 91.3% (21/23) | 100.0% (23/23) |
| Avg tokens / câu | 57.5 | 108.8 | 112.8 |
| Tổng cost (USD) | $0.000410 | $0.000758 | $0.000783 |
| Cost / câu đúng (USD) | $0.00040995 | $0.00003607 | $0.00003404 |
| Quality gate | FAIL | PASS | PASS |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm entry giải thích JWT vs API key vào `KNOWLEDGE_BASE` |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm entry giải thích Kubernetes HPA vào `KNOWLEDGE_BASE` |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**
- Agent v2 tốn thêm latency cho bước retrieval và tốn thêm input tokens (vì chèn context vào prompt), nhưng độ chính xác tăng mạnh so với v1, giúp **cost / câu đúng** hiệu quả hơn đáng kể.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (`screenshots/grafana-dashboard.png`)
- [ ] Một trace chậm trong Jaeger (`screenshots/jaeger-slow-trace.png`)
- [ ] Một trace lỗi trong Jaeger (`screenshots/jaeger-error-trace.png`)
- [ ] Trang Alerts của Prometheus với ít nhất 2 alert đang **firing** (`screenshots/prometheus-alert-firing.png`)

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | (Không có alert firing) | — | — |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**
- Phải kết hợp **eval trên golden dataset (CI quality gate)** trước khi deploy, theo dõi **chất lượng câu trả lời / feedback người dùng (thumbs up/down)** và **độ dài/chi phí token bất thường** vì Prometheus chỉ đo sức khoẻ hạ tầng (RPS, latency, error rate), không đo độ đúng ngữ nghĩa của câu trả lời.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: `[ĐIỀN TRACE_ID THẬT]`
- Tổng thời gian: `[ĐIỀN SỐ] ms`
- Span chiếm nhiều thời gian nhất: `[ĐIỀN TÊN SPAN] ([ĐIỀN SỐ] ms, [ĐIỀN %]%)`
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"message": "DÁN DÒNG LOG JSON THẬT CÓ CÙNG TRACE_ID VÀO ĐÂY"}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?
- `[ĐIỀN GIẢI THÍCH DỰA TRÊN SỐ LIỆU CSV THẬT]`

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. SLO phải đặt theo percentile (`p95`/`p99`) chứ không theo trung bình vì tail latency ảnh hưởng trực tiếp trải nghiệm người dùng.
  2. Eval trên golden dataset + quality gate bằng exit code giúp chặn regression chất lượng trước khi code lên production.
  3. Metrics (Prometheus/Grafana), Tracing (OpenTelemetry/Jaeger) và JSON Logs liên kết qua `trace_id` là bộ ba giúp khoanh vùng lỗi nhanh chóng.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?
  - Thêm alert theo dõi chi phí LLM theo giờ/ngày vượt ngưỡng, tỉ lệ rate-limit `429`, và chất lượng retrieval (empty context rate).
