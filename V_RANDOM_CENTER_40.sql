CREATE OR REPLACE VIEW V_RANDOM_CENTER_40 AS

WITH CANDIDATES AS (

    SELECT
        STORE_NO,
        STORE_NM,
        LAT AS CENTER_LAT,
        LON AS CENTER_LON,
        DIST_CENTER,

        ROW_NUMBER() OVER (
            ORDER BY HASH(STORE_NO)
        ) AS RN

    FROM V_SANGA_CLEAN

    WHERE YR = 2026

      -- 중심점 주변 300m가 기존 1km 데이터 범위 밖으로
      -- 잘리지 않도록 중앙로역 700m 이내만 사용
      AND DIST_CENTER <= 700

      -- 성심당 바로 옆은 방향 계산이 불안정하므로 제외
      AND DIST_ANCHOR >= 50
)

SELECT
    RN AS CENTER_ID,
    STORE_NO AS CENTER_STORE_NO,
    STORE_NM AS CENTER_STORE_NM,
    CENTER_LAT,
    CENTER_LON,
    DIST_CENTER

FROM CANDIDATES

WHERE RN <= 40;

SELECT COUNT(*) AS N_CENTER
FROM V_RANDOM_CENTER_40;

SELECT *
FROM V_RANDOM_CENTER_40
ORDER BY CENTER_ID;


CREATE OR REPLACE VIEW V_RANDOM_CENTER_BASE AS

SELECT
    C.CENTER_ID,
    C.CENTER_LAT,
    C.CENTER_LON,

    S.YR,
    S.STORE_NO,
    S.ROLE,
    S.LAT,
    S.LON,

    /* 임의 중심점 → 점포 거리 */
    ST_DISTANCE(
        ST_MAKEPOINT(S.LON, S.LAT),
        ST_MAKEPOINT(C.CENTER_LON, C.CENTER_LAT)
    ) AS DIST_RANDOM_CENTER,

    /* 임의 중심점 → 점포 방위각 */
    MOD(
        DEGREES(
            ATAN2(
                S.LON - C.CENTER_LON,
                S.LAT - C.CENTER_LAT
            )
        ) + 360,
        360
    ) AS STORE_BEARING,

    /* 임의 중심점 → 성심당 방위각 */
    MOD(
        DEGREES(
            ATAN2(
                127.42718 - C.CENTER_LON,
                36.32752 - C.CENTER_LAT
            )
        ) + 360,
        360
    ) AS ANCHOR_BEARING

FROM V_RANDOM_CENTER_40 C

CROSS JOIN V_ROLE_CLASSIFIED S

WHERE S.YR IN (2021, 2026);


CREATE OR REPLACE VIEW V_RANDOM_CENTER_SECTOR AS

WITH X AS (

    SELECT
        *,

        ABS(
            MOD(
                STORE_BEARING - ANCHOR_BEARING + 180,
                360
            ) - 180
        ) AS ANGLE_DIFF

    FROM V_RANDOM_CENTER_BASE

    WHERE DIST_RANDOM_CENTER <= 300
)

SELECT
    *,

    CASE
        WHEN ANGLE_DIFF <= 60
            THEN '성심당방향'

        WHEN ANGLE_DIFF >= 120
            THEN '반대방향'

        ELSE '측면'
    END AS SECTOR

FROM X;


CREATE OR REPLACE VIEW V_RANDOM_CENTER_LIFE AS

SELECT
    CENTER_ID,
    YR,
    SECTOR,

    COUNT(*) AS N,

    AVG(
        IFF(ROLE = '생활밀착', 1, 0)
    ) AS LIFE_RATIO

FROM V_RANDOM_CENTER_SECTOR

WHERE SECTOR IN ('성심당방향', '반대방향')

GROUP BY
    CENTER_ID,
    YR,
    SECTOR;


    SELECT *
FROM V_RANDOM_CENTER_LIFE
ORDER BY CENTER_ID, YR, SECTOR;


CREATE OR REPLACE VIEW V_RANDOM_CENTER_DID AS

SELECT
    CENTER_ID,

    (
        MAX(
            IFF(
                YR = 2026
                AND SECTOR = '성심당방향',
                LIFE_RATIO,
                NULL
            )
        )
        -
        MAX(
            IFF(
                YR = 2021
                AND SECTOR = '성심당방향',
                LIFE_RATIO,
                NULL
            )
        )
    ) * 100
    AS D_ANCHOR_PP,

    (
        MAX(
            IFF(
                YR = 2026
                AND SECTOR = '반대방향',
                LIFE_RATIO,
                NULL
            )
        )
        -
        MAX(
            IFF(
                YR = 2021
                AND SECTOR = '반대방향',
                LIFE_RATIO,
                NULL
            )
        )
    ) * 100
    AS D_OPPO_PP

FROM V_RANDOM_CENTER_LIFE

GROUP BY CENTER_ID;


