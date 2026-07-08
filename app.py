from pathlib import Path
import math

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "operation_dashboard_data.csv.gz"

COUNTERS = list("ABCDEFGHIJKLMN")
AREA_LIST = COUNTERS + ["IM1", "IM2"]
AREAS = ["전체"] + AREA_LIST

SELF_COUNTERS = {"B", "F", "G", "L"}
IM_AREAS = {"IM1", "IM2"}

TYPE_MAP = {}
UNIT_MAP = {}

for c in COUNTERS:
    if c == "A":
        TYPE_MAP[c] = "프리미엄 체크인"
        UNIT_MAP[c] = "창구"
    elif c in SELF_COUNTERS:
        TYPE_MAP[c] = "셀프 체크인"
        UNIT_MAP[c] = "기기"
    else:
        TYPE_MAP[c] = "일반 체크인"
        UNIT_MAP[c] = "창구"

TYPE_MAP["IM1"] = "출국장 진입"
TYPE_MAP["IM2"] = "출국장 진입"
UNIT_MAP["IM1"] = "출입문"
UNIT_MAP["IM2"] = "출입문"


# =========================================================
# IM1 / IM2 보정 기준
# =========================================================
IM_MAX_GATES = 6
IM_MIN_ACTIVE_GATES = 3
IM1_PEOPLE_PER_GATE = 30
IM2_PEOPLE_PER_GATE = 30


NUMERIC_COLS = [
    "분",
    "계획수요",
    "실시간인원수",
    "계획오픈수",
    "실시간필요수",
    "필요수차이",
    "계획기본직원수",
    "계획지원직원수",
    "계획총직원수",
    "실시간기본직원수",
    "실시간지원직원수",
    "실시간총직원수",
    "직원차이",
]


st.set_page_config(
    page_title="T2 운영 최적화 수정 시스템",
    layout="wide",
)


st.markdown(
    """
<style>
.block-container {
    padding-top: 2.2rem;
    padding-bottom: 2.5rem;
}
.main-title {
    font-size: 34px;
    font-weight: 900;
    letter-spacing: -0.7px;
    line-height: 1.35;
    margin-top: 6px;
    margin-bottom: 8px;
    overflow: visible;
}
.sub-title {
    font-size: 16px;
    color: #5f6368;
    margin-bottom: 24px;
}
.mode-plan {
    padding: 15px 18px;
    border-radius: 16px;
    background: #eef4ff;
    color: #174ea6;
    font-size: 17px;
    font-weight: 850;
    margin-bottom: 18px;
}
.mode-live {
    padding: 15px 18px;
    border-radius: 16px;
    background: #e8f5e9;
    color: #137333;
    font-size: 17px;
    font-weight: 850;
    margin-bottom: 18px;
}
.mode-alert {
    padding: 15px 18px;
    border-radius: 16px;
    background: #fdecea;
    color: #b3261e;
    font-size: 17px;
    font-weight: 850;
    margin-bottom: 18px;
}
.mode-reduce {
    padding: 15px 18px;
    border-radius: 16px;
    background: #fff7ed;
    color: #c2410c;
    font-size: 17px;
    font-weight: 850;
    margin-bottom: 18px;
}
.metric-card {
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    padding: 18px 20px;
    background: #ffffff;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
    min-height: 112px;
}
.metric-label {
    color: #64748b;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 31px;
    font-weight: 950;
    letter-spacing: -0.5px;
}
.metric-sub {
    color: #64748b;
    font-size: 13px;
    margin-top: 4px;
}
.action-box {
    border-radius: 16px;
    padding: 15px 17px;
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    margin-bottom: 11px;
}
.action-title {
    font-weight: 900;
    font-size: 18px;
    letter-spacing: -0.2px;
}
.action-sub {
    color: #4b5563;
    font-size: 14px;
    margin-top: 5px;
    line-height: 1.45;
}
.section-gap {
    margin-top: 16px;
}
</style>
    """,
    unsafe_allow_html=True,
)


def ceil_div(value, base):
    value = float(value)
    if value <= 0:
        return 0
    return math.ceil(value / base)


def calc_im_gates(area, people):
    people = float(people)

    if people <= 0:
        return 0

    if area == "IM2":
        gates = ceil_div(people, IM2_PEOPLE_PER_GATE)
    else:
        gates = ceil_div(people, IM1_PEOPLE_PER_GATE)

    gates = max(IM_MIN_ACTIVE_GATES, gates)
    gates = min(IM_MAX_GATES, gates)

    return int(gates)


