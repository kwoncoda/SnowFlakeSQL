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
# v4 수정사항
#   - [버그] 캐시된 load() 안에서 MOCK_MODE를 기록하던 구조 수정
#     → rerun 시 캐시 히트로 본문이 실행되지 않아 실데이터인데도 🟡 MOCK으로 표시되던 문제
#     → 조회(_fetch)만 캐시하고, 상태 기록은 캐시 밖 load()에서 수행
#   - [버그] 실패한 조회가 MOCK과 함께 1시간 캐시되던 문제 → 예외는 캐시되지 않으므로
#     VIEW 생성 즉시 다음 rerun에서 자동으로 🟢 전환
#   - 사이드바에 캐시 수동 초기화 버튼 추가
#   - STEP 1 지도: 실데이터 8만 건 전량 렌더 방지(샘플링)
#   - .style.applymap → .style.map (pandas 2.1+ deprecation, 구버전 폴백 포함)
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

MOCK_MODE = {}   # 화면별로 mock 사용 여부 기록 → 상단 배지에 표시
LOAD_ERRORS = {}  # 화면별로 실패 이유 기록 → 디버깅용


# ─────────────────────────────────────────────────────────────────
# 데이터 로더 — VIEW 없으면 MOCK으로 자동 폴백
#
# ★ 중요: 캐시는 "조회"에만 건다.
#   MOCK_MODE 기록을 캐시된 함수 안에 두면, rerun 시 캐시 히트로 본문이
#   실행되지 않아 매 rerun마다 초기화되는 MOCK_MODE가 비어 있게 되고,
#   .get(name, True) 기본값 때문에 실데이터인데도 MOCK으로 표시된다.
# ─────────────────────────────────────────────────────────────────

FULL_SCHEMA = "PROJECT_DB.SHARED_FILES"  # SHOW VIEWS 결과 기준 확정 경로


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch(view_name: str) -> pd.DataFrame:
    """Snowflake VIEW 조회만 담당. 예외는 Streamlit이 캐시하지 않으므로
    실패한 VIEW는 다음 rerun에서 자동 재시도된다."""
    return session.table(f"{FULL_SCHEMA}.{view_name}").to_pandas()


def load(view_name: str) -> pd.DataFrame:
    """VIEW를 읽되, 없거나 접근 실패 시 MOCK 반환. 상태 기록은 여기(캐시 밖)서 한다."""
    if SNOW_OK:
        try:
            df = _fetch(view_name)
            MOCK_MODE[view_name] = False
            LOAD_ERRORS.pop(view_name, None)
            return df.copy()   # 캐시 객체 직접 수정 방지
        except Exception as e:
            LOAD_ERRORS[view_name] = str(e)
    MOCK_MODE[view_name] = True
    return MOCK.get(view_name, pd.DataFrame()).copy()


def status_badge(view_name: str):
    """이 화면이 mock인지 실데이터인지 표시"""
    is_mock = MOCK_MODE.get(view_name, True)
    if is_mock:
        err = LOAD_ERRORS.get(view_name)
        if err:
            st.caption(f"🟡 MOCK 데이터 사용 중 — `{view_name}` 연결 실패")
            with st.expander(f"⚠ {view_name} 실패 원인 보기", expanded=False):
                st.code(err[:500])
        else:
            st.caption(f"🟡 MOCK 데이터 사용 중 — `{view_name}` 아직 없음. 태운 님 작업 완료 후 자동 전환됩니다.")
    else:
        st.caption(f"🟢 실데이터 — `{view_name}`")


def style_verdict(styler, func, subset):
    """pandas 2.1+ 는 Styler.map, 그 이전은 Styler.applymap"""
    if hasattr(styler, "map"):
        return styler.map(func, subset=subset)
    return styler.applymap(func, subset=subset)


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

