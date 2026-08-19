SELECT * FROM SANGA_ALL;


SELECT COUNT(*) AS TOTAL_ROWS
FROM SANGA_ALL;

SELECT
    SOURCE_TABLE,
    COUNT(*) AS N
FROM SANGA_ALL
GROUP BY SOURCE_TABLE
ORDER BY SOURCE_TABLE;

SELECT
    SOURCE_TABLE,
    STORE_NO,
    STORE_NM,
    INDUTY_LCLS_NM,
    INDUTY_MCLS_NM,
    INDUTY_SCLS_NM,
    LAT,
    LON
FROM SANGA_ALL
LIMIT 30;


CREATE OR REPLACE TABLE SANGA_PANEL_CORE_1KM AS

SELECT
    STORE_NO,
    STORE_NM,
    BRANCH_NM,

    INDUTY_LCLS_CD,
    TRIM(INDUTY_LCLS_NM) AS INDUTY_LCLS_NM,

    INDUTY_MCLS_CD,
    TRIM(INDUTY_MCLS_NM) AS INDUTY_MCLS_NM,

    INDUTY_SCLS_CD,
    TRIM(INDUTY_SCLS_NM) AS INDUTY_SCLS_NM,

    STD_INDUTY_CD,
    STD_INDUTY_NM,

    SIDO_CD,
    SIDO_NM,
    SIGUNGU_CD,
    SIGUNGU_NM,

    ADM_DONG_CD,
    ADM_DONG_NM,

    LEG_DONG_CD,
    LEG_DONG_NM,

    JIBUN_ADDR,
    ROAD_NM_ADDR,

    BLDG_MNG_NO,
    BLDG_NM,

    DONG_INFO,
    FLR_INFO,
    HO_INFO,

    LON,
    LAT,

    SOURCE_TABLE,

    2000 + TRY_TO_NUMBER(SOURCE_TABLE) AS YR

FROM SANGA_ALL

WHERE LAT IS NOT NULL
  AND LON IS NOT NULL

  -- 대전 좌표 이상치 방지
  AND LAT BETWEEN 36.15 AND 36.55
  AND LON BETWEEN 127.25 AND 127.65

  -- 중앙로역 기준 1km
  AND ST_DISTANCE(
        ST_MAKEPOINT(LON, LAT),
        ST_MAKEPOINT(127.42750, 36.32870)
      ) <= 1000;



SELECT COUNT(*) AS TOTAL_ROWS
FROM SANGA_PANEL_CORE_1KM;


SELECT
    YR,
    COUNT(*) AS N
FROM SANGA_PANEL_CORE_1KM
GROUP BY YR
ORDER BY YR;


SELECT
    YR,
    COUNT(*) AS ROW_N,
    COUNT(DISTINCT STORE_NO) AS STORE_N,
    COUNT(*) - COUNT(DISTINCT STORE_NO) AS DUPLICATE_N
FROM SANGA_PANEL_CORE_1KM
GROUP BY YR
ORDER BY YR;

SELECT GET_DDL('VIEW', 'SANGA_ALL');

SELECT
    YR,
    ROWS_PER_STORE,
    COUNT(*) AS STORE_CNT
FROM (
    SELECT
        YR,
        STORE_NO,
        COUNT(*) AS ROWS_PER_STORE
    FROM SANGA_PANEL_CORE_1KM
    GROUP BY YR, STORE_NO
)
GROUP BY YR, ROWS_PER_STORE
ORDER BY YR, ROWS_PER_STORE;


WITH X AS (
    SELECT
        YR,
        STORE_NO,
        COUNT(*) AS ROW_N,

        COUNT(DISTINCT HASH(
            TRIM(INDUTY_LCLS_NM),
            TRIM(INDUTY_MCLS_NM),
            TRIM(INDUTY_SCLS_NM),
            LAT,
            LON,
            JIBUN_ADDR
        )) AS VERSION_N

    FROM SANGA_PANEL_CORE_1KM

    GROUP BY
        YR,
        STORE_NO
)

