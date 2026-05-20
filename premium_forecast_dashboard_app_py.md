# app.py（正式运营版 UI）

```python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="未来14天课量预测驾驶舱",
    page_icon="📈",
    layout="wide"
)

# =========================
# 页面样式
# =========================

st.markdown(
    """
    <style>
    .main {
        background-color: #f7f9fc;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    h1 {
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# 标题
# =========================

st.title("📈 未来14天课量预测驾驶舱")
st.caption("Booking Curve Forecasting Engine")

# =========================
# Sidebar
# =========================

st.sidebar.header("📂 上传数据")

uploaded_file = st.sidebar.file_uploader(
    "上传未来14天已约课量",
    type=["xlsx"]
)

# =========================
# 默认Booking Curve
# =========================

flex_curve = {
    0: 1.00,
    1: 0.92,
    2: 0.85,
    3: 0.78,
    4: 0.70,
    5: 0.63,
    6: 0.58,
    7: 0.52,
    8: 0.47,
    9: 0.43,
    10: 0.39,
    11: 0.35,
    12: 0.31,
    13: 0.27,
    14: 0.24
}

fixed_curve = {
    0: 1.00,
    1: 0.97,
    2: 0.95,
    3: 0.92,
    4: 0.90,
    5: 0.88,
    6: 0.86,
    7: 0.84,
    8: 0.82,
    9: 0.80,
    10: 0.78,
    11: 0.76,
    12: 0.74,
    13: 0.72,
    14: 0.70
}

# =========================
# 自动识别字段
# =========================

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df.columns = [str(c).strip() for c in df.columns]

    st.success("✅ 数据上传成功")

    st.subheader("📋 数据预览")
    st.dataframe(df.head())

    # 自动识别字段

    date_col = None
    time_col = None
    booked_col = None

    for col in df.columns:

        col_lower = str(col).lower()

        if "date" in col_lower or "日期" in col_lower:
            date_col = col

        if "time" in col_lower or "时段" in col_lower:
            time_col = col

        if (
            "book" in col_lower
            or "约" in col_lower
            or "课量" in col_lower
        ):
            booked_col = col

    # fallback

    if date_col is None:
        date_col = df.columns[0]

    if time_col is None:
        time_col = df.columns[1]

    if booked_col is None:
        booked_col = df.columns[-1]

    # 数据处理

    df[date_col] = pd.to_datetime(df[date_col])

    today = pd.Timestamp.today().normalize()

    df["days_before"] = (
        df[date_col] - today
    ).dt.days

    # 参数区

    st.sidebar.header("⚙️ 模型参数")

    flex_ratio = st.sidebar.slider(
        "灵活课堂占比",
        0.0,
        1.0,
        0.45,
        0.01
    )

    fixed_ratio = 1 - flex_ratio

    # 核心预测

    results = []

    for _, row in df.iterrows():

        booked = row[booked_col]

        days_before = int(max(0, min(14, row["days_before"])))

        flex_booked = booked * flex_ratio
        fixed_booked = booked * fixed_ratio

        flex_final = flex_booked / flex_curve[days_before]
        fixed_final = fixed_booked / fixed_curve[days_before]

        final_total = flex_final + fixed_final

        increment = final_total - booked

        results.append({
            "日期": row[date_col],
            "时段": row[time_col],
            "当前已约": round(booked),
            "预测最终课量": round(final_total),
            "预测新增量": round(increment),
            "距离上课天数": days_before
        })

    result_df = pd.DataFrame(results)

    # =========================
    # KPI区域
    # =========================

    total_current = int(result_df["当前已约"].sum())
    total_final = int(result_df["预测最终课量"].sum())
    total_increment = int(result_df["预测新增量"].sum())

    peak_day = result_df.groupby("日期")["预测最终课量"].sum().idxmax()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "当前已约总课量",
            f"{total_current:,}"
        )

    with c2:
        st.metric(
            "预测最终总课量",
            f"{total_final:,}"
        )

    with c3:
        st.metric(
            "预测新增课量",
            f"{total_increment:,}"
        )

    with c4:
        st.metric(
            "预测高峰日",
            str(peak_day.date())
        )

    st.markdown("---")

    # =========================
    # 趋势图
    # =========================

    st.subheader("📈 未来14天课量趋势")

    chart_df = result_df.groupby("日期")[[
        "当前已约",
        "预测最终课量"
    ]].sum().reset_index()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=chart_df["日期"],
        y=chart_df["当前已约"],
        mode='lines+markers',
        name='当前已约'
    ))

    fig.add_trace(go.Scatter(
        x=chart_df["日期"],
        y=chart_df["预测最终课量"],
        mode='lines+markers',
        name='预测最终课量'
    ))

    fig.update_layout(
        height=500,
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # 热力图
    # =========================

    st.subheader("🔥 高峰时段热力图")

    heat_df = result_df.pivot_table(
        index="日期",
        columns="时段",
        values="预测最终课量",
        aggfunc='sum'
    )

    fig2 = px.imshow(
        heat_df,
        text_auto=True,
        aspect='auto'
    )

    fig2.update_layout(height=650)

    st.plotly_chart(fig2, use_container_width=True)

    # =========================
    # 高峰预警
    # =========================

    st.subheader("🚨 高峰预警")

    threshold = result_df["预测最终课量"].quantile(0.9)

    alert_df = result_df[
        result_df["预测最终课量"] >= threshold
    ]

    if len(alert_df) > 0:

        st.warning(
            f"检测到 {len(alert_df)} 个高峰时段，建议提前扩充教师供给"
        )

        st.dataframe(alert_df)

    # =========================
    # 明细数据
    # =========================

    st.subheader("📋 预测明细")

    st.dataframe(result_df)

    # =========================
    # 下载结果
    # =========================

    csv = result_df.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        label="📥 下载预测结果",
        data=csv,
        file_name=f"未来14天课量预测_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime='text/csv'
    )

else:

    st.info("⬅️ 请先上传未来14天已约课量Excel")

    st.markdown(
        """
        ### 系统功能

        - 自动预测未来14天课量
        - Booking Curve智能预测
        - 高峰预警
        - 时段热力图
        - 预测新增量分析
        - CSV下载
        """
    )

```

# requirements.txt

```text
streamlit
pandas
numpy
plotly
openpyxl
```

# 使用方法

1. 替换 GitHub 仓库里的 app.py
2. requirements.txt 内容同步替换
3. Streamlit 会自动重新部署
4. 1分钟后刷新网页即可