# V_PLACEBO_SUMMARY — 실제 SQL 재생성분 기준 (컬럼명 TEST_NAME/OBSERVED_VALUE로 변경됨)
# 경쟁재 비중 항목이 빠지고 HHI 다양성으로 교체됨. 폐업률/각도회귀 위약값도 재계산되어 소폭 변경.
MOCK["V_PLACEBO_SUMMARY"] = pd.DataFrame({
    "TEST_NAME":      ["폐업률 -7.0%p", "각도 회귀 (클러스터 SE)", "HHI 다양성", "보완재 비중", "생활밀착 비중", "프랜차이즈 비중"],
    "OBSERVED_VALUE": ["-7.0%p", "p=0.496", "-672", "+3.69%p", "-1.79%p", "+5.93%p"],
    "PLACEBO_RANK":   ["하위 23.3%", "-", "상위 71.7%", "상위 3.3%", "하위 11.7%", "상위 10.0%"],
    "VERDICT":        ["기각", "기각", "기각", "통과", "경계", "통과"],
})

# V_ROLE_TREND — 실패3, 연도×방향 업종비율 (long format: YR,SECTOR,ROLE,N,TOTAL_N,PCT)
_role_years   = [2021, 2022, 2023, 2024, 2025, 2026]
_role_sectors = ["성심당방향", "반대방향"]
_role_total_n = {"성심당방향": [677, 634, 356, 396, 482, 457],
                  "반대방향":   [238, 239, 237, 260, 229, 212]}
_role_pct = {
    "생활밀착": {"성심당방향": [5.02, 4.89, 3.65, 3.54, 4.36, 4.16],
                "반대방향":   [7.56, 7.53, 8.44, 7.31, 8.30, 8.49]},
    "보완재":   {"성심당방향": [18.02, 20.03, 35.39, 29.55, 21.58, 22.10],
                "반대방향":   [14.71, 15.48, 16.03, 15.38, 15.28, 15.09]},
    "경쟁재":   {"성심당방향": [4.87, 4.73, 7.87, 8.08, 6.43, 6.35],
                "반대방향":   [6.72, 6.69, 7.17, 6.54, 6.99, 6.60]},
}
_rows = []
for role, sec_map in _role_pct.items():
    for sector in _role_sectors:
        for i, yr in enumerate(_role_years):
            total_n = _role_total_n[sector][i]
            pct = sec_map[sector][i]
            _rows.append({"YR": yr, "SECTOR": sector, "ROLE": role,
                          "N": round(total_n * pct / 100), "TOTAL_N": total_n, "PCT": pct})
MOCK["V_ROLE_TREND"] = pd.DataFrame(_rows)

