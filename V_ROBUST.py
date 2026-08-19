from snowflake.snowpark.context import get_active_session
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

session = get_active_session()

# 1. Snowflake VIEW 불러오기
r = session.table("V_ROBUST_INPUT").to_pandas()

# 2. 파생변수
# 0 = 성심당 방향
# 1 = 성심당 방향에서 90도 차이
# 2 = 정반대 방향
r["ANG_C"] = r["ANGLE_DIFF"] / 90.0

# 거리 로그 변환
r["LOGD"] = np.log(r["DIST_CENTER"])

# 업력 로그 변환
r["TEN"] = np.log1p(
    pd.to_numeric(
        r["AGE_MONTHS"],
        errors="coerce"
    ).clip(lower=0)
)

# 면적 로그 변환
# 면적 결측은 0으로 처리
r["AREA"] = np.log1p(
    pd.to_numeric(
        r["AREA_SQM"],
        errors="coerce"
    )
    .clip(lower=0)
    .fillna(0)
)

# 3. 모델에 필요한 값이 없는 행 제거
r = r.dropna(
    subset=[
        "Y",
        "ANG_C",
        "LOGD",
        "TEN",
        "AREA",
        "BIZ_GROUP",
        "CY",
        "SLOT"
    ]
)

# 4. SLOT을 클러스터 ID로 변환
cluster_id = pd.factorize(r["SLOT"])[0]

# 5. 로지스틱 회귀 + SLOT Cluster Robust SE
res = smf.logit(
    """
    Y ~ ANG_C
      + LOGD
      + ANG_C:LOGD
      + C(BIZ_GROUP)
      + TEN
      + AREA
      + C(CY)
    """,
    data=r
).fit(
    disp=0,
    cov_type="cluster",
    cov_kwds={
        "groups": cluster_id
    }
)

# 6. 핵심 결과만 정리
rows = []

for variable in ["ANG_C", "LOGD", "ANG_C:LOGD"]:
    rows.append({
        "VARIABLE": variable,
        "COEF": float(res.params[variable]),
        "SE": float(res.bse[variable]),
        "P_VALUE": float(res.pvalues[variable]),
        "N": int(res.nobs),
        "N_BLOCKS": int(r["SLOT"].nunique())
    })

result = pd.DataFrame(rows)
print(result)