SELECT
    CENTER_ID,

    ROUND(D_ANCHOR_PP, 2) AS D_ANCHOR_PP,
    ROUND(D_OPPO_PP, 2) AS D_OPPO_PP,

    ROUND(
        D_ANCHOR_PP - D_OPPO_PP,
        2
    ) AS DID_PP

FROM V_RANDOM_CENTER_DID

ORDER BY DID_PP;

SELECT
    COUNT(*) AS N_CENTER,

    ROUND(
        AVG(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS PLACEBO_MEAN_PP,

    ROUND(
        STDDEV_SAMP(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS PLACEBO_SD_PP,

    ROUND(
        MIN(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS MIN_PP,

    ROUND(
        MAX(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS MAX_PP,

    COUNT_IF(
        D_ANCHOR_PP - D_OPPO_PP <= -1.79
    ) AS N_LE_OBSERVED,

    ROUND(
        COUNT_IF(
            D_ANCHOR_PP - D_OPPO_PP <= -1.79
        )
        / COUNT(*) * 100,
        1
    ) AS LOWER_PCT

FROM V_RANDOM_CENTER_DID

WHERE D_ANCHOR_PP IS NOT NULL
  AND D_OPPO_PP IS NOT NULL;


  SELECT
    ROUND(
        PERCENTILE_CONT(0.05)
        WITHIN GROUP (
            ORDER BY D_ANCHOR_PP - D_OPPO_PP
        ),
        2
    ) AS P05_PP,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY D_ANCHOR_PP - D_OPPO_PP
        ),
        2
    ) AS MEDIAN_PP,

    ROUND(
        PERCENTILE_CONT(0.95)
        WITHIN GROUP (
            ORDER BY D_ANCHOR_PP - D_OPPO_PP
        ),
        2
    ) AS P95_PP

FROM V_RANDOM_CENTER_DID

WHERE D_ANCHOR_PP IS NOT NULL
  AND D_OPPO_PP IS NOT NULL;


  CREATE OR REPLACE VIEW V_RANDOM_CENTER_40 AS

WITH CANDIDATES AS (

    SELECT
        STORE_NO,
        STORE_NM,
        LAT AS CENTER_LAT,
        LON AS CENTER_LON,
        DIST_CENTER,
        DIST_ANCHOR,

        ROW_NUMBER() OVER (
            PARTITION BY
                ROUND(LAT, 5),
                ROUND(LON, 5)
            ORDER BY HASH(STORE_NO)
        ) AS LOC_RN

    FROM V_SANGA_CLEAN

    WHERE YR = 2026
      AND DIST_CENTER <= 700
      AND DIST_ANCHOR >= 50
),

UNIQUE_POINTS AS (

    SELECT *
    FROM CANDIDATES
    WHERE LOC_RN = 1
),

PICK_40 AS (

    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY HASH(STORE_NO)
        ) AS CENTER_ID

    FROM UNIQUE_POINTS
)

SELECT
    CENTER_ID,
    STORE_NO AS CENTER_STORE_NO,
    STORE_NM AS CENTER_STORE_NM,
    CENTER_LAT,
    CENTER_LON,
    DIST_CENTER

FROM PICK_40

WHERE CENTER_ID <= 40;


SELECT
    COUNT(*) AS N_CENTER,
    COUNT(
        DISTINCT CONCAT(
            ROUND(CENTER_LAT, 5),
            '|',
            ROUND(CENTER_LON, 5)
        )
    ) AS N_UNIQUE_CENTER
FROM V_RANDOM_CENTER_40;


SELECT
    COUNT(*) AS N_CENTER,

    ROUND(
        AVG(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS PLACEBO_MEAN_PP,

    ROUND(
        STDDEV_SAMP(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS PLACEBO_SD_PP,

    ROUND(
        MIN(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS MIN_PP,

    ROUND(
        MAX(D_ANCHOR_PP - D_OPPO_PP),
        2
    ) AS MAX_PP,

    COUNT_IF(
        D_ANCHOR_PP - D_OPPO_PP <= -1.79
    ) AS N_LE_OBSERVED,

    ROUND(
        COUNT_IF(
            D_ANCHOR_PP - D_OPPO_PP <= -1.79
        )
        / COUNT(*) * 100,
        1
    ) AS LOWER_PCT

FROM V_RANDOM_CENTER_DID

WHERE D_ANCHOR_PP IS NOT NULL
  AND D_OPPO_PP IS NOT NULL;

  SELECT
    ROUND(
        PERCENTILE_CONT(0.05)
        WITHIN GROUP (
            ORDER BY D_ANCHOR_PP - D_OPPO_PP
        ),
        2
    ) AS P05_PP,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY D_ANCHOR_PP - D_OPPO_PP
        ),
        2
    ) AS MEDIAN_PP,

    ROUND(
        PERCENTILE_CONT(0.95)
        WITHIN GROUP (
            ORDER BY D_ANCHOR_PP - D_OPPO_PP
        ),
        2
    ) AS P95_PP

FROM V_RANDOM_CENTER_DID

WHERE D_ANCHOR_PP IS NOT NULL
  AND D_OPPO_PP IS NOT NULL;