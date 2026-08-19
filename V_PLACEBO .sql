CREATE OR REPLACE TABLE DIM_REF_POINT (
    POINT_NM VARCHAR,
    P_LAT FLOAT,
    P_LON FLOAT
);

INSERT INTO DIM_REF_POINT VALUES
    ('성심당',       36.32752, 127.42718),
    ('대전역',       36.33249, 127.43301),
    ('중앙로역',     36.32870, 127.42750),
    ('대전시청',     36.35040, 127.38450),
    ('서대전네거리', 36.32120, 127.41280),
    ('복합터미널',   36.35120, 127.43560),
    ('유성온천역',   36.35430, 127.34180);


SELECT *
FROM DIM_REF_POINT;


CREATE OR REPLACE VIEW V_PLACEBO AS

WITH D AS (

    SELECT
        P.POINT_NM,
        C.PERIOD,
        C.Y_CLOSED_24M,

        ST_DISTANCE(
            ST_MAKEPOINT(C.LON, C.LAT),
            ST_MAKEPOINT(P.P_LON, P.P_LAT)
        ) AS DD

    FROM V_COHORT C

    CROSS JOIN DIM_REF_POINT P

    WHERE C.PERIOD IN ('PRE', 'POST')
),

G AS (

    SELECT
        POINT_NM,
        PERIOD,

        AVG(
            CASE
                WHEN DD <= 500
                THEN Y_CLOSED_24M
            END
        ) AS NEAR_RATE,

        AVG(
            CASE
                WHEN DD > 3000
                THEN Y_CLOSED_24M
            END
        ) AS FAR_RATE,

        COUNT_IF(DD <= 500) AS N_NEAR

    FROM D

    GROUP BY
        POINT_NM,
        PERIOD
)

SELECT
    POINT_NM,

    MAX(
        CASE
            WHEN PERIOD = 'PRE'
            THEN (NEAR_RATE - FAR_RATE) * 100
        END
    ) AS GAP_PRE_PP,

    MAX(
        CASE
            WHEN PERIOD = 'POST'
            THEN (NEAR_RATE - FAR_RATE) * 100
        END
    ) AS GAP_POST_PP,

    MAX(
        CASE
            WHEN PERIOD = 'POST'
            THEN (NEAR_RATE - FAR_RATE) * 100
        END
    )
    -
    MAX(
        CASE
            WHEN PERIOD = 'PRE'
            THEN (NEAR_RATE - FAR_RATE) * 100
        END
    ) AS DID_PP,

    MAX(
        CASE
            WHEN PERIOD = 'POST'
            THEN N_NEAR
        END
    ) AS N_NEAR_POST

FROM G

GROUP BY POINT_NM;


SELECT
    POINT_NM,
    ROUND(GAP_PRE_PP, 2) AS GAP_PRE_PP,
    ROUND(GAP_POST_PP, 2) AS GAP_POST_PP,
    ROUND(DID_PP, 2) AS DID_PP,
    N_NEAR_POST
FROM V_PLACEBO
ORDER BY DID_PP;