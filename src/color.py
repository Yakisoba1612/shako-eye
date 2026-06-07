import io
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import os
from datetime import datetime
import japanize_matplotlib

st.set_page_config(page_title="Visible Spectrum Simulator", layout="wide")
st.title("Visible Spectrum Simulator")

base_dir = os.path.dirname(os.path.abspath(__file__))
target_dir = os.path.normpath(os.path.join(base_dir, 'csv', 'color'))
output_dir = os.path.normpath(os.path.join(os.path.dirname(base_dir), 'output', 'color'))

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
save_filename = f"{timestamp}_color.png"

# サイドバー展開状態の初期化
if "expand_all" not in st.session_state:
    st.session_state.expand_all = True

def set_expand_state(state):
    st.session_state.expand_all = state

# サイドバー：ファイル選択
with st.sidebar.expander("ファイル選択", expanded=st.session_state.expand_all):
    if os.path.exists(target_dir):
        csv_files = [f for f in os.listdir(target_dir) if f.endswith('.csv')]
        if csv_files:
            selected_filename = st.selectbox("読み込むCSVファイル", csv_files)
            csv_path = os.path.join(target_dir, selected_filename)
        else:
            st.error("csv/color ディレクトリ内にCSVファイルが見つかりません。")
            csv_path = None
    else:
        st.error(f"ディレクトリが見つかりません: {target_dir}")
        csv_path = None

# サイドバー：表示・非表示設定
with st.sidebar.expander("表示・非表示設定", expanded=st.session_state.expand_all):
    show_title = st.checkbox("グラフタイトルを表示", value=True)
    show_xlabel = st.checkbox("横軸ラベルを表示", value=True)
    show_xticks = st.checkbox("目盛り数値を表示", value=True)

# サイドバー：カラー設定
with st.sidebar.expander("カラー設定", expanded=st.session_state.expand_all):
    bg_color = st.color_picker("背景色", value="#FFFFFF")
    text_color = st.color_picker("文字色（枠線含む）", value="#000000")

# サイドバー：表示範囲設定
with st.sidebar.expander("表示範囲設定", expanded=st.session_state.expand_all):
    disp_lower = st.number_input("表示範囲下限 (nm)", min_value=360, max_value=830, value=360, step=1)
    disp_upper = st.number_input("表示範囲上限 (nm)", min_value=360, max_value=830, value=830, step=1)

# サイドバー：横軸目盛り設定
with st.sidebar.expander("横軸目盛り設定", expanded=st.session_state.expand_all):
    tick_start = st.number_input("目盛り開始波長 (nm)", min_value=360, max_value=830, value=400, step=1)
    tick_end = st.number_input("目盛り終了波長 (nm)", min_value=360, max_value=830, value=800, step=1)
    tick_step = st.number_input("目盛り間隔 (nm)", min_value=1, max_value=200, value=50, step=1)

# サイドバー：ラベル・フォント設定
with st.sidebar.expander("ラベル・フォント設定", expanded=st.session_state.expand_all):
    plot_title = st.text_input("グラフタイトル", value="可視光スペクトル")
    title_size = st.slider("タイトル文字サイズ", min_value=5, max_value=30, value=14)
    xlabel_text = st.text_input("横軸ラベル", value="波長 (nm)")
    xlabel_size = st.slider("軸ラベル文字サイズ", min_value=5, max_value=30, value=12)
    xtick_size = st.slider("目盛り数値サイズ", min_value=5, max_value=100, value=10)

# サイドバー：キャンバスサイズ
with st.sidebar.expander("キャンバスサイズ（アスペクト比）", expanded=st.session_state.expand_all):
    width_px = st.number_input("画像の横幅 (px)", min_value=100, max_value=5000, value=1200, step=10)
    height_px = st.number_input("画像の高さ (px)", min_value=100, max_value=5000, value=400, step=10)

# サイドバー：余白調整
with st.sidebar.expander("余白調整 (0.0〜1.0)", expanded=st.session_state.expand_all):
    margin_right = st.slider("右余白", 0.5, 1.0, 0.95, 0.01)
    margin_left = st.slider("左余白", 0.0, 0.5, 0.1, 0.01)
    margin_top = st.slider("上余白", 0.5, 1.0, 0.85, 0.01)
    margin_bottom = st.slider("下余白", 0.0, 0.5, 0.2, 0.01)

