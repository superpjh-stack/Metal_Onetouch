# Sprint 9 — 프론트엔드 전체 통합 + UI 완성 Design

> **Feature**: sprint-9-frontend-ui  
> **Date**: 2026-05-07  
> **Status**: Design Phase

---

## 1. 구현 범위

### 1.1 T-01: /shipment/page.tsx 완전 구현

**파일**: `frontend/src/app/(dashboard)/shipment/page.tsx`

**컴포넌트 구조**:
```
ShipmentPage (메인)
├── PageHeader (출하물류, 출하등록 버튼)
├── SummaryCard × 3 (대기/배송중/인수완료 카운트)
├── Tabs
│   ├── TabsTrigger "출하 목록" → DataTable<Shipment>
│   │   └── 컬럼: 출하번호, 고객사, 상태, 계획출하일, LOT수, 실출하일, 인수완료일, 상태변경버튼
│   └── TabsTrigger "대기 목록" → PendingShipmentTab
│       └── DataTable<Shipment> (pending 필터) + 출하처리 버튼
├── CreateShipmentDialog
│   ├── Select: 고객사 (/api/v1/master/customers)
│   ├── Input: 계획 출하일
│   ├── LOT 번들 (동적 행 추가/삭제)
│   └── Input: 비고
└── UpdateStatusDialog
    ├── 현재 출하 정보 표시
    ├── Select: 변경 상태 (pending→shipped, shipped→delivered, or 취소)
    └── Input: 비고
```

**상태 전환 규칙**:
```
pending → shipped (출하 처리)
pending → cancelled
shipped → delivered (인수 완료)
shipped → cancelled
```

**사용 Hook**:
- `useShipments(filters?)` — 목록 조회
- `useCreateShipment()` — 출하 등록
- `useUpdateShipmentStatus()` — 상태 변경
- `useQuery(['customers-select'])` — 고객사 목록 (직접 호출)

---

### 1.2 T-02: 사이드바 ML/수주 메뉴 추가

**파일**: `frontend/src/components/layout/sidebar.tsx`

**추가된 navItems**:
| 순서 | 레이블 | href | 아이콘 |
|------|--------|------|--------|
| 5 | 수주관리 | /orders | ShoppingCart |
| 11 | ML 학습 | /ml/training | Brain |
| 12 | 어노테이션 | /ml/annotation | Tag |

**최종 navItems (13개)**:
1. AI 대시보드 → /
2. 공정관리 → /process
3. 입고재고 → /inventory
4. 출하물류 → /shipment ← (기존 플레이스홀더 교체)
5. 수주관리 → /orders ← (신규)
6. 수주견적 AI → /quotation
7. 기준정보 → /master-data
8. KPI → /kpi
9. 데이터허브 → /data-hub
10. AI Agent → /ai-agent
11. ML 학습 → /ml/training ← (신규)
12. 어노테이션 → /ml/annotation ← (신규)
13. 시스템관리 → /system

---

### 1.3 T-03: 수주관리 사이드바 연결

**채택 방식**: 사이드바에 `/orders` 직접 추가 (별도 페이지 유지)

**기존 `/orders/page.tsx`** 완전 구현 상태 (변경 없음):
- 수주 목록 (상태 필터)
- 수주 등록 다이얼로그 (고객사, 납기일, 수주품목 행)

---

## 2. API 연동 요약

| 페이지 | API 엔드포인트 | 메서드 |
|--------|---------------|--------|
| /shipment | /api/v1/shipments/ | GET, POST |
| /shipment | /api/v1/shipments/{id}/status | PATCH |
| /shipment | /api/v1/master/customers | GET |

---

## 3. 완료 기준

| 항목 | 기준 |
|------|------|
| /shipment 플레이스홀더 제거 | ✅ 완전 구현 |
| 사이드바 13개 메뉴 정상 링크 | ✅ 전체 접근 가능 |
| 출하 등록 → 상태 변경 플로우 | ✅ CRUD 완성 |
| TypeScript 오류 | 0개 |
| 기존 페이지 회귀 없음 | 기존 동작 유지 |
