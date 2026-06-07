import streamlit as st
import numpy as np
from PIL import Image
import tifffile
import io
import os
import datetime
from utils import apply_custom_css

def convert_to_dng(input_image, apply_color_correction=False):
    # 画像をRGBで読み込み
    img = Image.open(input_image).convert('RGB')
    original_width, original_height = img.size

    # 16の倍数になるように新しいサイズを計算
    new_width = (original_width // 16) * 16
    new_height = (original_height // 16) * 16

    # クロップ（切り抜き）の開始位置と終了位置を計算（中央揃え）
    left = (original_width - new_width) // 2
    top = (original_height - new_height) // 2
    right = left + new_width
    bottom = top + new_height

    # 画像をクロップ
    img = img.crop((left, top, right, bottom))
    width, height = img.size # 新しいサイズを取得

    if apply_color_correction:
        #ガンマ解除
        img_float = np.array(img, dtype=np.float32) / 255.0
        img_linear = np.power(img_float, 2.2)
        img_array = np.clip(img_linear * 65535.0, 0, 65535).astype(np.uint16)
    else:
        img_array = np.array(img, dtype=np.uint16) << 8

    #ベイヤー配列擬似作成
    raw_pattern = np.zeros((height, width), dtype=np.uint16)
    raw_pattern[0::2, 0::2] = img_array[0::2, 0::2, 0] #R
    raw_pattern[0::2, 1::2] = img_array[0::2, 1::2, 1] #G
    raw_pattern[1::2, 0::2] = img_array[1::2, 0::2, 1] #G
    raw_pattern[1::2, 1::2] = img_array[1::2, 1::2, 2] #B

    dng_buffer = io.BytesIO()
    
    tags = [
        (259, 'H', 1, 1, False),                #Compression
        (262, 'H', 1, 32803, False),            #PhotometricInterpretation
        (33421, 'H', 2, [2, 2], False),         #CFARepeatPatternDim
        (33422, 'B', 4, [0, 1, 1, 2], False),   #CFAPattern
        (50706, 'B', 4, [1, 4, 0, 0], False),   #DNGVersion
    ]

    if apply_color_correction:
        #基準光源を印刷基準 (D50) に設定
        tags.append((50778, 'H', 1, 21, False))
        
        color_matrix = [
            31339, 10000, -16169, 10000, -4906, 10000,
            -9788, 10000,  19161, 10000,   335, 10000,
              719, 10000,  -2290, 10000, 14052, 10000
        ]
        tags.append((50721, 10, 9, color_matrix, False))
        
        tags.append((50728, 5, 3, [1, 1, 1, 1, 1, 1], False))

    with tifffile.TiffWriter(dng_buffer, imagej=False) as dng:
        dng.write(
            raw_pattern,
            photometric='cfa',
            extratags=tags,
            metadata=None
        )
    
    # DNGデータと一緒に、元のサイズとクロップ後のサイズを返す
    return dng_buffer.getvalue(), (original_width, original_height), (width, height)


st.set_page_config(layout="wide", page_title="DNG変換")
st.write("JPEGやPNGをアップロードして、RAW(.dng) 形式に変換します。")

try:
    apply_custom_css()
except NameError:
    pass

col1, col2 = st.columns([1, 2])

with col1:
    uploaded_file = st.file_uploader("画像を選択 または ドラッグ＆ドロップ", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.markdown("---")
        apply_correction = st.toggle("色調補正", value=True, help="ガンマ解除およびsRGB→DNG色調補正")

if uploaded_file is not None:
    with col2:
        st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)
    
    with col1:
        if st.button("DNGに変換・自動保存", use_container_width=True):
            with st.spinner("変換中..."):
                try:
                    # 戻り値を3つ受け取る
                    dng_data, orig_size, new_size = convert_to_dng(uploaded_file, apply_correction)
                
                    output_dir = os.path.join("output", "conversion")
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                
                    base_name = os.path.splitext(uploaded_file.name)[0]
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    new_filename = f"{base_name}_{timestamp}.dng"
                
                    save_path = os.path.join(output_dir, new_filename)
                
                    with open(save_path, "wb") as f:
                        f.write(dng_data)
                
                    st.success(f"保存完了:\n{new_filename}")

                    # クロップされた場合（サイズが変わった場合）のみ通知を表示
                    if orig_size != new_size:
                        st.info(
                            f"**画像の端を自動クロップしました**\n\n"
                            f"現像ソフトの読み込みエラーを防ぐため、16の倍数になるよう中央でトリミングしています。\n\n"
                            f"・元のサイズ: {orig_size[0]} × {orig_size[1]} px\n\n"
                            f"・変換サイズ: {new_size[0]} × {new_size[1]} px"
                        )
                
                    st.download_button(
                        label="パソコンにもダウンロード",
                        data=dng_data,
                        file_name=new_filename,
                        mime="image/x-adobe-dng",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"エラー: {e}")