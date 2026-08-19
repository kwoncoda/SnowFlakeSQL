# 성심당 원도심 상권 분석

> 성심당은 주변 점포를 더 오래 살리는가, 아니면 상권의 구성을 바꾸는가?

대전 원도심의 대표 앵커인 **성심당** 주변을 대상으로 점포 생존율과 업종 구성 변화를 분석한 Snowflake 프로젝트입니다. 지방행정 인허가 데이터와 소상공인 상가업소 스냅샷을 결합하고, 공간 분석·코호트 분석·위약검정·Snowpark Python 회귀분석을 거쳐 결과를 Streamlit in Snowflake 대시보드로 시각화합니다.

## 핵심 결론

단순히 성심당과 가깝거나 성심당 방향에 있다는 이유만으로 점포가 더 오래 살아남는다는 근거는 확인하지 못했습니다.

- 원형 거리 분석: 성심당의 폐업률 DiD는 **-3.15%p**였지만 중앙로역은 **-4.11%p**로 더 크게 나타났습니다.
- 방향 통제 분석: 중앙로역 300m 이내에서 성심당 방향 폐업률이 **-7.02%p** 낮았지만, 건물 단위 Cluster Robust SE 적용 시 **p=0.575**로 유의하지 않았습니다.
- 업종 구성 분석: 2021→2026년 성심당 방향의 음식점·주점 등 **보완재 비중은 +4.08%p**, 반대 방향은 +0.39%p 변했습니다. DiD는 **+3.69%p**이며 60개 방향 위약검정에서 상위 **3.3%**였습니다.

따라서 현재 데이터가 지지하는 가장 좁고 안전한 해석은 다음과 같습니다.

> 성심당 주변에서 점포 생존 효과는 확인되지 않았지만, 중앙로역 기준 성심당이 놓인 상업축에서는 음식점·주점 중심의 업종 구성 변화가 상대적으로 두드러졌다.

이는 관찰 연구 결과이며, “성심당이 음식점을 증가시켰다”는 직접적인 인과관계를 뜻하지 않습니다.

## 분석 흐름

```text
LOCALDATA 음식점 인허가 이력
  └─ FOOD_ALL
      └─ V_FOOD_CLEAN
          └─ V_COHORT
              └─ V_GEO
                  ├─ V_PLACEBO
                  ├─ V_SECTOR_BAND / V_SECTOR_GAP
                  └─ V_ROBUST_INPUT → Snowpark Python 회귀

소상공인 상가업소 연도별 스냅샷
  └─ SANGA_21 ... SANGA_26
      └─ SANGA_ALL
          └─ SANGA_PANEL_CORE_1KM
              └─ V_SANGA_CLEAN
                  └─ V_ROLE_CLASSIFIED
                      ├─ V_ROLE_TREND / V_ROLE_DID / V_ROLE_BAND
                      ├─ V_ROLE_PLACEBO_SCAN
                      ├─ V_RANDOM_CENTER_40 계열
                      └─ V_STORE_LIFESPAN / V_REPLACE_EVENTS 계열

한국부동산원 임대료 데이터
  └─ RENT_PRICE
      └─ V_RENT_INDEX

분석 결과
  └─ V_FINAL_SUMMARY
      └─ daejeonstore/streamlit_app.py
```

## 데이터

기본 데이터베이스와 스키마는 `PROJECT_DB.SHARED_FILES`를 전제로 합니다.

| 원본 객체 | 내용 | 주요 컬럼 |
| --- | --- | --- |
| `FOOD_ALL` | 대전 일반·휴게·제과 음식점 인허가 이력 | 인허가일, 폐업일, 업종군, 주소, 좌표 |
| `SANGA_21`~`SANGA_26` | 2021~2026년 상가업소정보 스냅샷 | 점포번호, 업종 대·중·소분류, 주소, 좌표, 지점명 |
| `SANGA_ALL` | 연도별 상가업소 테이블의 통합 VIEW | 원본 컬럼 + `SOURCE_TABLE` |
| `RENT_PRICE` | 대전 주요 상권의 분기별 임대가격지수 | 상권명, 분기별 지수 변화 |

주요 공간 기준은 다음과 같습니다.

| 구분 | 위도 | 경도 |
| --- | ---: | ---: |
| 성심당 | 36.32752 | 127.42718 |
| 중앙로역 | 36.32870 | 127.42750 |

- 중앙로역→성심당 기준 방위각: 약 **195.2°**
- 핵심 분석 범위: 중앙로역 반경 **300m**
- 패널 전처리 범위: 중앙로역 반경 **1km**
- 성심당 방향: 기준 방위각과의 차이 ≤ 60°
- 반대 방향: 기준 방위각과의 차이 ≥ 120°

## 주요 파일

### 공통 전처리와 공간 분석

