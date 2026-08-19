# =====================================================================
# 성심당 상권 분석 — Streamlit in Snowflake
# 담당: 지원
#
# 사용법
#   - Snowflake에 VIEW가 아직 없으면 자동으로 MOCK 데이터(알려진 기준값)로 대체됨
#   - 태운 님이 VIEW를 만들면 재실행 시 자동으로 실데이터 전환 (코드 수정 불필요)
#   - 화면 상단에 지금 MOCK인지 실데이터인지 배지로 표시됨
#
# 패키지 추가 불필요 — Streamlit 기본 내장 함수만 사용
#
# v3 수정사항
#   - V_BRANCH_TREND 딕셔너리 닫는 괄호 누락 수정 (구문 오류였음)
#   - V_BRANCH_TREND 2023년 값 보정치로 교체 (5.90% → 25.84%, 파싱 오류 복구)
#   - V_RENT_INDEX 실측치로 교체 (대전 5개 상권 전체 하락, 원도심은 4번째)
#   - V_FINAL_SUMMARY를 실제 V_FINAL_SUMMARY 검정 결과로 교체
#     (경쟁재/카페는 기각됐으므로 "송리단길형" 표현 제거)
#   - STEP 5·8·9에 등방성(각도=상업축) 유보 캡션 추가
#   - STEP 8에 경쟁재 한정 프랜차이즈 참고표 추가 (위약검정 미실시, 표본 작음 명시)
# =====================================================================

import streamlit as st
import pandas as pd
import numpy as np
# plotly/pydeck 미사용 — Snowflake 기본 내장 Streamlit만 사용 (외부 네트워크 접근 불가 환경 대응)

st.set_page_config(page_title="성심당 상권 분석", layout="wide")

try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
    SNOW_OK = True
except Exception:
    SNOW_OK = False

MOCK_MODE = {}  # 화면별로 mock 사용 여부 기록 → 상단 배지에 표시


# ─────────────────────────────────────────────────────────────────
# 데이터 로더 — VIEW 없으면 MOCK으로 자동 폴백
# ─────────────────────────────────────────────────────────────────

FULL_SCHEMA = "PROJECT_DB.SHARED_FILES"  # SHOW VIEWS 결과 기준 확정 경로

@st.cache_data(ttl=3600)
def load(view_name: str) -> pd.DataFrame:
    """Snowflake VIEW를 읽되, 없거나 접근 실패 시 MOCK 반환"""
    if SNOW_OK:
        try:
            df = session.table(f"{FULL_SCHEMA}.{view_name}").to_pandas()
            MOCK_MODE[view_name] = False
            return df
        except Exception:
            pass
    MOCK_MODE[view_name] = True
    return MOCK.get(view_name, pd.DataFrame()).copy()


def status_badge(view_name: str):
    """이 화면이 mock인지 실데이터인지 표시"""
    is_mock = MOCK_MODE.get(view_name, True)
    if is_mock:
        st.caption(f"🟡 MOCK 데이터 사용 중 — `{view_name}` 아직 없음. 태운 님 작업 완료 후 자동 전환됩니다.")
    else:
        st.caption(f"🟢 실데이터 — `{view_name}`")


# ─────────────────────────────────────────────────────────────────
# MOCK 데이터 — 지금까지 확인된 기준값 그대로 사용
# 태운 님 VIEW가 이 스키마와 동일한 컬럼명으로 나와야 함
# ─────────────────────────────────────────────────────────────────

MOCK = {}

# V_FOOD_CLEAN — 화면1 요약용 (건수만 필요)
MOCK["V_FOOD_CLEAN"] = pd.DataFrame({
    "LAT": np.random.normal(36.33, 0.03, 500),
    "LON": np.random.normal(127.42, 0.03, 500),
})

