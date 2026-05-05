# -*- coding: utf-8 -*-
# app.py  ——  时空呼吸 · 完整版 v4
# 运行: streamlit run app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib, json, os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════
# §1  工具函数
# ═══════════════════════════════════════════════════════════════
def aqi_meta(v: float) -> dict:
    v = float(v)
    if   v <= 35:  return dict(level='优',      css='lvl0', color='#00e676', risk='无',   idx=0)
    elif v <= 75:  return dict(level='良',       css='lvl1', color='#ffd600', risk='低',   idx=1)
    elif v <= 115: return dict(level='轻度污染',  css='lvl2', color='#ff9100', risk='中',   idx=2)
    elif v <= 150: return dict(level='中度污染',  css='lvl3', color='#ff5252', risk='高',   idx=3)
    elif v <= 250: return dict(level='重度污染',  css='lvl4', color='#d500f9', risk='极高', idx=4)
    else:          return dict(level='严重污染',  css='lvl5', color='#ff1744', risk='危险', idx=5)

def bhi_meta(v: float) -> dict:
    v = float(v)
    if   v < 20:  return dict(level='优质呼吸', color='#00e676', emoji='💚', bar_color='#00e676',
                              advice='空气清洁，适宜户外有氧运动与深呼吸练习')
    elif v < 40:  return dict(level='良好呼吸', color='#69f0ae', emoji='🌿', bar_color='#69f0ae',
                              advice='空气良好，正常户外活动，敏感人群适量减少剧烈运动')
    elif v < 60:  return dict(level='呼吸预警', color='#ffd600', emoji='⚠️', bar_color='#ffd600',
                              advice='建议佩戴口罩，减少户外逗留，儿童老人尽量留在室内')
    elif v < 80:  return dict(level='呼吸受损', color='#ff9100', emoji='😷', bar_color='#ff9100',
                              advice='请戴N95口罩，避免户外活动，打开空气净化器')
    else:         return dict(level='呼吸危险', color='#ff1744', emoji='🚨', bar_color='#ff1744',
                              advice='严重污染！请留在室内，关闭门窗，建议就医')

def aqi_level_str(v: float) -> str:
    v = float(v)
    if v<=35: return '优'
    elif v<=75: return '良'
    elif v<=115: return '轻度污染'
    elif v<=150: return '中度污染'
    elif v<=250: return '重度污染'
    else: return '严重污染'

PIE_CLR = {'优':'#00e676','良':'#ffd600','轻度污染':'#ff9100',
           '中度污染':'#ff5252','重度污染':'#d500f9','严重污染':'#ff1744'}
BHI_CLR = ['#00e676','#69f0ae','#ffd600','#ff9100','#ff1744']

# Plotly 暗色主题基础
_DARK = dict(
    template='plotly_dark',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#b8cfe0', family='Consolas, monospace'),
    margin=dict(l=40, r=20, t=50, b=40),
    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', zeroline=False, showline=False),
    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zeroline=False, showline=False),
)

def dk(fig, title='', h=360):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color='rgba(0,220,255,.85)',
                                         family='Consolas, monospace'), x=0.01),
        height=h, **_DARK)
    return fig

def gauge_chart(value: float, title: str, steps: list, color: str, max_v=300, h=260) -> go.Figure:
    """圆形仪表盘"""
    fig = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=value,
        delta={'reference': 0, 'relative': False,
               'font': {'size': 11, 'color': '#b8cfe0'}},
        number={'font': {'size': 36, 'color': color, 'family': 'Consolas, monospace'},
                'suffix': ''},
        title={'text': title, 'font': {'size': 12, 'color': '#7899b0'}},
        gauge={
            'axis': {'range': [0, max_v],
                     'tickcolor': '#7899b0', 'tickfont': {'size': 9},
                     'nticks': 7},
            'bar': {'color': color, 'thickness': 0.22},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 0,
            'steps': steps,
            'threshold': {
                'line': {'color': '#ff1744', 'width': 3},
                'thickness': 0.7,
                'value': 150,
            }
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=h,
                      margin=dict(l=30, r=30, t=40, b=10),
                      font=dict(color='#b8cfe0'))
    return fig

def pm25_gauge(value: float) -> go.Figure:
    m = aqi_meta(value)
    steps = [
        {'range': [0, 35],   'color': 'rgba(0,230,118,0.12)'},
        {'range': [35, 75],  'color': 'rgba(255,214,0,0.12)'},
        {'range': [75, 115], 'color': 'rgba(255,145,0,0.12)'},
        {'range': [115, 150],'color': 'rgba(255,82,82,0.12)'},
        {'range': [150, 250],'color': 'rgba(213,0,249,0.12)'},
        {'range': [250, 300],'color': 'rgba(255,23,68,0.12)'},
    ]
    return gauge_chart(value, 'PM2.5  μg/m³', steps, m['color'], max_v=300, h=260)

# ═══════════════════════════════════════════════════════════════
# §2  页面配置（必须第一个 st 调用）
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title='时空呼吸 · 空气质量智能预测',
    page_icon='🌬️',
    layout='wide',
    initial_sidebar_state='collapsed',
)

# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# §3  全局 CSS + 粒子背景(独立文件加载,避免转义问题)
# ═══════════════════════════════════════════════════════════════
from pathlib import Path
_STATIC = Path(__file__).parent / 'static'

def _load_static(name: str) -> str:
    """读取静态资源,失败时返回空字符串(不让应用崩溃)"""
    try:
        return (_STATIC / name).read_text(encoding='utf-8')
    except Exception:
        return ''

# 注入 CSS
_css = _load_static('aurora.css')
if _css:
    st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)
else:
    st.warning("[警告] static/aurora.css 未找到,UI 样式将退化为基础样式")