def calc_im_support_staff(gates):
    gates = int(gates)

    if gates <= 0:
        return 0
    if gates <= 3:
        return 1
    if gates <= 5:
        return 2
    return 3


def recalc_im_rows(df):
    df = df.copy()

    if "구역" not in df.columns:
        return df

    mask = df["구역"].isin(["IM1", "IM2"])

    if not mask.any():
        return df

    for idx, row in df.loc[mask].iterrows():
        area = row["구역"]

        plan_gates = calc_im_gates(area, row["계획수요"])
        sensor_gates = calc_im_gates(area, row["실시간인원수"])

        plan_support = calc_im_support_staff(plan_gates)
        sensor_support = calc_im_support_staff(sensor_gates)

        df.at[idx, "유형"] = "출국장 진입"
        df.at[idx, "단위"] = "출입문"

        df.at[idx, "계획오픈수"] = plan_gates
        df.at[idx, "실시간필요수"] = sensor_gates

        df.at[idx, "계획기본직원수"] = plan_gates
        df.at[idx, "계획지원직원수"] = plan_support
        df.at[idx, "계획총직원수"] = plan_gates + plan_support

        df.at[idx, "실시간기본직원수"] = sensor_gates
        df.at[idx, "실시간지원직원수"] = sensor_support
        df.at[idx, "실시간총직원수"] = sensor_gates + sensor_support

        df.at[idx, "필요수차이"] = sensor_gates - plan_gates
        df.at[idx, "직원차이"] = (sensor_gates + sensor_support) - (plan_gates + plan_support)

        if sensor_gates > plan_gates:
            df.at[idx, "상태"] = "추가 필요"
            df.at[idx, "권고"] = f"출입문 {sensor_gates - plan_gates}개 추가 개방 필요"
        elif sensor_gates < plan_gates:
            df.at[idx, "상태"] = "감축 가능"
            df.at[idx, "권고"] = f"출입문 {plan_gates - sensor_gates}개 감축 검토"
        else:
            df.at[idx, "상태"] = "계획 유지"
            df.at[idx, "권고"] = "계획 유지"

        if sensor_gates >= 5:
            df.at[idx, "IM판단"] = "집중 운영 권고"
        elif sensor_gates >= 3:
            df.at[idx, "IM판단"] = "부분 증설 권고"
        elif sensor_gates > 0:
            df.at[idx, "IM판단"] = "기본 개방 수준"
        else:
            df.at[idx, "IM판단"] = "출입문 대기 수요 없음"

    return df


@st.cache_resource(show_spinner=False)
def load_data(file_mtime):
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", compression="infer")

    df["일자"] = df["일자"].astype(str)
    df["구역"] = df["구역"].astype(str)
    df["시각"] = df["시각"].astype(str)

    if "IM판단" not in df.columns:
        df["IM판단"] = ""

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df[df["일자"].str.startswith("2025-")]
    df = df[df["구역"].isin(AREA_LIST)]

    return df


def fmt_num(value):
    try:
        return f"{int(round(float(value))):,}"
    except Exception:
        return str(value)


def fmt_signed(value):
    try:
        v = int(round(float(value)))
        return f"{v:+,}"
    except Exception:
        return str(value)


def minute_to_hhmm(minute):
    minute = int(minute)
    minute = max(0, min(1439, minute))
    return f"{minute // 60:02d}:{minute % 60:02d}"


def hhmm_to_minute(text):
    h, m = str(text).split(":")
    return int(h) * 60 + int(m)


def selectable_times():
    return [minute_to_hhmm(m) for m in range(0, 24 * 60, 15)]


def graph_window(selected_time):
    center = hhmm_to_minute(selected_time)
    start = max(0, center - 30)
    end = min(1439, center + 90)

    plan_label = f"계획 {minute_to_hhmm(start)}부터 {minute_to_hhmm(end)}까지"
    sensor_label = f"인원수 기준 {minute_to_hhmm(start)}부터 {selected_time}까지"

    return start, end, plan_label, sensor_label


def area_suffix(area):
    if area in SELF_COUNTERS:
        return "대"
    return "개"


def unit_suffix(unit):
    if unit == "기기":
        return "대"
    return "개"


