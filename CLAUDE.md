# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Planning Phase 완료** (2026-04-30). 사업계획서 42-46페이지 기반으로 기획 3팀이 마스터 플랜을 작성했습니다. 아직 소스코드는 없으며 설계 단계 진입 예정입니다.

## Project Context

- **Project name**: Metal-Onetouch AI+MES (원터치 제조AI 특화 스마트공장)
- **Industry**: 금속 가공 제조업 (판금/용접/절삭)
- **Development level**: Enterprise
- **Core value**: LOT 기반 전 공정 추적 + AI Agent (입고/출하/통합) + Vision AI (CAD 자동견적)

## System Architecture

**10대 모듈**: AI대시보드, 입고재고관리, 수주견적AI관리, 출하물류관리, 공정관리, 사용자/시스템관리, 기준정보관리, 데이터허브관리, AI Agent통합관리, KPI관리

**기술 스택**:
- Frontend: Next.js 14 + TypeScript + shadcn/ui + Recharts + Socket.io
- Backend: FastAPI (Python 3.11) + SQLAlchemy 2.0 + Celery
- AI/ML: LangChain + YOLOv8 + XGBoost + SHAP + MLflow
- RAG: Qdrant (온프레미스) + BGE-M3 임베딩
- LLM: GPT-4o / Claude 3.5 Sonnet
- DB: PostgreSQL 16 + TimescaleDB (IoT) + Redis + MinIO
- Streaming: MQTT → Kafka → Flink → TimescaleDB

**Development Phases**:
- Phase 1 (M1~4): MES 핵심 기반 — 공정관리, IoT연동, RBAC, 기초 대시보드
- Phase 2 (M5~8): 물류/품질 + RAG AI Agent 기초
- Phase 3 (M9~14): Vision AI 견적, 통합 AI Agent, ERP 완전 연동

## Development Pipeline

This project follows the bkit 9-phase pipeline. Start from Phase 1 and progress sequentially:

1. `/phase-1-schema` — Define domain terminology and data structures
2. `/phase-2-convention` — Establish coding conventions
3. `/phase-3-mockup` — Create UI/UX mockups
4. `/phase-4-api` — Design and implement backend APIs
5. `/phase-5-design-system` — Build component library
6. `/phase-6-ui-integration` — Integrate frontend with APIs
7. `/phase-7-seo-security` — SEO and security hardening
8. `/phase-8-review` — Architecture and gap analysis
9. `/phase-9-deployment` — Production deployment

## Docs Directory

- `docs/.pdca-status.json` — Tracks current PDCA phase and pipeline progress
- `docs/.bkit-memory.json` — bkit session memory across conversations