SELECT
    YR,
    COUNT(*) AS STORE_YEAR_N,
    COUNT_IF(ROW_N > 1) AS DUP_STORE_YEAR_N,
    COUNT_IF(VERSION_N > 1) AS CHANGED_STORE_YEAR_N

FROM X

GROUP BY YR
ORDER BY YR;


WITH X AS (
    SELECT
        YR,
        STORE_NO,

        COUNT(*) AS ROW_N,

        COUNT(DISTINCT TRIM(INDUTY_LCLS_NM)) AS L1_N,
        COUNT(DISTINCT TRIM(INDUTY_MCLS_NM)) AS L2_N,
        COUNT(DISTINCT TRIM(INDUTY_SCLS_NM)) AS L3_N,

        COUNT(DISTINCT JIBUN_ADDR) AS ADDR_N,

        COUNT(
            DISTINCT CONCAT(
                ROUND(LAT, 6),
                '|',
                ROUND(LON, 6)
            )
        ) AS GEO_N

    FROM SANGA_PANEL_CORE_1KM

    GROUP BY
        YR,
        STORE_NO
)

SELECT
    YR,

    COUNT(*) AS STORE_YEAR_N,

    COUNT_IF(ROW_N > 1) AS DUP_STORE_N,

    COUNT_IF(L1_N > 1) AS CHANGED_L1_N,
    COUNT_IF(L2_N > 1) AS CHANGED_L2_N,
    COUNT_IF(L3_N > 1) AS CHANGED_L3_N,

    COUNT_IF(ADDR_N > 1) AS CHANGED_ADDR_N,
    COUNT_IF(GEO_N > 1) AS CHANGED_GEO_N

FROM X

GROUP BY YR

ORDER BY YR;


WITH CHANGED AS (

    SELECT
        STORE_NO

    FROM SANGA_PANEL_CORE_1KM

    WHERE YR = 2024

    GROUP BY STORE_NO

    HAVING COUNT(
        DISTINCT CONCAT(
            COALESCE(TRIM(INDUTY_LCLS_NM), ''),
            '|',
            COALESCE(TRIM(INDUTY_MCLS_NM), ''),
            '|',
            COALESCE(TRIM(INDUTY_SCLS_NM), '')
        )
    ) > 1
)

SELECT
    S.STORE_NO,
    S.STORE_NM,

    S.INDUTY_LCLS_NM,
    S.INDUTY_MCLS_NM,
    S.INDUTY_SCLS_NM,

    S.JIBUN_ADDR,
    S.LAT,
    S.LON

FROM SANGA_PANEL_CORE_1KM S

JOIN CHANGED C
    ON S.STORE_NO = C.STORE_NO

WHERE S.YR = 2024

ORDER BY S.STORE_NO

LIMIT 100;



WITH ROLE_DATA AS (

    SELECT
        YR,
        STORE_NO,

        CASE
            WHEN TRIM(INDUTY_LCLS_NM) = '수리·개인'
             AND (
                    TRIM(INDUTY_SCLS_NM) LIKE '%미용실%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%네일%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%피부%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%이용원%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%세탁%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%빨래%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%수선%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%목욕%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%찜질%'
                 )
                THEN '생활밀착'

            WHEN TRIM(INDUTY_LCLS_NM) = '수리·개인'
                THEN '생활기타'

            WHEN TRIM(INDUTY_LCLS_NM) = '음식'
             AND (
                    TRIM(INDUTY_MCLS_NM) = '비알코올'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%제과%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%빵%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%도넛%'
                 OR TRIM(INDUTY_SCLS_NM) LIKE '%아이스크림%'
                 )
                THEN '경쟁재'

            WHEN TRIM(INDUTY_LCLS_NM) = '음식'
                THEN '보완재'

            WHEN TRIM(INDUTY_LCLS_NM) = '소매'
                THEN '소매'

            ELSE '기타'
        END AS ROLE

    FROM SANGA_PANEL_CORE_1KM
),

CHECK_ROLE AS (

    SELECT
        YR,
        STORE_NO,
        COUNT(*) AS ROW_N,
        COUNT(DISTINCT ROLE) AS ROLE_N

    FROM ROLE_DATA

    GROUP BY
        YR,
        STORE_NO
)

