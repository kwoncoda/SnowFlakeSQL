-- =====================================================================
-- 파일명: 02_rent_index_unpivot.sql
-- 담당자: 주현
-- 목적: 가로형 임대료 원본 데이터를 대시보드용 세로형(Long) 뷰로 변환
-- =====================================================================
CREATE OR REPLACE VIEW V_RENT_INDEX AS
SELECT 
    -- 'Y2024_1' -> '2024Q1' 형태로 문자열 치환
    REPLACE(REPLACE(QTR_COL, 'Y', ''), '_', 'Q') AS QTR, 
    DISTRICT,
    RENT_PRICE AS RENT_INDEX_CHG_PP
FROM RENT_PRICE
UNPIVOT (
    RENT_PRICE FOR QTR_COL IN (
        Y2022_1, Y2022_2, Y2022_3, Y2022_4,
        Y2023_1, Y2023_2, Y2023_3, Y2023_4,
        Y2024_1, Y2024_2, Y2024_3, Y2024_4,
        Y2025_1, Y2025_2, Y2025_3, Y2025_4,
        Y2026_1, Y2026_2
    )
);

-- 검증: 데이터가 세로로 잘 풀렸는지 확인
SELECT * FROM V_RENT_INDEX WHERE DISTRICT = '대전원도심' ORDER BY QTR;