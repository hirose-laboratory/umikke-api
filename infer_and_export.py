import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from datetime import date, datetime, timedelta
from PIL import Image
import matplotlib.pyplot as plt
from torchvision import transforms

import schemas

# ディレクトリおよびパスの設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 入力ファイルのパス設定
MODEL_PATH = os.path.join(BASE_DIR, "convlstm_op_final.pth")
MASK_FILE_PATH = os.path.join(BASE_DIR, "mask_blacked.png")

# 出力先ディレクトリの作成
OUT_IMG_DIR = os.path.join(BASE_DIR, "images", "edna")
OUT_CSV_DIR = os.path.join(BASE_DIR, "CSV", "edna")
os.makedirs(OUT_IMG_DIR, exist_ok=True)
os.makedirs(OUT_CSV_DIR, exist_ok=True)

# 推論に必要なパラメータの設定
IMG_SIZE = 128
SEQ_IN = 14
SEQ_OUT = 60
FISH_ID = 1  # 対象の魚種ID

# 対象海域の緯度・経度範囲
LAT_MIN, LAT_MAX = 34.22306, 34.37134
LON_MIN, LON_MAX = 136.64863, 136.95686

# 実行デバイスの設定
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ConvLSTMのセル定義
class ConvLSTMCell(nn.Module):
    def __init__(self, input_dim, hidden_dim, kernel_size, bias):
        super(ConvLSTMCell, self).__init__()
        self.hidden_dim = hidden_dim
        padding = kernel_size[0] // 2, kernel_size[1] // 2
        self.conv = nn.Conv2d(in_channels=input_dim + hidden_dim, out_channels=4 * hidden_dim, kernel_size=kernel_size, padding=padding, bias=bias)

    def forward(self, input_tensor, cur_state):
        h_cur, c_cur = cur_state
        # 入力と現在の隠れ状態を結合
        combined = torch.cat([input_tensor, h_cur], dim=1)
        # 畳み込み演算によるゲート計算
        cc_i, cc_f, cc_o, cc_g = torch.split(self.conv(combined), self.hidden_dim, dim=1)
        # 次のセル状態と隠れ状態の計算
        c_next = torch.sigmoid(cc_f) * c_cur + torch.sigmoid(cc_i) * torch.tanh(cc_g)
        h_next = torch.sigmoid(cc_o) * torch.tanh(c_next)
        return h_next, c_next

# Seq2Seq型ConvLSTMモデルの定義
class OperationalSeq2SeqConvLSTM(nn.Module):
    def __init__(self, env_channels=9, label_channels=3, hidden_channels=[64, 32]):
        super(OperationalSeq2SeqConvLSTM, self).__init__()
        # エンコーダ（過去データの入力）
        self.enc1 = ConvLSTMCell(env_channels, hidden_channels[0], (3, 3), True)
        self.enc2 = ConvLSTMCell(hidden_channels[0], hidden_channels[1], (3, 3), True)
        # デコーダ（未来データの予測）
        self.dec1 = ConvLSTMCell(label_channels, hidden_channels[0], (3, 3), True)
        self.dec2 = ConvLSTMCell(hidden_channels[0], hidden_channels[1], (3, 3), True)
        self.final_conv = nn.Conv2d(hidden_channels[1], label_channels, kernel_size=1)
        self.hidden_channels = hidden_channels

    def forward(self, env_inputs, future_steps=60):
        b, seq_in, _, h, w = env_inputs.size()
        h1, c1 = self._init_hidden(b, self.hidden_channels[0], h, w)
        h2, c2 = self._init_hidden(b, self.hidden_channels[1], h, w)
        
        # エンコード処理
        for t in range(seq_in):
            h1, c1 = self.enc1(env_inputs[:, t, :, :, :], (h1, c1))
            h2, c2 = self.enc2(h1, (h2, c2))
            
        pred_label = torch.sigmoid(self.final_conv(h2) * 1.5)
        outputs = []
        
        # デコード処理（予測ステップ数分繰り返す）
        for t in range(future_steps):
            outputs.append(pred_label)
            next_input = pred_label
            if t < future_steps - 1:
                h1, c1 = self.dec1(next_input, (h1, c1))
                h2, c2 = self.dec2(h1, (h2, c2))
                pred_label = torch.sigmoid(self.final_conv(h2) * 1.5)
                
        return torch.stack(outputs, dim=1)

    def _init_hidden(self, batch_size, hidden_dim, h, w):
        return (torch.zeros(batch_size, hidden_dim, h, w, device=DEVICE),
                torch.zeros(batch_size, hidden_dim, h, w, device=DEVICE))