SELECT
    YR,
    COUNT(*) AS STORE_YEAR_N,
    COUNT_IF(ROW_N > 1) AS DUP_STORE_N,
    COUNT_IF(ROLE_N > 1) AS CHANGED_ROLE_N,
    ROUND(
        COUNT_IF(ROLE_N > 1) / COUNT(*) * 100,
        2
    ) AS CHANGED_ROLE_PCT

FROM CHECK_ROLE

GROUP BY YR

ORDER BY YR;


WITH PAIRS AS (

    SELECT
        A.YR,
        A.STORE_NO,

        ST_DISTANCE(
            ST_MAKEPOINT(A.LON, A.LAT),
            ST_MAKEPOINT(B.LON, B.LAT)
        ) AS DIST_M

    FROM SANGA_PANEL_CORE_1KM A

    JOIN SANGA_PANEL_CORE_1KM B
      ON A.YR = B.YR
     AND A.STORE_NO = B.STORE_NO

    WHERE A.LAT IS NOT NULL
      AND A.LON IS NOT NULL
      AND B.LAT IS NOT NULL
      AND B.LON IS NOT NULL
),

STORE_MOVE AS (

    SELECT
        YR,
        STORE_NO,
        MAX(DIST_M) AS MAX_MOVE_M

    FROM PAIRS

    GROUP BY
        YR,
        STORE_NO
)

SELECT
    YR,

    COUNT(*) AS STORE_N,

    COUNT_IF(MAX_MOVE_M > 1)   AS MOVE_GT_1M,
    COUNT_IF(MAX_MOVE_M > 5)   AS MOVE_GT_5M,
    COUNT_IF(MAX_MOVE_M > 20)  AS MOVE_GT_20M,
    COUNT_IF(MAX_MOVE_M > 100) AS MOVE_GT_100M,

    ROUND(AVG(MAX_MOVE_M), 2) AS AVG_MAX_MOVE_M

FROM STORE_MOVE

GROUP BY YR

ORDER BY YR;


// V_SANGA_CLEAN 테이블 생성 쿼리

CREATE OR REPLACE VIEW V_SANGA_CLEAN AS

WITH NORMALIZED AS (

    SELECT
        STORE_NO,
        STORE_NM,

        TRIM(INDUTY_LCLS_NM) AS L1,
        TRIM(INDUTY_MCLS_NM) AS L2,
        TRIM(INDUTY_SCLS_NM) AS L3,

        ADM_DONG_CD,
        ADM_DONG_NM,
        JIBUN_ADDR,
        FLR_INFO,

        LAT,
        LON,
        YR

    FROM SANGA_PANEL_CORE_1KM

    WHERE STORE_NO IS NOT NULL
      AND LAT IS NOT NULL
      AND LON IS NOT NULL
),

-- 같은 점포·연도 안에서 동일하게 반복된 버전의 빈도를 계산
VERSION_COUNT AS (

    SELECT
        *,
        COUNT(*) OVER (
            PARTITION BY
                STORE_NO,
                YR,
                STORE_NM,
                L1,
                L2,
                L3,
                COALESCE(ADM_DONG_CD, ''),
                COALESCE(ADM_DONG_NM, ''),
                COALESCE(JIBUN_ADDR, ''),
                COALESCE(FLR_INFO, ''),
                LAT,
                LON
        ) AS VERSION_FREQ

    FROM NORMALIZED
),

-- 가장 많이 등장한 버전을 해당 연도의 대표값으로 선택
DEDUP AS (

    SELECT *

    FROM VERSION_COUNT

    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY STORE_NO, YR

        ORDER BY
            VERSION_FREQ DESC,
            L1,
            L2,
            L3,
            LAT,
            LON
    ) = 1
)

