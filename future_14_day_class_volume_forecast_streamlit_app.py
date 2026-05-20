import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="未来14天课量预测系统",
    layout="wide"
)

st.title("📈 未来14天课量预测系统")
st.markdown("基于 Booking Curve（约课曲线）预测未来14天各时段最终课量")


# =========================
# 工具函数
# =========================

def normalize_columns(df):
    df.columns = [str(col).strip() for col in df.columns]
    return df


@st.cache_data

def load_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)
    df = normalize_columns(df)
    return df


def safe_divide(a, b):
    if b == 0:
        return 0
    return a / b


# =========================
# Sidebar
# =========================

st.sidebar.header("📂 上传数据文件")

booking_file = st.sidebar.file_uploader(
    "上传未来14天已约课量",
    type=["xlsx"]
)

class_ratio_file = st.sidebar.file_uploader(
    "上传各类型课堂占比",
    type=["xlsx"]
)

flex_curve_file = st.sidebar.file_uploader(
    "上传灵活课堂约课曲线",
    type=["xlsx"]
)

fixed_curve_file = st.sidebar.file_uploader(
    "上传周期课堂&补课课堂约课曲线",
    type=["xlsx"]
)


# =========================
# 主逻辑
# =========================

if booking_file:

    booking_df = load_excel(booking_file)

    st.success("✅ 已成功读取未来14天已约课量数据")

    st.subheader("未来14天已约课量预览")
    st.dataframe(booking_df.head())

    st.markdown("---")

    # =========================
    # 手动字段选择
    # =========================

    st.subheader("字段映射")

    cols = booking_df.columns.tolist()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        date_col = st.selectbox("日期字段", cols)

    with col2:
        time_col = st.selectbox("时段字段", cols)

    with col3:
        booked_col = st.selectbox("已约课量字段", cols)

    with col4:
        weekday_mode = st.selectbox(
            "星期计算方式",
            ["自动根据日期计算", "文件已包含星期字段"]
        )

    if weekday_mode == "文件已包含星期字段":
        weekday_col = st.selectbox("星期字段", cols)

    # =========================
    # 数据处理
    # =========================

    forecast_df = booking_df.copy()

    forecast_df[date_col] = pd.to_datetime(forecast_df[date_col])

    if weekday_mode == "自动根据日期计算":
        forecast_df["weekday"] = forecast_df[date_col].dt.day_name()
    else:
        forecast_df["weekday"] = forecast_df[weekday_col]

    today = pd.Timestamp.today().normalize()

    forecast_df["days_before_class"] = (
        forecast_df[date_col] - today
    ).dt.days

    # =========================
    # 默认 Booking Curve
    # =========================

    default_flex_curve = {
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

    default_fixed_curve = {
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
    # 默认课堂占比
    # =========================

    default_flex_ratio = 0.45
    default_fixed_ratio = 0.55

    st.markdown("---")
    st.subheader("预测参数")

    col1, col2 = st.columns(2)

    with col1:
        flex_ratio = st.slider(
            "灵活课堂占比",
            min_value=0.0,
            max_value=1.0,
            value=default_flex_ratio,
            step=0.01
        )

    with col2:
        fixed_ratio = st.slider(
            "周期课堂&补课课堂占比",
            min_value=0.0,
            max_value=1.0,
            value=default_fixed_ratio,
            step=0.01
        )

    # =========================
    # 核心预测逻辑
    # =========================

    def get_curve_value(days, curve_dict):
        days = max(0, min(14, int(days)))
        return curve_dict.get(days, 1)


    final_forecast_list = []

    for _, row in forecast_df.iterrows():

        booked_cnt = row[booked_col]
        days_before = row["days_before_class"]

        flex_booked = booked_cnt * flex_ratio
        fixed_booked = booked_cnt * fixed_ratio

        flex_curve = get_curve_value(days_before, default_flex_curve)
        fixed_curve = get_curve_value(days_before, default_fixed_curve)

        flex_final = safe_divide(flex_booked, flex_curve)
        fixed_final = safe_divide(fixed_booked, fixed_curve)

        final_total = flex_final + fixed_final

        increment = final_total - booked_cnt

        final_forecast_list.append({
            "日期": row[date_col],
            "时段": row[time_col],
            "当前已约": round(booked_cnt, 0),
            "预测最终课量": round(final_total, 0),
            "预测新增量": round(increment, 0),
            "距离上课天数": days_before,
            "灵活课堂预测": round(flex_final, 0),
            "周期课堂预测": round(fixed_final, 0)
        })

    result_df = pd.DataFrame(final_forecast_list)

    # =========================
    # 输出结果
    # =========================

    st.markdown("---")
    st.subheader("📊 预测结果")

    st.dataframe(result_df)

    # =========================
    # 汇总指标
    # =========================

    total_current = result_df["当前已约"].sum()
    total_final = result_df["预测最终课量"].sum()
    total_increment = result_df["预测新增量"].sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("当前已约总课量", f"{int(total_current):,}")

    with col2:
        st.metric("预测最终总课量", f"{int(total_final):,}")

    with col3:
        st.metric("预测新增课量", f"{int(total_increment):,}")

    # =========================
    # 趋势图
    # =========================

    st.markdown("---")
    st.subheader("📈 课量趋势")

    chart_df = result_df.groupby("日期")[["当前已约", "预测最终课量"]].sum().reset_index()

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
        xaxis_title='日期',
        yaxis_title='课量'
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # 时段热力图
    # =========================

    st.markdown("---")
    st.subheader("🔥 时段热力图")

    pivot_df = result_df.pivot_table(
        index="日期",
        columns="时段",
        values="预测最终课量",
        aggfunc='sum'
    )

    fig_heat = px.imshow(
        pivot_df,
        aspect='auto',
        text_auto=True
    )

    fig_heat.update_layout(height=600)

    st.plotly_chart(fig_heat, use_container_width=True)

    # =========================
    # 下载结果
    # =========================

    st.markdown("---")

    csv = result_df.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        label="📥 下载预测结果CSV",
        data=csv,
        file_name=f"未来14天课量预测_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime='text/csv'
    )

    # =========================
    # 误差说明
    # =========================

    st.markdown("---")
    st.subheader("📌 预测误差说明")

    st.info(
        """
        当前模型基于 Booking Curve（约课曲线）预测。

        预计误差范围：

        • T+0 ~ T+2：±5%
        • T+3 ~ T+7：±8%~15%
        • T+8 ~ T+14：±15%~30%

        主要误差来源：

        1. 灵活课堂临时约课波动
        2. 活动/促销影响
        3. 教师供给变化
        4. 节假日影响
        5. cancel/no-show

        若后续增加：

        • 历史每日快照
        • 最终成课量
        • cancel率
        • slots数据

        则预测准确率可进一步提升。
        """
    )

else:

    st.info("请先上传未来14天已约课量文件")


# =========================
# 页脚
# =========================

st.markdown("---")
st.caption("未来14天课量预测系统 | Booking Curve Forecasting Model")
