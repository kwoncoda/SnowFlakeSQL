USE WAREHOUSE COMPUTE_WH;

-- 1. FOOD_ALL 전처리 및 대표 1건선별 (중복 제거 & 모든 속성 칼럼 유지)
WITH hg_base AS (
    SELECT 
        shop_id, service_type, shop_name, biz_type, hygiene_type, biz_group, 
        is_tourism_biz, is_chain, chain_src, license_date, close_date, status, 
        area_sqm, addr_jibun, addr_road, dong, slot, lat, lon, dist_anchor, dist_band,
        -- 주소 정제 및 좌표 3자리 컬럼 생성
        REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(addr_road), '\\s*[\\(（].+?[\\)）]', ''), '[）\\)]', ''), ',.*$', '') AS road_clean,
        REGEXP_REPLACE(REGEXP_REPLACE(TRIM(addr_jibun), '\\s*[\\(（].+?[\\)）]', ''), ',.*$', '') AS jibun_clean,
        ROUND(lat, 3) AS lat3,
        ROUND(lon, 3) AS lon3
    FROM PROJECT_DB.SHARED_FILES.FOOD_ALL
),
-- [좌표3자리 대표 1건]
hg_lat_dedup AS (
    SELECT * FROM hg_base
    QUALIFY ROW_NUMBER() OVER (PARTITION BY lat3, lon3 ORDER BY shop_id DESC) = 1
),
-- [도로명주소 대표 1건]
hg_road_dedup AS (
    SELECT * FROM hg_base 
    WHERE road_clean IS NOT NULL AND road_clean != ''
    QUALIFY ROW_NUMBER() OVER (PARTITION BY road_clean ORDER BY shop_id DESC) = 1
),
-- [지번주소 대표 1건]
hg_jibun_dedup AS (
    SELECT * FROM hg_base 
    WHERE jibun_clean IS NOT NULL AND jibun_clean != ''
    QUALIFY ROW_NUMBER() OVER (PARTITION BY jibun_clean ORDER BY shop_id DESC) = 1
),

-- 2. SANGA_ALL 전처리 (2025년 좌표 보정 적용 포함)
sanga_prep AS (
    SELECT 
        s.*,
        REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(s.road_nm_addr), '\\s*[\\(（].+?[\\)）]', ''), '[）\\)]', ''), ',.*$', '') AS road_clean,
        REGEXP_REPLACE(REGEXP_REPLACE(TRIM(s.jibun_addr), '\\s*[\\(（].+?[\\)）]', ''), ',.*$', '') AS jibun_clean,
        -- 좌표 보정 적용 (25년 오프셋 수정)
        ROUND(CASE WHEN s.lat > 37 AND s.lon > 128 THEN s.lat - 0.888706 ELSE s.lat END, 3) AS lat3,
        ROUND(CASE WHEN s.lat > 37 AND s.lon > 128 THEN s.lon - 1.248891 ELSE s.lon END, 3) AS lon3
    FROM PROJECT_DB.SHARED_FILES.SANGA_ALL s
)

-- 3. 1:1 조인 및 FOOD_ALL의 전체 칼럼 가져오기
SELECT 
    s.*,
    
    -- 매칭 유형 구분
    CASE 
        WHEN h1.shop_id IS NOT NULL THEN '1순위_좌표3자리'
        WHEN h2.shop_id IS NOT NULL THEN '2순위_도로명'
        WHEN h3.shop_id IS NOT NULL THEN '3순위_지번'
        ELSE '미매칭'
    END AS match_type,

    -- FOOD_ALL 속성 칼럼들을 COALESCE로 1/2/3순위에서 가져오기
    COALESCE(h1.shop_id, h2.shop_id, h3.shop_id)           AS hg_shop_id,
    COALESCE(h1.service_type, h2.service_type, h3.service_type) AS hg_service_type,
    COALESCE(h1.shop_name, h2.shop_name, h3.shop_name)     AS hg_shop_name,
    COALESCE(h1.biz_type, h2.biz_type, h3.biz_type)         AS hg_biz_type,
    COALESCE(h1.hygiene_type, h2.hygiene_type, h3.hygiene_type) AS hg_hygiene_type,
    COALESCE(h1.biz_group, h2.biz_group, h3.biz_group)     AS hg_biz_group,
    COALESCE(h1.is_tourism_biz, h2.is_tourism_biz, h3.is_tourism_biz) AS hg_is_tourism_biz,
    COALESCE(h1.is_chain, h2.is_chain, h3.is_chain)         AS hg_is_chain,
    COALESCE(h1.chain_src, h2.chain_src, h3.chain_src)     AS hg_chain_src,
    COALESCE(h1.license_date, h2.license_date, h3.license_date) AS hg_license_date,
    COALESCE(h1.close_date, h2.close_date, h3.close_date)   AS hg_close_date,
    COALESCE(h1.status, h2.status, h3.status)               AS hg_status,
    COALESCE(h1.area_sqm, h2.area_sqm, h3.area_sqm)         AS hg_area_sqm,
    COALESCE(h1.addr_jibun, h2.addr_jibun, h3.addr_jibun)   AS hg_addr_jibun,
    COALESCE(h1.addr_road, h2.addr_road, h3.addr_road)     AS hg_addr_road,
    COALESCE(h1.dong, h2.dong, h3.dong)                     AS hg_dong,
    COALESCE(h1.slot, h2.slot, h3.slot)                     AS hg_slot,
    COALESCE(h1.lat, h2.lat, h3.lat)                         AS hg_lat,
    COALESCE(h1.lon, h2.lon, h3.lon)                         AS hg_lon,
    COALESCE(h1.dist_anchor, h2.dist_anchor, h3.dist_anchor) AS hg_dist_anchor,
    COALESCE(h1.dist_band, h2.dist_band, h3.dist_band)     AS hg_dist_band

FROM sanga_prep s
LEFT JOIN hg_lat_dedup h1 
       ON s.lat3 = h1.lat3 AND s.lon3 = h1.lon3
LEFT JOIN hg_road_dedup h2 
       ON s.road_clean = h2.road_clean AND h1.shop_id IS NULL
LEFT JOIN hg_jibun_dedup h3 
       ON s.jibun_clean = h3.jibun_clean AND h1.shop_id IS NULL AND h2.shop_id IS NULL;