SELECT
    STORE_NO,
    STORE_NM,

    L1,
    L2,
    L3,

    ADM_DONG_CD,
    ADM_DONG_NM,
    JIBUN_ADDR,
    FLR_INFO,

    LAT,
    LON,
    YR,

    -- 성심당까지 거리
    ST_DISTANCE(
        ST_MAKEPOINT(LON, LAT),
        ST_MAKEPOINT(127.42718, 36.32752)
    ) AS DIST_ANCHOR,

    -- 중앙로역까지 거리
    ST_DISTANCE(
        ST_MAKEPOINT(LON, LAT),
        ST_MAKEPOINT(127.42750, 36.32870)
    ) AS DIST_CENTER,

    -- 중앙로역 기준 방향각
    MOD(
        DEGREES(
            ATAN2(
                LON - 127.42750,
                LAT - 36.32870
            )
        ) + 360,
        360
    ) AS BEARING

FROM DEDUP;


SELECT COUNT(*) AS N
FROM V_SANGA_CLEAN;

SELECT
    YR,
    COUNT(*) AS N,
    COUNT(DISTINCT STORE_NO) AS STORE_N
FROM V_SANGA_CLEAN
GROUP BY YR
ORDER BY YR;

SELECT
    MIN(DIST_CENTER) AS MIN_DIST,
    MAX(DIST_CENTER) AS MAX_DIST,
    COUNT_IF(DIST_CENTER > 1000) AS OVER_1KM
FROM V_SANGA_CLEAN;


CREATE OR REPLACE VIEW V_ROLE_CLASSIFIED AS

WITH BASE AS (

    SELECT
        *,

        -- 중앙로역 → 성심당 방향 기준각: 약 195.2°
        ABS(
            MOD(
                BEARING - 195.2 + 180,
                360
            ) - 180
        ) AS ANGLE_DIFF

    FROM V_SANGA_CLEAN
)

SELECT
    STORE_NO,
    STORE_NM,

    L1,
    L2,
    L3,

    ADM_DONG_CD,
    ADM_DONG_NM,
    JIBUN_ADDR,
    FLR_INFO,

    LAT,
    LON,
    YR,

    DIST_ANCHOR,
    DIST_CENTER,
    BEARING,
    ANGLE_DIFF,

    /* 방향 분류 */
    CASE
        WHEN ANGLE_DIFF <= 60
            THEN '성심당방향'

        WHEN ANGLE_DIFF >= 120
            THEN '반대방향'

        ELSE '측면'
    END AS SECTOR,

    /* 업종 역할 분류 */
    CASE

        /* 생활밀착 */
        WHEN L1 = '수리·개인'
         AND (
                L3 LIKE '%미용실%'
             OR L3 LIKE '%네일%'
             OR L3 LIKE '%피부%'
             OR L3 LIKE '%이용원%'
             OR L3 LIKE '%세탁%'
             OR L3 LIKE '%빨래%'
             OR L3 LIKE '%수선%'
             OR L3 LIKE '%목욕%'
             OR L3 LIKE '%찜질%'
         )
            THEN '생활밀착'

        /* 나머지 개인서비스 */
        WHEN L1 = '수리·개인'
            THEN '생활기타'

        /* 성심당과 경쟁 가능성이 높은 디저트/카페 */
        WHEN L1 = '음식'
         AND (
                L2 = '비알코올'
             OR L3 LIKE '%제과%'
             OR L3 LIKE '%빵%'
             OR L3 LIKE '%도넛%'
             OR L3 LIKE '%아이스크림%'
         )
            THEN '경쟁재'

        /* 나머지 음식점 */
        WHEN L1 = '음식'
            THEN '보완재'

        /* 소매 */
        WHEN L1 = '소매'
            THEN '소매'

        ELSE '기타'

    END AS ROLE

FROM BASE;


SELECT COUNT(*) AS N
FROM V_ROLE_CLASSIFIED;

SELECT
    ROLE,
    COUNT(*) AS N,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 2) AS PCT
FROM V_ROLE_CLASSIFIED
GROUP BY ROLE
ORDER BY N DESC;

SELECT
    SECTOR,
    COUNT(*) AS N,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 2) AS PCT
FROM V_ROLE_CLASSIFIED
GROUP BY SECTOR
ORDER BY N DESC;

