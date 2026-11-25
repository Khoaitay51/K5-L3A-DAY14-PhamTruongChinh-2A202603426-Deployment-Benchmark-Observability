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

Các file JSON của lượt đo develop cũng đặt ngưỡng p95 500 ms. Cả bốn mức tải đạt ngưỡng này và ngưỡng lỗi 2%.

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

Hàng Quality gate phản ánh lượt eval ghi trong báo cáo. So với SLO accuracy 100% ở mục 1, chỉ v2 sau khi sửa knowledge base đạt yêu cầu.

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

- [x] [Dashboard Grafana khi đang có tải](screenshots/grafana-dashboard.png)
- [x] [Trace chậm trong Jaeger](screenshots/jaeger-slow-trace.png)
- [x] [Trace lỗi HTTP 503 trong Jaeger](screenshots/jaeger-error-trace.png)
- [x] [Hai alert đang firing trên Prometheus](screenshots/prometheus-alert-firing.png)

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | ~75 giây | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | ~135 giây | Latency p95 |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | ~155 giây | Cost burn rate (USD/giờ) |
| D | `docker pause` 1 trong 2 instance | `AgentInstanceDown` | ~39 giây | Instances up |
| E | `AGENT_VERSION=v1` | Không có alert firing trong 150 giây | — | Eval trên golden dataset |

Ở lượt A+B, đặt đồng thời hai biến trên một instance và tạo tải bằng 30 người dùng Locust. Thời gian được tính từ lúc chạy lệnh cập nhật agent đến mẫu `ALERTS{alertstate="firing"}` đầu tiên, truy vấn theo bước 1 giây. Cả hai alert vào `pending` khoảng 14 giây sau lúc cập nhật, rồi chuyển sang `firing` sau thời gian chờ 60 và 120 giây tương ứng. Ảnh Grafana trong lượt này ghi nhận 15.3 req/s, 21.12% lỗi và p95 1.90 giây.

Ở lượt C, chuyển sang model lớn đồng thời tăng từ một lên hai instance. Prometheus báo mức chi phí quy đổi $15.35/giờ khi quan sát alert đang `firing`. Ở lượt D, Prometheus phát hiện một target ngừng scrape. Thời gian firing của C và D được tính từ lúc chạy lệnh đến `activeAt` cộng thời gian chờ của rule (120 và 30 giây tương ứng).

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**
- Lượt đối chứng dùng 8 người dùng Locust và một Prometheus mới. Locust ghi nhận p95 `/ask` là 190 ms và 23/772 lỗi (2.98%), gồm 9 phản hồi 502 từ Nginx và 14 phản hồi 503 từ agent. Prometheus không ghi nhận mẫu `ALERTS{alertstate="firing"}` nào trong lượt này.
- Chạy eval trên golden dataset ở CI và theo dõi phản hồi người dùng sau deploy để phát hiện suy giảm chất lượng. Các alert hiện tại đo latency, lỗi, tình trạng instance và chi phí. Eval ở mục 3 cho thấy v1 chỉ đạt 1/23 câu.

### 4.3 Debug bằng trace

Trace `05a8571f8072c80471d45f46ef891f8e` là request `POST /ask` thành công chậm nhất trong log đã lấy. Span gốc kéo dài 3206.71 ms. Trong các bước xử lý bên trong, `chat mock-llm-small` chiếm 2436.16 ms (76.0% tổng thời gian), còn `agent.retrieve_context` mất 20.91 ms.

```json
{"ts":"2026-11-25T16:39:11.67875+07:00","level":"INFO","service":"observable-agent","instance":"cdbcc97f8a3a","event":"http_request","trace_id":"05a8571f8072c80471d45f46ef891f8e","span_id":"9729719a47cf96fb","request_id":"454267e71ef3","method":"POST","route":"/ask","status":200,"ms":3205.2}
```

Trace `d96d00978cd6f622d01a031ef5be90a3` kéo dài 98.12 ms, trả HTTP 503 và có span `chat mock-llm-small` ở trạng thái lỗi. Log `llm_error` xác nhận lỗi đến từ upstream giả lập.

```json
{"ts":"2026-11-25T16:38:07.779784+07:00","level":"INFO","service":"observable-agent","instance":"cdbcc97f8a3a","event":"llm_error","trace_id":"d96d00978cd6f622d01a031ef5be90a3","span_id":"86e8fc5838f4b80c","request_id":"1c068964455d","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 67.54 | 190 | 220 | 1700 | 99 / 7894 (1.25%) |
| 3 | 59.04 | 200 | 840 | 8600 | 73 / 6994 (1.04%) |

Bảng lấy dòng `Aggregated` của Locust, gồm cả `/ask` và `/health`. Riêng `POST /ask`, p95 tăng từ 230 ms lên 1000 ms. Lượt ba instance chạm ngưỡng và trượt SLO `< 1000 ms`.

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?
- Trên cùng một máy local (chạy chung Nginx, Prometheus, Grafana, Jaeger, Locust và các container agent giới hạn `0.5 CPU`), việc tăng từ 1 lên 3 instance **không cải thiện p95** (tăng từ `220 ms` lên `840 ms`, `p99` lên `8600 ms`, RPS giảm nhẹ từ `67.54` xuống `59.04`).
- Một instance FastAPI có thể xử lý nhiều request đồng thời trong khi mock LLM chờ bằng `asyncio.sleep`. Lượt chạy ba instance dùng chung máy với Nginx, Locust và stack quan sát. CSV cho thấy tail latency tăng, nhưng cần thêm số liệu CPU, độ trễ upstream và tải của từng instance để xác định nút thắt.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. SLO phải đặt theo percentile (`p95`/`p99`) chứ không theo trung bình vì tail latency ảnh hưởng trực tiếp trải nghiệm người dùng.
  2. Eval trên golden dataset + quality gate bằng exit code giúp chặn regression chất lượng trước khi code lên production.
  3. Metrics (Prometheus/Grafana), Tracing (OpenTelemetry/Jaeger) và JSON Logs liên kết qua `trace_id` là bộ ba giúp khoanh vùng lỗi nhanh chóng.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?
  - Thêm alert theo dõi chi phí LLM theo giờ/ngày vượt ngưỡng, tỉ lệ rate-limit `429`, và chất lượng retrieval (empty context rate).