def axis_name(area):
    if area == "전체":
        return "필요 운영 수"
    if area in SELF_COUNTERS:
        return "필요 기기 수"
    if area in IM_AREAS:
        return "필요 출입문 수"
    return "필요 창구 수"


def keep_rate(area):
    if area == "A":
        return 0.70
    if area in SELF_COUNTERS:
        return 0.50
    if area in IM_AREAS:
        return 0.50
    return 0.60


def estimate_staff_from_units(area, units):
    units = int(max(0, units))

    if units <= 0:
        return 0

    if area == "A":
        support = 1 if units >= 3 else 0
        return units + support

    if area in SELF_COUNTERS:
        return min(math.ceil(units / 6), 3)

    if area in IM_AREAS:
        return units + calc_im_support_staff(units)

    if units < 8:
        support = 0
    elif units < 16:
        support = 1
    elif units < 24:
        support = 2
    else:
        support = 3

    return units + support


def add_recommendation_columns(rows):
    rows = rows.copy()

    decisions = []
    recommended_units = []
    adjust_units = []
    recommended_staff = []
    adjust_staff = []

    for _, row in rows.iterrows():
        area = row["구역"]

        plan_units = int(row["계획오픈수"])
        sensor_units = int(row["실시간필요수"])

        plan_staff = int(row["계획총직원수"])
        sensor_staff = int(row["실시간총직원수"])

        diff = sensor_units - plan_units

        if plan_units <= 0:
            if sensor_units > 0:
                decision = "추가 필요"
                final_units = sensor_units
                final_staff = sensor_staff
            else:
                decision = "계획 유지"
                final_units = 0
                final_staff = 0

        elif diff >= 2:
            decision = "추가 필요"
            final_units = sensor_units
            final_staff = sensor_staff

        elif diff <= -2:
            minimum_units = math.ceil(plan_units * keep_rate(area))
            final_units = max(sensor_units, minimum_units)

            if final_units < plan_units:
                decision = "감축 검토"
                final_staff = estimate_staff_from_units(area, final_units)
            else:
                decision = "계획 유지"
                final_units = plan_units
                final_staff = plan_staff

        else:
            decision = "계획 유지"
            final_units = plan_units
            final_staff = plan_staff

        decisions.append(decision)
        recommended_units.append(int(final_units))
        adjust_units.append(int(final_units - plan_units))
        recommended_staff.append(int(final_staff))
        adjust_staff.append(int(final_staff - plan_staff))

    rows["조정판단"] = decisions
    rows["권고필요수"] = recommended_units
    rows["조정필요수"] = adjust_units
    rows["권고직원수"] = recommended_staff
    rows["직원조정수"] = adjust_staff

    rows["추가필요수"] = rows["조정필요수"].clip(lower=0)
    rows["감축검토수"] = (-rows["조정필요수"]).clip(lower=0)

    return rows


def metric_card(title, value, suffix="", sub=""):
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">{title}</div>
    <div class="metric-value">{value}{suffix}</div>
    <div class="metric-sub">{sub}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def base_area_frame(area):
    if area == "전체":
        areas = AREA_LIST
    else:
        areas = [area]

    return pd.DataFrame({"구역": areas})


def fill_snapshot_defaults(rows):
    rows["유형"] = rows["유형"].fillna(rows["구역"].map(TYPE_MAP))
    rows["단위"] = rows["단위"].fillna(rows["구역"].map(UNIT_MAP))

    for col in NUMERIC_COLS:
        if col in rows.columns:
            rows[col] = pd.to_numeric(rows[col], errors="coerce").fillna(0)

    rows["상태"] = rows["상태"].fillna("계획 유지")
    rows["권고"] = rows["권고"].fillna("계획 유지")
    rows["IM판단"] = rows["IM판단"].fillna("")

    return rows


def current_snapshot(df, date, time_value, area):
    minute = hhmm_to_minute(time_value)

    rows = df[(df["일자"] == date) & (df["분"] == minute)].copy()

    if not rows.empty:
        rows = rows.drop_duplicates(subset=["구역"], keep="last")

    base = base_area_frame(area)
    rows = base.merge(rows, on="구역", how="left")

    rows["일자"] = rows["일자"].fillna(date)
    rows["분"] = rows["분"].fillna(minute).astype(int)
    rows["시각"] = rows["시각"].fillna(time_value)

    rows = fill_snapshot_defaults(rows)
    rows = recalc_im_rows(rows)
    rows = add_recommendation_columns(rows)

    if area != "전체":
        rows = rows[rows["구역"] == area].copy()

    return rows