SELECT
    YR,
    SECTOR,
    COUNT(*) AS N
FROM V_ROLE_CLASSIFIED
WHERE DIST_CENTER <= 300
  AND SECTOR IN ('성심당방향', '반대방향')
GROUP BY YR, SECTOR
ORDER BY YR, SECTOR;


CREATE OR REPLACE VIEW V_ROLE_TREND AS
SELECT
    YR,
    SECTOR,

    COUNT(*) AS N,

    AVG(IFF(ROLE = '생활밀착', 1, 0)) AS LIFE_RATIO,
    AVG(IFF(ROLE = '보완재',   1, 0)) AS SUPPORT_RATIO,
    AVG(IFF(ROLE = '경쟁재',   1, 0)) AS COMPETE_RATIO

FROM V_ROLE_CLASSIFIED

WHERE DIST_CENTER <= 300
  AND SECTOR IN ('성심당방향', '반대방향')

GROUP BY
    YR,
    SECTOR;


    SELECT
    YR,
    SECTOR,
    N,

    ROUND(LIFE_RATIO * 100, 2) AS LIFE_PCT,
    ROUND(SUPPORT_RATIO * 100, 2) AS SUPPORT_PCT,
    ROUND(COMPETE_RATIO * 100, 2) AS COMPETE_PCT

FROM V_ROLE_TREND

ORDER BY
    YR,
    CASE SECTOR
        WHEN '성심당방향' THEN 1
        WHEN '반대방향' THEN 2
    END;


    CREATE OR REPLACE VIEW V_ROLE_DID AS

WITH T AS (
    SELECT *
    FROM V_ROLE_TREND
    WHERE YR IN (2021, 2026)
)

SELECT
    'LIFE' AS ROLE_TYPE,

    (
        MAX(IFF(YR = 2026 AND SECTOR = '성심당방향', LIFE_RATIO, NULL))
        -
        MAX(IFF(YR = 2021 AND SECTOR = '성심당방향', LIFE_RATIO, NULL))
    ) * 100 AS D_ANCHOR_PP,

    (
        MAX(IFF(YR = 2026 AND SECTOR = '반대방향', LIFE_RATIO, NULL))
        -
        MAX(IFF(YR = 2021 AND SECTOR = '반대방향', LIFE_RATIO, NULL))
    ) * 100 AS D_OPPO_PP

FROM T

UNION ALL

SELECT
    'SUPPORT',

    (
        MAX(IFF(YR = 2026 AND SECTOR = '성심당방향', SUPPORT_RATIO, NULL))
        -
        MAX(IFF(YR = 2021 AND SECTOR = '성심당방향', SUPPORT_RATIO, NULL))
    ) * 100,

    (
        MAX(IFF(YR = 2026 AND SECTOR = '반대방향', SUPPORT_RATIO, NULL))
        -
        MAX(IFF(YR = 2021 AND SECTOR = '반대방향', SUPPORT_RATIO, NULL))
    ) * 100

FROM T

UNION ALL

SELECT
    'COMPETE',

    (
        MAX(IFF(YR = 2026 AND SECTOR = '성심당방향', COMPETE_RATIO, NULL))
        -
        MAX(IFF(YR = 2021 AND SECTOR = '성심당방향', COMPETE_RATIO, NULL))
    ) * 100,

    (
        MAX(IFF(YR = 2026 AND SECTOR = '반대방향', COMPETE_RATIO, NULL))
        -
        MAX(IFF(YR = 2021 AND SECTOR = '반대방향', COMPETE_RATIO, NULL))
    ) * 100

FROM T;

SELECT
    ROLE_TYPE,
    ROUND(D_ANCHOR_PP, 2) AS D_ANCHOR_PP,
    ROUND(D_OPPO_PP, 2) AS D_OPPO_PP,
    ROUND(D_ANCHOR_PP - D_OPPO_PP, 2) AS DID_PP
FROM V_ROLE_DID
ORDER BY
    CASE ROLE_TYPE
        WHEN 'LIFE' THEN 1
        WHEN 'SUPPORT' THEN 2
        WHEN 'COMPETE' THEN 3
    END;