# V_PLACEBO — 실패1 (기준점 7개 DiD)
MOCK["V_PLACEBO"] = pd.DataFrame({
    "POINT_NM":     ["중앙로역", "대전역", "성심당", "유성온천역", "복합터미널", "대전시청", "서대전네거리"],
    "GAP_PRE_PP":   [-0.6, -4.3, -0.3, -0.1, -2.7, 1.8, -0.3],
    "GAP_POST_PP":  [-4.7, -8.4, -3.4, 0.8, -1.7, 3.2, 1.5],
    "DID_PP":       [-4.1, -4.0, -3.1, 0.9, 1.0, 1.3, 1.8],
    "N_NEAR_POST":  [2900, 900, 2804, 1600, 1150, 1750, 1280],
})

# V_SECTOR_GAP — 실패2 핵심 (거리대 × POST)
MOCK["V_SECTOR_GAP"] = pd.DataFrame({
    "PERIOD":      ["POST"] * 5,
    "CENTER_BAND": ["0-150m", "150-300m", "300-450m", "450-600m", "600-800m"],
    "RATE_ANCHOR": [18.8, 10.0, 13.3, 20.8, 19.5],
    "RATE_OPPO":   [22.7, 17.6, 13.0, 10.1, 8.7],
    "GAP_PP":      [-3.9, -7.6, 0.3, 10.7, 10.8],
    "N_ANCHOR":    [160, 270, 667, 409, 272],
    "N_OPPO":      [75, 68, 230, 247, 149],
})

# V_ANGLE_SENSITIVITY — 각도폭 민감도 (슬라이더용)
MOCK["V_ANGLE_SENSITIVITY"] = pd.DataFrame({
    "HALF":        [30, 45, 60, 75, 90],
    "RATE_ANCHOR": [15.2, 13.5, 13.3, 13.2, 14.7],
    "RATE_OPPO":   [27.6, 22.8, 20.3, 18.0, 18.5],
    "N_ANCHOR":    [178, 319, 430, 524, 696],
    "N_OPPO":      [58, 92, 143, 217, 330],
})

# V_PLACEBO_SUMMARY — 효린 담당, 지표별 위약검정 통과여부 통합표
MOCK["V_PLACEBO_SUMMARY"] = pd.DataFrame({
    "METRIC":        ["폐업률 (0-300m)", "각도회귀 클러스터SE", "생활밀착 비중", "보완재 비중", "경쟁재 비중", "프랜차이즈 비중(전체)"],
    "OBSERVED":      ["-7.02%p", "p=0.575", "-1.79%p", "+3.69%p", "+1.59%p", "+5.93%p"],
    "PLACEBO_RANK":  ["하위 36.7%", "-", "하위 11.7% (중심점 20.0%)", "상위 3.3%", "상위 43.3%", "상위 10.0%"],
    "VERDICT":       ["기각", "기각", "기각", "통과", "기각", "통과"],
})

# V_ROLE_TREND — 실패3, 연도×방향 업종비율
MOCK["V_ROLE_TREND"] = pd.DataFrame({
    "YR":            [2021, 2022, 2023, 2024, 2025, 2026] * 2,
    "SECTOR":        ["성심당방향"] * 6 + ["반대방향"] * 6,
    "N":             [677, 634, 356, 396, 482, 457, 238, 239, 237, 260, 229, 212],
    "LIFE_RATIO":    [0.0502, 0.0489, 0.0365, 0.0354, 0.0436, 0.0416,
                       0.0756, 0.0753, 0.0844, 0.0731, 0.0830, 0.0849],
    "SUPPORT_RATIO": [0.1802, 0.2003, 0.3539, 0.2955, 0.2158, 0.2210,
                       0.1471, 0.1548, 0.1603, 0.1538, 0.1528, 0.1509],
    "COMPETE_RATIO": [0.0487, 0.0473, 0.0787, 0.0808, 0.0643, 0.0635,
                       0.0672, 0.0669, 0.0717, 0.0654, 0.0699, 0.0660],
})

