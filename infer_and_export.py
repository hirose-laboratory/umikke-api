import os
import glob
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from datetime import date, datetime, timedelta, timezone
from PIL import Image
import matplotlib.pyplot as plt
from torchvision import transforms

# ==================== 基本設定 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")
MASK_FILE_PATH = os.path.join(BASE_DIR, "mask_blacked.png")
MODEL_PATH = os.path.join(BASE_DIR, "convlstm_op_final.pth")

OUT_IMG_DIR = os.path.join(IMAGE_DIR, "edna")
OUT_CSV_DIR = os.path.join(BASE_DIR, "CSV", "edna")
os.makedirs(OUT_IMG_DIR, exist_ok=True)
os.makedirs(OUT_CSV_DIR, exist_ok=True)

IMG_SIZE = 128
SEQ_IN = 5
SEQ_OUT = 60
FISH_ID = 1  # カタクチイワシ

LAT_MIN, LAT_MAX = 34.22306, 34.37134
LON_MIN, LON_MAX = 136.64863, 136.95686

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==================== モデル定義 ====================
class ConvLSTMCell(nn.Module):
    def __init__(self, input_dim, hidden_dim, kernel_size, bias):
        super(ConvLSTMCell, self).__init__()
        self.hidden_dim = hidden_dim
        padding = kernel_size[0] // 2, kernel_size[1] // 2
        self.conv = nn.Conv2d(in_channels=input_dim + hidden_dim, out_channels=4 * hidden_dim, kernel_size=kernel_size, padding=padding, bias=bias)

    def forward(self, input_tensor, cur_state):
        h_cur, c_cur = cur_state
        combined = torch.cat([input_tensor, h_cur], dim=1)
        cc_i, cc_f, cc_o, cc_g = torch.split(self.conv(combined), self.hidden_dim, dim=1)
        c_next = torch.sigmoid(cc_f) * c_cur + torch.sigmoid(cc_i) * torch.tanh(cc_g)
        h_next = torch.sigmoid(cc_o) * torch.tanh(c_next)
        return h_next, c_next

class OperationalSeq2SeqConvLSTM(nn.Module):
    def __init__(self, env_channels=9, label_channels=3, hidden_channels=[64, 32]):
        super(OperationalSeq2SeqConvLSTM, self).__init__()
        self.enc1 = ConvLSTMCell(env_channels, hidden_channels[0], (3, 3), True)
        self.enc2 = ConvLSTMCell(hidden_channels[0], hidden_channels[1], (3, 3), True)
        self.dec1 = ConvLSTMCell(label_channels, hidden_channels[0], (3, 3), True)
        self.dec2 = ConvLSTMCell(hidden_channels[0], hidden_channels[1], (3, 3), True)
        self.final_conv = nn.Conv2d(hidden_channels[1], label_channels, kernel_size=1)
        self.hidden_channels = hidden_channels

    def forward(self, env_inputs, future_steps=60):
        b, seq_in, _, h, w = env_inputs.size()
        h1, c1 = self._init_hidden(b, self.hidden_channels[0], h, w)
        h2, c2 = self._init_hidden(b, self.hidden_channels[1], h, w)
        
        for t in range(seq_in):
            h1, c1 = self.enc1(env_inputs[:, t, :, :, :], (h1, c1))
            h2, c2 = self.enc2(h1, (h2, c2))
            
        pred_label = torch.sigmoid(self.final_conv(h2) * 1.5)
        outputs = []
        
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

# ==================== データ準備関数 ====================
def load_img_tensor(path):
    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor()
    ])
    if os.path.exists(path):
        return transform(Image.open(path).convert("RGB"))
    return torch.zeros((3, IMG_SIZE, IMG_SIZE))

def prepare_input_data():
    today = date.today()
    env_frames = []
    
    for i in range(SEQ_IN, 0, -1):
        target_date = today - timedelta(days=i)
        d_str = target_date.strftime("%Y%m%d")
        
        sst_p = os.path.join(IMAGE_DIR, "sst", f"sst_{d_str}.png")
        chl_p = os.path.join(IMAGE_DIR, "chl", f"chl_{d_str}.png")
        par_p = os.path.join(IMAGE_DIR, "par", f"par_{d_str}.png")
        
        sst, chl, par = load_img_tensor(sst_p), load_img_tensor(chl_p), load_img_tensor(par_p)
        env_frames.append(torch.cat([sst, chl, par], dim=0))
        
    return torch.stack(env_frames).unsqueeze(0).to(DEVICE) # (1, 5, 9, H, W)

# ==================== メイン推論処理 ====================
def run_inference():
    print("🔮 推論処理を開始します...")
    model = OperationalSeq2SeqConvLSTM().to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()
    
    # 陸地マスク準備
    if os.path.exists(MASK_FILE_PATH):
        mask_img = Image.open(MASK_FILE_PATH).convert("L")
        mask_np = np.array(mask_img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.NEAREST))
        sea_mask = (mask_np < 128)  # 海域: True, 陸地: False
    else:
        sea_mask = np.ones((IMG_SIZE, IMG_SIZE), dtype=bool)

    input_tensor = prepare_input_data()
    
    with torch.no_grad():
        preds = model(input_tensor, future_steps=SEQ_OUT).squeeze(0).cpu().numpy() # (60, 3, 128, 128)

    today = date.today()
    lats = np.linspace(LAT_MAX, LAT_MIN, IMG_SIZE)
    lons = np.linspace(LON_MIN, LON_MAX, IMG_SIZE)

    for step in range(SEQ_OUT):
        target_date = today + timedelta(days=step)
        dt_str = target_date.strftime("%Y%m%d")
        ts_str = f"{target_date.strftime('%Y-%m-%d')} 12:00:00"
        
        # 1. 予測ヒートマップ値の抽出（赤チャンネルを魚の密度指標とし0.0~1.0正規化）
        heatmap_matrix = preds[step, 0, :, :] # (128, 128)
        heatmap_matrix[~sea_mask] = 0.0
        
        # 2. 画像の保存
        img_out_path = os.path.join(OUT_IMG_DIR, f"edna_{dt_str}.png")
        plt.figure(figsize=(4, 4))
        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        plt.axis("off")
        plt.imshow(heatmap_matrix, cmap="hot", vmin=0, vmax=1)
        plt.savefig(img_out_path, bbox_inches='tight', pad_inches=0, dpi=100)
        plt.close()

        # 3. CSV出力（座標逆算＆1-0正規化データ）
        records = []
        for r in range(IMG_SIZE):
            for c in range(IMG_SIZE):
                if sea_mask[r, c]:
                    val = round(float(heatmap_matrix[r, c]), 4)
                    if val > 0.01: # 超軽量化のため極小値はカット（全グリッド保存時は判定解除）
                        records.append({
                            "fish_id": FISH_ID,
                            "latitude": round(float(lats[r]), 6),
                            "longitude": round(float(lons[c]), 6),
                            "target_timestamp": ts_str,
                            "heatmap_value": val
                        })

        df = pd.DataFrame(records)
        csv_out_path = os.path.join(OUT_CSV_DIR, f"edna_{dt_str}.csv")
        df.to_csv(csv_out_path, index=False)
        print(f"✅ 保存完了 [{step+1}/{SEQ_OUT}]: {dt_str} -> {csv_out_path}")

if __name__ == "__main__":
    run_inference()