# メイン処理
if csv_path and os.path.exists(csv_path):
    if disp_lower >= disp_upper:
        st.error("表示範囲の下限は上限より小さい値を設定してください。")
    elif tick_start > tick_end:
        st.error("目盛りの開始波長は終了波長以下の値を設定してください。")
    else:
        try:
            df = pd.read_csv(csv_path)
            hex_col = 'HEX'
            if hex_col not in df.columns:
                st.error(f"CSVに '{hex_col}' カラムがありません。")
            else:
                hex_colors = df[hex_col].dropna().astype(str).tolist()
                hex_colors = [c if c.startswith('#') else f"#{c}" for c in hex_colors]
                csv_start_wl = 360
                start_idx = max(0, disp_lower - csv_start_wl)
                end_idx = min(len(hex_colors), disp_upper - csv_start_wl + 1)
                sliced_colors = hex_colors[start_idx:end_idx]
                
                if len(sliced_colors) < 2:
                    st.warning("範囲内のカラーデータが不足しています。")
                else:
                    n_colors = len(sliced_colors)
                    cmap = mcolors.LinearSegmentedColormap.from_list("custom", sliced_colors, N=n_colors)
                    gradient = np.linspace(0, 1, n_colors).reshape(1, -1)
                    
                    display_dpi = 100
                    fig_w = width_px / display_dpi
                    fig_h = height_px / display_dpi
                    
                    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=display_dpi)
                    fig.patch.set_facecolor(bg_color)
                    ax.set_facecolor(bg_color)
                    
                    fig.subplots_adjust(left=margin_left, right=margin_right, bottom=margin_bottom, top=margin_top)
                    
                    ax.imshow(gradient, aspect='auto', cmap=cmap, extent=[disp_lower - 0.5, disp_upper + 0.5, 0, 1], interpolation='nearest')
                    ax.set_yticks([])
                    ax.set_xticks(np.arange(tick_start, tick_end + 1, tick_step))
                    
                    for spine in ax.spines.values():
                        spine.set_color(text_color)
                    
                    if show_title:
                        ax.set_title(plot_title, fontsize=title_size, color=text_color)
                    if show_xlabel:
                        ax.set_xlabel(xlabel_text, fontsize=xlabel_size, color=text_color)
                    if show_xticks:
                        ax.tick_params(axis='x', colors=text_color, labelsize=xtick_size)
                    else:
                        ax.set_xticklabels([])
                        ax.tick_params(axis='x', length=0)
                        
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=display_dpi, facecolor=fig.get_facecolor(), bbox_inches=None)
                    st.image(buf, use_container_width=False)

                    # 画像保存セクション
                    with st.sidebar.expander("画像保存", expanded=st.session_state.expand_all):
                        save_dpi_scale = st.selectbox("保存倍率 (1=入力px通り)", options=[1, 2, 3, 4], index=0)
                        use_tight = st.checkbox("余白を自動カットして保存", value=False)
                        
                        st.info(f"保存予定名: {save_filename}\n解像度: {width_px * save_dpi_scale} x {height_px * save_dpi_scale}")
                        
                        if st.button("画像を保存"):
                            if not os.path.exists(output_dir):
                                os.makedirs(output_dir)
                            save_path = os.path.join(output_dir, save_filename)
                            
                            save_bbox = 'tight' if use_tight else None
                            
                            fig.savefig(save_path, 
                                        dpi=display_dpi * save_dpi_scale, 
                                        facecolor=fig.get_facecolor(), 
                                        bbox_inches=save_bbox)
                            st.success(f"保存完了: {save_filename}")

        except Exception as e:
            st.error(f"実行中にエラーが発生しました: {e}")

# 最下部の全展開・全収納ボタン
st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns(2)
col1.button("全展開", on_click=set_expand_state, args=(True,), use_container_width=True)
col2.button("全収納", on_click=set_expand_state, args=(False,), use_container_width=True)