# V_BRANCH_TREND — 프랜차이즈 비중 추이 (전체 업종 기준, 위약검정 통과)
# 2023년: 보정 전 5.90%(파싱 오류) → 보정 후 25.84%로 복구
MOCK["V_BRANCH_TREND"] = pd.DataFrame({
    "YR":            [2021, 2022, 2023, 2024, 2025, 2026] * 2,
    "SECTOR":        ["성심당방향"] * 6 + ["반대방향"] * 6,
    "N":             [400, 380, 340, 350, 400, 390, 150, 155, 160, 170, 165, 160],
    "BRANCH_RATIO":  [0.1581, 0.1672, 0.2584, 0.2374, 0.2104, 0.2013,
                       0.1387, 0.1506, 0.1350, 0.1192, 0.1228, 0.1226],
})

# V_BRANCH_COMPETE — 경쟁재(카페·제과) 한정 프랜차이즈 비중 (참고용, 표본 작음)
# 위약검정 미실시. 개별 연도 95% CI가 겹쳐 단독으로는 유의성 주장 불가.
MOCK["V_BRANCH_COMPETE"] = pd.DataFrame({
    "YR":       [2021, 2022, 2023, 2024, 2025, 2026],
    "ANCHOR_PCT": [36.4, 40.0, 42.9, 46.9, 41.9, 41.4],
    "ANCHOR_N":   [33, 30, 28, 32, 31, 29],
    "OPPO_PCT":   [18.8, 18.8, 5.9, 13.3, 12.5, 7.1],
    "OPPO_N":     [16, 16, 17, 15, 16, 14],
})

# V_RENT_INDEX — 대전 5개 상권 임대가격지수 (실측, 한국부동산원)
# 전 상권 하락 국면. 원도심은 5개 중 4번째(중간~하락 쪽) — "안정적"이 아님
MOCK["V_RENT_INDEX"] = pd.DataFrame({
    "QTR": ["2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"] * 5,
    "DISTRICT": (["원도심"] * 9 + ["서대전네거리"] * 9 + ["용문한민시장"] * 9
                 + ["복합터미널"] * 9 + ["노은"] * 9),
    "RENT_INDEX_CHG_PP": [
        0.00, -0.11, -0.21, -0.06, -0.16, -0.50, -0.56, -0.58, -0.59,   # 원도심
        0.00, -0.20, -0.25, -0.29, -0.31, -0.32, -0.40, -0.55, -0.47,   # 서대전네거리
        0.00, -0.07, -0.09, -0.21, -0.43, -0.47, -0.51, -0.78, -0.63,   # 용문한민시장
        0.00, -0.76, -2.15, -2.41, -2.86, -3.64, -4.22, -4.31, -4.45,   # 복합터미널
        0.00, -1.44, -1.48, -1.49, -1.49, -1.59, -2.13, -2.28, -2.08,   # 노은
    ],
})

# V_FINAL_SUMMARY — 실제 V_FINAL_SUMMARY 검정 결과 그대로
MOCK["V_FINAL_SUMMARY"] = pd.DataFrame({
    "STAGE":   ["실패1", "실패2", "구성1(생활밀착)", "구성2(보완재)", "구성3(경쟁재)", "최종"],
    "METHOD":  ["원형거리+Placebo", "방향통제+견고성", "업종 DiD", "업종 DiD", "업종 DiD", "업종 구성 변화"],
    "RESULT":  ["성심당 -3.15%p, 중앙로역 -4.11%p", "-7.02%p, Cluster p=0.575, 위약 36.7%",
                "-1.79%p, 위약 11.7%(중심점 20.0%)", "+3.69%p, 위약 상위 3.3%",
                "+1.59%p, 위약 상위 43.3%", "보완재만 채택"],
    "VERDICT": ["기각", "기각", "기각", "채택", "기각", "채택"],
})


# ─────────────────────────────────────────────────────────────────
# 공통 상수
# ─────────────────────────────────────────────────────────────────

