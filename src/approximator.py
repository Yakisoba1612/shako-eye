import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import differential_evolution, minimize
from scipy.interpolate import interp1d
import altair as alt
import os
from utils import apply_custom_css

PRESETS_COLUMNS = [
    'preset_name', 'mode', 'peak', 'flat', 'rolloff', 'left_roll', 'right_roll', 
    'left_mid', 'left_top', 'left_bottom', 'right_mid', 'right_top', 'right_bottom', 
    'use_sub', 'sub_peak', 'sub_flat', 'sub_roll', 'sub_int', 'sub_left_roll', 
    'sub_right_roll', 'sub_left_mid', 'sub_left_top', 'sub_left_bottom', 
    'sub_right_mid', 'sub_right_top', 'sub_right_bottom'
]

def create_filter_weights(wavelengths, peak, flat_w, left_rolloff, right_rolloff, 
                          left_mid=0.5, left_top_curve=1.0, left_bottom_curve=1.0,
                          right_mid=0.5, right_top_curve=1.0, right_bottom_curve=1.0):
    weights = np.zeros_like(wavelengths, dtype=np.float64)
    left_flat = peak - flat_w / 2.0
    right_flat = peak + flat_w / 2.0
    left_zero = left_flat - left_rolloff
    right_zero = right_flat + right_rolloff

    mask_flat = (wavelengths >= left_flat) & (wavelengths <= right_flat)
    mask_left = (wavelengths > left_zero) & (wavelengths < left_flat)
    mask_right = (wavelengths > right_flat) & (wavelengths < right_zero)

    weights[mask_flat] = 1.0
    epsilon = 1e-6
    
    if np.any(mask_left):
        t_left = (left_flat - wavelengths[mask_left]) / left_rolloff
        t_left_safe = np.clip(t_left, epsilon, 1.0 - epsilon)
        m_l = np.clip(left_mid, epsilon, 1.0 - epsilon)
        ratio_left = (t_left_safe * (1.0 - m_l)) / (m_l * (1.0 - t_left_safe))
        k_left = np.where(t_left_safe <= m_l, left_top_curve, left_bottom_curve)
        weights[mask_left] = 1.0 / (1.0 + np.power(ratio_left, k_left))
        
    if np.any(mask_right):
        t_right = (wavelengths[mask_right] - right_flat) / right_rolloff
        t_right_safe = np.clip(t_right, epsilon, 1.0 - epsilon)
        m_r = np.clip(right_mid, epsilon, 1.0 - epsilon)
        ratio_right = (t_right_safe * (1.0 - m_r)) / (m_r * (1.0 - t_right_safe))
        k_right = np.where(t_right_safe <= m_r, right_top_curve, right_bottom_curve)
        weights[mask_right] = 1.0 / (1.0 + np.power(ratio_right, k_right))

    return weights

def simple_mode_model(wavelengths, peak, flat, rolloff, use_sub, sub_peak=400, sub_flat=10, sub_roll=30, sub_int=0.3):
    w = create_filter_weights(wavelengths, peak, flat, rolloff, rolloff, 0.5, 1.0, 1.0, 0.5, 1.0, 1.0)
    if use_sub:
        w_sub = create_filter_weights(wavelengths, sub_peak, sub_flat, sub_roll, sub_roll, 0.5, 1.0, 1.0, 0.5, 1.0, 1.0)
        w += w_sub * sub_int
    return w

def objective_simple(params, wavelengths_valid, target_valid, use_sub_flag):
    if use_sub_flag:
        pred_values = simple_mode_model(wavelengths_valid, params[0], params[1], params[2], True, params[3], params[4], params[5], params[6])
    else:
        pred_values = simple_mode_model(wavelengths_valid, params[0], params[1], params[2], False)
    return np.sum((pred_values - target_valid) ** 2)

def objective_hp(params, wavelengths, y_true):
    (peak, flat_w, left_roll, right_roll, left_mid, left_top, left_bottom, right_mid, right_top, right_bottom,
     sub_peak, sub_flat_w, sub_int, sub_left_roll, sub_right_roll, sub_left_mid, sub_left_top, sub_left_bottom, sub_right_mid, sub_right_top, sub_right_bottom) = params
    
    w_main = create_filter_weights(wavelengths, peak, flat_w, left_roll, right_roll, left_mid, left_top, left_bottom, right_mid, right_top, right_bottom)
    w_sub = create_filter_weights(wavelengths, sub_peak, sub_flat_w, sub_left_roll, sub_right_roll, sub_left_mid, sub_left_top, sub_left_bottom, sub_right_mid, sub_right_top, sub_right_bottom) * sub_int
    
    y_pred = w_main + w_sub
    return np.sum((y_true - y_pred)**2)