def day_series(df, date, area, start_min, end_min):
    day = df[
        (df["일자"] == date)
        & (df["분"] >= start_min)
        & (df["분"] <= end_min)
    ].copy()

    if area != "전체":
        day = day[day["구역"] == area].copy()

    day = recalc_im_rows(day)

    base = pd.DataFrame({"분": list(range(start_min, end_min + 1))})
    base["시각"] = base["분"].apply(minute_to_hhmm)

    if day.empty:
        out = base.copy()
        out["계획오픈수"] = 0
        out["실시간필요수"] = 0
        return out

    grouped = (
        day.groupby("분", as_index=False)[["계획오픈수", "실시간필요수"]]
        .sum()
    )

    out = base.merge(grouped, on="분", how="left")

    for col in ["계획오픈수", "실시간필요수"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    return out.sort_values("분")


def get_live_end_minute(selected_time):
    start_min, end_min, _, _ = graph_window(selected_time)
    selected_min = hhmm_to_minute(selected_time)

    if "live_elapsed" not in st.session_state:
        st.session_state["live_elapsed"] = 0

    live_end = selected_min + int(st.session_state["live_elapsed"])
    live_end = max(start_min, min(end_min, live_end))

    return live_end


def make_chart_data(df, date, area, selected_time, mode):
    start_min, end_min, plan_label, sensor_label = graph_window(selected_time)
    selected_min = hhmm_to_minute(selected_time)

    series = day_series(df, date, area, start_min, end_min)

    plan = series[["분", "시각", "계획오픈수"]].copy()
    plan = plan.rename(columns={"계획오픈수": "필요수"})
    plan["구분"] = "항공편 기반 계획"

    if mode == "OFF":
        return plan, plan_label, selected_time

    live_end = get_live_end_minute(selected_time)

    sensor_series = series[series["분"] <= live_end].copy()

    sensor = sensor_series[["분", "시각", "실시간필요수"]].copy()
    sensor = sensor.rename(columns={"실시간필요수": "필요수"})
    sensor["구분"] = "인원수 기준"

    chart = pd.concat([plan, sensor], ignore_index=True)
    chart = chart.sort_values(["분", "구분"])

    live_end_time = minute_to_hhmm(live_end)
    label = f"{plan_label} / 인원수 기준 {minute_to_hhmm(start_min)}부터 {live_end_time}까지"

    return chart, label, live_end_time


def calc_y_dtick(y_max):
    if y_max <= 10:
        return 1
    if y_max <= 30:
        return 2
    if y_max <= 80:
        return 5
    return 10


def draw_line_chart(chart, title_text, y_title):
    fig = px.line(
        chart,
        x="분",
        y="필요수",
        color="구분",
        custom_data=["시각", "구분"],
    )

    y_max = float(chart["필요수"].max()) if not chart.empty else 1
    y_top = max(1, math.ceil(y_max * 1.15))
    dtick = calc_y_dtick(y_top)

    fig.update_traces(
        mode="lines",
        line=dict(width=3),
        hovertemplate=(
            "시각=%{customdata[0]}<br>"
            "구분=%{customdata[1]}<br>"
            f"{y_title}=%{{y:.0f}}<extra></extra>"
        ),
    )

    fig.update_layout(
        title=title_text,
        height=430,
        margin=dict(l=10, r=10, t=42, b=10),
        legend_title_text="",
        xaxis_title="",
        yaxis_title=y_title,
        hovermode="x unified",
    )

    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )

    fig.update_yaxes(
        range=[0, y_top],
        tickmode="linear",
        dtick=dtick,
        tickformat="d",
        rangemode="tozero",
    )

    st.plotly_chart(fig, width="stretch")


def draw_current_bar(current):
    chart_df = current[["구역", "계획오픈수", "실시간필요수", "권고필요수"]].melt(
        id_vars="구역",
        value_vars=["계획오픈수", "실시간필요수", "권고필요수"],
        var_name="구분",
        value_name="필요 수",
    )

    chart_df["구분"] = chart_df["구분"].replace(
        {
            "계획오픈수": "항공편 기반 계획",
            "실시간필요수": "인원수 기준",
            "권고필요수": "권고 필요",
        }
    )

    fig = px.bar(
        chart_df,
        x="구역",
        y="필요 수",
        color="구분",
        barmode="group",
        text="필요 수",
    )

    y_max = float(chart_df["필요 수"].max()) if not chart_df.empty else 1
    y_top = max(1, math.ceil(y_max * 1.2))
    dtick = calc_y_dtick(y_top)

    fig.update_traces(
        texttemplate="%{text:.0f}",
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        height=390,
        margin=dict(l=10, r=10, t=25, b=10),
        legend_title_text="",
        yaxis_title="필요 수",
        xaxis_title="",
    )

    fig.update_yaxes(
        range=[0, y_top],
        tickmode="linear",
        dtick=dtick,
        tickformat="d",
        rangemode="tozero",
    )

    st.plotly_chart(fig, width="stretch")