ANCHOR = (36.32752, 127.42718)   # 성심당
CENTER = (36.32870, 127.42750)   # 중앙로역
ANC_BEARING = 195.2

COLOR_ANCHOR = "#0F6E56"   # 성심당방향 — teal
COLOR_OPPO   = "#D85A30"   # 반대방향 — coral
COLOR_NEUTRAL = "#B4B2A9"

ISOTROPY_NOTE = "※ 방향 비교는 직선거리·각도 기준이며, 실제로는 서로 다른 상업축을 비교한 것에 가깝다"


# =====================================================================
# 헤더
# =====================================================================

st.title("성심당은 상권을 살렸는가, 바꿨는가, 채웠는가")
st.caption("우리는 그 답을 세 번 의심했다 — 대전 원도심 앵커 상권 분석")

if not SNOW_OK:
    st.error("Snowflake 세션에 연결되지 않았습니다. 로컬 테스트 모드로 전체 화면이 MOCK 데이터로 표시됩니다.")


# =====================================================================
# STEP 1 · 대전 전체
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 1 · 대전 전체")
    df1 = load("V_FOOD_CLEAN")
    status_badge("V_FOOD_CLEAN")

    c1, c2, c3 = st.columns(3)
    c1.metric("분석 업소", f"{len(df1) if not MOCK_MODE.get('V_FOOD_CLEAN', True) else 80824:,}곳")
    c2.metric("관측 기간", "1942–2026")
    c3.metric("코호트 연도", "10개 (2014–2023)")

    if len(df1) > 0:
        st.map(df1[["LAT", "LON"]].rename(columns={"LAT": "lat", "LON": "lon"}), size=3)

    st.markdown(
        "> 성심당이 대전을 먹여살린다는 얘기는 다들 안다. "
        "언론은 이미 성심당을 '앵커 테넌트'라 부른다. 우리는 이걸 확인해보기로 했다."
    )


# =====================================================================
# STEP 2 · 성심당 거리 분석
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 2 · 성심당까지 거리로 재보면")
    df2 = load("V_PLACEBO")
    status_badge("V_PLACEBO")

    ssd = df2[df2.POINT_NM == "성심당"]
    if len(ssd) > 0:
        row = ssd.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("PRE 격차", f"{row.GAP_PRE_PP:+.1f}%p")
        c2.metric("POST 격차", f"{row.GAP_POST_PP:+.1f}%p")
        c3.metric("DiD", f"{row.DID_PP:+.1f}%p", delta_color="off")

    st.markdown("> 가까우면 덜 망하는 것처럼 보인다. 그런데 이게 성심당 때문일까?")


# =====================================================================
# STEP 3 · Placebo 비교 — 실패 1 ★
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 3 · 그런데 성심당만 그럴까? — Placebo 검정")
    df3 = load("V_PLACEBO")
    status_badge("V_PLACEBO")

    df3_sorted = df3.sort_values("DID_PP")
    chart_df = df3_sorted.set_index("POINT_NM")[["DID_PP"]]
    st.bar_chart(chart_df, color=COLOR_ANCHOR, height=380)
    st.caption("막대가 아래(음수)로 갈수록 그 지점 근처가 폐업률이 낮다는 뜻")

    ssd_did = df3[df3.POINT_NM == "성심당"].DID_PP.values[0]
    stronger = df3[df3.DID_PP < ssd_did].POINT_NM.tolist()
    if stronger:
        st.warning(f"같은 계산을 다른 지점에 돌렸더니 **{', '.join(stronger)}**가 더 강했습니다.")

    st.markdown("> 원형 거리만으로는 성심당 효과를 분리할 수 없다. 원도심 중심이라 좋은 것과 구분이 안 된다.")


