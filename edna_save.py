import argparse
import os
from datetime import datetime
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import schemas

# ベースディレクトリとデフォルトの入出力先パスを設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_DIR = os.path.join(BASE_DIR, "CSV", "edna")
DEFAULT_IMG_DIR = os.path.join(BASE_DIR, "images", "edna")

# 出力先ディレクトリが存在しない場合は作成
os.makedirs(DEFAULT_CSV_DIR, exist_ok=True)
os.makedirs(DEFAULT_IMG_DIR, exist_ok=True)

# 対象エリアの緯度経度の範囲
LAT_MIN, LAT_MAX = 34.22306, 34.37134
LON_MIN, LON_MAX = 136.64863, 136.95686


def normalize_values(values: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    配列内の数値を0.0から1.0の範囲にスケーリングする
    マスクが指定されている場合は、対象外の領域を除外して計算を行う
    """
    result = values.copy().astype(np.float64)

    if mask is not None:
        target_vals = result[mask]
    else:
        target_vals = result

    # データが空の場合はそのまま返す
    if len(target_vals) == 0:
        return result

    val_min = np.nanmin(target_vals)
    val_max = np.nanmax(target_vals)

    # 最小値と最大値に差がある場合のみ正規化を実行
    if val_max > val_min:
        if mask is not None:
            result[mask] = (result[mask] - val_min) / (val_max - val_min)
            result[~mask] = 0.0
        else:
            result = (result - val_min) / (val_max - val_min)
    else:
        # 値に変化がない場合は中間値（0.5）を設定
        if mask is not None:
            result[mask] = 0.5
            result[~mask] = 0.0

    return result


def export_edna_prediction_matrix_to_csv(
    heatmap_matrix: np.ndarray,
    fish_id: int,
    target_timestamp: datetime,
    output_filename: Optional[str] = None,
    sea_mask: Optional[np.ndarray] = None,
    normalize: bool = True,
    save_image: bool = True,
    csv_dir: str = DEFAULT_CSV_DIR,
    img_dir: str = DEFAULT_IMG_DIR
) -> Tuple[str, Optional[str]]:
    """
    推論結果の2次元配列を正規化し、CSVおよび画像ファイルとして出力する
    """
    h, w = heatmap_matrix.shape
    lats = np.linspace(LAT_MAX, LAT_MIN, h)
    lons = np.linspace(LON_MIN, LON_MAX, w)

    # 正規化処理と海域マスクの適用
    proc_matrix = normalize_values(heatmap_matrix, sea_mask) if normalize else heatmap_matrix.copy()
    if sea_mask is not None:
        proc_matrix[~sea_mask] = 0.0

    ts_str = target_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    dt_str = target_timestamp.strftime("%Y%m%d")

    # CSV出力用のデータレコードを作成
    records = []
    for r in range(h):
        for c in range(w):
            # 陸地部分はデータから除外
            if sea_mask is not None and not sea_mask[r, c]:
                continue

            val = float(proc_matrix[r, c])
            records.append({
                "fish_id": fish_id,
                "latitude": round(float(lats[r]), 6),
                "longitude": round(float(lons[c]), 6),
                "target_timestamp": ts_str,
                "heatmap_value": round(val, 4)
            })

    # スキーマ検証を実行しデータフレームに変換
    validated_data = [schemas.EDNAPredictionBase(**rec).model_dump() for rec in records]
    df = pd.DataFrame(validated_data)

    # 出力ファイル名を設定
    if not output_filename:
        output_filename = f"edna_pred_{fish_id}_{dt_str}.csv"
    
    if not output_filename.endswith(".csv"):
        output_filename += ".csv"

    # CSVファイルの上書き保存
    os.makedirs(csv_dir, exist_ok=True)
    csv_path = os.path.join(csv_dir, output_filename)
    df.to_csv(csv_path, index=False, encoding="utf-8", mode="w")

    # 必要に応じてヒートマップ画像を生成し保存
    img_path = None
    if save_image:
        os.makedirs(img_dir, exist_ok=True)
        img_name = output_filename.replace(".csv", ".png")
        img_path = os.path.join(img_dir, img_name)

        plt.figure(figsize=(5, 5))
        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        plt.axis("off")
        plt.imshow(proc_matrix, cmap="hot", vmin=0.0, vmax=1.0)
        plt.savefig(img_path, bbox_inches="tight", pad_inches=0, dpi=100)
        plt.close()

    return csv_path, img_path


def clean_and_overwrite_existing_csv(
    csv_path: str,
    normalize: bool = True,
    save_image: bool = True,
    img_dir: str = DEFAULT_IMG_DIR
) -> str:
    """
    既存のCSVファイルを読み込み、値の正規化やフォーマットの整形を行って上書きする
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"対象のCSVファイルが見つかりません: {csv_path}")

    df = pd.read_csv(csv_path)
    required_cols = {"fish_id", "latitude", "longitude", "target_timestamp", "heatmap_value"}
    
    # 必須カラムの存在確認
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSVのカラム構成が正しくありません: {csv_path}")

    if df.empty:
        return csv_path

    # 値の正規化
    if normalize:
        vals = df["heatmap_value"].values
        df["heatmap_value"] = np.round(normalize_values(vals), 4)

    # 座標の小数点桁数を統一
    df["latitude"] = df["latitude"].round(6)
    df["longitude"] = df["longitude"].round(6)

    # スキーマの再検証
    records = df.to_dict(orient="records")
    validated_records = [schemas.EDNAPredictionBase(**rec).model_dump() for rec in records]
    clean_df = pd.DataFrame(validated_records)

    # ファイルの上書き保存
    clean_df.to_csv(csv_path, index=False, encoding="utf-8", mode="w")

    # 画像の生成と保存
    if save_image:
        os.makedirs(img_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(csv_path))[0]
        img_path = os.path.join(img_dir, f"{base_name}.png")

        try:
            # 緯度と経度に基づいて2次元グリッドに変換
            grid = clean_df.pivot(index="latitude", columns="longitude", values="heatmap_value").values
            grid = np.flipud(grid) # 緯度が高い順になるように上下を反転
            plt.figure(figsize=(5, 5))
            plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
            plt.axis("off")
            plt.imshow(grid, cmap="hot", vmin=0.0, vmax=1.0)
            plt.savefig(img_path, bbox_inches="tight", pad_inches=0, dpi=100)
            plt.close()
        except Exception:
            # 座標がグリッド状に整っていない場合は画像生成をスキップ
            pass

    return csv_path


