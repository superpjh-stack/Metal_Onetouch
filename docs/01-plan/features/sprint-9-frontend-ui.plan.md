# Sprint 9 — 프론트엔드 전체 통합 + UI 완성 Plan

> **Feature**: sprint-9-frontend-ui  
> **Date**: 2026-05-07  
> **Status**: Plan Phase  
> **Priority**: High

---

## 1. 목표

Sprint 1~6에서 백엔드 구현이 완료된 모든 API와 프론트엔드를 완전히 연결하고,
누락된 페이지/라우트를 완성하여 10개 모듈이 모두 동작하는 상태를 만든다.

---

## 2. 현황 분석

### 2.1 완전 구현된 페이지 (정상)
| 경로 | 모듈 | 상태 |
|------|------|------|
| `/` | AI 대시보드 | ✅ 정상 |
| `/process` | 공정관리 | ✅ 정상 |
| `/process/[wo_id]` | 작업지시 상세 | ✅ 정상 |
| `/inventory` | 입고재고 | ✅ 정상 |
| `/quotation` | 수주견적 AI (CAD) | ✅ 정상 |
| `/master-data` | 기준정보 관리 | ✅ 정상 |
| `/kpi` | KPI 관리 | ✅ 정상 |
| `/data-hub` | 데이터허브 (IoT 시뮬) | ✅ 정상 |
| `/ai-agent` | AI Agent (RAG 채팅) | ✅ 정상 |
| `/system` | 시스템관리 (사용자) | ✅ 정상 |
| `/ml/training` | ML 학습 관리 | ✅ 구현완료, 사이드바 미연결 |
| `/ml/annotation` | 어노테이션 편집기 | ✅ 구현완료, 사이드바 미연결 |

### 2.2 문제 있는 페이지
| 경로 | 문제 | 조치 |
|------|------|------|
| `/shipment` | 플레이스홀더 "개발 예정" — 사이드바 연결됨 | 전체 구현 필요 |
| `/logistics` | 완전 구현됐으나 사이드바 미연결 (잘못된 라우트) | `/shipment`으로 내용 이전 |
| `/orders` | 수주관리 완전 구현됐으나 사이드바 미포함 | 사이드바 추가 또는 `/quotation` 탭 통합 |
| `/admin` | 구현됐으나 사이드바 미포함 | 시스템관리 하위 또는 제거 검토 |

---

## 3. 구현 범위

### P1 — 반드시 완성 (Critical)

#### T-01: `/shipment/page.tsx` 완전 구현
- 출하 목록 조회 (상태 필터)
- 출하 등록 다이얼로그 (고객사 선택, LOT 번들, 날짜)
- 출하 상태 업데이트 (대기→배송중→인수완료)
- LOT 출하 리스크 뱃지 표시
- API: `useShipments`, `useCreateShipment`, `useUpdateShipmentStatus`

#### T-02: 사이드바 ML 메뉴 추가
- "ML 모델" 그룹 또는 "데이터허브" 하위 메뉴
- `/ml/training` (YOLOv8 학습 관리)
- `/ml/annotation` (어노테이션 편집)

#### T-03: 수주관리 사이드바 연결
- 옵션 A: `/quotation` 페이지에 탭 추가 (CAD 견적 + 수주 목록)
- 옵션 B: 사이드바에 `/orders` 별도 메뉴 추가
- **채택: 옵션 A** — quotation 페이지에 "수주목록" 탭 통합

### P2 — 품질 개선 (High)

#### T-04: `process/[wo_id]` 상세 페이지 점검
- 실적 입력 폼 동작 확인
- 공정 완료 처리 버튼
- LOT 이력 표시

#### T-05: 공통 에러 처리 개선
- API 오류 시 toast 알림 (현재 일부 누락)
- 로딩 Skeleton 통일성 점검

#### T-06: TypeScript 타입 오류 점검
- `frontend/src/types/index.ts` 누락 타입 보완
- API 응답 타입 일치 여부 확인

### P3 — 선택 구현 (Medium)

#### T-07: 반응형 레이아웃 점검
- 모바일/태블릿 뷰 기본 동작 확인

---

## 4. 기술 스택

- Next.js 14 App Router + TypeScript
- shadcn/ui 컴포넌트 (기존 유지)
- React Query (useQuery, useMutation)
- Zustand (ui-store, auth-store)
- Recharts (차트)

---

## 5. 완료 기준

| 기준 | 목표 |
|------|------|
| 사이드바 모든 링크 동작 | 10/10 페이지 정상 접근 |
| 플레이스홀더 페이지 제거 | 0개 |
| ML 메뉴 접근 가능 | /ml/training, /ml/annotation |
| TypeScript 컴파일 오류 | 0개 (기존 수준 유지) |
| 핵심 CRUD 동작 | 등록/조회/상태변경 |

---

## 6. 구현 순서

```
Step 1: /shipment/page.tsx 완전 구현 (T-01)
Step 2: 사이드바 ML 메뉴 추가 (T-02)
Step 3: quotation 탭에 수주목록 통합 (T-03)
Step 4: process/[wo_id] 점검 (T-04)
Step 5: 에러 처리 점검 (T-05)
Step 6: Gap 분석 및 최종 검증
```
