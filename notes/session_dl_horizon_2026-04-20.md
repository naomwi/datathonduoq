# SPRINT SESSION NOTE: Deep Learning & Horizon-Routing (2026-04-20)

## 1. Mở Đầu (The Pivot from Post-Processing)
Tiếp nối thành công của `recencyexp20` (896k Public), ý tưởng tạo chuỗi Re-anchor bằng hàm toán học (`tail_ramp40`) ở đuôi dự báo đã **thất bại trên Public (911k)**. 
Ngoài ra, báo cáo gốc của người dùng về việc OOF có bias dương 682k là **SAI**. Phân tích audit chẩn đoán thực tế `recencyexp20` OOF chỉ có `+48k` bias (Overpredict 53.6%). Sự ngộ nhận về bias đã được dỡ bỏ. Mọi nỗ lực tinh chỉnh Post-Processing kết thúc.

## 2. Hướng Đi 1: Cắt Nhánh Horizon (Horizon-Binned Recursive Modeling)
Lý thuyết: CatBoost bị "Recursive Error Accumulation", nghĩa là dùng những dự đoán sai lệch ngắn hạn (lag_1, lag_7) đưa vào dự đoán 500 ngày tiếp theo khiến đuôi gãy vụn.

* **Version 1 (Depth Crippling):** Đào tạo Model A (Early - depth 6) và Model B (Late - depth 4 để chống nhiễu). Tuy nhiên, vì Model B vẫn ăn rác nội suy `lag_1..28`, nó làm MAE kém đi (637k Combined Offline).
* **Version 2 (Tỉa đệ quy - Recursive Feature Pruning):** Quyết định chặt đứt quy trình đệ quy bằng cách **cắt bớt hoàn toàn các momentum features (`lag_1..28`, `rollmean`) khỏi Model B**, bắt nó chỉ dựa vào `lag_364`, lịch, và hàm dự phòng mùa vụ.
  * **Kết quả:** Combined MAE 621k. Rớt hạng. 
  * **Bài học:** Việc chặt nhánh đệ quy đúng là chặn được nhiễu, nhưng đồng thời khiến Model Late bị "Mù Momentum". Nó học theo mức cân bằng trung bình dài hạn nên dưới mức (underfit) so với sự đứt gãy 2022 thực tế. "Trọng số Decay" (Recency) cực kỳ cần thiết để bám Trend, vứt Momentum Lags là vứt luôn chìa khóa bắt Trend.

## 3. Hướng Đi 2: Dứt điểm với Deep Learning (Direct Multi-Step)
Vì Recursive Trees tích lũy rác, ta giải quyết bằng Deep Learning: 1 bộ Encoder thu lại 90 ngày quá khứ -> 1 bộ Decoder nén dữ liệu và tuôn thẳng tương lai 500 ngày mà không cần đệ quy lag_1.

* **Tiếp cận 1: Seq2Seq LSTM Native (Tự code chuẩn PyTorch Lightning)**
  * Bản chuẩn (Raw): Thu được `692k Combined MAE`. Model chạy 10s, bắt tín hiệu rất thô bản. Đánh bại XGB Baseline nhưng thua xa CatBoost.
  * Bản châm Decay (`recencyexp20`): Bơm trọng số giảm dần theo Recency vào trong L1Loss của LTSM. Kết quả sấp mặt (`712k MAE`). Lý do: LSTM khác với Trees, nó là cỗ máy ngốn Data khổng lồ. Exponential weight làm biến mất ảnh hưởng của 8 năm đầu (`2012-2020`), khiến LSTM bị đói data và underfit cục bộ. Khác với Cây Quyết Định (cần rất ít data để rẽ nhánh), Deep Learning không thể học tốt từ Time Series nhỏ hẹp.
* **Tiếp cận 2: Temporal Fusion Transformer (TFT) của PyTorch-Forecasting**
  * Sửa lỗi CUDA Deterministic Bug (`upsample_linear1d_backward`) khiến thư viện này chết từ những ngày trước.
  * Train 20 Epochs.
  * Bản Run 1 (20 Epochs): Revenue MAE 783k. Chạy 13 phút.
  * Bản Run 2 (100 Epochs, Patience=10): Revenue MAE 882k. Chạy 26.5 phút.
  * **Kết quả:** Train càng lâu, MAE càng TỆ ĐI (từ 783k rớt xuống 882k). Điều này chứng minh TFT đã bị **Overfit** vào kỷ nguyên cũ (2012-2020) và hoàn toàn gãy vụn khi đối mặt với regime shift của 2021-2022. Cỗ máy cồng kềnh thất bại thảm hại trước CatBoost.

## 4. Chốt Chặng Lịch Sử & Next Step
- Mọi mưu mô kiến trúc lớn (Horizon Routing, Recursive Pruning, Deep Learning, Calibration Post-processing) đều ngã ngựa trước thuật toán vô cùng nguyên thủy: **CatBoost Recursive + Recency Exponential Decay (Base 0.20)**. 
- Mức OOF Offline đạt đỉnh: 603k. Mức Public Leaderboard đạt đỉnh xác nhận: 896k.
- Bước kế tiếp: Chốt sổ mô hình. Tiến tới Tối Ưu Hóa Hypermameters của CatBoost (Grid Search) hoặc Xây Dựng Report Kỹ Thuật đúc kết những insight xương máu này.