def clean_and_overwrite_all_in_dir(
    csv_dir: str = DEFAULT_CSV_DIR,
    img_dir: str = DEFAULT_IMG_DIR,
    normalize: bool = True,
    save_image: bool = True
) -> int:
    """
    指定ディレクトリ内のすべてのCSVファイルに対して一括で整形・上書き処理を実行する
    """
    if not os.path.exists(csv_dir):
        return 0

    csv_files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    if not csv_files:
        return 0

    count = 0
    for filename in sorted(csv_files):
        csv_path = os.path.join(csv_dir, filename)
        try:
            clean_and_overwrite_existing_csv(
                csv_path=csv_path,
                normalize=normalize,
                save_image=save_image,
                img_dir=img_dir
            )
            count += 1
        except Exception:
            pass

    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="eDNA 予測データのクリーンアップおよび上書き保存処理")
    parser.add_argument("--csv_dir", type=str, default=DEFAULT_CSV_DIR, help="対象CSVディレクトリ")
    parser.add_argument("--img_dir", type=str, default=DEFAULT_IMG_DIR, help="出力画像ディレクトリ")
    parser.add_argument("--no_normalize", action="store_true", help="正規化を行わずにそのまま上書きする場合に指定")
    parser.add_argument("--no_image", action="store_true", help="画像を生成しない場合に指定")

    args = parser.parse_args()

    clean_and_overwrite_all_in_dir(
        csv_dir=args.csv_dir,
        img_dir=args.img_dir,
        normalize=not args.no_normalize,
        save_image=not args.no_image
    )