def operation_table_off(current):
    table = current[
        [
            "구역",
            "유형",
            "계획수요",
            "계획오픈수",
            "단위",
            "계획기본직원수",
            "계획지원직원수",
            "계획총직원수",
        ]
    ].copy()

    table = table.sort_values(["계획오픈수", "계획총직원수"], ascending=False)

    table = table.rename(
        columns={
            "계획수요": "계획 수요",
            "계획오픈수": "계획 필요",
            "계획기본직원수": "기본 직원",
            "계획지원직원수": "지원 직원",
            "계획총직원수": "총 직원",
        }
    )

    return table


def operation_table_live(current):
    table = current[
        [
            "구역",
            "유형",
            "계획수요",
            "실시간인원수",
            "계획오픈수",
            "실시간필요수",
            "권고필요수",
            "조정필요수",
            "조정판단",
            "계획총직원수",
            "실시간총직원수",
            "권고직원수",
            "직원조정수",
            "IM판단",
        ]
    ].copy()

    table["정렬값"] = table["조정필요수"].abs()
    table = table.sort_values(["정렬값", "직원조정수"], ascending=False)
    table = table.drop(columns=["정렬값"])

    table = table.rename(
        columns={
            "계획수요": "계획 수요",
            "실시간인원수": "실시간 인원",
            "계획오픈수": "계획 필요",
            "실시간필요수": "인원수 기준",
            "권고필요수": "권고 필요",
            "조정필요수": "조정 수",
            "조정판단": "조정 판단",
            "계획총직원수": "계획 직원",
            "실시간총직원수": "인원수 기준 직원",
            "권고직원수": "권고 직원",
            "직원조정수": "직원 조정",
            "IM판단": "IM 판단",
        }
    )

    return table


# =========================================================
# 화면 시작
# =========================================================
st.markdown(
    '<div class="main-title">✈️ T2 운영 최적화 수정 시스템</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="sub-title">항공편 기반 사전 운영계획과 인원수 기반 실시간 보정 결과를 비교해 관리자 조치 여부를 판단합니다.</div>',
    unsafe_allow_html=True,
)


if not DATA_PATH.exists():
    st.error("operation_dashboard_data.csv.gz 파일이 없습니다. 먼저 전처리 코드를 실행하세요.")
    st.code(
        'cd /d "G:\\캡디\\2026-07-06 과제 2번 최종"\npython make_operation_dashboard_data.py',
        language="cmd",
    )
    st.stop()


file_mtime = DATA_PATH.stat().st_mtime
df = load_data(file_mtime)

if df.empty:
    st.error("데이터가 비어 있습니다. 전처리 결과를 확인하세요.")
    st.stop()


dates = sorted(df["일자"].dropna().unique())
times = selectable_times()

with st.sidebar:
    st.header("관제 설정")

    selected_date = st.selectbox("일자", dates, index=0)

    selected_area = st.selectbox("구역", AREAS, index=0)

    selected_time = st.selectbox(
        "데이터 기준 시각",
        times,
        index=times.index("08:00") if "08:00" in times else 0,
    )

    mode = st.radio(
        "표시 방식",
        ["OFF", "LIVE"],
        index=0,
    )

    refresh_seconds = 20

    if mode == "LIVE":
        refresh_seconds = st.selectbox("LIVE 갱신 간격", [10, 20, 30, 60], index=1)

    st.caption("OFF: 항공편 기반 운영계획만 표시")
    st.caption("LIVE: 인원수 데이터를 실시간 센서값처럼 순차 반영")


session_key = f"{selected_date}|{selected_area}|{selected_time}|{mode}"

if st.session_state.get("session_key") != session_key:
    st.session_state["session_key"] = session_key
    st.session_state["live_elapsed"] = 0


