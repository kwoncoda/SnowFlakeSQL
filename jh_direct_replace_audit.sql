-- =====================================================================
-- 파일명: 03_direct_replace_audit.sql
-- 담당자: 주현
-- 목적: 점포별 생존 기간(Lifespan) 및 QUALIFY를 활용한 1:1 교체 이벤트 추출
-- =====================================================================

-- 1. 개별 점포의 존속 기간(Lifespan) 추출 및 BAND_CENTER 자체 생성
CREATE OR REPLACE VIEW V_STORE_LIFESPAN AS
SELECT 
    JIBUN_ADDR, 
    COALESCE(FLR_INFO, 'NA') AS FLR_INFO,
    STORE_NO, 
    ROLE, 
    SECTOR,
    CASE 
        WHEN DIST_CENTER <= 150 THEN '0-150m'
        WHEN DIST_CENTER <= 300 THEN '150-300m'
        WHEN DIST_CENTER <= 450 THEN '300-450m'
        WHEN DIST_CENTER <= 600 THEN '450-600m'
        WHEN DIST_CENTER <= 800 THEN '600-800m'
        ELSE '800m+' 
    END AS BAND_CENTER,
    MIN(YR) AS OPEN_YR,
    MAX(YR) AS CLOSE_YR
FROM V_ROLE_CLASSIFIED
GROUP BY 1, 2, 3, 4, 5, 6;

-- 2. 대체 이벤트 1:1 판정 (다대다 폭발 방지)
CREATE OR REPLACE VIEW V_REPLACE_EVENTS AS
SELECT 
    old.SECTOR,
    old.BAND_CENTER,
    old.ROLE AS OLD_ROLE,
    new.ROLE AS NEW_ROLE,
    IFF(old.ROLE = new.ROLE, 1, 0) AS IS_DIRECT_REPLACE
FROM V_STORE_LIFESPAN old
JOIN V_STORE_LIFESPAN new
  ON old.JIBUN_ADDR = new.JIBUN_ADDR
 AND old.FLR_INFO = new.FLR_INFO
 AND old.STORE_NO != new.STORE_NO
 AND new.OPEN_YR > old.CLOSE_YR
 AND new.OPEN_YR <= old.CLOSE_YR + 2 
-- [핵심 로직] 다대다 조인을 방지하고, 폐업한 점포(old) 1개당 가장 빨리 들어온 신규 점포(new) 1개만 매칭!
QUALIFY ROW_NUMBER() OVER (PARTITION BY old.STORE_NO ORDER BY new.OPEN_YR ASC, new.STORE_NO ASC) = 1;

-- 3. 주현 님이 제안한 '거리대별' 분석 뷰
CREATE OR REPLACE VIEW V_REPLACE_BY_BAND AS
SELECT 
    BAND_CENTER,
    SECTOR,
    COUNT(*) AS N_EVENTS,
    SUM(IS_DIRECT_REPLACE) AS N_DIRECT,
    ROUND(AVG(IS_DIRECT_REPLACE) * 100, 1) AS DIRECT_RATE_PCT
FROM V_REPLACE_EVENTS
WHERE SECTOR IN ('성심당방향', '반대방향')
GROUP BY BAND_CENTER, SECTOR
ORDER BY BAND_CENTER, SECTOR;

-- 4. 300m 이내 방향별 직접대체율 뷰 (화면 연동 및 검증용)
CREATE OR REPLACE VIEW V_REPLACE_AUDIT AS
SELECT
    SECTOR,
    COUNT(*) AS N_EVENTS,
    SUM(IS_DIRECT_REPLACE) AS N_DIRECT,
    ROUND(AVG(IS_DIRECT_REPLACE) * 100, 1) AS DIRECT_RATE_PCT
FROM V_REPLACE_EVENTS
WHERE BAND_CENTER IN ('0-150m', '150-300m')
  AND SECTOR IN ('성심당방향', '반대방향')
GROUP BY SECTOR;

-- 5. Z-Test (비율 차이 검정) 뷰 
CREATE OR REPLACE VIEW V_REPLACE_ZTEST AS
WITH a AS (SELECT * FROM V_REPLACE_AUDIT WHERE SECTOR='성심당방향'),
     b AS (SELECT * FROM V_REPLACE_AUDIT WHERE SECTOR='반대방향'),
     pooled AS (
        SELECT (a.N_DIRECT + b.N_DIRECT)::FLOAT / NULLIF(a.N_EVENTS + b.N_EVENTS, 0) AS P_POOL
        FROM a, b
     )
SELECT
    a.DIRECT_RATE_PCT AS RATE_ANCHOR,
    b.DIRECT_RATE_PCT AS RATE_OPPO,
    ROUND(a.DIRECT_RATE_PCT - b.DIRECT_RATE_PCT, 1) AS DIFF_PP,
    ROUND(
      (a.DIRECT_RATE_PCT/100 - b.DIRECT_RATE_PCT/100) /
      NULLIF(SQRT(p.P_POOL*(1-p.P_POOL)*(1.0/a.N_EVENTS + 1.0/b.N_EVENTS)), 0), 3
    ) AS Z_SCORE
FROM a, b, pooled p;

-- =====================================================================
-- 실행 후 검증
-- =====================================================================
SELECT * FROM V_REPLACE_BY_BAND ORDER BY BAND_CENTER, SECTOR;PROJECT_DB.SHARED_FILES.FOOD_ALL