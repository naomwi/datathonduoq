"""
Seq2Seq LSTM Sprint for Revenue/COGS Forecasting
An Encoder-Decoder model to overcome recursive error accumulation over long horizons.
Encoder reads 90 days of history. Decoder maps 500+ days into the future using only deterministic covariates.
Now with Exponential Recency Weighting injected into the Custom L1 Loss!
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import lightning as L
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import ensure_inputs, PROMO_RAW_COLUMNS, apply_future_promo_policy

RUN_PREFIX = "seq2seq_sprint_weighted"
SCREEN_FOLD = ("2021-01-01", "2022-07-02")
CALENDAR_COLS = [
    "sin_dayofyear", "cos_dayofyear", "sin_dayofweek", "cos_dayofweek", 
    "sin_month", "cos_month", "is_weekend", "is_month_start", "is_month_end"
]
TARGET_COLS = ["Revenue", "COGS"]

class RetailSeq2SeqDataset(Dataset):
    def __init__(self, data_df: pd.DataFrame, train_end_date: pd.Timestamp, enc_seq_len=90, dec_seq_len=180, is_train=True, weight_decay=0.20):
        self.df = data_df
        self.enc_seq_len = enc_seq_len
        self.dec_seq_len = dec_seq_len
        self.is_train = is_train
        self.weight_decay = weight_decay
        self.train_end_date = train_end_date
        
        self.target_data = self.df[TARGET_COLS].values
        self.enc_feat_data = self.df[TARGET_COLS + CALENDAR_COLS + PROMO_RAW_COLUMNS].values
        self.dec_feat_data = self.df[CALENDAR_COLS + PROMO_RAW_COLUMNS].values
        self.dates = pd.to_datetime(self.df["Date"]).values
        
        self.total_len = len(self.df)
        self.valid_starts = self.total_len - self.enc_seq_len - self.dec_seq_len + 1
        
    def __len__(self):
        return max(1, self.valid_starts if self.is_train else 1)
        
    def __getitem__(self, idx):
        if not self.is_train:
            enc_start = self.total_len - self.enc_seq_len - self.dec_seq_len
        else:
            enc_start = idx
            
        enc_end = enc_start + self.enc_seq_len
        dec_end = enc_end + self.dec_seq_len
        
        x_enc = self.enc_feat_data[enc_start:enc_end]
        x_dec = self.dec_feat_data[enc_end:dec_end]
        y_dec = self.target_data[enc_end:dec_end]
        
        # Calculate sample weight based on the forecast origin (enc_end - 1)
        origin_date = pd.Timestamp(self.dates[enc_end - 1])
        days_from_end = (self.train_end_date - origin_date).days
        years_from_end = max(0.0, days_from_end / 365.25)
        weight = np.exp(-self.weight_decay * years_from_end)
        
        return torch.FloatTensor(x_enc), torch.FloatTensor(x_dec), torch.FloatTensor(y_dec), torch.FloatTensor([weight])

class Seq2SeqRegressor(L.LightningModule):
    def __init__(self, enc_dim: int, dec_dim: int, hidden_dim=256, num_layers=2, lr=1e-3, target_scaler: StandardScaler = None):
        super().__init__()
        self.save_hyperparameters()
        self.lr = lr
        self.target_scaler = target_scaler
        
        self.encoder = nn.LSTM(enc_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        self.decoder = nn.LSTM(dec_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.GELU(),
            nn.Linear(128, 2)
        )
        
    def forward(self, x_enc, x_dec):
        _, (h_n, c_n) = self.encoder(x_enc)
        dec_out, _ = self.decoder(x_dec, (h_n, c_n))
        return self.fc(dec_out)
        
    def training_step(self, batch, batch_idx):
        x_enc, x_dec, y_dec, weight = batch
        y_hat = self(x_enc, x_dec)
        
        # Weighted L1 Loss
        l1 = torch.abs(y_hat - y_dec) # (batch, seq, 2)
        weighted_l1 = l1 * weight.view(-1, 1, 1) # broadcast weight across sequence and targets
        loss = weighted_l1.mean()
        
        self.log("train_loss", loss, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx):
        x_enc, x_dec, y_dec, weight = batch
        y_hat = self(x_enc, x_dec)
        loss = torch.abs(y_hat - y_dec).mean() # standard unweighted validation loss
        self.log("val_loss", loss, prog_bar=True)
        return loss

    def configure_optimizers(self):
        # Add OneCycleLR for faster convergence and better local minima
        optimizer = torch.optim.AdamW(self.parameters(), lr=self.lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer, max_lr=self.lr, total_steps=self.trainer.estimated_stepping_batches
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {"scheduler": scheduler, "interval": "step"}
        }

    def inverse_transform_targets(self, targets: torch.Tensor) -> np.ndarray:
        if self.target_scaler is None:
            return targets.cpu().numpy()
        shape = targets.shape
        flat = targets.cpu().numpy().reshape(-1, 2)
        inv = self.target_scaler.inverse_transform(flat)
        return inv.reshape(shape)

def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Initializing Weighted Seq2Seq LSTM offline evaluation...")

    feature_store, base = ensure_inputs()
    
    start_ts = pd.Timestamp(SCREEN_FOLD[0])
    end_ts = pd.Timestamp(SCREEN_FOLD[1])
    cutoff = start_ts - pd.Timedelta(days=1)
    
    adjusted_base = apply_future_promo_policy(base, cutoff, "seasonal_month_day_recent_2y")
    
    full_df = feature_store[["Date"] + TARGET_COLS + CALENDAR_COLS].copy()
    full_df = full_df.merge(adjusted_base[["Date"] + PROMO_RAW_COLUMNS], on="Date", how="inner")
    full_df = full_df.sort_values("Date").reset_index(drop=True)
    
    train_mask = full_df["Date"] <= cutoff
    
    # Fit normalizers on train only
    target_scaler = StandardScaler()
    feat_scaler = StandardScaler()
    feature_cols = TARGET_COLS + CALENDAR_COLS + PROMO_RAW_COLUMNS
    
    train_slice = full_df.loc[train_mask].copy()
    target_scaler.fit(train_slice[TARGET_COLS])
    feat_scaler.fit(train_slice[feature_cols])
    
    normalized_df = full_df.copy()
    normalized_df[feature_cols] = feat_scaler.transform(full_df[feature_cols])
    normalized_df[TARGET_COLS] = target_scaler.transform(full_df[TARGET_COLS])
    
    enc_seq_len = 90
    prediction_length = int((end_ts - start_ts).days + 1)
    train_dec_seq_len = 180 

    train_dataset = RetailSeq2SeqDataset(normalized_df[train_mask], train_end_date=cutoff, enc_seq_len=enc_seq_len, dec_seq_len=train_dec_seq_len, is_train=True, weight_decay=0.20)
    # the val_mask goes exactly up to prediction_length
    val_mask = full_df["Date"] <= end_ts
    val_dataset = RetailSeq2SeqDataset(normalized_df[val_mask], train_end_date=cutoff, enc_seq_len=enc_seq_len, dec_seq_len=prediction_length, is_train=False)

    logger.info(f"Train samples: {len(train_dataset)}, Horizon: {prediction_length}")
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False, num_workers=0)

    enc_dim = len(TARGET_COLS + CALENDAR_COLS + PROMO_RAW_COLUMNS)
    dec_dim = len(CALENDAR_COLS + PROMO_RAW_COLUMNS)
    
    # Note: Using larger hidden dim and LR
    model = Seq2SeqRegressor(enc_dim=enc_dim, dec_dim=dec_dim, hidden_dim=256, num_layers=2, lr=3e-3, target_scaler=target_scaler)
    
    checkpoint_callback = ModelCheckpoint(
        dirpath=str(run_dir),
        filename="best_model",
        save_top_k=1,
        monitor="val_loss",
        mode="min"
    )
    early_stop = EarlyStopping(monitor="val_loss", min_delta=1e-4, patience=15, mode="min")
    
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.use_deterministic_algorithms(False)
    L.seed_everything(42, workers=False)
    
    trainer = L.Trainer(
        max_epochs=100,
        accelerator="gpu" if torch.cuda.is_available() else "cpu",
        devices=1,
        callbacks=[early_stop, checkpoint_callback],
        enable_progress_bar=False,
    )
    
    logger.info("Training Weighted LSTM...")
    trainer.fit(model, train_loader, val_loader)
    
    # Load best checkpoint automatically applied by model checkpoint if required, but early stopping handles val well
    # Just running evaluating
    logger.info("Evaluating on Fold 2021-2022...")
    model.eval()
    with torch.no_grad():
        x_enc, x_dec, y_true, _ = next(iter(val_loader))
        if torch.cuda.is_available():
            x_enc, x_dec = x_enc.cuda(), x_dec.cuda()
            model = model.cuda()
            
        y_pred = model(x_enc, x_dec)
        
    y_pred_inv = model.inverse_transform_targets(y_pred)
    y_true_inv = model.inverse_transform_targets(y_true)
    
    rev_pred = np.maximum(y_pred_inv[0, :, 0], 0.0)
    cogs_pred = np.maximum(y_pred_inv[0, :, 1], 0.0)
    rev_true = y_true_inv[0, :, 0]
    cogs_true = y_true_inv[0, :, 1]
    
    rev_mae = mean_absolute_error(rev_true, rev_pred)
    cogs_mae = mean_absolute_error(cogs_true, cogs_pred)
    comb_mae = (rev_mae + cogs_mae) / 2.0
    rev_r2 = r2_score(rev_true, rev_pred)
    
    logger.info(f"Test Result -> Combined MAE: {comb_mae:,.2f} | Rev MAE: {rev_mae:,.2f} | Rev R2: {rev_r2:.3f}")
    
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Seq2Seq LSTM Sprint (Weighted)\n\n")
        f.write(f"- Fold: {SCREEN_FOLD[0]} to {SCREEN_FOLD[1]}\n")
        f.write(f"- Network: 2-Layer LSTM (Hidden=256)\n")
        f.write(f"- Sample weights: recency decay 0.20\n\n")
        f.write("## Results\n")
        f.write(f"- Combined MAE: **{comb_mae:,.2f}**\n")
        f.write(f"- Revenue MAE: **{rev_mae:,.2f}**\n")
        f.write(f"- COGS MAE: **{cogs_mae:,.2f}**\n")
        f.write(f"- Revenue R2: **{rev_r2:.3f}**\n")

if __name__ == "__main__":
    main()