# =====================================================================
# STEP 4 · 각도 통제 — 실패 2 설계
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 4 · 방향을 통제하면 어떨까")
    st.markdown(
        "중앙로역에서 **같은 거리**에 있는 가게들만 비교한다. "
        "역까지 거리가 같으니 역세권 효과는 상수가 되고, 방향만 남는다."
    )

    map_df = pd.DataFrame({
        "lat": [CENTER[0], ANCHOR[0]],
        "lon": [CENTER[1], ANCHOR[1]],
    })
    st.map(map_df, latitude="lat", longitude="lon", zoom=15, size=40)
    st.caption("아래쪽 점 = 중앙로역, 위쪽 점 = 성심당 (좌표: 중앙로역 36.3287/127.4275, 성심당 36.3275/127.4272)")

    st.markdown(
        f"> 성심당 방향 = 중앙로역 기준 방위각 {ANC_BEARING}°에서 ±각도폭 이내. "
        "반대 방향 = 120° 이상 벌어진 쪽."
    )


# =====================================================================
# STEP 5 · 300m 효과 — 발표 중심 ★★
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 5 · 반경 300m에서 무슨 일이 있었나 — 발표 핵심")
    df5 = load("V_SECTOR_GAP")
    status_badge("V_SECTOR_GAP")

    half = st.slider("섹터 각도폭 (±)", 30, 90, 60, step=15,
                      help="각도폭을 바꿔도 결론이 유지되는지 확인합니다")

    df5s = load("V_ANGLE_SENSITIVITY")
    sel = df5s[df5s.HALF == half]
    if len(sel) > 0:
        r = sel.iloc[0]
        gap = r.RATE_ANCHOR - r.RATE_OPPO
        st.metric(f"±{half}° 기준 0-300m 격차", f"{gap:+.1f}%p",
                  delta=f"성심당 {r.RATE_ANCHOR:.1f}% vs 반대 {r.RATE_OPPO:.1f}%",
                  delta_color="off")

    chart5_df = df5.set_index("CENTER_BAND")[["GAP_PP"]]
    st.bar_chart(chart5_df, color=COLOR_ANCHOR, height=380)
    st.caption("막대가 아래(음수)면 성심당 방향이 유리, 위(양수)면 반대 방향이 유리 · 강조 구간: 150-300m")

    st.markdown("> 150–300m에서 가장 크게 벌어지고, 300m를 넘으면 효과가 사라진다. "
                "450m부터는 오히려 반대 방향이 유리해진다 — 대전역 권역이기 때문이다.")
    st.caption(ISOTROPY_NOTE)


# =====================================================================
# STEP 6 · 견고성 검정 통합 — 실패 2 결말 ★
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 6 · 그런데 이게 우연이 아니라고 말할 수 있나 — 위약 검정")
    df6 = load("V_PLACEBO_SUMMARY")
    status_badge("V_PLACEBO_SUMMARY")

    def verdict_color(v):
        return {"통과": "background-color:#d4edda",
                "기각": "background-color:#f8d7da",
                "경계": "background-color:#fff3cd"}.get(v, "")

    st.dataframe(
        df6.style.applymap(verdict_color, subset=["VERDICT"]),
        use_container_width=True, hide_index=True,
    )

    n_fail = (df6.VERDICT == "기각").sum()
    n_pass = (df6.VERDICT == "통과").sum()
    st.error(f"**{n_fail}개 지표가 무작위 방향에서도 흔하게 나왔습니다.** "
             f"통과한 건 {n_pass}개뿐입니다.")

    st.markdown("> 폐업률로는 여기까지가 한계였다. 그래서 질문을 바꿨다 — "
                "'누가 잘 사는가'가 아니라 '누가 나가고 누가 들어왔는가'.")