# V_BRANCH_TREND — 실측치 그대로 (long format: YR,SECTOR,ROLE,N,K,BRANCH_PCT,CI_LO_PCT,CI_HI_PCT)
MOCK["V_BRANCH_TREND"] = pd.DataFrame([
    {"YR": 2021, "SECTOR": "반대방향", "ROLE": "경쟁재", "N": 16, "K": 3, "BRANCH_PCT": 18.75, "CI_LO_PCT": 6.59, "CI_HI_PCT": 43.01},
    {"YR": 2021, "SECTOR": "반대방향", "ROLE": "기타", "N": 70, "K": 2, "BRANCH_PCT": 2.86, "CI_LO_PCT": 0.79, "CI_HI_PCT": 9.83},
    {"YR": 2021, "SECTOR": "반대방향", "ROLE": "보완재", "N": 35, "K": 1, "BRANCH_PCT": 2.86, "CI_LO_PCT": 0.51, "CI_HI_PCT": 14.53},
    {"YR": 2021, "SECTOR": "반대방향", "ROLE": "생활기타", "N": 3, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 56.15},
    {"YR": 2021, "SECTOR": "반대방향", "ROLE": "생활밀착", "N": 18, "K": 3, "BRANCH_PCT": 16.67, "CI_LO_PCT": 5.84, "CI_HI_PCT": 39.22},
    {"YR": 2021, "SECTOR": "반대방향", "ROLE": "소매", "N": 96, "K": 24, "BRANCH_PCT": 25.0, "CI_LO_PCT": 17.41, "CI_HI_PCT": 34.51},
    {"YR": 2021, "SECTOR": "성심당방향", "ROLE": "경쟁재", "N": 33, "K": 12, "BRANCH_PCT": 36.36, "CI_LO_PCT": 22.19, "CI_HI_PCT": 53.38},
    {"YR": 2021, "SECTOR": "성심당방향", "ROLE": "기타", "N": 97, "K": 14, "BRANCH_PCT": 14.43, "CI_LO_PCT": 8.8, "CI_HI_PCT": 22.78},
    {"YR": 2021, "SECTOR": "성심당방향", "ROLE": "보완재", "N": 122, "K": 38, "BRANCH_PCT": 31.15, "CI_LO_PCT": 23.61, "CI_HI_PCT": 39.83},
    {"YR": 2021, "SECTOR": "성심당방향", "ROLE": "생활기타", "N": 4, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 48.99},
    {"YR": 2021, "SECTOR": "성심당방향", "ROLE": "생활밀착", "N": 34, "K": 1, "BRANCH_PCT": 2.94, "CI_LO_PCT": 0.52, "CI_HI_PCT": 14.92},
    {"YR": 2021, "SECTOR": "성심당방향", "ROLE": "소매", "N": 387, "K": 42, "BRANCH_PCT": 10.85, "CI_LO_PCT": 8.13, "CI_HI_PCT": 14.35},
    {"YR": 2022, "SECTOR": "반대방향", "ROLE": "경쟁재", "N": 16, "K": 3, "BRANCH_PCT": 18.75, "CI_LO_PCT": 6.59, "CI_HI_PCT": 43.01},
    {"YR": 2022, "SECTOR": "반대방향", "ROLE": "기타", "N": 69, "K": 2, "BRANCH_PCT": 2.9, "CI_LO_PCT": 0.8, "CI_HI_PCT": 9.97},
    {"YR": 2022, "SECTOR": "반대방향", "ROLE": "보완재", "N": 37, "K": 3, "BRANCH_PCT": 8.11, "CI_LO_PCT": 2.8, "CI_HI_PCT": 21.3},
    {"YR": 2022, "SECTOR": "반대방향", "ROLE": "생활기타", "N": 2, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 65.76},
    {"YR": 2022, "SECTOR": "반대방향", "ROLE": "생활밀착", "N": 18, "K": 3, "BRANCH_PCT": 16.67, "CI_LO_PCT": 5.84, "CI_HI_PCT": 39.22},
    {"YR": 2022, "SECTOR": "반대방향", "ROLE": "소매", "N": 97, "K": 25, "BRANCH_PCT": 25.77, "CI_LO_PCT": 18.11, "CI_HI_PCT": 35.28},
    {"YR": 2022, "SECTOR": "성심당방향", "ROLE": "경쟁재", "N": 30, "K": 12, "BRANCH_PCT": 40.0, "CI_LO_PCT": 24.59, "CI_HI_PCT": 57.68},
    {"YR": 2022, "SECTOR": "성심당방향", "ROLE": "기타", "N": 92, "K": 14, "BRANCH_PCT": 15.22, "CI_LO_PCT": 9.29, "CI_HI_PCT": 23.94},
    {"YR": 2022, "SECTOR": "성심당방향", "ROLE": "보완재", "N": 127, "K": 40, "BRANCH_PCT": 31.5, "CI_LO_PCT": 24.06, "CI_HI_PCT": 40.02},
    {"YR": 2022, "SECTOR": "성심당방향", "ROLE": "생활기타", "N": 6, "K": 1, "BRANCH_PCT": 16.67, "CI_LO_PCT": 3.01, "CI_HI_PCT": 56.35},
    {"YR": 2022, "SECTOR": "성심당방향", "ROLE": "생활밀착", "N": 31, "K": 1, "BRANCH_PCT": 3.23, "CI_LO_PCT": 0.57, "CI_HI_PCT": 16.19},
    {"YR": 2022, "SECTOR": "성심당방향", "ROLE": "소매", "N": 348, "K": 38, "BRANCH_PCT": 10.92, "CI_LO_PCT": 8.06, "CI_HI_PCT": 14.63},
    {"YR": 2023, "SECTOR": "반대방향", "ROLE": "경쟁재", "N": 17, "K": 1, "BRANCH_PCT": 5.88, "CI_LO_PCT": 1.05, "CI_HI_PCT": 26.98},
    {"YR": 2023, "SECTOR": "반대방향", "ROLE": "기타", "N": 62, "K": 2, "BRANCH_PCT": 3.23, "CI_LO_PCT": 0.89, "CI_HI_PCT": 11.02},
    {"YR": 2023, "SECTOR": "반대방향", "ROLE": "보완재", "N": 38, "K": 5, "BRANCH_PCT": 13.16, "CI_LO_PCT": 5.75, "CI_HI_PCT": 27.33},
    {"YR": 2023, "SECTOR": "반대방향", "ROLE": "생활기타", "N": 2, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 65.76},
    {"YR": 2023, "SECTOR": "반대방향", "ROLE": "생활밀착", "N": 20, "K": 3, "BRANCH_PCT": 15.0, "CI_LO_PCT": 5.24, "CI_HI_PCT": 36.04},
    {"YR": 2023, "SECTOR": "반대방향", "ROLE": "소매", "N": 98, "K": 21, "BRANCH_PCT": 21.43, "CI_LO_PCT": 14.46, "CI_HI_PCT": 30.55},
    {"YR": 2023, "SECTOR": "성심당방향", "ROLE": "경쟁재", "N": 28, "K": 12, "BRANCH_PCT": 42.86, "CI_LO_PCT": 26.51, "CI_HI_PCT": 60.93},
    {"YR": 2023, "SECTOR": "성심당방향", "ROLE": "기타", "N": 84, "K": 17, "BRANCH_PCT": 20.24, "CI_LO_PCT": 13.04, "CI_HI_PCT": 30.04},
    {"YR": 2023, "SECTOR": "성심당방향", "ROLE": "보완재", "N": 126, "K": 43, "BRANCH_PCT": 34.13, "CI_LO_PCT": 26.43, "CI_HI_PCT": 42.77},
    {"YR": 2023, "SECTOR": "성심당방향", "ROLE": "생활기타", "N": 6, "K": 1, "BRANCH_PCT": 16.67, "CI_LO_PCT": 3.01, "CI_HI_PCT": 56.35},
    {"YR": 2023, "SECTOR": "성심당방향", "ROLE": "생활밀착", "N": 13, "K": 1, "BRANCH_PCT": 7.69, "CI_LO_PCT": 1.37, "CI_HI_PCT": 33.31},
    {"YR": 2023, "SECTOR": "성심당방향", "ROLE": "소매", "N": 99, "K": 18, "BRANCH_PCT": 18.18, "CI_LO_PCT": 11.82, "CI_HI_PCT": 26.92},
    {"YR": 2024, "SECTOR": "반대방향", "ROLE": "경쟁재", "N": 15, "K": 2, "BRANCH_PCT": 13.33, "CI_LO_PCT": 3.74, "CI_HI_PCT": 37.88},
    {"YR": 2024, "SECTOR": "반대방향", "ROLE": "기타", "N": 72, "K": 1, "BRANCH_PCT": 1.39, "CI_LO_PCT": 0.25, "CI_HI_PCT": 7.46},
    {"YR": 2024, "SECTOR": "반대방향", "ROLE": "보완재", "N": 40, "K": 3, "BRANCH_PCT": 7.5, "CI_LO_PCT": 2.58, "CI_HI_PCT": 19.86},
    {"YR": 2024, "SECTOR": "반대방향", "ROLE": "생활기타", "N": 2, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 65.76},
    {"YR": 2024, "SECTOR": "반대방향", "ROLE": "생활밀착", "N": 19, "K": 3, "BRANCH_PCT": 15.79, "CI_LO_PCT": 5.52, "CI_HI_PCT": 37.57},
    {"YR": 2024, "SECTOR": "반대방향", "ROLE": "소매", "N": 112, "K": 22, "BRANCH_PCT": 19.64, "CI_LO_PCT": 13.34, "CI_HI_PCT": 27.95},
    {"YR": 2024, "SECTOR": "성심당방향", "ROLE": "경쟁재", "N": 32, "K": 15, "BRANCH_PCT": 46.88, "CI_LO_PCT": 30.87, "CI_HI_PCT": 63.55},
    {"YR": 2024, "SECTOR": "성심당방향", "ROLE": "기타", "N": 107, "K": 23, "BRANCH_PCT": 21.5, "CI_LO_PCT": 14.77, "CI_HI_PCT": 30.19},
    {"YR": 2024, "SECTOR": "성심당방향", "ROLE": "보완재", "N": 117, "K": 34, "BRANCH_PCT": 29.06, "CI_LO_PCT": 21.6, "CI_HI_PCT": 37.85},
    {"YR": 2024, "SECTOR": "성심당방향", "ROLE": "생활기타", "N": 5, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 43.45},
    {"YR": 2024, "SECTOR": "성심당방향", "ROLE": "생활밀착", "N": 14, "K": 3, "BRANCH_PCT": 21.43, "CI_LO_PCT": 7.57, "CI_HI_PCT": 47.59},
    {"YR": 2024, "SECTOR": "성심당방향", "ROLE": "소매", "N": 121, "K": 19, "BRANCH_PCT": 15.7, "CI_LO_PCT": 10.29, "CI_HI_PCT": 23.23},
    {"YR": 2025, "SECTOR": "반대방향", "ROLE": "경쟁재", "N": 16, "K": 2, "BRANCH_PCT": 12.5, "CI_LO_PCT": 3.5, "CI_HI_PCT": 36.02},
    {"YR": 2025, "SECTOR": "반대방향", "ROLE": "기타", "N": 61, "K": 1, "BRANCH_PCT": 1.64, "CI_LO_PCT": 0.29, "CI_HI_PCT": 8.72},
    {"YR": 2025, "SECTOR": "반대방향", "ROLE": "보완재", "N": 35, "K": 1, "BRANCH_PCT": 2.86, "CI_LO_PCT": 0.51, "CI_HI_PCT": 14.53},
    {"YR": 2025, "SECTOR": "반대방향", "ROLE": "생활기타", "N": 2, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 65.76},
    {"YR": 2025, "SECTOR": "반대방향", "ROLE": "생활밀착", "N": 18, "K": 3, "BRANCH_PCT": 16.67, "CI_LO_PCT": 5.84, "CI_HI_PCT": 39.22},
    {"YR": 2025, "SECTOR": "반대방향", "ROLE": "소매", "N": 96, "K": 21, "BRANCH_PCT": 21.88, "CI_LO_PCT": 14.78, "CI_HI_PCT": 31.14},
    {"YR": 2025, "SECTOR": "성심당방향", "ROLE": "경쟁재", "N": 31, "K": 13, "BRANCH_PCT": 41.94, "CI_LO_PCT": 26.42, "CI_HI_PCT": 59.23},
    {"YR": 2025, "SECTOR": "성심당방향", "ROLE": "기타", "N": 100, "K": 24, "BRANCH_PCT": 24.0, "CI_LO_PCT": 16.69, "CI_HI_PCT": 33.23},
    {"YR": 2025, "SECTOR": "성심당방향", "ROLE": "보완재", "N": 104, "K": 34, "BRANCH_PCT": 32.69, "CI_LO_PCT": 24.43, "CI_HI_PCT": 42.18},
    {"YR": 2025, "SECTOR": "성심당방향", "ROLE": "생활기타", "N": 3, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 56.15},
    {"YR": 2025, "SECTOR": "성심당방향", "ROLE": "생활밀착", "N": 21, "K": 3, "BRANCH_PCT": 14.29, "CI_LO_PCT": 4.98, "CI_HI_PCT": 34.64},
    {"YR": 2025, "SECTOR": "성심당방향", "ROLE": "소매", "N": 221, "K": 27, "BRANCH_PCT": 12.22, "CI_LO_PCT": 8.53, "CI_HI_PCT": 17.19},
    {"YR": 2026, "SECTOR": "반대방향", "ROLE": "경쟁재", "N": 14, "K": 1, "BRANCH_PCT": 7.14, "CI_LO_PCT": 1.27, "CI_HI_PCT": 31.47},
    {"YR": 2026, "SECTOR": "반대방향", "ROLE": "기타", "N": 57, "K": 1, "BRANCH_PCT": 1.75, "CI_LO_PCT": 0.31, "CI_HI_PCT": 9.29},
    {"YR": 2026, "SECTOR": "반대방향", "ROLE": "보완재", "N": 32, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 10.72},
    {"YR": 2026, "SECTOR": "반대방향", "ROLE": "생활기타", "N": 2, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 65.76},
    {"YR": 2026, "SECTOR": "반대방향", "ROLE": "생활밀착", "N": 18, "K": 3, "BRANCH_PCT": 16.67, "CI_LO_PCT": 5.84, "CI_HI_PCT": 39.22},
    {"YR": 2026, "SECTOR": "반대방향", "ROLE": "소매", "N": 89, "K": 21, "BRANCH_PCT": 23.6, "CI_LO_PCT": 15.98, "CI_HI_PCT": 33.39},
    {"YR": 2026, "SECTOR": "성심당방향", "ROLE": "경쟁재", "N": 29, "K": 12, "BRANCH_PCT": 41.38, "CI_LO_PCT": 25.51, "CI_HI_PCT": 59.26},
    {"YR": 2026, "SECTOR": "성심당방향", "ROLE": "기타", "N": 95, "K": 23, "BRANCH_PCT": 24.21, "CI_LO_PCT": 16.71, "CI_HI_PCT": 33.72},
    {"YR": 2026, "SECTOR": "성심당방향", "ROLE": "보완재", "N": 101, "K": 31, "BRANCH_PCT": 30.69, "CI_LO_PCT": 22.54, "CI_HI_PCT": 40.26},
    {"YR": 2026, "SECTOR": "성심당방향", "ROLE": "생활기타", "N": 4, "K": 0, "BRANCH_PCT": 0.0, "CI_LO_PCT": 0.0, "CI_HI_PCT": 48.99},
    {"YR": 2026, "SECTOR": "성심당방향", "ROLE": "생활밀착", "N": 19, "K": 2, "BRANCH_PCT": 10.53, "CI_LO_PCT": 2.94, "CI_HI_PCT": 31.39},
    {"YR": 2026, "SECTOR": "성심당방향", "ROLE": "소매", "N": 209, "K": 24, "BRANCH_PCT": 11.48, "CI_LO_PCT": 7.84, "CI_HI_PCT": 16.52},
])


