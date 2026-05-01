# Datathon 2026 - Duoq Team

Dự án này chứa mã nguồn dự báo doanh thu (Revenue) và chi phí (COGS) cho cuộc thi Datathon. 

## Cấu trúc thư mục

- `replicate/`: Thư mục quan trọng nhất chứa kịch bản tái tạo (reproduce) kết quả nộp bài.
- `dataset/`: Chứa dữ liệu đầu vào (sales, cogs, promotions, v.v.). **Lưu ý**: Các file sinh ra trung gian (feature_store) hoặc file log/kết quả đã được ignore để giảm dung lượng repo.
- `logs/`: (Đã ignore) Chứa logs và model weights khi huấn luyện nghiệm thu offline.
- `notes/`: Chứa các bản nháp, nhật ký làm việc (audit, brainstorm).
- Các file `.py` ở thư mục gốc: Là mã nguồn (source code) tạo đặc trưng (features), huấn luyện mô hình (train) và thực thi pipeline hậu xử lý.

## Hướng dẫn chạy lại kết quả (Reproduce)

Bản nộp cuối cùng (Final Submission) của nhóm là bản **Strict Clean** (không overfit Public Leaderboard, chỉ dùng historical shape).

Để chạy lại kết quả và sinh ra file nộp bài chung cuộc (`final_submission.csv`), vui lòng thực thi lệnh sau từ thư mục gốc của dự án:

```bash
python replicate/reproduce_final_submission.py
```

Lệnh này sẽ tự động:
1. Đọc dữ liệu thô từ `dataset/`.
2. Khởi tạo Panel và thiết lập các biến đổi (Features).
3. Sử dụng mô hình Anchor (CatBoost) để dự báo.
4. Xử lý hậu kỳ (Post-processing) và lưu kết quả ra file `replicate/final_submission.csv`.

*(File `replicate/final_submission.csv` chính là file được dùng để nộp trên hệ thống của ban tổ chức).*