| 파일 | 역할 |
| --- | --- |
| `role.sql` | 권한 부여 예시와 `SANGA_ALL` 통합 VIEW 생성 |
| `FS_ALL.sql` | 상가업소정보와 음식점 인허가정보를 좌표·도로명·지번 우선순위로 매칭 |
| `v_cohort.sql` | `V_FOOD_CLEAN`, 생존 코호트 `V_COHORT`, 공간 파생변수 `V_GEO` 생성 |
| `V_PLACEBO .sql` | 성심당·대전역·중앙로역 등 7개 기준점의 원형 거리 위약 비교 |
| `V_SECTOR_BAND .sql` | 거리대×방향 폐업률, Wilson 신뢰구간, 각도폭 민감도 계산 |
| `V_ROBUST.sql` | 클러스터 회귀용 `V_ROBUST_INPUT` 생성 |
| `V_ROBUST.py` | 건물(`SLOT`) 단위 Cluster Robust SE 로지스틱 회귀 |
| `cluster.py` | 회귀와 무작위 방향 위약검정의 초기 통합 실험 코드 |

### 업종 구성과 추가 검증

| 파일 | 역할 |
| --- | --- |
| `V_ROLE_TREND.sql` | 상가 패널 정제, 업종 역할 분류, 연도별 추세·DiD·60방향 위약검정 |
| `V_ROLE_CLASSIFIED.sql` | 생활밀착·보완재·경쟁재 등 업종 역할과 `BRANCH_NM` 기반 지점 여부 분류 |
| `V_RANDOM_CENTER_40.sql` | 생활밀착 업종 변화가 다른 임의 중심점에서도 나타나는지 검정 |
| `jh_direct_replace_audit.sql` | 주소·층 단위의 점포 교체 이벤트와 동일 역할 대체율 계산 |
| `jh_detailed_transition_matrix.sql` | 교체 전후 세부업종 전환 매트릭스 생성 |
| `jh_rent_index_unpivot.sql` | 가로형 임대료 테이블을 대시보드용 long format으로 변환 |
| `V_FINAL_SUMMARY.sql` | 채택·기각된 분석 결과를 한 VIEW로 요약 |

### 대시보드

| 경로 | 역할 |
| --- | --- |
| `daejeonstore/streamlit_app.py` | 9단계 분석 스토리를 보여주는 Streamlit in Snowflake 앱 |
| `daejeonstore/snowflake.yml` | Snowflake CLI 배포 정의 |
| `daejeonstore/pyproject.toml` | Python 3.11 및 Streamlit 의존성 정의 |

## 권장 실행 순서

SQL 파일은 마이그레이션 도구가 아니라 분석 과정과 검증용 `SELECT`가 함께 들어 있는 작업 스크립트입니다. 파일 전체를 일괄 실행하기 전에 각 `CREATE OR REPLACE` 블록과 현재 스키마를 확인하세요.

1. `FOOD_ALL`, `SANGA_21`~`SANGA_26`, `RENT_PRICE` 원본을 `PROJECT_DB.SHARED_FILES`에 적재합니다.
2. `role.sql`의 `SANGA_ALL` 생성 구문을 실행합니다.
3. `v_cohort.sql`의 최종 정의를 기준으로 `V_FOOD_CLEAN` → `V_COHORT` → `V_GEO`를 생성합니다.
4. `V_PLACEBO .sql`과 `V_SECTOR_BAND .sql`을 실행합니다.
5. `V_ROBUST.sql`을 실행한 뒤 Snowpark 환경에서 `V_ROBUST.py`를 실행합니다.
6. `V_ROLE_TREND.sql`로 `SANGA_PANEL_CORE_1KM`과 업종 구성 분석 VIEW를 생성합니다.
7. 프랜차이즈 근사 지표가 필요하면 `V_ROLE_CLASSIFIED.sql`을 추가 실행합니다.
8. `V_RANDOM_CENTER_40.sql` 및 `jh_*.sql`의 추가 검증을 실행합니다.
9. `jh_rent_index_unpivot.sql`과 `V_FINAL_SUMMARY.sql`을 실행합니다.
10. 필요한 모든 VIEW의 스키마를 확인한 뒤 Streamlit 앱을 배포합니다.

`role.sql`에는 `USERADMIN` 전환과 `팀원_계정_이름` 자리표시자가 포함되어 있습니다. 실제 계정에 맞게 수정하고, 권한 부여가 필요할 때만 관리자 권한으로 실행하세요.

## Streamlit 앱

앱은 Snowflake 세션에서 `PROJECT_DB.SHARED_FILES`의 VIEW를 읽습니다. VIEW가 없거나 조회에 실패하면 해당 화면만 내장 MOCK 데이터로 폴백하며, 화면과 사이드바에 데이터 소스를 표시합니다.

```powershell
cd daejeonstore
streamlit run streamlit_app.py
```

