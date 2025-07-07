# 📘 Nexacro 중분류별 매출 구성비 구조 문서 (2025-07-07 기준)

## 🧭 상위 구조 계층 (Frame → Form → Component)

nexacro.getApplication().mainframe
└── frames[]                    // 열려 있는 화면 목록
    └── [WorkFrame]._form      // 현재 실행 중인 화면 Form
        └── components
            ├── gdList         ← 중분류 코드 리스트 (좌측 그리드)
            └── gdDetail       ← 상품 목록 (우측 그리드)

## ✅ 좌측: 중분류 코드 그리드 `gdList`

| 항목 | 설명 |
|------|------|
| 구성 | 중분류 코드, 분류명, 수량, 금액, 구성비 등 |
| 행 구조 | `gridrow_{n}` |
| 열 구조 | `cell_{n}_{col}` |
| 주요 셀 예시 |
| - 코드 "019" | `gdList.gridrow_9.cell_9_0:text` |
| - 분류명 "초콜릿" | `gdList.gridrow_9.cell_9_1:text` |
| 클릭 대상 | `:text` 없는 `cell_9_0` div (이벤트 전송 대상) |

## ✅ 우측: 상품 목록 그리드 `gdDetail`

| 항목 | 설명 |
|------|------|
| 구성 | 중분류별 상품 상세 정보 |
| 표시 행 수 | 한 화면에 4행 (스크롤로 추가 불러오기 가능) |
| 행 구조 | `gridrow_{row}` |
| 열 구조 | `cell_{row}_{col}` |
| 텍스트 셀 | `cell_{row}_{col}:text` |

### 🔢 열 인덱스 (col 번호별 항목)

| 열(col) | 항목명     | 예시 ID |
|---------|------------|----------|
| 0       | 상품코드   | `cell_0_0:text` |
| 1       | 상품명     | `cell_0_1:text` |
| 2       | 매출       | `cell_0_2:text` |
| 3       | 발주       | `cell_0_3:text` |
| 4       | 매입       | `cell_0_4:text` |
| 5       | 폐기       | `cell_0_5:text` |
| 6       | 현재고     | `cell_0_6:text` |

## ✅ 스크롤 구성

| 구성 요소 | ID 예시 | 설명 |
|------------|----------|------|
| 스크롤 버튼 | `incbutton:icontext` | 클릭 시 다음 4행 로딩됨 |
| 스크롤 후에도 DOM 구조는 동일 | `gridrow_{n}` | 다음 4행은 `gridrow_0 ~ 3`로 다시 채워짐 (이전 내용 덮어쓰기됨) |

## 🧩 작동 흐름 요약

1. **중분류 코드 클릭** → `gdList.cell_{n}_0` 클릭
2. → Nexacro 트랜잭션 (`searchDetail`) 발생
3. → `gdDetail`에 4개의 상품 정보 표시
4. **스크롤 버튼 클릭 시** → 다음 4행 데이터로 교체

## ✅ DOM ID 패턴 요약표

| 대상 | DOM ID 패턴 |
|------|--------------|
| 중분류 코드 | `gdList.gridrow_{n}.cell_{n}_0[:text]` |
| 중분류명 | `gdList.gridrow_{n}.cell_{n}_1:text` |
| 상품코드 | `gdDetail.gridrow_{n}.cell_{n}_0:text` |
| 상품명 | `gdDetail.gridrow_{n}.cell_{n}_1:text` |
| 기타 항목 | `gdDetail.gridrow_{n}.cell_{n}_{col}:text` |

## ✅ 예시 콘솔 명령 요약 (기억용)

### 중분류 '019' 클릭
dispatchMouseEventTo('gdList.gridrow_9.cell_9_0');

### 중분류명 추출
document.querySelector('div[id*="gdList"][id*="cell_9_1:text"]')?.innerText;

### 상품코드 4개 추출
for (let i = 0; i < 4; i++) {
  console.log(document.querySelector(`div[id*="gdDetail"][id*="gridrow_${i}"][id*="cell_${i}_0:text"]`)?.innerText);
}

## 📌 정리 요약

- Nexacro 그리드는 DOM id 패턴이 `gridrow_{row}.cell_{row}_{col}[:text]`로 **정형화**되어 있음
- 스크롤이 필요한 경우에는 **기존 row index를 재사용하여 새로운 데이터만 로딩**됨
- **중분류 ↔ 상품코드** 간 연결은 DOM id 구조만으로 정확히 추적 가능
