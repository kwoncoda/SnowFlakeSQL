-- =====================================================================
-- 파일명: 04_detailed_transition_matrix.sql (수정판 v2)
-- 담당자: 주현
-- 목적: 1:1 교체 이벤트에 세부업종(L2/L3)을 붙여 상세 전환 매트릭스 생성
-- 변경점: V_FOOD_CLEAN 조인 삭제. V_STORE_LIFESPAN은 그대로 두고,
--         V_ROLE_CLASSIFIED를 STORE_NO+연도로 재조인해 L2/L3를 가져옴.
-- =====================================================================

-- 1. 1:1 교체 이벤트 뷰 — STORE_NO를 살려서 이후 조인에 쓴다
CREATE OR REPLACE VIEW V_REPLACE_EVENTS_DETAIL AS
SELECT
    old.SECTOR,
    old.BAND_CENTER,
    old.JIBUN_ADDR,
    old.ROLE       AS OLD_ROLE,
    old.STORE_NO   AS OLD_STORE_NO,      -- ★ 추가
    old.CLOSE_YR   AS OLD_CLOSE_YR,      -- ★ 추가
    new.ROLE       AS NEW_ROLE,
    new.STORE_NO   AS NEW_STORE_NO,      -- ★ 추가
    new.OPEN_YR    AS NEW_OPEN_YR
FROM V_STORE_LIFESPAN old
JOIN V_STORE_LIFESPAN new
  ON old.JIBUN_ADDR = new.JIBUN_ADDR
 AND old.FLR_INFO   = new.FLR_INFO
 AND old.STORE_NO  != new.STORE_NO
 AND new.OPEN_YR    > old.CLOSE_YR
 AND new.OPEN_YR   <= old.CLOSE_YR + 2
QUALIFY ROW_NUMBER() OVER (PARTITION BY old.STORE_NO ORDER BY new.OPEN_YR ASC, new.STORE_NO ASC) = 1;

-- 2. 세부업종(L2/L3) 결합 — V_ROLE_CLASSIFIED를 STORE_NO+연도로 재조인
CREATE OR REPLACE VIEW V_TRANSITION_MATRIX AS
SELECT
    r.SECTOR,
    r.BAND_CENTER,
    r.OLD_ROLE                       AS "기존_대분류",
    old_rc.L3                        AS "기존_세부업종",
    r.NEW_ROLE                       AS "신규_대분류",
    new_rc.L3                        AS "신규_세부업종",
    COUNT(*)                         AS N_EVENTS
FROM V_REPLACE_EVENTS_DETAIL r
LEFT JOIN V_ROLE_CLASSIFIED old_rc
  ON old_rc.STORE_NO = r.OLD_STORE_NO
 AND old_rc.YR       = r.OLD_CLOSE_YR         -- 폐업 직전(마지막 관측) 연도의 세부업종
LEFT JOIN V_ROLE_CLASSIFIED new_rc
  ON new_rc.STORE_NO = r.NEW_STORE_NO
 AND new_rc.YR       = r.NEW_OPEN_YR          -- 개업 연도의 세부업종
WHERE r.SECTOR IN ('성심당방향', '반대방향')
  AND r.BAND_CENTER IN ('0-150m', '150-300m')
GROUP BY r.SECTOR, r.BAND_CENTER, r.OLD_ROLE, old_rc.L3, r.NEW_ROLE, new_rc.L3
ORDER BY r.SECTOR, r.BAND_CENTER, N_EVENTS DESC;

SELECT * FROM V_TRANSITION_MATRIX;