CREATE OR REPLACE FUNCTION WILSON_LO(k FLOAT, n FLOAT)
RETURNS FLOAT AS
$$
    CASE
        WHEN n <= 0 THEN NULL
        ELSE
            ((k/n + 1.9208/n)
             - 1.96 * SQRT(
                 (k/n)*(1-k/n)/n
                 + 0.9604/(n*n)
             ))
            / (1 + 3.8416/n)
    END
$$;


CREATE OR REPLACE FUNCTION WILSON_HI(k FLOAT, n FLOAT)
RETURNS FLOAT AS
$$
    CASE
        WHEN n <= 0 THEN NULL
        ELSE
            ((k/n + 1.9208/n)
             + 1.96 * SQRT(
                 (k/n)*(1-k/n)/n
                 + 0.9604/(n*n)
             ))
            / (1 + 3.8416/n)
    END
$$;

CREATE OR REPLACE VIEW V_SECTOR_BAND AS

SELECT
    PERIOD,
    CENTER_BAND,
    SECTOR,

    COUNT(*) AS N,

    AVG(Y_CLOSED_24M) AS RATE,

    WILSON_LO(
        SUM(Y_CLOSED_24M),
        COUNT(*)
    ) AS CI_LO,

    WILSON_HI(
        SUM(Y_CLOSED_24M),
        COUNT(*)
    ) AS CI_HI

FROM V_GEO

WHERE SECTOR IN ('ANCHOR', 'OPPOSITE')

GROUP BY
    PERIOD,
    CENTER_BAND,
    SECTOR;


SELECT *
FROM V_SECTOR_BAND
WHERE PERIOD = 'POST'
ORDER BY
    CASE CENTER_BAND
        WHEN '0-150m' THEN 1
        WHEN '150-300m' THEN 2
        WHEN '300-450m' THEN 3
        WHEN '450-600m' THEN 4
        WHEN '600-800m' THEN 5
        ELSE 6
    END,
    SECTOR;


CREATE OR REPLACE VIEW V_SECTOR_GAP AS

SELECT
    PERIOD,
    CENTER_BAND,

    MAX(
        CASE
            WHEN SECTOR = 'ANCHOR'
            THEN RATE
        END
    ) * 100 AS RATE_ANCHOR,

    MAX(
        CASE
            WHEN SECTOR = 'OPPOSITE'
            THEN RATE
        END
    ) * 100 AS RATE_OPPO,

    (
        MAX(
            CASE
                WHEN SECTOR = 'ANCHOR'
                THEN RATE
            END
        )
        -
        MAX(
            CASE
                WHEN SECTOR = 'OPPOSITE'
                THEN RATE
            END
        )
    ) * 100 AS GAP_PP,

    MAX(
        CASE
            WHEN SECTOR = 'ANCHOR'
            THEN N
        END
    ) AS N_ANCHOR,

    MAX(
        CASE
            WHEN SECTOR = 'OPPOSITE'
            THEN N
        END
    ) AS N_OPPO

FROM V_SECTOR_BAND

GROUP BY
    PERIOD,
    CENTER_BAND;


SELECT
    CENTER_BAND,
    ROUND(RATE_ANCHOR, 2) AS RATE_ANCHOR,
    ROUND(RATE_OPPO, 2) AS RATE_OPPO,
    ROUND(GAP_PP, 2) AS GAP_PP,
    N_ANCHOR,
    N_OPPO

FROM V_SECTOR_GAP

WHERE PERIOD = 'POST'

ORDER BY
    CASE CENTER_BAND
        WHEN '0-150m' THEN 1
        WHEN '150-300m' THEN 2
        WHEN '300-450m' THEN 3
        WHEN '450-600m' THEN 4
        WHEN '600-800m' THEN 5
        ELSE 6
    END;


CREATE OR REPLACE VIEW V_ANGLE_SENSITIVITY AS

WITH HALFS AS (

    SELECT COLUMN1 AS HALF
    FROM VALUES
        (30),
        (45),
        (60),
        (75),
        (90)
)

SELECT
    H.HALF,

    AVG(
        CASE
            WHEN G.ANGLE_DIFF <= H.HALF
            THEN G.Y_CLOSED_24M
        END
    ) * 100 AS RATE_ANCHOR,

    AVG(
        CASE
            WHEN G.ANGLE_DIFF >= 180 - H.HALF
            THEN G.Y_CLOSED_24M
        END
    ) * 100 AS RATE_OPPO,

    COUNT_IF(
        G.ANGLE_DIFF <= H.HALF
    ) AS N_ANCHOR,

    COUNT_IF(
        G.ANGLE_DIFF >= 180 - H.HALF
    ) AS N_OPPO

FROM V_GEO G

CROSS JOIN HALFS H

WHERE G.PERIOD = 'POST'
  AND G.DIST_CENTER > 0
  AND G.DIST_CENTER <= 300

GROUP BY H.HALF;


SELECT
    HALF,
    ROUND(RATE_ANCHOR, 2) AS RATE_ANCHOR,
    ROUND(RATE_OPPO, 2) AS RATE_OPPO,
    ROUND(RATE_ANCHOR - RATE_OPPO, 2) AS GAP_PP,
    N_ANCHOR,
    N_OPPO

FROM V_ANGLE_SENSITIVITY

ORDER BY HALF;



SELECT
    CENTER_BAND,
    SECTOR,
    N,
    ROUND(RATE * 100, 2) AS CLOSED_RATE_PCT,
    ROUND(CI_LO * 100, 2) AS CI_LO_PCT,
    ROUND(CI_HI * 100, 2) AS CI_HI_PCT
FROM V_SECTOR_BAND
WHERE PERIOD = 'POST'
ORDER BY
    CASE CENTER_BAND
        WHEN '0-150m' THEN 1
        WHEN '150-300m' THEN 2
        WHEN '300-450m' THEN 3
        WHEN '450-600m' THEN 4
        WHEN '600-800m' THEN 5
        ELSE 6
    END,
    SECTOR;


SELECT
    CENTER_BAND,
    ROUND(RATE_ANCHOR, 2) AS RATE_ANCHOR,
    ROUND(RATE_OPPO, 2) AS RATE_OPPO,
    ROUND(GAP_PP, 2) AS GAP_PP,
    N_ANCHOR,
    N_OPPO
FROM V_SECTOR_GAP
WHERE PERIOD = 'POST'
ORDER BY
    CASE CENTER_BAND
        WHEN '0-150m' THEN 1
        WHEN '150-300m' THEN 2
        WHEN '300-450m' THEN 3
        WHEN '450-600m' THEN 4
        WHEN '600-800m' THEN 5
        ELSE 6
    END;