def render_off_view():
    chart, window_label, data_time = make_chart_data(
        df=df,
        date=selected_date,
        area=selected_area,
        selected_time=selected_time,
        mode="OFF",
    )

    current = current_snapshot(df, selected_date, data_time, selected_area)
    y_title = axis_name(selected_area)
    suffix = area_suffix(selected_area)

    st.subheader(f"🗓️ {selected_date} {selected_time} 데이터 기준 시각")

    st.markdown(
        '<div class="mode-plan">OFF: 항공편 기반 운영계획만 표시</div>',
        unsafe_allow_html=True,
    )

    plan_demand = current["계획수요"].sum()
    plan_units = int(current["계획오픈수"].sum())
    plan_staff = int(current["계획총직원수"].sum())

    if selected_area == "전체":
        fourth_title = "계획 적용 구역"
        fourth_value = fmt_num((current["계획오픈수"] > 0).sum())
        fourth_suffix = "곳"
    else:
        fourth_title = "구역 상태"
        fourth_value = "운영 필요" if plan_units > 0 else "운영 없음"
        fourth_suffix = ""

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("계획 수요", fmt_num(plan_demand), "명")

    with c2:
        metric_card(y_title, fmt_num(plan_units), suffix)

    with c3:
        metric_card("계획 직원", fmt_num(plan_staff), "명")

    with c4:
        metric_card(fourth_title, fourth_value, fourth_suffix)

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    st.subheader("📈 항공편 기반 운영계획 변화")
    st.caption(window_label)
    draw_line_chart(chart, "항공편 기반 계획", y_title)

    if selected_area == "전체":
        with st.expander("구역별 운영계획 표 보기", expanded=False):
            st.dataframe(
                operation_table_off(current),
                width="stretch",
                hide_index=True,
            )

    else:
        row = current.iloc[0]
        row_suffix = unit_suffix(row["단위"])

        st.subheader(f"📍 {selected_area} 운영계획 상세")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card("구역 유형", row["유형"])

        with c2:
            metric_card("계획 수요", fmt_num(row["계획수요"]), "명")

        with c3:
            metric_card(y_title, fmt_num(row["계획오픈수"]), row_suffix)

        with c4:
            metric_card("계획 직원", fmt_num(row["계획총직원수"]), "명")