CREATE OR REPLACE VIEW V_ROLE_BAND AS

SELECT
    CASE
        WHEN DIST_CENTER <= 150 THEN '0-150m'
        WHEN DIST_CENTER <= 300 THEN '150-300m'
        WHEN DIST_CENTER <= 450 THEN '300-450m'
        WHEN DIST_CENTER <= 600 THEN '450-600m'
        ELSE '600m-1km'
    END AS BAND,

    SECTOR,

    COUNT(*) AS N,

    AVG(IFF(ROLE = '생활밀착', 1, 0)) AS LIFE_RATIO,

    AVG(IFF(ROLE = '보완재', 1, 0)) AS SUPPORT_RATIO

FROM V_ROLE_CLASSIFIED

WHERE YR = 2026
  AND SECTOR IN ('성심당방향', '반대방향')

GROUP BY
    BAND,
    SECTOR;


SELECT
    BAND,
    SECTOR,
    N,
    ROUND(LIFE_RATIO * 100, 2) AS LIFE_PCT,
    ROUND(SUPPORT_RATIO * 100, 2) AS SUPPORT_PCT

FROM V_ROLE_BAND

ORDER BY
    CASE BAND
        WHEN '0-150m' THEN 1
        WHEN '150-300m' THEN 2
        WHEN '300-450m' THEN 3
        WHEN '450-600m' THEN 4
        WHEN '600m-1km' THEN 5
    END,
    CASE SECTOR
        WHEN '성심당방향' THEN 1
        WHEN '반대방향' THEN 2
    END;


    CREATE OR REPLACE VIEW V_ROLE_PLACEBO_SCAN AS

WITH DIRECTIONS AS (

    SELECT
        SEQ4() * 5 AS B0

    FROM TABLE(GENERATOR(ROWCOUNT => 72))
),

BASE AS (

    SELECT
        YR,
        BEARING,
        ROLE

    FROM V_ROLE_CLASSIFIED

    WHERE DIST_CENTER <= 300
      AND YR IN (2021, 2026)
),

EXPANDED AS (

    SELECT
        D.B0,
        B.YR,
        B.ROLE,

        ABS(
            MOD(
                B.BEARING - D.B0 + 180,
                360
            ) - 180
        ) AS ANGLE_DIFF

    FROM DIRECTIONS D
    CROSS JOIN BASE B
),

YEAR_STATS AS (

    SELECT
        B0,
        YR,

        /* 생활밀착 */
        AVG(
            IFF(
                ANGLE_DIFF <= 60,
                IFF(ROLE = '생활밀착', 1, 0),
                NULL
            )
        ) AS LIFE_ANCHOR,

        AVG(
            IFF(
                ANGLE_DIFF >= 120,
                IFF(ROLE = '생활밀착', 1, 0),
                NULL
            )
        ) AS LIFE_OPPO,

        /* 보완재 */
        AVG(
            IFF(
                ANGLE_DIFF <= 60,
                IFF(ROLE = '보완재', 1, 0),
                NULL
            )
        ) AS SUPPORT_ANCHOR,

        AVG(
            IFF(
                ANGLE_DIFF >= 120,
                IFF(ROLE = '보완재', 1, 0),
                NULL
            )
        ) AS SUPPORT_OPPO,

        /* 경쟁재 */
        AVG(
            IFF(
                ANGLE_DIFF <= 60,
                IFF(ROLE = '경쟁재', 1, 0),
                NULL
            )
        ) AS COMPETE_ANCHOR,

        AVG(
            IFF(
                ANGLE_DIFF >= 120,
                IFF(ROLE = '경쟁재', 1, 0),
                NULL
            )
        ) AS COMPETE_OPPO

    FROM EXPANDED

    GROUP BY
        B0,
        YR
)

