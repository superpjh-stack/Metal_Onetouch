# Changelog — Metal-Onetouch AI+MES

모든 주목할 만한 변경 사항이 이 파일에 기록됩니다.
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) 형식을 따릅니다.

---

## [2026-05-07] - Sprint 9 Frontend UI 완료

### Summary
플레이스홀더 출하물류 페이지를 완전 기능 페이지로 교체하고, 사이드바 메뉴를 3개 추가하여 10개 모듈 전체 통합 완성.

### Added
- **T-01: /shipment/page.tsx 완전 구현**
  - ShipmentPage 메인 컴포넌트 (상태별 요약 카드 × 3)
  - Tabs (출하목록 / 대기목록)
  - DataTable (출하번호, 고객사, 상태, 날짜, 상태변경 버튼)
  - CreateShipmentDialog (고객사 선택, 계획출하일, LOT 번들 동적 행)
  - UpdateStatusDialog (상태 전환: pending→shipped→delivered)
  - API 훅: useShipments, useCreateShipment, useUpdateShipmentStatus

- **T-02: 사이드바 메뉴 3개 추가**
  - 수주관리 → /orders (ShoppingCart 아이콘)
  - ML 학습 → /ml/training (Brain 아이콘)
  - 어노테이션 → /ml/annotation (Tag 아이콘)
  - navItems: 10개 → 13개

- **T-03: 수주관리 사이드바 연결**
  - /orders/page.tsx 기존 기능 유지
  - 사이드바 메뉴를 통한 접근성 확보

### Changed
- sidebar.tsx: navItems 배열 확장 (10개 → 13개)
- 플레이스홀더 페이지 구조 교체 (개발 예정 → 완전 기능)

### Fixed
- /shipment 페이지 "개발 예정" 플레이스홀더 완전 제거
- 사이드바 ML/수주 메뉴 누락 해결

### Verified
- Match Rate: 100% (16/16 체크리스트)
- Gap Analysis: Critical 0건, Major 0건, Minor 0건
- TypeScript 오류: 0개
- API 연동: 3/3 완료

### Technical Details
- **상태 전환 로직**: pending → shipped → delivered (단방향) + 취소 옵션
- **LOT 번들**: React Hook Form 동적 배열 관리
- **API 연동**: 3개 엔드포인트 (GET 목록, POST 등록, PATCH 상태변경)
- **UI 컴포넌트**: shadcn/ui 컴포넌트 기반, Recharts 없음

### Related Documents
- Report: `docs/04-report/features/sprint-9-frontend-ui.report.md`
- Design: `docs/02-design/features/sprint-9-frontend-ui.design.md`
- Analysis: `docs/03-analysis/sprint-9-frontend-ui.analysis.md`

---

## Version History

| 버전 | 날짜 | 요약 | 상태 |
|------|------|------|------|
| 1.0 | 2026-05-07 | Sprint 9 Frontend UI 완료 | ✅ Approved |