로컬 실행 시 Snowflake 활성 세션이 없으므로 MOCK 모드로 동작합니다. 실데이터 확인은 Streamlit in Snowflake 환경에서 수행하세요.

대시보드의 주요 화면은 다음과 같습니다.

1. 전체 음식점 데이터 지도
2. 성심당 거리 분석
3. 7개 기준점 Placebo 비교
4. 중앙로역 기준 방향 통제 설계
5. 거리대별 폐업률과 각도폭 민감도
6. 견고성·위약검정 통합표
7. 임대료 및 생활밀착 업종 검토
8. 프랜차이즈 비중 추세와 업소 단위 보조 분석
9. 최종 채택·기각 결과

## 업종 역할 정의

| 역할 | 분류 기준 |
| --- | --- |
| 생활밀착 | 미용실, 네일, 피부관리, 이용원, 세탁, 수선, 목욕·찜질 등 |
| 보완재 | 경쟁재를 제외한 음식점·주점 등 |
| 경쟁재 | 카페·비알코올 음료, 제과, 빵, 도넛, 아이스크림 등 |
| 생활기타 | 생활밀착에 포함되지 않는 기타 개인서비스 |
| 소매 | 상가업소 대분류가 소매인 업종 |
| 기타 | 위 분류에 포함되지 않는 업종 |

`IS_BRANCH`는 `BRANCH_NM`이 비어 있지 않은지를 사용한 **프랜차이즈 근사값**입니다. 실제 가맹 여부와 일치한다고 가정해서는 안 됩니다.

## 현재 구현 체크포인트

- `v_cohort.sql`, `V_ROLE_TREND.sql`, `V_RANDOM_CENTER_40.sql`에는 실험 과정에서 같은 VIEW를 여러 번 재정의한 흔적이 있습니다. 최종 배포용으로는 VIEW별 단일 정의 파일로 분리하는 것이 안전합니다.
- `FS_ALL.sql`은 현재 결과를 반환하는 CTE 쿼리이며 `FS_ALL` 객체를 직접 생성하지 않습니다. 영구 사용 시 `CREATE VIEW FS_ALL AS` 또는 `CREATE TABLE FS_ALL AS`로 감싸야 합니다.
- Streamlit은 `V_ROLE_TREND`를 `YR, SECTOR, ROLE, N, TOTAL_N, PCT` 형태의 long format으로 기대하지만 현재 SQL은 `LIFE_RATIO`, `SUPPORT_RATIO`, `COMPETE_RATIO` 열을 가진 wide format을 생성합니다. 실데이터 연결 전에 둘 중 하나의 스키마를 통일해야 합니다.
- 앱이 사용하는 `V_PLACEBO_SUMMARY`, `V_BRANCH_TREND`의 생성 SQL은 현재 폴더에 포함되어 있지 않습니다. Snowflake에 별도로 존재하지 않으면 해당 화면은 MOCK 데이터로 표시됩니다.
- `jh_direct_replace_audit.sql` 마지막 줄에는 검증 쿼리 뒤에 불필요한 문자열이 붙어 있으므로 해당 부분을 제거한 뒤 실행해야 합니다.
- `snowflake.yml`에는 `.streamlit/config.toml`이 배포 아티팩트로 선언되어 있지만 현재 저장소에는 파일이 없습니다.

## 해석 시 주의사항

- 대전 원도심 단일 사례이므로 다른 도시나 앵커 상권으로 바로 일반화할 수 없습니다.
- 직선거리와 방위각 비교는 공간이 모든 방향에서 비슷하다는 등방성 가정을 포함합니다. 실제로는 서로 다른 도로·상업축의 차이를 비교했을 수 있습니다.
- 상가업소정보는 연도별 스냅샷이므로 정확한 개·폐업일이나 장기 생존을 직접 관측하지 못합니다.
- 2021년과 2026년 사이 업종분류 체계나 수집 범위가 동일한지 별도 검증이 필요합니다.
- 유동인구, 카드 매출, 임대차 계약 데이터가 없어 관광객 유입과 실제 매출·임대료의 인과 경로는 검증하지 못했습니다.
- 좁은 반경과 소표본 구간은 공간적 노이즈에 민감하므로 신뢰구간과 위약검정 결과를 함께 봐야 합니다.

## 관련 문서

- `../docs/진행가이드.md` — 전체 분석 설계와 팀 작업 가이드
- `../docs/V_FINAL_SUMMARY 결과.md` — 최종 결과 상세 해설
- `../docs/발표 장표 구성.md` — 12장 발표 스토리 구성
- `../docs/지원 Streamlit 시각화 자료 설명.md` — 화면별 시각화 의도

## 기술 스택

- Snowflake SQL / Geospatial Functions
- Snowpark Python
- pandas / NumPy / statsmodels
- Streamlit in Snowflake