# 注入粒子 canvas + JS
_js = _load_static('aurora.js')
if _js:
    st.markdown(
        f"<canvas id='particle-bg'></canvas><script>{_js}</script>",
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════
# §4  数据 & 模型加载
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=120)
def load_data() -> pd.DataFrame:
    df = pd.read_csv('data_with_features.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

@st.cache_resource
def load_models() -> dict:
    mp = {
        'LightGBM':     'models/LightGBM_model.pkl',
        'XGBoost':      'models/XGBoost_model.pkl',
        'RandomForest': 'models/RandomForest_model.pkl',
        'GradientBoosting': 'models/GradientBoosting_model.pkl',
        'Ridge':        'models/Ridge_model.pkl',
    }
    return {n: joblib.load(p) for n, p in mp.items() if os.path.exists(p)}


@st.cache_resource
def load_mstn_v2():
    """
    加载 MSTN v2 深度学习模型（v2 升级新增）
    返回 dict 含 model, scaler_X, scaler_y, available
    """
    weights = 'models/mstn_v2_best.pth'
    sx_path = 'models/mstn_scaler_X.pkl'
    sy_path = 'models/mstn_scaler_y.pkl'
    if not (os.path.exists(weights) and os.path.exists(sx_path) and os.path.exists(sy_path)):
        return {'available': False, 'reason': '模型权重未找到，请先运行 6_advanced_model_v2.py'}
    try:
        import torch
        import importlib.util
        spec = importlib.util.spec_from_file_location("adv", "6_advanced_model_v2.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        scaler_X = joblib.load(sx_path)
        scaler_y = joblib.load(sy_path)
        n_features = scaler_X.n_features_in_
        model = mod.MSTNv2(input_dim=n_features, hidden_dim=64)
        state = torch.load(weights, map_location='cpu', weights_only=True)
        model.load_state_dict(state)
        model.eval()
        return {
            'available': True,
            'model': model,
            'scaler_X': scaler_X,
            'scaler_y': scaler_y,
            'n_features': n_features,
        }
    except ImportError as e:
        return {'available': False, 'reason': f'PyTorch 未安装: {e}'}
    except Exception as e:
        return {'available': False, 'reason': str(e)}


def predict_with_mstn_v2(mstn_pack, X_seq):
    """
    使用 MSTN v2 推理。返回点预测 + 置信区间。

    参数：
        mstn_pack: load_mstn_v2 的返回值
        X_seq: numpy [T=24, F] 单个序列

    返回：
        dict: q05_orig / q50_orig / q95_orig 三个反标准化的浓度值
    """
    import torch
    if not mstn_pack['available']:
        return None

    X_scaled = mstn_pack['scaler_X'].transform(X_seq).astype('float32')
    X_t = torch.from_numpy(X_scaled).unsqueeze(0)
    with torch.no_grad():
        pred, _, _ = mstn_pack['model'](X_t)
    quantiles = pred.numpy().flatten()
    quantiles_orig = mstn_pack['scaler_y'].inverse_transform(
        quantiles.reshape(-1, 1)
    ).flatten()
    return {
        'q05': float(quantiles_orig[0]),
        'q50': float(quantiles_orig[1]),
        'q95': float(quantiles_orig[2]),
    }


@st.cache_resource
def load_fcols() -> list:
    p = 'models/feature_cols.json'
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []

@st.cache_data(ttl=300)
def load_comparison() -> pd.DataFrame:
    p = 'model_comparison.csv'
    if os.path.exists(p):
        return pd.read_csv(p, index_col=0)
    return pd.DataFrame()

@st.cache_data(ttl=300)
def load_predictions() -> pd.DataFrame:
    p = 'predictions.csv'
    if os.path.exists(p):
        return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data(ttl=300)
def load_importance() -> pd.DataFrame:
    p = 'feature_importance.csv'
    if os.path.exists(p):
        return pd.read_csv(p)
    return pd.DataFrame()

# ── 启动 ──
try:
    df_all   = load_data()
    models   = load_models()
    FCOLS    = load_fcols()
    df_comp  = load_comparison()
    df_pred  = load_predictions()
    df_imp   = load_importance()
except FileNotFoundError as e:
    st.error(f"❌ 数据文件缺失：{e}")
    st.code("python data_collector.py\npython feature_engineer.py\npython model_trainer.py")
    st.stop()

if not models:
    st.error("❌ 未找到模型文件，请先运行 python model_trainer.py")
    st.stop()
if not FCOLS:
    st.warning("⚠️ 未找到 models/feature_cols.json，请重新运行 model_trainer.py")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# §5  侧边栏
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:18px 0 22px'>
      <div style='font-size:2.5rem'>🌬️</div>
      <div style='font-family:Orbitron,sans-serif;font-size:.75rem;color:#00d4ff;
                  letter-spacing:4px;font-weight:700;margin-top:6px'>时空呼吸</div>
      <div style='font-size:.58rem;color:rgba(0,212,255,.4);letter-spacing:2px;margin-top:3px'>
        AIR QUALITY AI SYSTEM
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 城市/站点
    have_city = 'city' in df_all.columns and df_all['city'].nunique() > 1
    if have_city:
        st.markdown("**🏙️ 城市 / 站点**")
        city_sel = st.selectbox('', sorted(df_all['city'].unique()), label_visibility='collapsed')
    elif 'city' in df_all.columns:
        city_sel = df_all['city'].iloc[0]
        st.markdown(f"<div class='alert alert-blue'>📍 {city_sel}</div>", unsafe_allow_html=True)
    else:
        city_sel = None

    st.markdown("---")

    # 日期范围
    st.markdown("**📅 时间范围**")
    d_min = df_all['timestamp'].min().date()
    d_max = df_all['timestamp'].max().date()
    date_range = st.date_input('', value=(d_max - timedelta(days=60), d_max),
                               min_value=d_min, max_value=d_max,
                               label_visibility='collapsed')

    st.markdown("---")

    # 模型选择
    st.markdown("**🤖 预测模型**")
    model_sel = st.selectbox('', list(models.keys()), label_visibility='collapsed')

    st.markdown("---")

    # 展示窗口设置
    st.markdown("**⚙️ 显示设置**")
    show_n = st.slider('时序显示点数', 200, 5000, 1000, 100)
    forecast_h = st.slider('预测小时数', 6, 72, 24, 6)

    st.markdown("---")

    # 数据集摘要
    st.markdown("**📦 数据集**")
    n_cities = df_all['city'].nunique() if 'city' in df_all.columns else 1
    span_days = (df_all['timestamp'].max() - df_all['timestamp'].min()).days
    for val, lbl in [
        (f"{len(df_all):,}", "总记录数"),
        (f"{span_days} 天", "时间跨度"),
        (f"{df_all.shape[1]}", "特征维度"),
        (f"{n_cities}", "城市/站点"),
    ]:
        st.markdown(
            f"<div class='bignum-card'>"
            f"<div class='bignum-val'>{val}</div>"
            f"<div class='bignum-lbl'>{lbl}</div></div>",
            unsafe_allow_html=True)

    # ─── LLM 深度分析 配置区 ───────────────────────────
    st.markdown("---")
    st.markdown("**🧠 AI 深度分析**")
    try:
        import deep_analysis as _dsmod_sb
        _existing_key = _dsmod_sb.get_api_key()
        if _existing_key:
            st.markdown(
                "<div class='alert alert-green' style='font-size:.7rem;padding:8px 12px'>"
                "✅ DeepSeek 已配置<br>"
                "<span style='font-family:JetBrains Mono,monospace;font-size:.65rem;opacity:.7'>"
                + _dsmod_sb.mask_key(_existing_key) +
                "</span></div>",
                unsafe_allow_html=True
            )
        else:
            with st.expander('🔑 配置 API Key', expanded=False):
                st.markdown(
                    "<div style='font-size:.7rem;color:rgba(180,210,230,.65);"
                    "line-height:1.7;margin-bottom:8px'>"
                    "推荐放在 <code>.streamlit/secrets.toml</code>(详见 DEEPSEEK_SETUP.md)。"
                    "下方临时输入仅当前 session 有效。"
                    "</div>",
                    unsafe_allow_html=True
                )
                _temp_key = st.text_input(
                    'API Key (sk-...)', type='password',
                    value=st.session_state.get('_dskey_temp', ''),
                    key='_dskey_input',
                    label_visibility='collapsed',
                    placeholder='sk-xxxxxxxxxxxxxxxx'
                )
                if _temp_key and _temp_key.startswith('sk-'):
                    st.session_state['_dskey_temp'] = _temp_key
                    st.success('✅ 已加载: ' + _dsmod_sb.mask_key(_temp_key))
                    st.rerun()
    except Exception:
        st.markdown(
            "<div class='alert alert-yellow' style='font-size:.7rem;padding:8px 12px'>"
            "⚠️ deep_analysis.py 未找到</div>",
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════════════
# §6  数据过滤（全局共享）
# ═══════════════════════════════════════════════════════════════
city_df = df_all[df_all['city'] == city_sel].copy() if (city_sel and 'city' in df_all.columns) else df_all.copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    ds = pd.Timestamp(date_range[0])
    de = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
else:
    ds = pd.Timestamp(d_max - timedelta(days=60))
    de = pd.Timestamp(d_max) + pd.Timedelta(days=1)

city_df = city_df[(city_df['timestamp'] >= ds) & (city_df['timestamp'] < de)].sort_values('timestamp').reset_index(drop=True)

if city_df.empty:
    st.error("⚠️ 所选范围内无数据，请在侧边栏调整日期范围")
    st.stop()

# ── 全局共享状态 ──
latest    = city_df.iloc[-1]
pm25_cur  = float(latest.get('pm25', 0))
aqi       = aqi_meta(pm25_cur)
bhi_cur   = float(latest.get('breathing_health_index', min(100, pm25_cur / 5)))
bhi_info  = bhi_meta(bhi_cur)
pm25_24h  = float(city_df.iloc[-25]['pm25']) if len(city_df) > 25 else pm25_cur
dv        = pm25_cur - pm25_24h
dcls      = 'kd-up' if dv > 0 else ('kd-down' if dv < 0 else 'kd-flat')
dstr      = f"{'↑' if dv>0 else '↓'}{abs(dv):.1f} vs 24h前"

# ── 呼吸球 CSS 变量（随AQI变化）──
speed_map = {'优': '4s', '良': '3.5s', '轻度污染': '2.8s', '中度污染': '2.2s', '重度污染': '1.8s', '严重污染': '1.4s'}
orb_speed = speed_map.get(aqi['level'], '3s')

# ═══════════════════════════════════════════════════════════════
# §7  Hero 标题(v3 电影级)
# ═══════════════════════════════════════════════════════════════
now_str = datetime.now().strftime('%Y-%m-%d  %H:%M')

# 把当前 BHI 颜色暴露给前端,让粒子背景响应数据状态
st.markdown(
    "<script>window.__bhiMeta = {color: '" + bhi_info["color"] + "', level: '" + bhi_info["level"] + "'};</script>",
    unsafe_allow_html=True
)

st.markdown(f"""
<div class='hero-v3'>
  <div class='hero-glowbar'></div>
  <div class='hero-eyebrow'>大数据实践赛 · 环境与人类发展大数据</div>
  <div class='hero-title-v3'>SHIKONG · HUXI</div>
  <div class='hero-zh'>时 · 空 · 呼 · 吸</div>
  <div class='hero-sub-v3'>TEMPORAL · SPATIAL · BREATHING INTELLIGENCE</div>
  <div class='hero-tags-v3'>
    <span class='hero-tag-v3 live'>实时数据</span>
    <span class='hero-tag-v3'>MSTN v2 多尺度时空融合</span>
    <span class='hero-tag-v3'>BHI 呼吸健康指数</span>
    <span class='hero-tag-v3'>三源大数据融合</span>
    <span class='hero-tag-v3' style='color:rgba(0,212,255,.5)'>{now_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# §8  主 Tab 区
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    '🏠  实时监控',
    '💚  呼吸健康',
    '🤖  智能预测',
    '📊  深度分析',
    '🌏  城市对比',
    '📦  大数据洞察',
    '🧠  AI 问数',
])

# ┌─────────────────────────────────────────────────────────────┐
# │  TAB 1 · 实时监控                                           │
# └─────────────────────────────────────────────────────────────┘
with tab1:
    # 预警横幅
    if pm25_cur > 150:
        st.markdown(f"<div class='alert alert-red'>🚨  严重污染预警 · PM2.5 = <b>{pm25_cur:.1f}</b> μg/m³ · {aqi['level']} · 请立即减少户外活动</div>", unsafe_allow_html=True)
    elif pm25_cur > 115:
        st.markdown(f"<div class='alert alert-orange'>⚠️  中度污染 · PM2.5 = <b>{pm25_cur:.1f}</b> μg/m³ · 建议佩戴N95口罩，减少外出</div>", unsafe_allow_html=True)
    elif pm25_cur > 75:
        st.markdown(f"<div class='alert alert-yellow'>⚡  轻度污染 · PM2.5 = <b>{pm25_cur:.1f}</b> μg/m³ · 建议佩戴口罩，敏感人群注意</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='alert alert-green'>✅  空气{aqi['level']} · PM2.5 = <b>{pm25_cur:.1f}</b> μg/m³ · 适宜户外活动</div>", unsafe_allow_html=True)

    # 顶部：仪表盘 + KPI 卡片
    col_g, col_k = st.columns([1, 3])

    with col_g:
        st.plotly_chart(pm25_gauge(pm25_cur), use_container_width=True)

    with col_k:
        # 6 个 KPI
        k1, k2, k3 = st.columns(3)
        k4, k5, k6 = st.columns(3)

        def kpi_html(lbl, val, unit, delta, dcl, clr):
            return (f"<div class='glass kpi-wrap'>"
                    f"<div class='kpi-bar' style='background:linear-gradient(90deg,{clr}80,{clr}20)'></div>"
                    f"<div class='kpi-label'>{lbl}</div>"
                    f"<div class='kpi-value' style='color:{clr}'>{val}</div>"
                    f"<div class='kpi-unit'>{unit}</div>"
                    f"<div class='kpi-delta {dcl}'>{delta}</div></div>")

        k1.markdown(kpi_html('空气质量', aqi['level'], '', '风险等级：' + aqi['risk'], 'kd-flat', aqi['color']), unsafe_allow_html=True)
        k2.markdown(kpi_html('BHI 呼吸健康指数', f'{bhi_cur:.0f}', '/ 100', bhi_info['level'], 'kd-flat', bhi_info['color']), unsafe_allow_html=True)
        k3.markdown(kpi_html('24h 变化', f'{abs(dv):.1f}', 'μg/m³', dstr, dcls, aqi['color']), unsafe_allow_html=True)

        temp_v = latest.get('temperature')
        wind_v = latest.get('wind_speed')
        pres_v = latest.get('pressure')
        k4.markdown(kpi_html('气温', f'{float(temp_v):.1f}' if temp_v is not None else '--', '°C', '', 'kd-flat', '#64b5f6'), unsafe_allow_html=True)
        k5.markdown(kpi_html('风速', f'{float(wind_v):.1f}' if wind_v is not None else '--', 'm/s', '↑风速↓PM2.5' if wind_v and float(wind_v) > 3 else '', 'kd-down' if wind_v and float(wind_v) > 3 else 'kd-flat', '#4fc3f7'), unsafe_allow_html=True)
        k6.markdown(kpi_html('气压', f'{float(pres_v):.0f}' if pres_v is not None else '--', 'hPa', '', 'kd-flat', '#81d4fa'), unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # 时序图
    st.markdown("<div class='sec'>📈 PM2.5 浓度时序趋势</div>", unsafe_allow_html=True)
    disp = city_df.tail(show_n)
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=disp['timestamp'], y=disp['pm25'],
        mode='lines', name='PM2.5',
        line=dict(color='#00d4ff', width=1.8),
        fill='tozeroy', fillcolor='rgba(0,212,255,0.06)',
    ))
    # 24h 滚动均值
    if 'pm25_rolling_mean_24h' in disp.columns:
        fig_ts.add_trace(go.Scatter(
            x=disp['timestamp'], y=disp['pm25_rolling_mean_24h'],
            mode='lines', name='24h 均线',
            line=dict(color='#ffd600', width=1.2, dash='dot'),
        ))
    for yv, lbl, clr in [(35, '优 35', '#00e676'), (75, '良 75', '#ffd600'), (115, '轻 115', '#ff9100'), (150, '中 150', '#ff5252')]:
        fig_ts.add_hline(y=yv, line_dash='dash', line_color=clr, line_width=0.8,
                         annotation_text=lbl, annotation_font_size=9, annotation_position='right')
    dk(fig_ts, '', 360)
    fig_ts.update_layout(legend=dict(orientation='h', y=1.08, x=0.01,
                                     font=dict(size=11)))
    st.plotly_chart(fig_ts, use_container_width=True)

    # 下方两列：小时分布 + AQI饼图
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("<div class='sec'>⏰ 24小时 PM2.5 均值模式</div>", unsafe_allow_html=True)
        if 'hour' in city_df.columns and len(city_df) > 48:
            hourly = city_df.groupby('hour')['pm25'].agg(['mean', 'std']).reset_index()
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(
                x=list(hourly['hour']) + list(hourly['hour'])[::-1],
                y=list(hourly['mean'] + hourly['std']) + list(hourly['mean'] - hourly['std'])[::-1],
                fill='toself', fillcolor='rgba(0,212,255,0.08)',
                line=dict(color='rgba(0,0,0,0)'), name='±1σ',
            ))
            fig_h.add_trace(go.Scatter(
                x=hourly['hour'], y=hourly['mean'],
                mode='lines+markers', name='均值',
                line=dict(color='#00d4ff', width=2.5),
                marker=dict(size=6, color='#00d4ff',
                             line=dict(color='#030a14', width=2)),
            ))
            cur_hour = datetime.now().hour
            fig_h.add_vline(x=cur_hour, line_dash='dash', line_color='#ff9100',
                            line_width=1.5, annotation_text='当前', annotation_font_size=9)
            dk(fig_h, '', 300)
            st.plotly_chart(fig_h, use_container_width=True)

    with c_right:
        st.markdown("<div class='sec'>🎨 AQI 等级分布</div>", unsafe_allow_html=True)
        ac = city_df['pm25'].apply(aqi_level_str).value_counts()
        fig_pie = go.Figure(go.Pie(
            labels=ac.index, values=ac.values,
            marker=dict(colors=[PIE_CLR.get(l, '#888') for l in ac.index],
                        line=dict(color='rgba(0,0,0,0)', width=0)),
            hole=0.5,
            textfont=dict(family='Exo 2, sans-serif', size=11),
        ))
        dk(fig_pie, '', 300)
        fig_pie.update_layout(legend=dict(font=dict(size=11), x=0.75))
        st.plotly_chart(fig_pie, use_container_width=True)

    # 月度热力图 season×hour
    st.markdown("<div class='sec'>🗓️ 季节 × 时段 PM2.5 热力矩阵</div>", unsafe_allow_html=True)
    if 'hour' in city_df.columns and 'month' in city_df.columns and len(city_df) > 200:
        pvt = city_df.pivot_table(values='pm25', index='hour', columns='month', aggfunc='mean')
        fig_hm = go.Figure(go.Heatmap(
            z=pvt.values, x=[f'{m}月' for m in pvt.columns], y=[f'{h:02d}:00' for h in pvt.index],
            colorscale='RdYlGn_r', colorbar=dict(title='μg/m³', tickfont=dict(size=10)),
            hovertemplate='%{x} %{y}<br>均值: %{z:.1f} μg/m³<extra></extra>',
        ))
        dk(fig_hm, '', 380)
        st.plotly_chart(fig_hm, use_container_width=True)


# ┌─────────────────────────────────────────────────────────────┐
# │  TAB 2 · 呼吸健康                                           │
# └─────────────────────────────────────────────────────────────┘
with tab2:
    st.markdown("<div class='sec'>💚 呼吸健康指数（BHI）实时状态</div>", unsafe_allow_html=True)

    col_orb, col_mid, col_trend = st.columns([1, 1.2, 2])

    with col_orb:
        # 动态呼吸球
        st.markdown(f"""
        <style>
          :root {{
            --oc: {bhi_info['color']};
            --speed: {orb_speed};
          }}
        </style>
        <div class='breath-orb-wrap'>
          <div class='breath-orb'>
            <div class='orb-ring ring-1'></div>
            <div class='orb-ring ring-2'></div>
            <div class='orb-ring ring-3'></div>
            <div class='orb-ring ring-4'></div>
            <div class='orb-particles'>
              <span style='top:50%;left:50%;--ox:18px;--oy:-22px;animation-delay:0s'></span>
              <span style='top:50%;left:50%;--ox:-22px;--oy:-15px;animation-delay:.5s'></span>
              <span style='top:50%;left:50%;--ox:25px;--oy:12px;animation-delay:1s'></span>
              <span style='top:50%;left:50%;--ox:-15px;--oy:25px;animation-delay:1.5s'></span>
              <span style='top:50%;left:50%;--ox:-28px;--oy:-8px;animation-delay:.8s'></span>
              <span style='top:50%;left:50%;--ox:8px;--oy:28px;animation-delay:1.2s'></span>
              <span style='top:50%;left:50%;--ox:30px;--oy:-5px;animation-delay:.3s'></span>
              <span style='top:50%;left:50%;--ox:-5px;--oy:-30px;animation-delay:1.7s'></span>
            </div>
            <div class='orb-core'>
              <div class='orb-num'>{bhi_cur:.0f}</div>
            </div>
          </div>
          <div style='font-family:Orbitron,sans-serif;font-size:.7rem;letter-spacing:3px;
                      color:{bhi_info["color"]};margin-top:16px;text-align:center'>
            {bhi_info["emoji"]} {bhi_info["level"]}
          </div>
          <div style='font-size:.66rem;color:rgba(200,225,245,.6);text-align:center;
                      margin-top:8px;max-width:160px;line-height:1.6;font-family:Exo 2,sans-serif'>
            {bhi_info["advice"]}
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_mid:
        # BHI 分解
        st.markdown("<div style='padding-top:8px'></div>", unsafe_allow_html=True)
        bhi_series = city_df.get('breathing_health_index',
                                  (city_df['pm25'] / 5).clip(0, 100))
        bhi_avg_7d = float(bhi_series.tail(168).mean()) if len(bhi_series) >= 24 else bhi_cur
        bhi_max_7d = float(bhi_series.tail(168).max()) if len(bhi_series) >= 24 else bhi_cur
        bhi_min_7d = float(bhi_series.tail(168).min()) if len(bhi_series) >= 24 else bhi_cur

        for lbl, val, clr in [
            ('当前 BHI', f'{bhi_cur:.1f}', bhi_info['color']),
            ('7日均值', f'{bhi_avg_7d:.1f}', '#64b5f6'),
            ('7日峰值', f'{bhi_max_7d:.1f}', '#ff5252'),
            ('7日谷值', f'{bhi_min_7d:.1f}', '#00e676'),
        ]:
            pct = min(100, val if isinstance(val, float) else float(val.replace('.', '', 1) if '.' in val else val))
            st.markdown(f"""
            <div style='margin-bottom:14px'>
              <div style='display:flex;justify-content:space-between;
                          font-family:Exo 2,sans-serif;font-size:.7rem;
                          color:rgba(180,210,230,.7);margin-bottom:4px'>
                <span>{lbl}</span>
                <span style='color:{clr};font-weight:700'>{val}</span>
              </div>
              <div class='bhi-bar-bg'>
                <div class='bhi-bar-fill' style='width:{float(val):.0f}%;background:{clr}'></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    with col_trend:
        st.markdown("<div class='sec'>BHI 趋势</div>", unsafe_allow_html=True)
        bs = city_df.get('breathing_health_index', (city_df['pm25'] / 5).clip(0, 100))
        fig_bhi = go.Figure()
        for th, lbl, clr in [(20,'优质','#00e676'),(40,'良好','#69f0ae'),(60,'预警','#ffd600'),(80,'受损','#ff9100')]:
            fig_bhi.add_hrect(y0=th, y1=th+20 if th<80 else 100,
                              fillcolor=f'{clr}', opacity=0.04, line_width=0)
        fig_bhi.add_trace(go.Scatter(
            x=city_df['timestamp'], y=bs,
            mode='lines', name='BHI',
            line=dict(color=bhi_info['color'], width=2),
            fill='tozeroy', fillcolor=f'rgba(105,240,174,0.06)',
        ))
        for th, lbl, clr in [(20,'优质','#00e676'),(40,'良好','#69f0ae'),(60,'预警','#ffd600'),(80,'受损','#ff9100')]:
            fig_bhi.add_hline(y=th, line_dash='dot', line_color=clr, line_width=0.8,
                              annotation_text=lbl, annotation_font_size=9, annotation_position='right')
        dk(fig_bhi, '', 320)
        st.plotly_chart(fig_bhi, use_container_width=True)

    # BHI 分布饼图
    st.markdown("<div class='sec'>📊 BHI 等级分布</div>", unsafe_allow_html=True)
    c_pie, c_recs = st.columns([1, 2])
    with c_pie:
        thresholds = [0, 20, 40, 60, 80, 101]
        labels_bhi = ['优质呼吸', '良好呼吸', '呼吸预警', '呼吸受损', '呼吸危险']
        bhi_cut = pd.cut(bs, bins=thresholds, labels=labels_bhi, right=False)
        cnt = bhi_cut.value_counts()
        fig_bp = go.Figure(go.Pie(
            labels=cnt.index.tolist(), values=cnt.values,
            marker=dict(colors=BHI_CLR, line=dict(color='rgba(0,0,0,0)', width=0)),
            hole=0.5,
            textfont=dict(family='Exo 2, sans-serif', size=10),
        ))
        dk(fig_bp, '', 280)
        st.plotly_chart(fig_bp, use_container_width=True)

    with c_recs:
        st.markdown("<div class='sec'>🎯 个性化防护建议</div>", unsafe_allow_html=True)
        recs = [
            ('🧘', '运动建议',
             f'{"适宜晨练（推荐06-09时）" if bhi_cur<40 else "建议改为室内运动，暂停户外锻炼"}'),
            ('😷', '口罩建议',
             f'{"推荐N95口罩" if bhi_cur>=60 else ("建议普通口罩" if bhi_cur>=40 else "当前无需佩戴口罩")}'),
            ('🏠', '室内建议',
             f'{"关闭门窗，开启空气净化器" if bhi_cur>=80 else ("减少开窗时间" if bhi_cur>=60 else "适当开窗通风")}'),
            ('🚗', '出行建议',
             f'{"建议减少外出，必要时全程防护" if bhi_cur>=60 else ("可正常出行，避免长时间暴露" if bhi_cur>=40 else "全天适宜外出")}'),
        ]
        rc1, rc2 = st.columns(2)
        for i, (icon, title, text) in enumerate(recs):
            col = rc1 if i % 2 == 0 else rc2
            active_clr = bhi_info['color'] if bhi_cur >= 40 else '#00e676'
            col.markdown(f"""
            <div class='rec-card' style='border-color:rgba(255,255,255,.07)'>
              <div class='rec-icon'>{icon}</div>
              <div class='rec-title' style='color:{active_clr}'>{title}</div>
              <div class='rec-text'>{text}</div>
            </div>
            """, unsafe_allow_html=True)
            col.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


# ┌─────────────────────────────────────────────────────────────┐
# │  TAB 3 · 智能预测                                           │
# └─────────────────────────────────────────────────────────────┘
with tab3:
    # 预测下一小时
    sel_model = models[model_sel]
    lr = city_df.iloc[[-1]].copy().replace([np.inf, -np.inf], 0)
    try:
        Xp = lr.reindex(columns=FCOLS, fill_value=0).fillna(0)
        pred_val = float(max(0.0, sel_model.predict(Xp)[0]))
    except Exception as e:
        st.error(f"预测失败：{e}")
        pred_val = pm25_cur

    pred_aqi = aqi_meta(pred_val)
    pred_bhi = bhi_meta(min(100, pred_val / 5))

    # 预测卡片 + 历史 48h 图
    c_card, c_hist = st.columns([1, 2])

    with c_card:
        st.markdown(f"""
        <div class='glass' style='padding:24px;text-align:center;border-color:rgba(0,212,255,.25)'>
          <div style='font-family:Exo 2,sans-serif;font-size:.62rem;
                      color:rgba(0,212,255,.55);letter-spacing:3px;margin-bottom:14px'>
            {model_sel.upper()} · 下一小时预测
          </div>
          <div style='font-family:Orbitron,sans-serif;font-size:3.2rem;font-weight:900;
                      color:{pred_aqi["color"]};line-height:1;margin-bottom:4px'>
            {pred_val:.1f}
          </div>
          <div style='font-family:Exo 2,sans-serif;font-size:.75rem;
                      color:rgba(180,210,230,.5);margin-bottom:16px'>
            μg / m³  PM2.5
          </div>
          <div style='display:inline-block;padding:6px 20px;border-radius:30px;
                      background:rgba(0,0,0,.3);border:1px solid {pred_aqi["color"]};
                      font-family:Exo 2,sans-serif;font-weight:700;font-size:.9rem;
                      color:{pred_aqi["color"]};margin-bottom:16px'>
            {pred_aqi["level"]}
          </div>
          <div style='font-size:.72rem;color:rgba(200,225,245,.65);
                      font-family:Exo 2,sans-serif;line-height:1.8'>
            当前：{pm25_cur:.1f} → 预测：{pred_val:.1f}<br>
            变幅：{'↑' if pred_val>pm25_cur else '↓'}{abs(pred_val-pm25_cur):.1f} μg/m³<br>
            健康风险：{pred_aqi["risk"]}
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c_hist:
        st.markdown("<div class='sec'>历史48h + 预测</div>", unsafe_allow_html=True)
        hist48 = city_df.tail(48)
        next_ts = city_df['timestamp'].iloc[-1] + pd.Timedelta(hours=1)
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(
            x=hist48['timestamp'], y=hist48['pm25'],
            mode='lines', name='历史实况',
            line=dict(color='#00d4ff', width=2),
        ))
        fig_p.add_trace(go.Scatter(
            x=[city_df['timestamp'].iloc[-1], next_ts],
            y=[pm25_cur, pred_val],
            mode='lines+markers', name=f'{model_sel} 预测',
            line=dict(color=pred_aqi['color'], width=3, dash='dash'),
            marker=dict(size=[6, 16], color=['#00d4ff', pred_aqi['color']],
                        symbol=['circle', 'diamond'],
                        line=dict(color='#030a14', width=2)),
        ))
        dk(fig_p, '', 360)
        fig_p.update_layout(legend=dict(orientation='h', y=1.08, x=0.01, font=dict(size=11)))
        st.plotly_chart(fig_p, use_container_width=True)

    # 24小时参考预测表（基于历史同时段统计）
    st.markdown("<div class='sec'>📋 未来24小时参考预测（基于历史同时段均值）</div>", unsafe_allow_html=True)

    if 'hour' in city_df.columns:
        hour_stats = city_df.groupby('hour')['pm25'].agg(['mean', 'std']).reset_index()
        hour_stats.columns = ['hour', 'mean', 'std']
        base_ts = city_df['timestamp'].iloc[-1]
        rows_html = ''
        for i in range(1, min(25, forecast_h + 1)):
            fts = base_ts + pd.Timedelta(hours=i)
            fh  = fts.hour
            row = hour_stats[hour_stats['hour'] == fh]
            if len(row) == 0:
                continue
            fmean = float(row['mean'].values[0])
            fstd  = float(row['std'].values[0])
            fa    = aqi_meta(fmean)
            bl    = aqi_level_str(max(0, fmean - fstd))
            bh    = aqi_level_str(min(500, fmean + fstd))
            rows_html += (
                f"<tr>"
                f"<td style='color:rgba(0,212,255,.7)'>{fts.strftime('%m/%d %H:00')}</td>"
                f"<td><span class='fc-dot' style='background:{fa['color']}'></span>"
                f"<span style='color:{fa['color']};font-weight:700'>{fmean:.1f}</span></td>"
                f"<td style='color:rgba(180,210,230,.5)'>{max(0,fmean-fstd):.1f} ~ {fmean+fstd:.1f}</td>"
                f"<td style='color:{fa['color']}'>{fa['level']}</td>"
                f"<td style='color:rgba(180,210,230,.5)'>{fa['risk']}</td>"
                f"</tr>"
            )
        st.markdown(f"""
        <div class='glass' style='padding:16px;overflow-x:auto'>
          <table class='forecast-table'>
            <thead><tr>
              <th>时间</th><th>预测PM2.5</th><th>区间(±1σ)</th><th>等级</th><th>健康风险</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)

    # 历史预测误差（若有）
    if not df_pred.empty:
        st.markdown("<div class='sec'>📈 批量历史预测效果评估</div>", unsafe_allow_html=True)
        n = min(600, len(df_pred))
        fig_cmp = make_subplots(rows=2, cols=1,
                                subplot_titles=('预测值 vs 真实值', '误差分布'),
                                vertical_spacing=0.12, row_heights=[0.6, 0.4])
        fig_cmp.add_trace(go.Scatter(x=list(range(n)), y=df_pred['true_value'][:n],
                                     mode='lines', name='真实值',
                                     line=dict(color='#00d4ff', width=1.5)), row=1, col=1)
        fig_cmp.add_trace(go.Scatter(x=list(range(n)), y=df_pred['predicted_value'][:n],
                                     mode='lines', name='预测值',
                                     line=dict(color='#ff9100', width=1.5)), row=1, col=1)
        fig_cmp.add_trace(go.Histogram(x=df_pred['error'][:n], nbinsx=60,
                                       marker=dict(color='#69f0ae', opacity=0.8),
                                       name='误差'), row=2, col=1)
        mae  = np.abs(df_pred['error']).mean()
        rmse = np.sqrt((df_pred['error'] ** 2).mean())
        mask = df_pred['true_value'] > 1
        mape = float(np.mean(np.abs(df_pred.loc[mask, 'error'] / df_pred.loc[mask, 'true_value'])) * 100) if mask.any() else 0
        fig_cmp.update_layout(
            title=dict(text=f'MAE = {mae:.2f}  ·  RMSE = {rmse:.2f}  ·  MAPE = {mape:.1f}%',
                       font=dict(size=12, color='rgba(0,212,255,.85)',
                                  family='Consolas,monospace'), x=0.01),
            height=560, **_DARK)
        fig_cmp.update_layout(legend=dict(orientation='h', y=1.06, x=0.01, font=dict(size=11)))
        st.plotly_chart(fig_cmp, use_container_width=True)

    # 多模型雷达图
    if not df_comp.empty and 'test_r2' in df_comp.columns:
        st.markdown("<div class='sec'>🎯 多模型性能雷达对比</div>", unsafe_allow_html=True)
        c_rdr, c_tbl = st.columns([1, 1])
        with c_rdr:
            fig_r = go.Figure()
            model_colors = ['#00d4ff', '#ff9100', '#00e676', '#d500f9', '#ff5252']
            for i, (mname, row) in enumerate(df_comp.iterrows()):
                r2n   = max(0, float(row.get('test_r2', 0)))
                maen  = max(0, 1 - float(row.get('test_mae', 20)) / 20)
                rmsen = max(0, 1 - float(row.get('test_rmse', 25)) / 25)
                clr   = model_colors[i % len(model_colors)]
                fig_r.add_trace(go.Scatterpolar(
                    r=[r2n, maen, rmsen, r2n],
                    theta=['R²', '低MAE', '低RMSE', 'R²'],
                    fill='toself', name=mname, opacity=0.65,
                    line=dict(color=clr, width=2),
                    fillcolor=f'rgba({int(clr[1:3],16)},{int(clr[3:5],16)},{int(clr[5:7],16)},0.1)',
                ))
            fig_r.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=9)),
                    angularaxis=dict(tickfont=dict(family='Exo 2,sans-serif', size=11)),
                ),
                paper_bgcolor='rgba(0,0,0,0)', height=360,
                font=dict(color='#b8cfe0', family='Exo 2,sans-serif'),
                legend=dict(font=dict(size=11)),
                margin=dict(l=60, r=60, t=30, b=30),
            )
            st.plotly_chart(fig_r, use_container_width=True)

        with c_tbl:
            st.markdown("<div class='sec'>模型精度排名</div>", unsafe_allow_html=True)
            best_model = df_comp['test_r2'].idxmax() if 'test_r2' in df_comp.columns else ''
            tbl_rows = ''
            for mname, row in df_comp.sort_values('test_r2', ascending=False).iterrows():
                badge = "<span class='model-best'>★ BEST</span>" if mname == best_model else ''
                tbl_rows += (
                    f"<tr><td>{mname}{badge}</td>"
                    f"<td style='color:#00d4ff'>{row.get('test_mae', '-'):.2f}</td>"
                    f"<td style='color:#ff9100'>{row.get('test_rmse', '-'):.2f}</td>"
                    f"<td style='color:#00e676'>{row.get('test_r2', '-'):.4f}</td></tr>"
                )
            st.markdown(f"""
            <div class='glass' style='padding:14px'>
              <table class='forecast-table'>
                <thead><tr><th>模型</th><th>MAE</th><th>RMSE</th><th>R²</th></tr></thead>
                <tbody>{tbl_rows}</tbody>
              </table>
            </div>
            """, unsafe_allow_html=True)


# ┌─────────────────────────────────────────────────────────────┐
# │  TAB 4 · 深度分析                                           │
# └─────────────────────────────────────────────────────────────┘
with tab4:
    # 相关性矩阵 + 季节分布
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='sec'>🔗 特征相关性矩阵</div>", unsafe_allow_html=True)
        feats_corr = [f for f in ['pm25', 'temperature', 'pressure', 'wind_speed', 'dewpoint', 'snow_hours']
                      if f in city_df.columns]
        if len(feats_corr) >= 2:
            corr = city_df[feats_corr].corr()
            fig_c = go.Figure(go.Heatmap(
                z=corr.values, x=feats_corr, y=feats_corr,
                colorscale='RdBu_r', zmid=0,
                text=[[f'{v:.2f}' for v in row] for row in corr.values],
                texttemplate='%{text}', textfont=dict(size=10, family='Consolas,monospace'),
                colorbar=dict(title='r', tickfont=dict(size=9)),
            ))
            dk(fig_c, '', 380)
            st.plotly_chart(fig_c, use_container_width=True)

    with c2:
        st.markdown("<div class='sec'>📅 月度 PM2.5 趋势（箱线图）</div>", unsafe_allow_html=True)
        if 'month' in city_df.columns:
            month_names = {1:'1月',2:'2月',3:'3月',4:'4月',5:'5月',6:'6月',
                           7:'7月',8:'8月',9:'9月',10:'10月',11:'11月',12:'12月'}
            fig_box = go.Figure()
            for m in sorted(city_df['month'].unique()):
                sub = city_df[city_df['month'] == m]['pm25']
                fig_box.add_trace(go.Box(
                    y=sub, name=month_names.get(m, str(m)),
                    boxpoints=False, line=dict(width=1.5),
                    marker=dict(opacity=0),
                ))
            dk(fig_box, '', 380)
            st.plotly_chart(fig_box, use_container_width=True)

    # 3D 散点
    st.markdown("<div class='sec'>🌐 温度 × 风速 × PM2.5 三维分布</div>", unsafe_allow_html=True)
    if ('temperature' in city_df.columns and 'wind_speed' in city_df.columns
            and len(city_df) > 20):
        smp = city_df.sample(min(4000, len(city_df)), random_state=42)
        fig_3d = go.Figure(go.Scatter3d(
            x=smp['temperature'], y=smp['wind_speed'], z=smp['pm25'],
            mode='markers',
            marker=dict(
                size=3, color=smp['pm25'],
                colorscale='Viridis', showscale=True,
                colorbar=dict(title='PM2.5', tickfont=dict(size=9)),
                opacity=0.7,
            ),
        ))
        fig_3d.update_layout(
            scene=dict(
                xaxis=dict(title='温度(°C)', gridcolor='rgba(255,255,255,0.06)',
                           backgroundcolor='rgba(0,0,0,0)'),
                yaxis=dict(title='风速(m/s)', gridcolor='rgba(255,255,255,0.06)',
                           backgroundcolor='rgba(0,0,0,0)'),
                zaxis=dict(title='PM2.5(μg/m³)', gridcolor='rgba(255,255,255,0.06)',
                           backgroundcolor='rgba(0,0,0,0)'),
                bgcolor='rgba(0,0,0,0)',
            ),
            paper_bgcolor='rgba(0,0,0,0)', height=500,
            font=dict(color='#b8cfe0', family='Exo 2,sans-serif'),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_3d, use_container_width=True)

    # 特征重要性
    if not df_imp.empty:
        st.markdown("<div class='sec'>🔬 Top 20 特征重要性</div>", unsafe_allow_html=True)
        top = df_imp.head(20)
        colors_fi = [
            '#00d4ff' if 'pm25' in f else
            '#00e676' if any(x in f for x in ['hour', 'month', 'season', 'sin', 'cos']) else
            '#ff9100' if any(x in f for x in ['temp', 'wind', 'pressure']) else
            '#ffd600' if 'rolling' in f or 'lag' in f else
            '#b0bec5'
            for f in top['feature']
        ]
        fig_fi = go.Figure(go.Bar(
            y=top['feature'], x=top['importance'], orientation='h',
            marker=dict(color=colors_fi, line=dict(width=0)),
            text=[f'{v:.4f}' for v in top['importance']],
            textposition='outside', textfont=dict(size=9, family='Consolas,monospace'),
        ))
        dk(fig_fi, '', 500)
        fig_fi.update_layout(yaxis=dict(autorange='reversed'))
        st.plotly_chart(fig_fi, use_container_width=True)

        # 图例说明
        st.markdown("""
        <div style='display:flex;gap:16px;font-family:Exo 2,sans-serif;font-size:.68rem;
                    color:rgba(180,210,230,.65);flex-wrap:wrap;margin-top:-8px'>
          <span><span style='color:#00d4ff'>■</span> PM2.5 相关特征</span>
          <span><span style='color:#00e676'>■</span> 时间/季节特征</span>
          <span><span style='color:#ff9100'>■</span> 气象特征</span>
          <span><span style='color:#ffd600'>■</span> 滞后/滚动特征</span>
        </div>
        """, unsafe_allow_html=True)

    # 年度趋势
    st.markdown("<div class='sec'>📆 年度 PM2.5 均值与波动</div>", unsafe_allow_html=True)
    yr = city_df.copy()
    yr['year'] = yr['timestamp'].dt.year
    ya = yr.groupby('year')['pm25'].agg(['mean', 'std', 'min', 'max']).reset_index()
    fig_yr = go.Figure()
    fig_yr.add_trace(go.Scatter(
        x=list(ya['year']) + list(ya['year'])[::-1],
        y=list(ya['mean'] + ya['std']) + list(ya['mean'] - ya['std'])[::-1],
        fill='toself', fillcolor='rgba(0,212,255,0.08)',
        line=dict(color='rgba(0,0,0,0)'), name='±1σ 波动区间',
    ))
    fig_yr.add_trace(go.Scatter(
        x=ya['year'], y=ya['mean'], mode='lines+markers', name='年均值',
        line=dict(color='#00d4ff', width=3),
        marker=dict(size=10, color='#00d4ff', line=dict(color='#030a14', width=2)),
    ))
    fig_yr.add_trace(go.Scatter(
        x=ya['year'], y=ya['max'], mode='lines', name='年最大值',
        line=dict(color='#ff5252', width=1.5, dash='dot'),
    ))
    dk(fig_yr, '', 340)
    fig_yr.update_layout(legend=dict(orientation='h', y=1.1, x=0.01, font=dict(size=11)))
    st.plotly_chart(fig_yr, use_container_width=True)


# ┌─────────────────────────────────────────────────────────────┐
# │  TAB 5 · 城市对比                                           │
# └─────────────────────────────────────────────────────────────┘
with tab5:
    if not have_city:
        st.markdown("""
        <div class='glass' style='text-align:center;padding:60px 40px'>
          <div style='font-size:3rem;margin-bottom:16px'>🌏</div>
          <div style='font-family:Exo 2,sans-serif;font-size:1rem;color:rgba(0,212,255,.6);margin-bottom:10px'>
            当前数据集为单城市模式
          </div>
          <div style='font-family:Exo 2,sans-serif;font-size:.78rem;color:rgba(180,210,230,.5);line-height:1.8'>
            运行 <code style='background:rgba(0,212,255,.1);padding:2px 8px;border-radius:4px'>
            python 0_collect_multi_source_data.py</code> 采集多城市数据<br>
            或运行 <code style='background:rgba(0,212,255,.1);padding:2px 8px;border-radius:4px'>
            python 7_multi_city_fusion.py</code> 进行城市融合分析
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        cities = sorted(df_all['city'].unique())
        city_stats = df_all.groupby('city')['pm25'].agg(['mean', 'std', 'median', 'max']).reset_index()
        city_stats.columns = ['city', 'mean', 'std', 'median', 'max']
        city_stats = city_stats.sort_values('mean', ascending=False)

        # 城市均值对比
        st.markdown("<div class='sec'>🏙️ 城市 PM2.5 均值对比</div>", unsafe_allow_html=True)
        clrs_city = [aqi_meta(v)['color'] for v in city_stats['mean']]
        fig_city = go.Figure(go.Bar(
            x=city_stats['city'], y=city_stats['mean'],
            marker=dict(color=clrs_city, line=dict(width=0)),
            error_y=dict(type='data', array=city_stats['std'], color='rgba(255,255,255,0.3)'),
            text=[f'{v:.1f}' for v in city_stats['mean']],
            textposition='outside',
            textfont=dict(size=10, family='Consolas,monospace'),
        ))
        dk(fig_city, '', 340)
        st.plotly_chart(fig_city, use_container_width=True)

        # 各城市时序叠加
        st.markdown("<div class='sec'>📈 各城市 PM2.5 时序叠加（月均）</div>", unsafe_allow_html=True)
        fig_mc = go.Figure()
        palette = ['#00d4ff', '#ff9100', '#00e676', '#d500f9', '#ff5252', '#ffd600']
        for i, city_name in enumerate(cities):
            sub = df_all[df_all['city'] == city_name].copy()
            sub['ym'] = sub['timestamp'].dt.to_period('M').astype(str)
            mo = sub.groupby('ym')['pm25'].mean().reset_index()
            fig_mc.add_trace(go.Scatter(
                x=mo['ym'], y=mo['pm25'], mode='lines',
                name=city_name,
                line=dict(color=palette[i % len(palette)], width=2),
            ))
        dk(fig_mc, '', 380)
        fig_mc.update_layout(legend=dict(orientation='h', y=1.1, x=0.01, font=dict(size=11)))
        st.plotly_chart(fig_mc, use_container_width=True)

        # 城市 AQI 分布并排
        st.markdown("<div class='sec'>🎨 各城市 AQI 分布</div>", unsafe_allow_html=True)
        n_c = len(cities)
        cols_city = st.columns(min(n_c, 4))
        for i, city_name in enumerate(cities[:4]):
            sub = df_all[df_all['city'] == city_name]
            ac2 = sub['pm25'].apply(aqi_level_str).value_counts()
            fig_cp = go.Figure(go.Pie(
                labels=ac2.index, values=ac2.values,
                marker=dict(colors=[PIE_CLR.get(l, '#888') for l in ac2.index],
                            line=dict(color='rgba(0,0,0,0)', width=0)),
                hole=0.5, showlegend=False,
                textfont=dict(size=9),
            ))
            dk(fig_cp, city_name, 220)
            cols_city[i % 4].plotly_chart(fig_cp, use_container_width=True)


# ┌─────────────────────────────────────────────────────────────┐
# │  TAB 6 · 大数据洞察                                         │
# └─────────────────────────────────────────────────────────────┘
with tab6:
    # 大数字统计
    st.markdown("<div class='sec'>📦 数据集规模概览</div>", unsafe_allow_html=True)
    gc1, gc2, gc3, gc4, gc5 = st.columns(5)
    span_full = (df_all['timestamp'].max() - df_all['timestamp'].min()).days
    for col, val, lbl in zip(
        [gc1, gc2, gc3, gc4, gc5],
        [f"{len(df_all):,}", f"{span_full}", f"{df_all.shape[1]}", f"{n_cities}", f"{df_all['pm25'].mean():.1f}"],
        ['总记录数 (条)', '时间跨度 (天)', '特征维度', '城市 / 站点', 'PM2.5 均值 μg/m³'],
    ):
        col.markdown(f"<div class='bignum-card'><div class='bignum-val'>{val}</div><div class='bignum-lbl'>{lbl}</div></div>", unsafe_allow_html=True)

    # 处理管道流图
    st.markdown("<div class='sec'>⚙️ 数据处理全链路管道</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='glass' style='padding:20px'>
      <div class='pipeline'>
        <div class='pipe-step'><div class='pipe-step-icon'>📡</div><div class='pipe-step-name'>数据采集</div></div>
        <div class='pipe-arrow'>→</div>
        <div class='pipe-step'><div class='pipe-step-icon'>🧹</div><div class='pipe-step-name'>数据清洗</div></div>
        <div class='pipe-arrow'>→</div>
        <div class='pipe-step'><div class='pipe-step-icon'>⚗️</div><div class='pipe-step-name'>特征工程</div></div>
        <div class='pipe-arrow'>→</div>
        <div class='pipe-step'><div class='pipe-step-icon'>🤖</div><div class='pipe-step-name'>模型训练</div></div>
        <div class='pipe-arrow'>→</div>
        <div class='pipe-step'><div class='pipe-step-icon'>🔬</div><div class='pipe-step-name'>消融实验</div></div>
        <div class='pipe-arrow'>→</div>
        <div class='pipe-step'><div class='pipe-step-icon'>📊</div><div class='pipe-step-name'>可视化</div></div>
        <div class='pipe-arrow'>→</div>
        <div class='pipe-step'><div class='pipe-step-icon'>🚀</div><div class='pipe-step-name'>Web部署</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 全量 AQI 分布 + 年度趋势
    ca6, cb6 = st.columns(2)
    with ca6:
        st.markdown("<div class='sec'>🎨 全量数据 AQI 分布</div>", unsafe_allow_html=True)
        aac = df_all['pm25'].apply(aqi_level_str).value_counts()
        fig_aac = go.Figure(go.Pie(
            labels=aac.index, values=aac.values,
            marker=dict(colors=[PIE_CLR.get(l, '#888') for l in aac.index],
                        line=dict(color='rgba(0,0,0,0)', width=0)),
            hole=0.5, textfont=dict(family='Exo 2,sans-serif', size=11),
        ))
        dk(fig_aac, '', 340)
        st.plotly_chart(fig_aac, use_container_width=True)

    with cb6:
        st.markdown("<div class='sec'>📆 全量数据年度趋势</div>", unsafe_allow_html=True)
        ya2 = df_all.copy()
        ya2['year'] = ya2['timestamp'].dt.year
        ya2g = ya2.groupby('year')['pm25'].agg(['mean', 'std']).reset_index()
        fig_ya2 = go.Figure()
        fig_ya2.add_trace(go.Scatter(
            x=list(ya2g['year']) + list(ya2g['year'])[::-1],
            y=list(ya2g['mean'] + ya2g['std']) + list(ya2g['mean'] - ya2g['std'])[::-1],
            fill='toself', fillcolor='rgba(0,212,255,0.08)',
            line=dict(color='rgba(0,0,0,0)'), name='±1σ',
        ))
        fig_ya2.add_trace(go.Scatter(
            x=ya2g['year'], y=ya2g['mean'], mode='lines+markers', name='年均',
            line=dict(color='#00d4ff', width=3),
            marker=dict(size=10, color='#00d4ff', line=dict(color='#030a14', width=2)),
        ))
        dk(fig_ya2, '', 340)
        st.plotly_chart(fig_ya2, use_container_width=True)

    # 数据来源说明
    st.markdown("<div class='sec'>📚 数据来源与可信度声明</div>", unsafe_allow_html=True)
    srcs = [
        ('#00d4ff', '📦 UCI 北京 PM2.5 数据集',
         '2010–2014年北京逐小时PM2.5与气象数据，原始记录43,824条，权威公开学术数据集，被数百篇论文引用',
         'https://archive.ics.uci.edu/ml/datasets/Beijing+PM2.5+Data'),
        ('#69f0ae', '📡 OpenAQ 开放平台',
         '全球开放空气质量数据，覆盖100+国家实时监测站，免费API接入，无需注册，数据实时更新',
         'https://openaq.org/'),
        ('#ffd600', '🌤 NOAA GSOD 气象数据',
         'NOAA全球地面气象日汇总数据集，1929年至今，涵盖全球数千个气象站，补充气象特征维度',
         'https://www.ncei.noaa.gov/data/global-summary-of-the-day/'),
    ]
    sc1, sc2, sc3 = st.columns(3)
    for col, (clr, name, desc, url) in zip([sc1, sc2, sc3], srcs):
        col.markdown(f"""
        <div class='src-card' style='border:1px solid {clr}25'>
          <div class='src-name' style='color:{clr}'>{name}</div>
          <div class='src-desc'>{desc}</div>
          <div class='src-url'>{url}</div>
        </div>
        """, unsafe_allow_html=True)

    # 数据下载
    st.markdown("<div class='sec'>⬇️ 数据导出</div>", unsafe_allow_html=True)
    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        csv_sub = city_df[['timestamp', 'pm25']].to_csv(index=False).encode()
        st.download_button('⬇️ 下载当前视图 PM2.5 数据', csv_sub,
                           'pm25_data.csv', 'text/csv', use_container_width=True)
    with dl2:
        if not df_pred.empty:
            st.download_button('⬇️ 下载预测结果', df_pred.to_csv(index=False).encode(),
                               'predictions.csv', 'text/csv', use_container_width=True)
        else:
            st.button('⬇️ 预测结果（暂无）', disabled=True, use_container_width=True)
    with dl3:
        if not df_comp.empty:
            st.download_button('⬇️ 下载模型对比表', df_comp.to_csv().encode(),
                               'model_comparison.csv', 'text/csv', use_container_width=True)
        else:
            st.button('⬇️ 模型对比（暂无）', disabled=True, use_container_width=True)


# ┌─────────────────────────────────────────────────────────────┐
# │  TAB 7  ·  AI 智能分析中心(离线规则 + DeepSeek 深度分析)      │
# └─────────────────────────────────────────────────────────────┘
with tab7:
    # 引入 AI 引擎(独立模块,失败时优雅降级)
    try:
        from qa_engine import AirQualityQAEngine
        _qa_ok = True
    except Exception as _e:
        _qa_ok = False
        st.error(f"AI 引擎加载失败:{_e}")

    # 引入 DeepSeek 深度分析(可选,失败优雅降级)
    try:
        import deep_analysis as dsmod
        _ds_ok = True
    except Exception:
        dsmod = None
        _ds_ok = False

    if _qa_ok:
        @st.cache_resource
        def _get_qa_engine(n_rows):
            return AirQualityQAEngine(df_all)
        engine = _get_qa_engine(len(df_all))

        # 检测 DeepSeek 配置
        _llm_key = dsmod.get_api_key() if _ds_ok else None
        _llm_ready = bool(_llm_key)

        # ─── 头部:模式状态卡 ───
        st.markdown("<div class='sec'>🧠 AI 智能分析中心 · INTELLIGENT ANALYSIS HUB</div>",
                    unsafe_allow_html=True)

        mode_c1, mode_c2 = st.columns([2, 1])
        with mode_c1:
            st.markdown("""
            <div class='glass' style='padding:18px;border-color:rgba(139,92,246,.32)'>
              <div style='font-family:Exo 2,sans-serif;font-size:.78rem;
                          color:rgba(200,225,245,.78);line-height:1.8'>
                <span style='color:#b794ff;font-weight:700'>双模式架构</span><br>
                • <b>离线模式</b>(默认)— 12 类规则匹配,演示绝对稳定,无需联网<br>
                • <b>深度模式</b> — DeepSeek-Chat LLM,开放式归因 + 政策建议
              </div>
            </div>
            """, unsafe_allow_html=True)
        with mode_c2:
            if _llm_ready:
                key_disp = dsmod.mask_key(_llm_key)
                st.markdown(
                    "<div class='glass' style='text-align:center;padding:18px;"
                    "border-color:rgba(0,230,118,.35)'>"
                    "<div style='font-size:1.6rem'>🟢</div>"
                    "<div style='font-family:Orbitron,sans-serif;font-size:.7rem;"
                    "letter-spacing:3px;color:#69f0ae;margin-top:6px'>"
                    "深度模式 ONLINE"
                    "</div>"
                    "<div style='font-size:.62rem;color:rgba(180,210,230,.5);"
                    "margin-top:4px;font-family:JetBrains Mono,monospace'>"
                    + key_disp +
                    "</div></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown("""
                <div class='glass' style='text-align:center;padding:18px;
                            border-color:rgba(255,214,0,.32)'>
                  <div style='font-size:1.6rem'>🟡</div>
                  <div style='font-family:Orbitron,sans-serif;font-size:.7rem;
                              letter-spacing:3px;color:#ffd600;margin-top:6px'>
                    离线模式 OFFLINE
                  </div>
                  <div style='font-size:.62rem;color:rgba(180,210,230,.5);margin-top:4px'>
                    配置 secrets.toml 解锁深度分析
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════
        # 子区 1: AI 自动洞察(仅深度模式)
        # ═══════════════════════════════════════════════════
        if _llm_ready:
            st.markdown("<div class='sec'>💡 AI 自动洞察 · AUTO INSIGHTS</div>",
                        unsafe_allow_html=True)

            @st.cache_data(ttl=3600, show_spinner=False)
            def _gen_insights_cached(_hash, _summary):
                client = dsmod.DeepSeekClient(_llm_key)
                return client.auto_insights(_summary)

            cb1, cb2 = st.columns([1, 3])
            with cb1:
                refresh_ins = st.button('🔄  生成/刷新洞察',
                                         use_container_width=True,
                                         key='btn_refresh_ins')
            with cb2:
                st.markdown("""
                <div style='padding:8px 12px;font-size:.7rem;
                            color:rgba(180,210,230,.6);
                            font-family:Exo 2,sans-serif;line-height:1.7'>
                  💰 单次约 ¥0.001-0.003 · 缓存 1 小时 · 数据变化时自动重算
                </div>
                """, unsafe_allow_html=True)

            if refresh_ins or 'insights_cache' not in st.session_state:
                with st.spinner('🧠 DeepSeek 正在分析数据...'):
                    summary = dsmod.build_data_summary(city_df)
                    h = dsmod.summary_hash(summary)
                    st.session_state.insights_cache = _gen_insights_cached(h, summary)

            ins_result = st.session_state.get('insights_cache', {})
            if ins_result.get('ok'):
                ins_list = ins_result.get('insights', [])
                if ins_list:
                    cols_n = min(len(ins_list), 5)
                    ins_cols = st.columns(cols_n)
                    level_color = {'info': '#64b5f6', 'warn': '#ffd600', 'crit': '#ff5252'}
                    for i, ins in enumerate(ins_list[:5]):
                        clr = level_color.get(ins.get('level', 'info'), '#00d4ff')
                        ic = ins.get('icon', '📊')
                        ti = ins.get('title', '')
                        ds = ins.get('desc', '')
                        ins_cols[i].markdown(
                            "<div class='glass' style='border-color:" + clr + "40;"
                            "padding:14px;min-height:160px'>"
                            "<div style='font-size:1.4rem;margin-bottom:6px'>" + ic + "</div>"
                            "<div style='font-family:Exo 2,sans-serif;font-weight:700;"
                            "font-size:.82rem;color:" + clr + ";margin-bottom:6px;"
                            "letter-spacing:1px'>" + ti + "</div>"
                            "<div style='font-size:.7rem;color:rgba(200,225,245,.78);"
                            "line-height:1.7'>" + ds + "</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )
                    st.markdown(
                        "<div style='text-align:right;font-size:.62rem;"
                        "color:rgba(180,210,230,.45);"
                        "font-family:JetBrains Mono,monospace;margin-top:6px'>"
                        "本次费用: " + ins_result.get('cost', '—') + " · powered by DeepSeek"
                        "</div>",
                        unsafe_allow_html=True
                    )
            elif ins_result.get('error'):
                st.markdown(
                    "<div class='alert alert-orange' style='font-size:.78rem'>"
                    "⚠️ 生成失败: " + ins_result['error'] + " — 已自动回退,可继续用问答"
                    "</div>",
                    unsafe_allow_html=True
                )

        # ═══════════════════════════════════════════════════
        # 子区 2: 智能问答(双模式)
        # ═══════════════════════════════════════════════════
        st.markdown("<div class='sec'>💬 智能问答 · ASK ANYTHING</div>",
                    unsafe_allow_html=True)

        # 模式开关
        use_deep = False
        if _llm_ready:
            use_deep = st.toggle('🚀 启用深度模式(LLM 推理,可问开放式问题)',
                                  value=False, key='use_deep_qa')

        st.markdown("""
        <div class='glass' style='padding:18px;margin-bottom:14px'>
          <div style='font-family:Exo 2,sans-serif;font-size:.78rem;
                      color:rgba(200,225,245,.78);line-height:1.8'>
            💡 <b>直接用中文问数据集相关的任何问题</b>。
          </div>
        </div>
        """, unsafe_allow_html=True)

        # 状态
        if 'ai_input' not in st.session_state:
            st.session_state.ai_input = ''
        if 'ai_history' not in st.session_state:
            st.session_state.ai_history = []

        # 推荐问题(根据模式动态切换)
        st.markdown("<div class='sec'>💎 试试这些问题</div>", unsafe_allow_html=True)
        suggested_offline = [
            '历史最高 PM2.5 出现在什么时候?',
            '哪个月份污染最严重?',
            '一天中什么时段空气最差?',
            '风速对 PM2.5 有什么影响?',
            '整体平均浓度是多少?',
            '当前给我一个健康建议',
            'BHI 是什么?',
            'MSTN 模型精度怎样?',
            'PM2.5 超过 75 的样本占比?',
            '历年趋势如何?',
        ]
        suggested_deep = [
            '为什么冬季污染这么严重?从气象学角度分析',
            '如果取消机动车限行,PM2.5 会涨多少?',
            '北京和华北雾霾的根本成因是什么?',
            '从这些数据能看出环保政策的效果吗?',
            '老人和小孩的防护策略应该有什么不同?',
        ]
        show_sug = suggested_deep if use_deep else suggested_offline
        sg_cols = st.columns(min(5, len(show_sug)))
        for i, s in enumerate(show_sug):
            if sg_cols[i % 5].button(s, key='sg_' + str(i) + '_' + str(use_deep),
                                      use_container_width=True):
                st.session_state.ai_input = s

        # 输入与按钮
        user_q = st.text_input(
            '🔎  请输入你的问题',
            value=st.session_state.ai_input,
            placeholder='深度模式可问开放式问题,离线模式答 12 类高频问题',
            key='ai_input_box',
            label_visibility='collapsed'
        )
        bc1, bc2, _bsp = st.columns([1, 1, 5])
        with bc1:
            ask = st.button('🚀  提问', use_container_width=True, key='btn_ask')
        with bc2:
            clr = st.button('🗑️  清空', use_container_width=True, key='btn_clr')
        if clr:
            st.session_state.ai_history = []
            st.session_state.ai_input = ''
            st.rerun()

        # 处理提问
        if ask and user_q.strip():
            if use_deep and _llm_ready:
                with st.spinner('🧠 DeepSeek 正在思考...'):
                    client = dsmod.DeepSeekClient(_llm_key)
                    ctx = dsmod.build_data_context(city_df)
                    rsp = client.deep_qa(user_q.strip(), ctx)
                if rsp['ok']:
                    result = {
                        'answer': rsp['answer'],
                        'data': None,
                        'chart_hint': None,
                        'mode': 'deep',
                        'cost': rsp.get('cost', '—'),
                    }
                else:
                    # 失败回退到离线
                    result = engine.query(user_q.strip())
                    result['mode'] = 'offline_fallback'
                    result['fallback_reason'] = rsp['error']
            else:
                result = engine.query(user_q.strip())
                result['mode'] = 'offline'
            st.session_state.ai_history.insert(0, {'q': user_q.strip(), 'r': result})
            st.session_state.ai_input = ''

        # 渲染对话历史
        if st.session_state.ai_history:
            st.markdown("<div class='sec'>📜 对话记录</div>", unsafe_allow_html=True)
            for entry in st.session_state.ai_history[:8]:
                q = entry['q']
                r = entry['r']
                # 模式徽章
                mode = r.get('mode', 'offline')
                badge_map = {
                    'deep': "<span style='background:rgba(139,92,246,.2);color:#b794ff;"
                            "padding:2px 8px;border-radius:10px;font-size:.6rem;"
                            "letter-spacing:1px'>🚀 深度</span>",
                    'offline': "<span style='background:rgba(0,212,255,.15);color:#80deea;"
                               "padding:2px 8px;border-radius:10px;font-size:.6rem;"
                               "letter-spacing:1px'>⚡ 离线</span>",
                    'offline_fallback': "<span style='background:rgba(255,145,0,.2);"
                                        "color:#ffb74d;padding:2px 8px;border-radius:10px;"
                                        "font-size:.6rem;letter-spacing:1px'>⚠️ 回退</span>",
                }
                badge = badge_map.get(mode, '')
                cost_tag = ''
                if r.get('cost') and r['cost'] != '—':
                    cost_tag = ("<span style='font-size:.6rem;color:rgba(180,210,230,.45);"
                                "margin-left:8px;font-family:JetBrains Mono,monospace'>"
                                + r['cost'] + "</span>")
                fb_tag = ''
                if r.get('fallback_reason'):
                    fb_tag = ("<div style='font-size:.65rem;color:#ffb74d;margin-top:4px'>"
                              "⚠️ LLM 调用失败(" + r['fallback_reason'] + "),已自动回退"
                              "</div>")

                ans_html = r['answer'].replace('\n\n', '<br><br>').replace('\n', '<br>')
                st.markdown(
                    "<div class='ai-chat-window' style='max-height:none;margin-bottom:10px'>"
                    "<div class='ai-msg ai-msg-user'>" + q + "</div>"
                    "<div class='ai-msg ai-msg-ai'>"
                    "<span class='ai-tag'>AI · 时空呼吸智能体 " + badge + cost_tag + "</span>"
                    + ans_html + fb_tag +
                    "</div></div>",
                    unsafe_allow_html=True
                )

                # 配可视化
                if r.get('data') is not None and isinstance(r['data'], pd.DataFrame) and not r['data'].empty:
                    hint = r.get('chart_hint', '')
                    df_r = r['data']
                    if hint == 'bar_month':
                        fig_q = go.Figure(go.Bar(
                            x=df_r['month'].astype(str) + '月',
                            y=df_r['月均PM2.5'],
                            marker=dict(color=df_r['月均PM2.5'], colorscale='RdYlGn_r',
                                        line=dict(width=0)),
                            text=[f'{v:.0f}' for v in df_r['月均PM2.5']],
                            textposition='outside',
                        ))
                        dk(fig_q, '', 320)
                        st.plotly_chart(fig_q, use_container_width=True)
                    elif hint == 'line_hour':
                        fig_q = go.Figure(go.Scatter(
                            x=df_r['hour'], y=df_r['时均PM2.5'], mode='lines+markers',
                            line=dict(color='#00d4ff', width=2.5),
                            marker=dict(size=8, color=df_r['时均PM2.5'], colorscale='RdYlGn_r',
                                        line=dict(color='#030a14', width=2)),
                            fill='tozeroy', fillcolor='rgba(0,212,255,.06)',
                        ))
                        fig_q.update_layout(xaxis=dict(title='小时', dtick=2),
                                            yaxis=dict(title='PM2.5 (μg/m³)'))
                        dk(fig_q, '', 320)
                        st.plotly_chart(fig_q, use_container_width=True)
                    elif hint == 'corr_bar':
                        cn_map = {'temperature': '温度', 'wind_speed': '风速',
                                  'pressure': '气压', 'dewpoint': '露点'}
                        df_r['气象因子_cn'] = df_r['气象因子'].map(lambda x: cn_map.get(x, x))
                        clrs = ['#ff5252' if v > 0 else '#00e676' for v in df_r['r 系数']]
                        fig_q = go.Figure(go.Bar(
                            x=df_r['气象因子_cn'], y=df_r['r 系数'],
                            marker=dict(color=clrs, line=dict(width=0)),
                            text=[f'{v:+.3f}' for v in df_r['r 系数']],
                            textposition='outside',
                        ))
                        fig_q.update_layout(yaxis=dict(title='与 PM2.5 相关系数 r', range=[-1, 1]))
                        dk(fig_q, '', 320)
                        st.plotly_chart(fig_q, use_container_width=True)
                    elif hint == 'line_year':
                        fig_q = go.Figure(go.Scatter(
                            x=df_r['year'], y=df_r['年均PM2.5'], mode='lines+markers',
                            line=dict(color='#00d4ff', width=3),
                            marker=dict(size=12, color='#00d4ff',
                                        line=dict(color='#030a14', width=2)),
                        ))
                        dk(fig_q, '', 300)
                        st.plotly_chart(fig_q, use_container_width=True)

                # 兜底建议
                if r.get('chart_hint') == 'suggestions' and r.get('suggestions'):
                    sug_html = "<div style='margin-top:10px'>"
                    for s in r['suggestions']:
                        sug_html += "<span class='ai-suggest'>" + s + "</span>"
                    sug_html += "</div>"
                    st.markdown(sug_html, unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════
        # 子区 3: 政策建议生成器(仅深度模式)
        # ═══════════════════════════════════════════════════
        if _llm_ready:
            st.markdown("<div class='sec'>🎯 智能政策建议 · POLICY ADVISOR</div>",
                        unsafe_allow_html=True)
            pc1, pc2 = st.columns([2, 1])
            with pc1:
                target = st.selectbox(
                    '👥 目标群体',
                    ['政府决策', '企业减排', '市民防护', '敏感人群(老人/儿童/孕妇/慢病)'],
                    key='policy_target', label_visibility='collapsed')
            with pc2:
                gen_pol = st.button('💎 生成政策建议',
                                     use_container_width=True, key='btn_policy')

            @st.cache_data(ttl=3600, show_spinner=False)
            def _gen_policy_cached(_hash, _target, _summary):
                client = dsmod.DeepSeekClient(_llm_key)
                return client.policy_advice(_target, _summary)

            if gen_pol:
                with st.spinner('🧠 正在为「' + target + '」定制建议...'):
                    summary = dsmod.build_data_summary(city_df)
                    h = dsmod.summary_hash(summary) + target
                    st.session_state['policy_result'] = _gen_policy_cached(h, target, summary)

            pol_result = st.session_state.get('policy_result', {})
            if pol_result.get('ok') and pol_result.get('advice'):
                adv_list = pol_result['advice']
                pri_color = {'high': '#ff5252', 'mid': '#ffd600', 'low': '#69f0ae'}
                pri_label = {'high': '★★★ 高优先', 'mid': '★★ 中优先', 'low': '★ 普通'}
                adv_cols = st.columns(len(adv_list))
                for i, a in enumerate(adv_list):
                    pri = a.get('priority', 'mid')
                    clr = pri_color.get(pri, '#64b5f6')
                    title = a.get('title', '')
                    reason = a.get('reason', '')
                    action = a.get('action', '')
                    pri_lbl = pri_label.get(pri, '')
                    adv_cols[i].markdown(
                        "<div class='glass' style='border-color:" + clr + "50;"
                        "padding:18px;min-height:230px'>"
                        "<div style='font-family:Exo 2,sans-serif;font-size:.6rem;"
                        "letter-spacing:2px;color:" + clr + ";font-weight:700;"
                        "margin-bottom:8px'>" + pri_lbl + "</div>"
                        "<div style='font-family:Exo 2,sans-serif;font-weight:700;"
                        "font-size:.92rem;color:" + clr + ";margin-bottom:10px;"
                        "border-bottom:1px solid " + clr + "30;padding-bottom:8px'>"
                        + title + "</div>"
                        "<div style='font-size:.72rem;color:rgba(200,225,245,.85);"
                        "line-height:1.7;margin-bottom:8px'>"
                        "<b style='color:#80deea'>📊 数据论据:</b><br>" + reason + "</div>"
                        "<div style='font-size:.72rem;color:rgba(200,225,245,.85);"
                        "line-height:1.7'>"
                        "<b style='color:#69f0ae'>🚀 执行细节:</b><br>" + action + "</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                st.markdown(
                    "<div style='text-align:right;font-size:.62rem;"
                    "color:rgba(180,210,230,.45);"
                    "font-family:JetBrains Mono,monospace;margin-top:8px'>"
                    "本次费用: " + pol_result.get('cost', '—') + " · powered by DeepSeek"
                    "</div>",
                    unsafe_allow_html=True
                )
            elif pol_result.get('error'):
                st.markdown(
                    "<div class='alert alert-orange' style='font-size:.78rem'>"
                    "⚠️ 生成失败: " + pol_result['error'] +
                    "</div>",
                    unsafe_allow_html=True
                )


# ═══════════════════════════════════════════════════════════════
# §9  底部
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div class='footer'>
  🌬️ &nbsp; 时空呼吸 &nbsp;·&nbsp; TEMPORAL-SPATIAL BREATHING INTELLIGENCE SYSTEM
  &nbsp;·&nbsp; 大数据实践赛 &nbsp;·&nbsp; 环境与人类发展大数据
</div>
""", unsafe_allow_html=True)