# V_RENT_INDEX — 대전 5개 상권 임대가격지수 (실측, 한국부동산원)
# 전 상권 하락 국면. 원도심은 5개 중 4번째(중간~하락 쪽) — "안정적"이 아님
MOCK["V_RENT_INDEX"] = pd.DataFrame({
    "QTR": ["2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"] * 5,
    "DISTRICT": (["대전원도심"] * 9 + ["서대전네거리"] * 9 + ["용문한민시장"] * 9
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

    is_mock_1 = MOCK_MODE.get("V_FOOD_CLEAN", True)
    n_shops = len(df1) if not is_mock_1 else 80824  # MOCK일 때만 참고용 근사치(지도용 500건 샘플 아님)

    c1, c2, c3 = st.columns(3)
    c1.metric("분석 업소", f"{n_shops:,}곳", delta=("MOCK 근사치" if is_mock_1 else "실데이터 실측"), delta_color="off")
    c2.metric("관측 기간", "1942–2026")
    c3.metric("코호트 연도", "10개 (2014–2023)")

    if len(df1) > 0:
        # 실데이터는 8만 건 규모 — 전량 렌더 시 브라우저가 버티지 못하므로 샘플링
        MAP_SAMPLE_N = 3000
        map1 = df1[["LAT", "LON"]].dropna()
        if len(map1) > MAP_SAMPLE_N:
            map1 = map1.sample(MAP_SAMPLE_N, random_state=42)
            st.caption(f"지도는 {MAP_SAMPLE_N:,}건 무작위 샘플 표시 (전체 {n_shops:,}곳)")
        st.map(map1.rename(columns={"LAT": "lat", "LON": "lon"}), size=3)

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
        style_verdict(df6.style, verdict_color, ["VERDICT"]),
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

    latest_q = df7.QTR.max()
    rank = df7[df7.QTR == latest_q].sort_values("RENT_INDEX_CHG_PP", ascending=False)
    wondo_rows = rank[rank.DISTRICT == "대전원도심"]
    if len(wondo_rows) > 0:
        wondosim = wondo_rows.iloc[0]
        rank_pos = list(rank.DISTRICT).index("대전원도심") + 1
        st.metric("원도심 임대료 변화 (2024Q2→2026Q2)", f"{wondosim.RENT_INDEX_CHG_PP:+.2f}%p",
                  delta=f"대전 {len(rank)}개 상권 중 낙폭 {rank_pos}번째로 작음 (상대적으로 안정)",
                  delta_color="off")
    else:
        rank_pos = None
        st.caption(f"⚠ 최신 분기({latest_q})에 '대전원도심' 데이터가 없습니다 — DISTRICT 값을 확인해주세요.")

    df7b = load("V_ROLE_TREND")
    if len(df7b) > 0:
        def _role_pct(df, yr, sector, role):
            row = df[(df.YR == yr) & (df.SECTOR == sector) & (df.ROLE == role)]
            return float(row.PCT.iloc[0]) if len(row) else None
        life21 = _role_pct(df7b, 2021, "성심당방향", "생활밀착")
        life26 = _role_pct(df7b, 2026, "성심당방향", "생활밀착")
        if life21 is not None and life26 is not None:
            st.metric("생활밀착업종 비율 (성심당방향)",
                      f"{life26:.2f}%",
                      delta=f"{(life26-life21):+.2f}%p (2021 대비)")
        else:
            st.caption("⚠ V_ROLE_TREND에서 ROLE='생활밀착' 값을 찾지 못했습니다 — 실제 ROLE 값을 확인해주세요.")

    if rank_pos is not None:
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

    # 업종(ROLE) 전체를 합산해 "전체 업종 기준 프랜차이즈 비중" 계산
    agg = df8.groupby(["YR", "SECTOR"], as_index=False)[["N", "K"]].sum()
    agg["PCT"] = agg["K"] / agg["N"] * 100

    chart8_df = agg.pivot(index="YR", columns="SECTOR", values="PCT")
    st.line_chart(chart8_df, height=400)

    def _agg_pct(yr, sector):
        row = agg[(agg.YR == yr) & (agg.SECTOR == sector)]
        return float(row.PCT.iloc[0]) if len(row) else None

    a21, a26 = _agg_pct(2021, "성심당방향"), _agg_pct(2026, "성심당방향")
    b21, b26 = _agg_pct(2021, "반대방향"), _agg_pct(2026, "반대방향")

    if None not in (a21, a26, b21, b26):
        c1, c2 = st.columns(2)
        c1.metric("성심당 방향 (2021→2026)", f"{a26:.1f}%", delta=f"{(a26-a21):+.1f}%p")
        c2.metric("반대 방향 (2021→2026)", f"{b26:.1f}%", delta=f"{(b26-b21):+.1f}%p")

        st.success(f"격차가 {(a21-b21):+.1f}%p → {(a26-b26):+.1f}%p로 벌어졌다. "
                   "위약 검정 상위 10.0%로 통과.")

    st.markdown("> 반대 방향은 5년간 12~15%에서 거의 움직이지 않았다. "
                "성심당 방향만 개인 가게가 프랜차이즈로 교체되고 있다.")
    st.caption(ISOTROPY_NOTE)

    with st.expander("참고 · 경쟁재(카페·제과) 한정 프랜차이즈 비중 — 표본 작음, 위약검정 미실시"):
        dfc = df8[df8.ROLE == "경쟁재"].copy()
        table = pd.DataFrame({"YR": sorted(dfc.YR.unique())})
        for sector in ["성심당방향", "반대방향"]:
            s = dfc[dfc.SECTOR == sector].set_index("YR")
            table[sector] = table["YR"].map(
                lambda y, s=s: f"{s.loc[y,'BRANCH_PCT']:.1f}% (n={int(s.loc[y,'N'])})" if y in s.index else "-")
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.caption(
            "개별 연도는 표본이 작아(n=14~33) 95% 신뢰구간이 겹치며, 단독으로는 통계적 유의성을 주장할 수 없다. "
            "6개년 연속 같은 방향(성심당방향 우세)이라는 경향성만 참고로 제시한다. "
            "위 STEP 8의 전체 업종 프랜차이즈 지표(위약검정 상위 10.0% 통과)가 메인 근거다."
        )


# =====================================================================
# STEP 8.5 · 업소 단위 재검증 — 다른 방법으로도 같은 결론
# =====================================================================

with st.container(border=True):
    st.subheader("STEP 8.5 · 업소 단위로 다시 검증해도 같은 결과였다")
    st.caption("🟢 정적 값 — 개별 업소 로지스틱 회귀·거리곡선 (일회성 분석, Snowpark Python)")

    c1, c2, c3 = st.columns(3)
    c1.metric("방향 효과 (OR)", "3.25", delta="p < 0.001", delta_color="off")
    c2.metric("거리 효과 (OR)", "1.03", delta="p = 0.493 (무의미)", delta_color="off")
    c3.metric("역U자 곡선 피크", "약 280m", delta="연도 통제해도 동일", delta_color="off")

    st.markdown(
        "> 개별 업소 10,548건을 로지스틱 회귀로 다시 검증했다. **방향 효과는 매우 유의했지만"
        "(OR=3.25, p<0.001), 거리 자체는 무의미했다(p=0.493).** "
        "원형 거리로는 성심당 효과를 못 잡았던 실패 1의 결론을, 업소 단위에서 다시 확인한 셈이다."
    )

    st.divider()
    st.markdown("**그런데 반박이 하나 남는다 — '어느 방향이든 도심에서 300m쯤 상권이 몰리는 거 아닌가?'**")

    peak_df = pd.DataFrame({
        "YR":         [2021, 2022, 2023, 2024, 2025, 2026] * 2,
        "SECTOR":     ["성심당방향"] * 6 + ["반대방향"] * 6,
        "PEAK_M":     [332, 304, 261, 263, 284, 288,   348, 347, 347, 344, 349, 352],
        "PEAK_PCT":   [33.9, 36.9, 56.5, 52.4, 43.2, 43.9,   21.0, 22.9, 19.7, 19.5, 21.9, 22.6],
    })

    pc1, pc2 = st.columns(2)
    with pc1:
        st.caption("피크 위치 (m) — 낮을수록 성심당에 가까움")
        st.line_chart(peak_df.pivot(index="YR", columns="SECTOR", values="PEAK_M"), height=280)
    with pc2:
        st.caption("피크 높이 (보완재 비중 %) — 상권 집중도")
        st.line_chart(peak_df.pivot(index="YR", columns="SECTOR", values="PEAK_PCT"), height=280)

    st.success(
        "반대 방향은 6년 내내 피크 위치(347~352m)와 높이(19~23%)가 거의 고정돼 있다 — "
        "**전형적인 '도심 구조 때문' 패턴이다.** "
        "그런데 성심당 방향은 피크가 332m → 261m(2023) → 288m로 **움직였고**, "
        "높이도 33.9% → 56.5% → 43.9%로 **급등했다가 내려왔다.** "
        "'도심이라 원래 그렇다'면 둘 다 고정돼야 하는데, 한쪽만 움직였다."
    )
    st.markdown(
        "> **이게 이 프로젝트에서 가장 강한 인과 증거다.** 도심 구조라는 대안 설명을 이 비교 하나로 기각할 수 있다. "
        "피크가 가장 가까워지고 가장 높아진 시점이 2023년 — 성심당이 SNS에서 폭발적으로 화제가 된 시점과 겹친다."
    )
    st.caption("※ 이 분석은 Snowflake View가 아닌 1회성 Python 스크립트 결과이며, 재현 시 SQL 뷰로 별도 등록 필요")


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
        style_verdict(df9.style, verdict_color9, ["VERDICT"]),
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
- **"소매" 비중이 크게 감소했지만(DiD -13%p)**, ROLE 구성비는 합이 100%에 수렴하는 구조라
  다른 업종이 늘면 산술적으로 줄어드는 항목일 수 있다. 절대 점포 수 추이 확인 전까지는 보조 참고만
- **"기타" 항목의 DiD(+8.98%p)가 보완재보다 크지만, 어떤 업종이 포함되는지 세부 확인이 안 됨**
  — 헤드라인 근거로 사용하지 않음
- 경쟁재 프랜차이즈의 "6개년 연속 동일 방향" 관찰은 표본이 매년 상당 부분 겹치는 동일 모집단이라,
  독립시행을 가정한 통계적 유의성 계산(예: (1/2)^6)은 적용할 수 없음 — 경향성 참고로만 사용
        """)


# =====================================================================
# 사이드바 — 개발용 상태 패널
# =====================================================================

with st.sidebar:
    st.header("개발 상태")
    st.write("Snowflake 연결:", "🟢 연결됨" if SNOW_OK else "🔴 미연결 (로컬 테스트)")

    if st.button("🔄 캐시 비우고 다시 읽기", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

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