def render_live_view():
    chart, window_label, data_time = make_chart_data(
        df=df,
        date=selected_date,
        area=selected_area,
        selected_time=selected_time,
        mode="LIVE",
    )

    current = current_snapshot(df, selected_date, data_time, selected_area)
    y_title = axis_name(selected_area)
    suffix = area_suffix(selected_area)

    st.subheader(f"🟢 {selected_date} {data_time} 데이터 기준 시각")

    add_count = int((current["조정판단"] == "추가 필요").sum())
    reduce_count = int((current["조정판단"] == "감축 검토").sum())

    if add_count > 0 and reduce_count > 0:
        st.markdown(
            f'<div class="mode-alert">LIVE: 인원수 데이터를 실시간 센서값처럼 반영 · 추가 {add_count}개 구역 / 감축 검토 {reduce_count}개 구역</div>',
            unsafe_allow_html=True,
        )
    elif add_count > 0:
        st.markdown(
            f'<div class="mode-alert">LIVE: 인원수 데이터를 실시간 센서값처럼 반영 · {add_count}개 구역 추가 운영 필요</div>',
            unsafe_allow_html=True,
        )
    elif reduce_count > 0:
        st.markdown(
            f'<div class="mode-reduce">LIVE: 인원수 데이터를 실시간 센서값처럼 반영 · {reduce_count}개 구역 감축 검토</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="mode-live">LIVE: 인원수 데이터를 실시간 센서값처럼 반영 · 계획 유지</div>',
            unsafe_allow_html=True,
        )

    plan_units = int(current["계획오픈수"].sum())
    sensor_units = int(current["실시간필요수"].sum())
    recommend_units = int(current["권고필요수"].sum())
    adjust_units = int(current["조정필요수"].sum())
    adjust_staff = int(current["직원조정수"].sum())

    if adjust_units > 0:
        decision_text = f"추가 {fmt_num(adjust_units)}{suffix}"
    elif adjust_units < 0:
        decision_text = f"감축 검토 {fmt_num(abs(adjust_units))}{suffix}"
    else:
        decision_text = "계획 유지"

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("계획 필요", fmt_num(plan_units), suffix)

    with c2:
        metric_card("인원수 기준", fmt_num(sensor_units), suffix)

    with c3:
        metric_card("권고 필요", fmt_num(recommend_units), suffix)

    with c4:
        metric_card("조정 판단", decision_text, "", f"직원 조정 {fmt_signed(adjust_staff)}명")

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    st.subheader("📈 계획 대비 인원수 기준 변화")
    st.caption(window_label)
    draw_line_chart(chart, "항공편 기반 계획 vs 인원수 기준", y_title)

    if selected_area == "전체":
        left, right = st.columns([1.05, 1])

        with left:
            st.subheader("🚨 우선 조치 구역")

            priority = current[current["조정판단"] != "계획 유지"].copy()
            priority["정렬값"] = priority["조정필요수"].abs()
            priority = priority.sort_values(["정렬값", "직원조정수"], ascending=False).head(6)

            if priority.empty:
                st.success("현재 데이터 기준 조정 필요 구역이 없습니다.")
            else:
                for _, row in priority.iterrows():
                    row_suffix = unit_suffix(row["단위"])
                    adjust = int(row["조정필요수"])

                    if adjust > 0:
                        title = f"{row['구역']} · {adjust}{row_suffix} 추가 운영 필요"
                    else:
                        title = f"{row['구역']} · {abs(adjust)}{row_suffix} 감축 검토"

                    st.markdown(
                        f"""
<div class="action-box">
    <div class="action-title">{title}</div>
    <div class="action-sub">
        유형: {row['유형']} |
        계획 {int(row['계획오픈수'])}{row_suffix} →
        인원수 기준 {int(row['실시간필요수'])}{row_suffix} →
        권고 {int(row['권고필요수'])}{row_suffix} |
        직원 {int(row['계획총직원수'])}명 → {int(row['권고직원수'])}명
    </div>
</div>
                        """,
                        unsafe_allow_html=True,
                    )

        with right:
            st.subheader("📊 현재 기준 비교")
            draw_current_bar(current)

        with st.expander("실시간 구역별 보정표 보기", expanded=False):
            st.dataframe(
                operation_table_live(current),
                width="stretch",
                hide_index=True,
            )

    else:
        row = current.iloc[0]
        row_suffix = unit_suffix(row["단위"])

        st.subheader(f"📍 {selected_area} 실시간 보정 상세")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card("계획 필요", fmt_num(row["계획오픈수"]), row_suffix)

        with c2:
            metric_card("인원수 기준", fmt_num(row["실시간필요수"]), row_suffix)

        with c3:
            metric_card("권고 필요", fmt_num(row["권고필요수"]), row_suffix)

        with c4:
            metric_card("조정 수", fmt_signed(row["조정필요수"]), row_suffix)

        c5, c6, c7, c8 = st.columns(4)

        with c5:
            metric_card("계획 수요", fmt_num(row["계획수요"]), "명")

        with c6:
            metric_card("실시간 인원", fmt_num(row["실시간인원수"]), "명")

        with c7:
            metric_card("권고 직원", fmt_num(row["권고직원수"]), "명")

        with c8:
            metric_card("직원 조정", fmt_signed(row["직원조정수"]), "명")

        if row["조정판단"] == "추가 필요":
            st.warning(f"권고 조치: {int(row['조정필요수'])}{row_suffix} 추가 운영 필요")
        elif row["조정판단"] == "감축 검토":
            st.info(f"권고 조치: {abs(int(row['조정필요수']))}{row_suffix} 감축 검토")
        else:
            st.success("권고 조치: 계획 유지")

        if selected_area in ["IM1", "IM2"] and str(row["IM판단"]).strip():
            st.warning(row["IM판단"])

    start_min, end_min, _, _ = graph_window(selected_time)
    current_live_end = hhmm_to_minute(data_time)

    if current_live_end < end_min:
        st.session_state["live_elapsed"] = int(st.session_state.get("live_elapsed", 0)) + 1


if mode == "OFF":
    render_off_view()
else:
    if not hasattr(st, "fragment"):
        st.error("현재 Streamlit 버전이 st.fragment를 지원하지 않습니다. requirements.txt에서 streamlit>=1.37.0으로 올려야 합니다.")
        st.stop()

    live_run_every = f"{int(refresh_seconds)}s"

    @st.fragment(run_every=live_run_every)
    def live_fragment():
        render_live_view()

    live_fragment()
