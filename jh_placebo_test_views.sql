-- =====================================================================
-- 파일명: 01_placebo_test_views.sql
-- 담당자: 주현
-- 목적: 기준점 테이블 생성 및 원형 거리 기반 위약 검정(Placebo) 뷰 생성
-- =====================================================================

-- 1. 기준점 테이블 생성
CREATE OR REPLACE TABLE DIM_REF_POINT (
    POINT_NM VARCHAR, 
    P_LAT FLOAT, 
    P_LON FLOAT
);

-- 1-1. 대전 주요 앵커 상권 7곳 좌표 삽입
INSERT INTO DIM_REF_POINT VALUES
  ('성심당',      36.32752, 127.42718),
  ('대전역',      36.33249, 127.43301),
  ('중앙로역',    36.32870, 127.42750),
  ('대전시청',    36.35040, 127.38450),
  ('서대전네거리', 36.32120, 127.41280),
  ('복합터미널',  36.35120, 127.43560),
  ('유성온천역',  36.35430, 127.34180);

-- 2. 위약 검정 뷰 (V_PLACEBO) 생성
CREATE OR REPLACE VIEW V_PLACEBO AS
WITH d AS (
    -- c.Y 대신 실제 컬럼명인 c.Y_CLOSED_24M을 사용합니다.
    SELECT p.POINT_NM, c.PERIOD, c.Y_CLOSED_24M AS Y,
           ST_DISTANCE(ST_MAKEPOINT(c.LON, c.LAT),
                       ST_MAKEPOINT(p.P_LON, p.P_LAT)) AS DD
    FROM V_COHORT c
    CROSS JOIN DIM_REF_POINT p
    WHERE c.PERIOD IN ('PRE','POST')
),
g AS (
    SELECT POINT_NM, PERIOD,
           AVG(CASE WHEN DD <= 500  THEN Y END) AS NEAR_RATE,
           AVG(CASE WHEN DD >  3000 THEN Y END) AS FAR_RATE,
           COUNT_IF(DD <= 500)                  AS N_NEAR
    FROM d 
    GROUP BY 1,2
)
SELECT POINT_NM,
       MAX(CASE WHEN PERIOD='PRE'  THEN (NEAR_RATE-FAR_RATE)*100 END) AS GAP_PRE_PP,
       MAX(CASE WHEN PERIOD='POST' THEN (NEAR_RATE-FAR_RATE)*100 END) AS GAP_POST_PP,
       MAX(CASE WHEN PERIOD='POST' THEN (NEAR_RATE-FAR_RATE)*100 END)
     - MAX(CASE WHEN PERIOD='PRE'  THEN (NEAR_RATE-FAR_RATE)*100 END) AS DID_PP,
       MAX(CASE WHEN PERIOD='POST' THEN N_NEAR END)                   AS N_NEAR_POST
FROM g 
GROUP BY 1 
ORDER BY DID_PP;

-- =====================================================================
-- 3. 검증용 쿼리 (실행 후 결과가 맞는지 꼭 확인하세요)
-- 목표값: 중앙로역 -4.1%p / 대전역 -4.0%p / 성심당 -3.1%p / 대전시청 +1.3%p
-- =====================================================================
SELECT POINT_NM, DID_PP, N_NEAR_POST 
FROM V_PLACEBO 
WHERE POINT_NM IN ('중앙로역', '대전역', '성심당', '대전시청')
ORDER BY DID_PP ASC;