SELECT
    B0,

    /* 성심당 실제 방향 195.2°와의 각도차 */
    ABS(
        MOD(
            B0 - 195.2 + 180,
            360
        ) - 180
    ) AS DIST_FROM_SEONGSIMDANG_DIR,

    /* 생활밀착 DiD */
    (
        MAX(IFF(YR = 2026, LIFE_ANCHOR, NULL))
        - MAX(IFF(YR = 2021, LIFE_ANCHOR, NULL))

        -

        (
            MAX(IFF(YR = 2026, LIFE_OPPO, NULL))
            - MAX(IFF(YR = 2021, LIFE_OPPO, NULL))
        )
    ) * 100 AS LIFE_DID_PP,

    /* 보완재 DiD */
    (
        MAX(IFF(YR = 2026, SUPPORT_ANCHOR, NULL))
        - MAX(IFF(YR = 2021, SUPPORT_ANCHOR, NULL))

        -

        (
            MAX(IFF(YR = 2026, SUPPORT_OPPO, NULL))
            - MAX(IFF(YR = 2021, SUPPORT_OPPO, NULL))
        )
    ) * 100 AS SUPPORT_DID_PP,

    /* 경쟁재 DiD */
    (
        MAX(IFF(YR = 2026, COMPETE_ANCHOR, NULL))
        - MAX(IFF(YR = 2021, COMPETE_ANCHOR, NULL))

        -

        (
            MAX(IFF(YR = 2026, COMPETE_OPPO, NULL))
            - MAX(IFF(YR = 2021, COMPETE_OPPO, NULL))
        )
    ) * 100 AS COMPETE_DID_PP

FROM YEAR_STATS

GROUP BY B0;


SELECT COUNT(*) AS N_PLACEBO
FROM V_ROLE_PLACEBO_SCAN
WHERE DIST_FROM_SEONGSIMDANG_DIR > 30;


SELECT
    COUNT(*) AS N_PLACEBO,

    ROUND(AVG(SUPPORT_DID_PP), 2) AS PLACEBO_MEAN_PP,

    ROUND(STDDEV_SAMP(SUPPORT_DID_PP), 2) AS PLACEBO_SD_PP,

    ROUND(MIN(SUPPORT_DID_PP), 2) AS MIN_PP,

    ROUND(MAX(SUPPORT_DID_PP), 2) AS MAX_PP,

    COUNT_IF(SUPPORT_DID_PP >= 3.69) AS N_GE_OBSERVED,

    ROUND(
        COUNT_IF(SUPPORT_DID_PP >= 3.69)
        / COUNT(*) * 100,
        1
    ) AS TOP_PCT

FROM V_ROLE_PLACEBO_SCAN

WHERE DIST_FROM_SEONGSIMDANG_DIR > 30;

SELECT
    'LIFE' AS ROLE_TYPE,

    -1.79 AS OBSERVED_DID_PP,

    ROUND(AVG(LIFE_DID_PP), 2) AS PLACEBO_MEAN_PP,
    ROUND(STDDEV_SAMP(LIFE_DID_PP), 2) AS PLACEBO_SD_PP,

    ROUND(
        COUNT_IF(LIFE_DID_PP <= -1.79)
        / COUNT(*) * 100,
        1
    ) AS EXTREME_PCT

FROM V_ROLE_PLACEBO_SCAN

WHERE DIST_FROM_SEONGSIMDANG_DIR > 30

UNION ALL

SELECT
    'SUPPORT',

    3.69,

    ROUND(AVG(SUPPORT_DID_PP), 2),
    ROUND(STDDEV_SAMP(SUPPORT_DID_PP), 2),

    ROUND(
        COUNT_IF(SUPPORT_DID_PP >= 3.69)
        / COUNT(*) * 100,
        1
    )

FROM V_ROLE_PLACEBO_SCAN

WHERE DIST_FROM_SEONGSIMDANG_DIR > 30

UNION ALL

SELECT
    'COMPETE',

    1.59,

    ROUND(AVG(COMPETE_DID_PP), 2),
    ROUND(STDDEV_SAMP(COMPETE_DID_PP), 2),

    ROUND(
        COUNT_IF(COMPETE_DID_PP >= 1.59)
        / COUNT(*) * 100,
        1
    )

FROM V_ROLE_PLACEBO_SCAN

WHERE DIST_FROM_SEONGSIMDANG_DIR > 30;