# 画像をテンソルとして読み込む関数
def load_img_tensor(path):
    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor()
    ])
    if os.path.exists(path):
        return transform(Image.open(path).convert("RGB"))
    return torch.zeros((3, IMG_SIZE, IMG_SIZE))

# 推論用の入力データを準備する関数
def prepare_input_data(base_time: datetime):
    # 基準日から過去方向（SEQ_IN日分）のデータを取得
    target_date_obj = base_time.date()
    env_frames = []
    
    for i in range(SEQ_IN, 0, -1):
        target_date = target_date_obj - timedelta(days=i)
        d_str = target_date.strftime("%Y%m%d")
        
        sst_p = os.path.join(BASE_DIR, "images", "sst", f"sst_{d_str}.png")
        chl_p = os.path.join(BASE_DIR, "images", "chl", f"chl_{d_str}.png")
        par_p = os.path.join(BASE_DIR, "images", "par", f"par_{d_str}.png")
        
        sst, chl, par = load_img_tensor(sst_p), load_img_tensor(chl_p), load_img_tensor(par_p)
        env_frames.append(torch.cat([sst, chl, par], dim=0))
        
    return torch.stack(env_frames).unsqueeze(0).to(DEVICE)

# 推論実行および結果ファイル出力のメイン関数
def run_inference_and_export(base_time: datetime = None):
    if base_time is None:
        base_time = datetime.now()

    # モデルの存在確認とロード
    if not os.path.exists(MODEL_PATH):
        print(f"Error: モデルファイルが見つかりません: {MODEL_PATH}")
        return

    model = OperationalSeq2SeqConvLSTM().to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()

    # 陸地マスク画像のロード（海域のみを対象とするため）
    if os.path.exists(MASK_FILE_PATH):
        mask_img = Image.open(MASK_FILE_PATH).convert("L")
        mask_np = np.array(mask_img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.NEAREST))
        sea_mask = (mask_np < 128)
    else:
        sea_mask = np.ones((IMG_SIZE, IMG_SIZE), dtype=bool)

    # 推論の実行
    input_tensor = prepare_input_data(base_time)
    with torch.no_grad():
        preds = model(input_tensor, future_steps=SEQ_OUT).squeeze(0).cpu().numpy()

    target_date_obj = base_time.date()
    lats = np.linspace(LAT_MAX, LAT_MIN, IMG_SIZE)
    lons = np.linspace(LON_MIN, LON_MAX, IMG_SIZE)

    # 予測結果を日ごとに画像とCSVファイルとして出力
    for step in range(SEQ_OUT):
        target_date = target_date_obj + timedelta(days=step)
        dt_str = target_date.strftime("%Y%m%d")
        ts_str = f"{target_date.strftime('%Y-%m-%d')} 12:00:00"

        heatmap_matrix = preds[step, 0, :, :]
        # 陸地部分の値を0にマスク処理
        heatmap_matrix[~sea_mask] = 0.0

        # 画像出力
        img_path = os.path.join(OUT_IMG_DIR, f"edna_{dt_str}.png")
        plt.figure(figsize=(4, 4))
        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        plt.axis("off")
        plt.imshow(heatmap_matrix, cmap="hot", vmin=0, vmax=1)
        plt.savefig(img_path, bbox_inches="tight", pad_inches=0, dpi=100)
        plt.close()

        # CSVデータ作成
        records = []
        for r in range(IMG_SIZE):
            for c in range(IMG_SIZE):
                if sea_mask[r, c]:
                    val = float(heatmap_matrix[r, c])
                    records.append({
                        "fish_id": FISH_ID,
                        "latitude": round(float(lats[r]), 6),
                        "longitude": round(float(lons[c]), 6),
                        "target_timestamp": ts_str,
                        "heatmap_value": round(val, 4)
                    })

        # バリデーション後、データフレームに変換してCSV保存
        validated_records = [schemas.EDNAPredictionBase(**rec).model_dump() for rec in records]
        df = pd.DataFrame(validated_records)
        
        csv_path = os.path.join(OUT_CSV_DIR, f"edna_{dt_str}.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8")

if __name__ == "__main__":
    run_inference_and_export()
