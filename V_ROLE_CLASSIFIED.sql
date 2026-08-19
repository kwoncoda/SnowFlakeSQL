CREATE OR REPLACE VIEW V_SANGA_CLEAN AS

WITH NORMALIZED AS (

    SELECT
        STORE_NO,
        STORE_NM,
        BRANCH_NM,

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

VERSION_COUNT AS (

    SELECT
        *,
        COUNT(*) OVER (
            PARTITION BY
                STORE_NO,
                YR,
                STORE_NM,
                COALESCE(BRANCH_NM, ''),
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
    BRANCH_NM,

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

    ST_DISTANCE(
        ST_MAKEPOINT(LON, LAT),
        ST_MAKEPOINT(127.42718, 36.32752)
    ) AS DIST_ANCHOR,

    ST_DISTANCE(
        ST_MAKEPOINT(LON, LAT),
        ST_MAKEPOINT(127.42750, 36.32870)
    ) AS DIST_CENTER,

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


CREATE OR REPLACE VIEW V_ROLE_CLASSIFIED AS

WITH BASE AS (

    SELECT
        *,
        ABS(
            MOD(
                BEARING - 195.2 + 180,
                360
            ) - 180
        ) AS ANGLE_DIFF

    FROM V_SANGA_CLEAN
),

BRANCH_FLAG AS (

    SELECT
        STORE_NO,
        YR,

        MAX(
            IFF(
                TRIM(COALESCE(BRANCH_NM, '')) <> '',
                1,
                0
            )
        ) AS IS_BRANCH_FLAG

    FROM SANGA_PANEL_CORE_1KM

    GROUP BY
        STORE_NO,
        YR
)

SELECT
    B.STORE_NO,
    B.STORE_NM,

    B.L1,
    B.L2,
    B.L3,

    B.ADM_DONG_CD,
    B.ADM_DONG_NM,
    B.JIBUN_ADDR,
    B.FLR_INFO,

    B.LAT,
    B.LON,
    B.YR,

    B.DIST_ANCHOR,
    B.DIST_CENTER,
    B.BEARING,
    B.ANGLE_DIFF,

    /* 신규 컬럼 */
    IFF(
        COALESCE(F.IS_BRANCH_FLAG, 0) = 1,
        TRUE,
        FALSE
    ) AS IS_BRANCH,

    /* 방향 */
    CASE
        WHEN B.ANGLE_DIFF <= 60
            THEN '성심당방향'

        WHEN B.ANGLE_DIFF >= 120
            THEN '반대방향'

        ELSE '측면'
    END AS SECTOR,

    /* 업종 ROLE */
    CASE

        WHEN B.L1 = '수리·개인'
         AND (
                B.L3 LIKE '%미용실%'
             OR B.L3 LIKE '%네일%'
             OR B.L3 LIKE '%피부%'
             OR B.L3 LIKE '%이용원%'
             OR B.L3 LIKE '%세탁%'
             OR B.L3 LIKE '%빨래%'
             OR B.L3 LIKE '%수선%'
             OR B.L3 LIKE '%목욕%'
             OR B.L3 LIKE '%찜질%'
         )
            THEN '생활밀착'

        WHEN B.L1 = '수리·개인'
            THEN '생활기타'

        WHEN B.L1 = '음식'
         AND (
                B.L2 = '비알코올'
             OR B.L3 LIKE '%제과%'
             OR B.L3 LIKE '%빵%'
             OR B.L3 LIKE '%도넛%'
             OR B.L3 LIKE '%아이스크림%'
         )
            THEN '경쟁재'

        WHEN B.L1 = '음식'
            THEN '보완재'

        WHEN B.L1 = '소매'
            THEN '소매'

        ELSE '기타'

    END AS ROLE

FROM BASE B

LEFT JOIN BRANCH_FLAG F
    ON B.STORE_NO = F.STORE_NO
   AND B.YR = F.YR;

SELECT
    SECTOR,
    COUNT(*) AS N,
    COUNT_IF(IS_BRANCH) AS BRANCH_N,
    ROUND(
        COUNT_IF(IS_BRANCH) / COUNT(*) * 100,
        2
    ) AS BRANCH_PCT
FROM V_ROLE_CLASSIFIED
WHERE YR = 2026
  AND DIST_CENTER <= 300
  AND SECTOR IN ('성심당방향', '반대방향')
GROUP BY SECTOR
ORDER BY SECTOR;

SELECT
    STORE_NO,
    STORE_NM,
    YR,
    IS_BRANCH
FROM V_ROLE_CLASSIFIED
LIMIT 20;


SELECT
    SECTOR,
    COUNT(*) AS N,
    COUNT_IF(IS_BRANCH) AS BRANCH_N,

    ROUND(
        COUNT_IF(IS_BRANCH) / COUNT(*) * 100,
        2
    ) AS BRANCH_PCT

FROM V_ROLE_CLASSIFIED

WHERE YR = 2026
  AND DIST_CENTER <= 300
  AND SECTOR IN ('성심당방향', '반대방향')

GROUP BY SECTOR

ORDER BY
    CASE SECTOR
        WHEN '성심당방향' THEN 1
        WHEN '반대방향' THEN 2
    END;


    DESC VIEW V_GEO;


CREATE OR REPLACE VIEW V_GEO_SECTOR AS
SELECT *
FROM V_GEO;


SELECT * FROM RENT_PRICE;