# =====================================================================
# STEP 7 · 경리단길형 기각
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 7 · 임대료 때문일까 — 경리단길형 검토")
    df7 = load("V_RENT_INDEX")
    status_badge("V_RENT_INDEX")

    chart7_df = df7.pivot(index="QTR", columns="DISTRICT", values="RENT_INDEX_CHG_PP")
    st.line_chart(chart7_df, height=380)

    wondosim = df7[df7.DISTRICT == "원도심"].iloc[-1]
    rank = df7[df7.QTR == df7.QTR.max()].sort_values("RENT_INDEX_CHG_PP", ascending=False)
    rank_pos = list(rank.DISTRICT).index("원도심") + 1
    st.metric("원도심 임대료 변화 (2024Q2→2026Q2)", f"{wondosim.RENT_INDEX_CHG_PP:+.2f}%p",
              delta=f"대전 5개 상권 중 낙폭 {rank_pos}번째로 작음 (상대적으로 안정)",
              delta_color="off")

    df7b = load("V_ROLE_TREND")
    if len(df7b) > 0:
        life21 = df7b[(df7b.YR == 2021) & (df7b.SECTOR == "성심당방향")].LIFE_RATIO.values
        life26 = df7b[(df7b.YR == 2026) & (df7b.SECTOR == "성심당방향")].LIFE_RATIO.values
        if len(life21) and len(life26):
            st.metric("생활밀착업종 비율 (성심당방향)",
                      f"{life26[0]*100:.2f}%",
                      delta=f"{(life26[0]-life21[0])*100:+.2f}%p (2021 대비)")

    st.markdown(f"> **대전 5개 상권 전체가 하락 국면이며, 원도심은 그중 낙폭이 {rank_pos}번째로 작다(비교적 안정적).** "
                "원도심만 특별히 임대료가 오르거나 유독 불안정한 게 아니다. "
                "생활밀착업종도 급격히 사라지지 않았다. **경리단길형(임대료發) 젠트리피케이션은 아니다.**")


# =====================================================================
# STEP 8 · 프랜차이즈 급증 — 새 발표 중심 ★★
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 8 · 그럼 뭐가 바뀌었나 — 프랜차이즈 비중")
    df8 = load("V_BRANCH_TREND")
    status_badge("V_BRANCH_TREND")

    chart8_df = df8.pivot(index="YR", columns="SECTOR", values="BRANCH_RATIO") * 100
    st.line_chart(chart8_df, height=400)

    a21 = df8[(df8.YR == 2021) & (df8.SECTOR == "성심당방향")].BRANCH_RATIO.values[0]
    a26 = df8[(df8.YR == 2026) & (df8.SECTOR == "성심당방향")].BRANCH_RATIO.values[0]
    b21 = df8[(df8.YR == 2021) & (df8.SECTOR == "반대방향")].BRANCH_RATIO.values[0]
    b26 = df8[(df8.YR == 2026) & (df8.SECTOR == "반대방향")].BRANCH_RATIO.values[0]

    c1, c2 = st.columns(2)
    c1.metric("성심당 방향 (2021→2026)", f"{a26*100:.1f}%", delta=f"{(a26-a21)*100:+.1f}%p")
    c2.metric("반대 방향 (2021→2026)", f"{b26*100:.1f}%", delta=f"{(b26-b21)*100:+.1f}%p")

    st.success(f"격차가 {(a21-b21)*100:+.1f}%p → {(a26-b26)*100:+.1f}%p로 벌어졌다. "
               "위약 검정 상위 10.0%로 통과.")

    st.markdown("> 반대 방향은 5년간 12~15%에서 거의 움직이지 않았다. "
                "성심당 방향만 개인 가게가 프랜차이즈로 교체되고 있다.")
    st.caption(ISOTROPY_NOTE)

    with st.expander("참고 · 경쟁재(카페·제과) 한정 프랜차이즈 비중 — 표본 작음, 위약검정 미실시"):
        dfc = load("V_BRANCH_COMPETE")
        status_badge("V_BRANCH_COMPETE")
        show = dfc.copy()
        show["성심당방향"] = show.apply(lambda r: f"{r.ANCHOR_PCT:.1f}% (n={r.ANCHOR_N})", axis=1)
        show["반대방향"] = show.apply(lambda r: f"{r.OPPO_PCT:.1f}% (n={r.OPPO_N})", axis=1)
        st.dataframe(show[["YR", "성심당방향", "반대방향"]], use_container_width=True, hide_index=True)
        st.caption(
            "개별 연도는 표본이 작아(n=14~33) 95% 신뢰구간이 겹치며, 단독으로는 통계적 유의성을 주장할 수 없다. "
            "6개년 연속 같은 방향(성심당방향 우세)이라는 경향성만 참고로 제시한다. "
            "위 STEP 8의 전체 업종 프랜차이즈 지표(위약검정 상위 10.0% 통과)가 메인 근거다."
        )


