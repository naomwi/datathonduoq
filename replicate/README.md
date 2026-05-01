# Datathon 2026 - Tái tạo Final Submission

Thư mục này chứa môi trường được thiết kế chuyên biệt để tái tạo chính xác 100% tệp submission cuối cùng của hệ thống: `final_submission.csv`.

Tệp kết quả này tương đương với cấu hình: `submission_cleanv19_v17_ratio_monthsmooth_h2_recenteven_a160.csv`

## Cách chạy

Mở terminal tại thư mục gốc của dự án (hoặc trong thư mục `replicate`) và chạy lệnh sau:

```bash
python replicate/reproduce_final_submission.py
```

## Quá trình thực hiện
Script sẽ chạy qua một pipeline chuẩn mực (không rò rỉ dữ liệu):
1. **Load data:** Tải dữ liệu từ `dataset/sales.csv` và tạo Daily Panel.
2. **Model Anchor:** Load hoặc huấn luyện lại mô hình CatBoost đệ quy để dự báo sơ bộ xu hướng.
3. **Daily Allocation (V16):** Áp dụng khuôn mẫu ngày phân bổ (shape) từ tập train.
4. **COGS Ratio Smooth (V19):** Giới hạn tỷ lệ COGS/Revenue dựa trên mức trượt lịch sử (recent_even) với trọng số alpha `a=0.16` và làm mượt theo tháng (month-smooth).
5. **Output:** Tệp `final_submission.csv` được lưu thẳng vào thư mục `replicate/`.
