# Datathon 2026 - Duoq Team

Dự án này chứa mã nguồn dự báo doanh thu (**Revenue**) và chi phí (**COGS**) cho cuộc thi **Datathon 2026 Round 1**, cùng với notebook phân tích dữ liệu, notebook kiểm tra MCQ và pipeline tái tạo kết quả nộp bài.

---

## Cấu trúc thư mục

- `replicate/`: Thư mục quan trọng nhất chứa kịch bản tái tạo (reproduce) kết quả nộp bài.
- `dataset/`: Chứa dữ liệu đầu vào (`sales`, `orders`, `order_items`, `products`, `promotions`, `web_traffic`, v.v.).  
  Lưu ý: Các file sinh ra trung gian như `feature_store`, logs hoặc model weights có thể được ignore để giảm dung lượng repo.
- `notebook/`: Chứa các notebook phân tích EDA, kiểm tra MCQ và hỗ trợ báo cáo.
- `images/`: Chứa các hình ảnh dùng trong report, bao gồm biểu đồ EDA, pipeline mô hình và SHAP/feature importance.
- `requirements/`: Chứa tài liệu yêu cầu, môi trường hoặc các file tham chiếu liên quan.
- `logs/`: (Đã ignore) Chứa logs và model weights khi huấn luyện/nghiệm thu offline.
- `notes/`: Chứa các bản nháp, nhật ký làm việc, audit hoặc brainstorm nếu có.
- Các file `.py` ở thư mục gốc: Là mã nguồn tạo đặc trưng, huấn luyện mô hình và thực thi pipeline hậu xử lý.

---

## Notebooks

Thư mục `notebook/` chứa các notebook phục vụ phân tích và kiểm tra kết quả.

| Notebook | Mục đích |
|---|---|
| `Phase_A.ipynb` | Phân tích Revenue Anatomy: xu hướng doanh thu, seasonality, category contribution và các pattern tổng quan. |
| `Phase_B.ipynb` | Driver Analysis: phân tích traffic, order count, conversion proxy, promotion và channel quality. |
| `Phase_C.ipynb` | Operational Frictions: phân tích stockout, returns, delivery, review distribution và cancellation risk. |
| `Phase_D.ipynb` | Hỗ trợ phần forecasting/report: kiểm tra hình ảnh, mô hình, SHAP/pipeline và validation/output checks. |
| `multiple_choice.ipynb` | Notebook tính toán và kiểm tra đáp án phần MCQ của đề thi. |

Khuyến nghị chạy notebook theo thứ tự:

```text
Phase_A.ipynb → Phase_B.ipynb → Phase_C.ipynb → Phase_D.ipynb
```

Notebook `multiple_choice.ipynb` có thể chạy độc lập để tái tạo các đáp án trắc nghiệm.

---

## MCQ Reproducibility

File `notebook/multiple_choice.ipynb` được dùng để tính toán trực tiếp các câu hỏi trắc nghiệm từ dữ liệu gốc.

Notebook này dùng để kiểm tra các nhóm câu hỏi như:

- median inter-order gap của khách hàng có nhiều hơn một đơn hàng,
- gross margin trung bình theo product segment,
- return reason phổ biến nhất trong Streetwear,
- traffic source có bounce rate trung bình thấp nhất,
- tỷ lệ dòng đơn hàng có áp dụng khuyến mãi,
- số đơn hàng trung bình theo age group,
- region tạo doanh thu cao nhất,
- payment method xuất hiện nhiều nhất trong cancelled orders,
- return rate theo size,
- installment plan có payment value trung bình cao nhất.

Mục tiêu là đảm bảo đáp án MCQ có thể được reproduce từ CSV thay vì dựa vào suy luận thủ công.

---

## Hướng dẫn chạy lại kết quả Forecasting

Bản nộp cuối cùng (**Final Submission**) của nhóm là bản **Strict Clean**: không overfit Public Leaderboard và chỉ dùng historical shape / historical priors hợp lệ.

Để chạy lại kết quả và sinh ra file nộp bài chung cuộc (`final_submission.csv`), vui lòng thực thi lệnh sau từ thư mục gốc của dự án:

```bash
python replicate/reproduce_final_submission.py
```

Lệnh này sẽ tự động:

1. Đọc dữ liệu thô từ `dataset/`.
2. Khởi tạo panel dự báo và thiết lập các biến đổi đặc trưng.
3. Sử dụng mô hình Anchor (**CatBoost**) để dự báo Revenue.
4. Áp dụng các bước rule-based post-processing:
   - daily allocation,
   - COGS-to-Revenue ratio layer,
   - abnormal spike/tail capping,
   - sanity checks.
5. Lưu kết quả ra:

```text
replicate/final_submission.csv
```

File `replicate/final_submission.csv` chính là file được dùng để nộp trên hệ thống của ban tổ chức/Kaggle.

---

## Forecasting Approach

Pipeline forecasting được thiết kế theo hướng **leakage-safe**.

Thiết kế chính:

- **Revenue forecast** = demand anchor + daily seasonal allocation.
- **COGS forecast** = Revenue forecast × estimated COGS-to-Revenue ratio.
- **Post-processing** = daily allocation, COGS ratio control, spike capping và sanity checks.

Các kiểm soát leakage:

- Không dùng hidden test targets.
- Không dùng dữ liệu ngoài.
- Không dùng realized future orders, future traffic, future returns, future reviews hoặc future inventory states.
- Chỉ dùng dữ liệu lịch sử và thông tin calendar biết trước tại thời điểm dự báo.

---

## Key EDA Findings

Các notebook EDA hỗ trợ những insight chính trong report:

1. Doanh thu tăng mạnh đến khoảng 2017–2018 và suy giảm rõ từ 2019 trở đi.
2. Doanh thu có seasonality mạnh, đặc biệt trong giai đoạn April–June.
3. Streetwear chiếm phần lớn doanh thu, tạo product concentration risk.
4. Sau 2018, traffic tăng nhưng order volume và conversion proxy giảm mạnh.
5. Wrong-size returns và COD cancellations là hai điểm rò rỉ doanh thu vận hành quan trọng.
6. Các insight này được dùng để đề xuất hành động kinh doanh và định hướng thiết kế forecasting pipeline.

---

## Output Files

Output chính:

```text
replicate/final_submission.csv
```

Supporting assets:

```text
images/
```

Thư mục `images/` chứa các hình dùng trong report, bao gồm biểu đồ EDA, forecasting pipeline diagram và SHAP/model explainability.

---

## Notes for Reviewers

- Repo được tổ chức để có thể tái tạo final submission từ source code.
- `replicate/` là entry point chính để chạy lại file nộp.
- `notebook/` chứa phân tích EDA và tính toán MCQ minh bạch.
- Các file trung gian, cache, logs và model weights có thể được ignore để giữ repo gọn.
- Nếu cần reproduce đầy đủ, vui lòng bắt đầu từ `replicate/README.md` và `python replicate/reproduce_final_submission.py`.

---

## Team

**Duoq Team**  
Datathon 2026 Round 1