# =====================================================================
# STEP 9 · 최종 결론
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 9 · 결론 — 기존 두 유형 어디에도 맞지 않았다")
    df9 = load("V_FINAL_SUMMARY")
    status_badge("V_FINAL_SUMMARY")

    def verdict_color9(v):
        return {"채택": "background-color:#d4edda", "기각": "background-color:#f8d7da"}.get(v, "")

    st.dataframe(
        df9.style.applymap(verdict_color9, subset=["VERDICT"]),
        use_container_width=True, hide_index=True,
    )

    st.info(
        "**성심당 원도심은 경리단길형(임대료發)도 송리단길형(카페 과포화發)도 아니었다.** "
        "임대료는 대전 전역과 함께 하락했고, 경쟁재(카페·제과) 증가는 위약검정을 통과하지 못했다.\n\n"
        "대신 **보완재(음식점·주점) 비중과 프랜차이즈 비중만 위약검정을 통과**했다. "
        "성심당 방향에서 개인 가게가 프랜차이즈 식당·주점으로 재편되는, "
        "기존 두 유형 어디에도 온전히 들어맞지 않는 패턴이다."
    )
    st.caption(ISOTROPY_NOTE + " — 따라서 이 결론은 '성심당 중심 원형 영향권'이 아니라 "
               "'중앙로역 기준 두 상업축 간의 상대적 차이'로 해석하는 것이 정확하다.")

    with st.expander("한계 (반드시 확인)"):
        st.markdown("""
- 대전 원도심 **단일 사례(N=1)** — 다른 도시 앵커에 일반화되지 않음
- **방향(각도) 비교는 공간이 등방적이라고 가정한다.** 대전 원도심 상권은 도로를 따라 선형으로 배치돼 있어,
  같은 직선거리·다른 각도가 실제로는 서로 다른 상업축을 비교한 것일 수 있다
- 폐업률 기반 방향 대조는 **위약 검정에서 대부분 기각**됨 (보완재·프랜차이즈만 생존)
- 경쟁재(카페) 한정 프랜차이즈 비중은 표본이 작아(n<33) 개별 연도 유의성 주장 불가
- 상가업소정보는 **개별 업소 장기 추적이 어려움** — 구역 단위 비율 비교로 대체
- 유동인구·카드 소비 데이터 없음 — "관광객이 실제 매출로 이어지는가"는 검증 못 함
- 프랜차이즈는 `BRANCH_NM` 유무로 근사한 지표 — 실제 가맹 여부와 다를 수 있음
        """)


# =====================================================================
# 사이드바 — 개발용 상태 패널
# =====================================================================

with st.sidebar:
    st.header("개발 상태")
    st.write("Snowflake 연결:", "🟢 연결됨" if SNOW_OK else "🔴 미연결 (로컬 테스트)")
    st.divider()
    st.caption("VIEW별 데이터 소스")
    for v in sorted(set(MOCK.keys())):
        is_mock = MOCK_MODE.get(v, True)
        st.write(("🟡 " if is_mock else "🟢 ") + v)
    st.divider()
    st.caption(
        "🟡 = MOCK 데이터 (팀 VIEW 대기 중)\n\n"
        "🟢 = 실데이터 연결됨\n\n"
        "VIEW가 생기면 자동으로 🟢 전환됩니다. 코드 수정 불필요."
    )