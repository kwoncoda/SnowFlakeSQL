import statsmodels.formula.api as smf, numpy as np, pandas as pd
from snowflake.snowpark.context import get_active_session

session = get_active_session()
session.use_database("PROJECT_DB")
session.use_schema("SHARED_FILES")

r = session.table("V_GEO_SECTOR").filter(
        "PERIOD='POST' AND DIST_CENTER>0 AND DIST_CENTER<=1000").to_pandas()
r["ANG_C"] = r.ANGLE_DIFF / 90.0
r["LOGD"]  = np.log(r.DIST_CENTER)
r["TEN"]   = np.log1p(r.AGE_MONTHS.clip(lower=0))
r["AREA"]  = np.log1p(pd.to_numeric(r.AREA_SQM, errors="coerce").clip(lower=0).fillna(0))
r = r.dropna(subset=["Y_CLOSED_24M","ANG_C","LOGD","TEN","AREA","BIZ_GROUP","COHORT_YEAR","SLOT"])

res = smf.logit("Y_CLOSED_24M ~ ANG_C + LOGD + ANG_C:LOGD + C(BIZ_GROUP) + TEN + AREA + C(COHORT_YEAR)",
                data=r).fit(disp=0, cov_type="cluster",
                            cov_kwds={"groups": pd.factorize(r.SLOT)[0]})
print(res.summary())

def main(session):
    session.use_database("PROJECT_DB")
    session.use_schema("SHARED_FILES")
    # POST 기간, 중앙로역 300m 이내
    df = session.table("V_GEO_SECTOR").filter(
        "PERIOD='POST' AND DIST_CENTER>0 AND DIST_CENTER<=300"
    ).to_pandas()

    def sector_gap(ref_bearing, d):
        angle_diff = np.minimum(np.abs(d.BEARING - ref_bearing), 360 - np.abs(d.BEARING - ref_bearing))
        anchor = d.loc[angle_diff <= 60, "Y_CLOSED_24M"]
        oppo = d.loc[angle_diff >= 120, "Y_CLOSED_24M"]
        if len(anchor) == 0 or len(oppo) == 0:
            return None
        return anchor.mean() * 100 - oppo.mean() * 100

    real_gap = sector_gap(195.2, df)  # 실제 성심당 방향 기준 (−7.0%p가 나와야 함)

    np.random.seed(42)
    random_bearings = np.random.uniform(0, 360, 30)
    placebo_gaps = np.array([g for b in random_bearings if (g := sector_gap(b, df)) is not None])

    result = {
        "실제값(%p)": round(real_gap, 2),
        "위약평균(%p)": round(placebo_gaps.mean(), 2),
        "위약표준편차(%p)": round(placebo_gaps.std(), 2),
        "5퍼센타일(%p)": round(np.percentile(placebo_gaps, 5), 2),
        "95퍼센타일(%p)": round(np.percentile(placebo_gaps, 95), 2),
        "위약순위_하위(%)": round((placebo_gaps < real_gap).mean() * 100, 1),
    }
    print(result)
    return result

main(session)