def calculate_r2(y_true, y_pred):
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    yt = y_true[mask]
    yp = y_pred[mask]
    
    if len(yt) == 0:
        return 0.0
        
    ss_res = np.sum((yt - yp) ** 2)
    ss_tot = np.sum((yt - np.mean(yt)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0.0
    return r2

def load_and_preprocess(df):
    try:
        df = df.iloc[:, :2].copy()
        df.columns = ['wave', 'value']
        df['wave'] = pd.to_numeric(df['wave'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df_clean = df.dropna(subset=['wave', 'value']).copy()

        raw_x = df_clean['wave'].values
        raw_y = df_clean['value'].values

        if np.max(raw_x) < 10.0:
            raw_x = raw_x * 1000.0

        sort_idx = np.argsort(raw_x)
        raw_x = raw_x[sort_idx]
        raw_y = raw_y[sort_idx]

        return raw_x, raw_y
    except Exception as e:
        st.error(f"データ処理に失敗: {e}")
        return None, None

def save_preset(new_row_dict, preset_path):
    os.makedirs(os.path.dirname(preset_path), exist_ok=True)
    try:
        if not os.path.exists(preset_path):
            df_base = pd.DataFrame(columns=PRESETS_COLUMNS)
            df_base.to_csv(preset_path, index=False)
        
        row_data = {col: np.nan for col in PRESETS_COLUMNS}
        row_data.update(new_row_dict)
        
        df_new = pd.DataFrame([row_data])
        df_new.to_csv(preset_path, mode='a', header=False, index=False)
        st.success(f"'{preset_path}' にプリセットを保存成功")
    except PermissionError:
        st.error(f"保存に失敗。`{os.path.basename(preset_path)}` を開いている場合は閉じること。再度保存ボタンを押してください")
    except Exception as e:
        st.error(f"エラー: {e}")

def main():
    st.set_page_config(page_title="近似ツール", layout="wide")
    
    st.markdown("""
        <style>
        div.stButton > button {
            border-radius: 0px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    apply_custom_css()
        
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "csv", "approximation", "spectrum.csv")
    preset_path = os.path.join(current_dir, "csv", "presets.csv")

    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False
    if 'analyzed' not in st.session_state:
        st.session_state['analyzed'] = False
    if 'r2' not in st.session_state:
        st.session_state['r2'] = 0.0

    if "show_help" not in st.session_state:
        st.session_state.show_help = False

    def toggle_help():
        st.session_state.show_help = not st.session_state.show_help

    col_header, col_btn = st.columns([9, 1])

    with col_btn:
        button_label = "閉じる" if st.session_state.show_help else "使い方"
        st.button(button_label, on_click=toggle_help)

    if st.session_state.show_help:
        main_col, help_col = st.columns([3, 1])
    else:
        main_col = st.container()
        help_col = None

    with main_col:
        col1, col2, col3 = st.columns(3)
    
        with col1:
            st.subheader("1. データ取得")
            st.write(f"対象ファイル: spectrum.csv")
            
            if st.button("データ取り込み", type="secondary"):
                if os.path.exists(data_path):
                    df = pd.read_csv(data_path)
                    raw_x, raw_y = load_and_preprocess(df)
                    if raw_x is not None:
                        st.session_state['raw_x'] = raw_x
                        st.session_state['raw_y'] = raw_y
                        st.session_state['data_loaded'] = True
                        st.session_state['analyzed'] = False
                        st.success("取り込み成功")
                else:
                    st.error(f"{data_path} 未発見")
    
        with col2:
            st.subheader("2. 設定")
            mode = st.radio("プリセット方式を選択", ["簡易", "精密"], horizontal=True)
            use_sub = False
            if mode == "簡易":
                use_sub = st.toggle("副バンドを含める", value=False)
                
            if st.button("開始", type="primary") and st.session_state.get('data_loaded'):
                st.session_state['analyzed'] = False
                raw_x = st.session_state['raw_x']
                raw_y = st.session_state['raw_y']
                
                if mode == "簡易":
                    with st.spinner("簡易近似を計算中..."):
                        raw_y_norm = raw_y - np.min(raw_y)
                        max_y = np.max(raw_y_norm)
                        if max_y > 0:
                            raw_y_norm = raw_y_norm / max_y
                        
                        sim_wavelengths = np.arange(380, 785, 5)
                        min_w = np.min(raw_x)
                        max_w = np.max(raw_x)
                        f_interp = interp1d(raw_x, raw_y_norm, bounds_error=False, fill_value=np.nan)
                        target_values = f_interp(sim_wavelengths)
                        
                        valid_mask = (sim_wavelengths >= min_w) & (sim_wavelengths <= max_w)
                        
                        sim_w_valid = sim_wavelengths[valid_mask]
                        target_v_valid = target_values[valid_mask]
                        
                        if use_sub:
                            bounds = [(380, max_w), (0, 60), (5, 150), (380, max_w), (0, 50), (5, 150), (0.0, 1.0)]
                        else:
                            bounds = [(380, max_w), (0, 60), (5, 150)]
                            
                        result = differential_evolution(
                            objective_simple, bounds, 
                            args=(sim_w_valid, target_v_valid, use_sub),
                            strategy='best1bin', maxiter=2000, popsize=20, tol=0.01
                        )
                        
                        if result.success:
                            st.session_state['analyzed'] = True
                            st.session_state['mode'] = "簡易"
                            st.session_state['use_sub'] = use_sub
                            st.session_state['opt_params'] = result.x
                            st.session_state['sim_wavelengths'] = sim_wavelengths
                            st.session_state['target_values'] = target_values
                            st.session_state['valid_mask'] = valid_mask
                            
                            if use_sub:
                                opt_peak, opt_flat, opt_roll, opt_sub_peak, opt_sub_flat, opt_sub_roll, opt_sub_int = result.x
                            else:
                                opt_peak, opt_flat, opt_roll = result.x
                                opt_sub_peak, opt_sub_flat, opt_sub_roll, opt_sub_int = 0, 0, 0, 0
                            
                            pred_curve = simple_mode_model(sim_wavelengths, opt_peak, opt_flat, opt_roll, use_sub, opt_sub_peak, opt_sub_flat, opt_sub_roll, opt_sub_int)
                            st.session_state['pred_curve'] = pred_curve
                            st.session_state['r2'] = calculate_r2(target_v_valid, pred_curve[valid_mask])
    
                elif mode == "精密":
                    with st.spinner("精密近似を計算中..."):
                        bounds = [
                            (380, 780), (0, 100), (5, 150), (5, 150), (0.05, 0.95), (0.5, 5.0), (0.5, 5.0), (0.05, 0.95), (0.5, 5.0), (0.5, 5.0),
                            (380, 780), (0, 50), (0.0, 1.0), (5, 100), (5, 100), (0.05, 0.95), (0.5, 5.0), (0.5, 5.0), (0.05, 0.95), (0.5, 5.0), (0.5, 5.0)
                        ]
                        result_de = differential_evolution(objective_hp, bounds, args=(raw_x, raw_y), strategy='best1bin', maxiter=1000, popsize=15, tol=1e-4)
                        result_min = minimize(objective_hp, result_de.x, args=(raw_x, raw_y), method='L-BFGS-B', bounds=bounds, options={'ftol': 1e-9, 'maxiter': 500})
                        
                        st.session_state['analyzed'] = True
                        st.session_state['mode'] = "精密"
                        st.session_state['opt_params'] = result_min.x
                        
                        opt_p = result_min.x
                        w_main = create_filter_weights(raw_x, opt_p[0], opt_p[1], opt_p[2], opt_p[3], opt_p[4], opt_p[5], opt_p[6], opt_p[7], opt_p[8], opt_p[9])
                        w_sub = create_filter_weights(raw_x, opt_p[10], opt_p[11], opt_p[13], opt_p[14], opt_p[15], opt_p[16], opt_p[17], opt_p[18], opt_p[19], opt_p[20]) * opt_p[12]
                        y_pred = w_main + w_sub
                        
                        st.session_state['pred_curve'] = y_pred
                        st.session_state['r2'] = calculate_r2(raw_y, y_pred)
    
            elif not st.session_state.get('data_loaded'):
                st.warning("データを取得してください")
    
        with col3:
            st.subheader("3. 結果と保存")
            if st.session_state.get('analyzed') and 'r2' in st.session_state:
                r2 = st.session_state.get('r2', 0.0)
                st.metric(label="決定係数 (R²)", value=f"{r2:.4f}")
                
                preset_name = st.text_input("プリセット名で保存")
                if st.button("presets.csv に保存"):
                    if preset_name:
                        mode_val = st.session_state['mode']
                        if mode_val == "簡易":
                            res_x = st.session_state['opt_params']
                            curr_use_sub = st.session_state['use_sub']
                            if curr_use_sub:
                                opt_peak, opt_flat, opt_roll, opt_sub_peak, opt_sub_flat, opt_sub_roll, opt_sub_int = res_x
                            else:
                                opt_peak, opt_flat, opt_roll = res_x
                                opt_sub_peak, opt_sub_flat, opt_sub_roll, opt_sub_int = 0, 0, 0, 0
                                
                            new_data = {
                                "preset_name": preset_name,
                                "mode": "簡易",
                                "peak": round(opt_peak, 1),
                                "flat": round(opt_flat, 1),
                                "rolloff": round(opt_roll, 1),
                                "use_sub": curr_use_sub
                            }
                            if curr_use_sub:
                                new_data.update({
                                    "sub_peak": round(opt_sub_peak, 1),
                                    "sub_flat": round(opt_sub_flat, 1),
                                    "sub_roll": round(opt_sub_roll, 1),
                                    "sub_int": round(opt_sub_int, 3)
                                })
                        elif mode_val == "精密":
                            opt_p = st.session_state['opt_params']
                            new_data = {
                                "preset_name": preset_name,
                                "mode": "精密",
                                "peak": round(opt_p[0], 1), "flat": round(opt_p[1], 1),
                                "left_roll": round(opt_p[2], 1), "right_roll": round(opt_p[3], 1),
                                "left_mid": round(opt_p[4], 3), "left_top": round(opt_p[5], 2), "left_bottom": round(opt_p[6], 2),
                                "right_mid": round(opt_p[7], 3), "right_top": round(opt_p[8], 2), "right_bottom": round(opt_p[9], 2),
                                "use_sub": True,
                                "sub_peak": round(opt_p[10], 1), "sub_flat": round(opt_p[11], 1), "sub_int": round(opt_p[12], 3),
                                "sub_left_roll": round(opt_p[13], 1), "sub_right_roll": round(opt_p[14], 1),
                                "sub_left_mid": round(opt_p[15], 3), "sub_left_top": round(opt_p[16], 2), "sub_left_bottom": round(opt_p[17], 2),
                                "sub_right_mid": round(opt_p[18], 3), "sub_right_top": round(opt_p[19], 2), "sub_right_bottom": round(opt_p[20], 2)
                            }
                        save_preset(new_data, preset_path)
                    else:
                        st.warning("プリセット名未入力")
            else:
                st.write("未完了")
    
    st.divider()
    
    if st.session_state.get('data_loaded'):
        raw_x = st.session_state['raw_x']
        raw_y = st.session_state['raw_y']
        
        if st.session_state.get('analyzed'):
            mode = st.session_state['mode']
            
            if mode == "簡易":
                sim_wavelengths = st.session_state['sim_wavelengths']
                target_values = st.session_state['target_values']
                pred_curve = st.session_state['pred_curve']
                
                df_plot = pd.DataFrame({
                    "波長 (nm)": sim_wavelengths,
                    "csv（補完込）": target_values,
                    "近似値": pred_curve
                }).melt("波長 (nm)", var_name="データ種別", value_name="透過率")
                
            elif mode == "精密":
                y_pred = st.session_state['pred_curve']
                
                df_plot = pd.DataFrame({
                    "波長 (nm)": raw_x,
                    "csv（補完込）": raw_y,
                    "近似値": y_pred
                }).melt("波長 (nm)", var_name="データ種別", value_name="透過率")

            chart = alt.Chart(df_plot).mark_line(size=3).encode(
                x=alt.X("波長 (nm)", scale=alt.Scale(zero=False)),
                y="透過率",
                color="データ種別",
                strokeDash=alt.condition(alt.datum.データ種別 == '近似値', alt.value([5, 5]), alt.value([0]))
            ).properties(height=500).interactive()
            
            st.altair_chart(chart, use_container_width=True)
            
        else:
            df_plot_raw = pd.DataFrame({"波長 (nm)": raw_x, "透過率": raw_y})
            chart_raw = alt.Chart(df_plot_raw).mark_line(point=True).encode(
                x=alt.X("波長 (nm)", scale=alt.Scale(zero=False)),
                y="透過率"
            ).properties(height=500).interactive()
            
            st.altair_chart(chart_raw, use_container_width=True)

        if help_col is not None:
            with help_col:
                st.subheader("操作説明")
                st.write("1. src\ csv\ approximation\ spectrum.csvに値を入力します。  \nwaveが波長、valueが透過率（上限1）です。")
                st.write("2. 演算方式を選択して開始します。  \n精密法の場合は数分かかる場合があります。")
                st.write("3. 結果の一致度は決定係数をご参考に。  \n（何回かに一回、1.0000に達することがあります）")
                st.write("4. 好きな名称で保存、プリセットとして登録されます。  \n修正・削除したい場合はsrc\ csv\ presets.csvを編集してください。")

if __name__ == "__main__":
    main()