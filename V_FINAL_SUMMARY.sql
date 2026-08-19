CREATE OR REPLACE VIEW V_FINAL_SUMMARY AS

SELECT
    '실패1' AS STAGE,
    '원형 거리 + Placebo' AS METHOD,
    '성심당 -3.15%p, 중앙로역 -4.11%p' AS RESULT,
    '기각' AS VERDICT

UNION ALL

SELECT
    '실패2',
    '방향 통제 + 견고성 검정',
    '폐업률 -7.02%p, Cluster SE p=0.575, 공간 위약 36.7%',
    '기각'

UNION ALL

SELECT
    '구성1',
    '생활밀착 업종 DiD',
    '-1.79%p, 방향 위약 11.7%, 무작위 중심점 위약 20.0%',
    '기각'

UNION ALL

SELECT
    '구성2',
    '보완재 업종 DiD',
    '+3.69%p, 60방향 위약 상위 3.3%',
    '채택'

UNION ALL

SELECT
    '구성3',
    '경쟁재 업종 DiD',
    '+1.59%p, 60방향 위약 상위 43.3%',
    '기각'

UNION ALL

SELECT
    '최종',
    '업종 구성 변화',
    '보완재: 성심당 방향 +4.08%p vs 반대 방향 +0.39%p',
    '채택';


SELECT * FROM PROJECT_DB.SHARED_FILES.V_ROLE_CLASSIFIED;