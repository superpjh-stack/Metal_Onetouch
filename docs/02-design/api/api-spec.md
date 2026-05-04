# 원터치(Onetouch) AI+MES 시스템 API 명세

**Version**: 1.0.0  
**Base URL**: `https://api.onetouch.ai/api/v1`  
**인증**: JWT Bearer Token  
**최종 수정**: 2026-04-30

---

## 목차

1. [공통 규약](#공통-규약)
2. [에러 코드](#에러-코드)
3. [인증 (Auth)](#인증-auth)
4. [LOT 추적 (Lots)](#lot-추적-lots)
5. [공정 관리 (Processes)](#공정-관리-processes)
6. [품질 관리 (Quality)](#품질-관리-quality)
7. [견적/BOM (Estimates)](#견적bom-estimates)
8. [설비 모니터링 (Equipment)](#설비-모니터링-equipment)
9. [데이터허브 & AI (Hub)](#데이터허브--ai-hub)

---

## 공통 규약

### 공통 요청 헤더

| 헤더 | 필수 | 설명 |
|------|------|------|
| `Authorization` | 인증 필요 엔드포인트 | `Bearer {accessToken}` |
| `Content-Type` | POST/PATCH | `application/json` |
| `X-Request-ID` | 선택 | 클라이언트 요청 추적 ID |

### 공통 응답 형식

```json
// 성공 (단건)
{
  "data": { "...": "..." },
  "meta": {
    "requestId": "req_abc123",
    "timestamp": "2026-04-30T09:00:00Z"
  }
}

// 성공 (목록)
{
  "data": ["..."],
  "pagination": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "hasMore": true
  },
  "meta": {
    "requestId": "req_abc123",
    "timestamp": "2026-04-30T09:00:00Z"
  }
}

// 에러
{
  "error": {
    "code": "LOT_NOT_FOUND",
    "message": "해당 LOT를 찾을 수 없습니다.",
    "traceId": "trace_abc-123"
  }
}
```

### RBAC 역할 정의

| 역할 | 설명 |
|------|------|
| `admin` | 시스템 전체 관리자 |
| `manager` | 생산/품질 관리자 |
| `operator` | 현장 작업자 |
| `viewer` | 조회 전용 (경영진 포함) |
| `sales` | 영업/견적 담당 |

### Rate Limit 공통 정책

| 등급 | 제한 | 대상 |
|------|------|------|
| Standard | 100 req/min | 일반 조회 |
| Write | 30 req/min | 생성/수정 |
| Heavy | 10 req/min | 파일 업로드, AI 질의 |
| Export | 5 req/min | 대용량 다운로드 |

Rate Limit 초과 시 `429 Too Many Requests` + `Retry-After` 헤더 반환.

---

## 에러 코드

### 인증

| 코드 | HTTP | 설명 |
|------|------|------|
| `AUTH_REQUIRED` | 401 | 인증 토큰 없음 |
| `TOKEN_EXPIRED` | 401 | 액세스 토큰 만료 |
| `TOKEN_INVALID` | 401 | 유효하지 않은 토큰 |
| `REFRESH_TOKEN_EXPIRED` | 401 | 리프레시 토큰 만료, 재로그인 필요 |
| `INSUFFICIENT_PERMISSION` | 403 | 권한 부족 |

### LOT

| 코드 | HTTP | 설명 |
|------|------|------|
| `LOT_NOT_FOUND` | 404 | LOT를 찾을 수 없음 |
| `LOT_DUPLICATE` | 409 | 중복 LOT 번호 |
| `LOT_STATUS_INVALID` | 422 | 허용되지 않는 상태 전이 |

### 공정

| 코드 | HTTP | 설명 |
|------|------|------|
| `PROCESS_NOT_FOUND` | 404 | 공정을 찾을 수 없음 |
| `PROCESS_DATA_INVALID` | 422 | 공정 데이터 형식 오류 |

### 품질

| 코드 | HTTP | 설명 |
|------|------|------|
| `INSPECTION_LOT_NOT_PASSED` | 422 | LOT 품질 불합격 — 출하 불가 |
| `CLAIM_LOT_NOT_FOUND` | 404 | 클레임 대상 LOT 없음 |
| `INSPECTION_NOT_FOUND` | 404 | 검사 이력 없음 |
| `CLAIM_NOT_FOUND` | 404 | 클레임 없음 |

### 견적/CAD

| 코드 | HTTP | 설명 |
|------|------|------|
| `CAD_PARSE_FAILED` | 422 | CAD 파일 파싱 실패 |
| `CAD_CONFIDENCE_LOW` | 422 | AI 인식 신뢰도 기준 미달 |
| `CAD_ANALYSIS_PENDING` | 202 | CAD 분석 진행 중 |
| `ESTIMATE_NOT_FOUND` | 404 | 견적 없음 |
| `ESTIMATE_LOCKED` | 422 | 수주 확정된 견적 — 수정 불가 |

### 설비

| 코드 | HTTP | 설명 |
|------|------|------|
| `EQUIPMENT_NOT_FOUND` | 404 | 설비를 찾을 수 없음 |
| `SENSOR_DATA_UNAVAILABLE` | 503 | 센서 데이터 수신 불가 |

### 공통

| 코드 | HTTP | 설명 |
|------|------|------|
| `VALIDATION_ERROR` | 422 | 요청 데이터 유효성 오류 |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate Limit 초과 |
| `NOT_FOUND` | 404 | 리소스 없음 |

---

## 인증 (Auth)

### POST /api/v1/auth/login

로그인. 이메일/비밀번호로 JWT 토큰 발급.

- **인증**: 불필요
- **Rate Limit**: 10 req/min (brute-force 방지)

**Request Body**

```json
{
  "email": "operator@onetouch.ai",
  "password": "P@ssw0rd!"
}
```

**Response 200**

```json
{
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresIn": 3600,
    "tokenType": "Bearer",
    "user": {
      "id": "usr_abc123",
      "email": "operator@onetouch.ai",
      "name": "홍길동",
      "role": "operator",
      "department": "생산1팀"
    }
  },
  "meta": { "requestId": "req_001", "timestamp": "2026-04-30T09:00:00Z" }
}
```

**Response 401**

```json
{
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "이메일 또는 비밀번호가 올바르지 않습니다.",
    "traceId": "trace_001"
  }
}
```

**Response 422**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "이메일 형식이 올바르지 않습니다.",
    "traceId": "trace_002",
    "fields": [{ "field": "email", "message": "유효한 이메일 주소를 입력하세요." }]
  }
}
```

---

### POST /api/v1/auth/logout

로그아웃. 서버 측 리프레시 토큰 무효화.

- **인증**: 필요 (모든 역할)
- **Rate Limit**: Standard

**Request Headers**

```
Authorization: Bearer {accessToken}
```

**Request Body**

```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200**

```json
{
  "data": { "message": "로그아웃되었습니다." },
  "meta": { "requestId": "req_003", "timestamp": "2026-04-30T09:01:00Z" }
}
```

**Response 401**

```json
{
  "error": { "code": "TOKEN_INVALID", "message": "유효하지 않은 토큰입니다.", "traceId": "trace_003" }
}
```

---

### POST /api/v1/auth/refresh

액세스 토큰 갱신.

- **인증**: 불필요 (refreshToken 사용)
- **Rate Limit**: 30 req/min

**Request Body**

```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200**

```json
{
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresIn": 3600,
    "tokenType": "Bearer"
  },
  "meta": { "requestId": "req_004", "timestamp": "2026-04-30T09:02:00Z" }
}
```

**Response 401**

```json
{
  "error": { "code": "REFRESH_TOKEN_EXPIRED", "message": "세션이 만료되었습니다. 다시 로그인해 주세요.", "traceId": "trace_004" }
}
```

---

### GET /api/v1/auth/me

현재 로그인된 사용자 정보 조회.

- **인증**: 필요 (모든 역할)
- **Rate Limit**: Standard

**Response 200**

```json
{
  "data": {
    "id": "usr_abc123",
    "email": "operator@onetouch.ai",
    "name": "홍길동",
    "role": "operator",
    "department": "생산1팀",
    "permissions": ["lots:read", "process-results:write", "quality:read"],
    "lastLoginAt": "2026-04-30T08:55:00Z"
  },
  "meta": { "requestId": "req_005", "timestamp": "2026-04-30T09:03:00Z" }
}
```

**Response 401**

```json
{
  "error": { "code": "TOKEN_EXPIRED", "message": "액세스 토큰이 만료되었습니다.", "traceId": "trace_005" }
}
```

---

## LOT 추적 (Lots)

### LOT 상태 전이

```
RECEIVED → INSPECTION → IN_PROCESS → COMPLETED → SHIPPED
                ↓
            REJECTED
```

---

### POST /api/v1/lots

LOT 생성 (입고 시).

- **인증**: 필요 — `admin`, `manager`, `operator`
- **Rate Limit**: Write (30 req/min)

**Request Body**

```json
{
  "lotNumber": "LOT-2026-04-001",
  "supplierId": "sup_xyz789",
  "materialCode": "MAT-SUS304-3T",
  "materialName": "SUS304 스테인리스강판 3T",
  "quantity": 500,
  "unit": "kg",
  "receivedDate": "2026-04-30",
  "expiryDate": "2027-04-30",
  "inspectionRequired": true,
  "notes": "긴급 입고 건"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `lotNumber` | string | Y | 고유 LOT 번호 |
| `supplierId` | string | Y | 공급처 ID |
| `materialCode` | string | Y | 자재 코드 |
| `materialName` | string | Y | 자재명 |
| `quantity` | number | Y | 수량 |
| `unit` | string | Y | 단위 (kg, ea, m 등) |
| `receivedDate` | date | Y | 입고일 (YYYY-MM-DD) |
| `expiryDate` | date | N | 유효기간 |
| `inspectionRequired` | boolean | N | 검사 필요 여부 (기본 true) |
| `notes` | string | N | 비고 |

**Response 201**

```json
{
  "data": {
    "id": "lot_abc001",
    "lotNumber": "LOT-2026-04-001",
    "status": "RECEIVED",
    "supplierId": "sup_xyz789",
    "supplierName": "한국특수강(주)",
    "materialCode": "MAT-SUS304-3T",
    "materialName": "SUS304 스테인리스강판 3T",
    "quantity": 500,
    "unit": "kg",
    "receivedDate": "2026-04-30",
    "inspectionRequired": true,
    "createdBy": "usr_abc123",
    "createdAt": "2026-04-30T09:00:00Z"
  },
  "meta": { "requestId": "req_010", "timestamp": "2026-04-30T09:00:00Z" }
}
```

**Response 409**

```json
{
  "error": { "code": "LOT_DUPLICATE", "message": "이미 등록된 LOT 번호입니다: LOT-2026-04-001", "traceId": "trace_010" }
}
```

---

### GET /api/v1/lots

LOT 목록 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `status` | string | N | 상태 필터 (RECEIVED, INSPECTION, IN_PROCESS, COMPLETED, SHIPPED, REJECTED) |
| `date_from` | date | N | 입고일 시작 (YYYY-MM-DD) |
| `date_to` | date | N | 입고일 종료 (YYYY-MM-DD) |
| `supplier_id` | string | N | 공급처 ID |
| `material_code` | string | N | 자재 코드 |
| `search` | string | N | LOT 번호 검색 |
| `page` | integer | N | 페이지 (기본 1) |
| `limit` | integer | N | 페이지 크기 (기본 20, 최대 100) |
| `sort` | string | N | 정렬 (receivedDate:desc, lotNumber:asc) |

**Response 200**

```json
{
  "data": [
    {
      "id": "lot_abc001",
      "lotNumber": "LOT-2026-04-001",
      "status": "IN_PROCESS",
      "supplierName": "한국특수강(주)",
      "materialCode": "MAT-SUS304-3T",
      "materialName": "SUS304 스테인리스강판 3T",
      "quantity": 500,
      "unit": "kg",
      "receivedDate": "2026-04-30",
      "currentProcess": "레이저 절단",
      "defectRate": 0.02,
      "updatedAt": "2026-04-30T10:30:00Z"
    }
  ],
  "pagination": { "total": 243, "page": 1, "limit": 20, "hasMore": true },
  "meta": { "requestId": "req_011", "timestamp": "2026-04-30T09:05:00Z" }
}
```

---

### GET /api/v1/lots/{lot_id}

LOT 상세 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `lot_id` | string | LOT ID |

**Response 200**

```json
{
  "data": {
    "id": "lot_abc001",
    "lotNumber": "LOT-2026-04-001",
    "status": "IN_PROCESS",
    "supplier": {
      "id": "sup_xyz789",
      "name": "한국특수강(주)",
      "code": "SUP-001"
    },
    "material": {
      "code": "MAT-SUS304-3T",
      "name": "SUS304 스테인리스강판 3T",
      "spec": "두께 3mm, 폭 1220mm"
    },
    "quantity": 500,
    "unit": "kg",
    "receivedDate": "2026-04-30",
    "expiryDate": "2027-04-30",
    "currentProcess": "레이저 절단",
    "processProgress": 35,
    "qualitySummary": {
      "inspectionCount": 2,
      "passCount": 2,
      "defectRate": 0.02
    },
    "notes": "긴급 입고 건",
    "createdBy": "usr_abc123",
    "createdAt": "2026-04-30T09:00:00Z",
    "updatedAt": "2026-04-30T10:30:00Z"
  },
  "meta": { "requestId": "req_012", "timestamp": "2026-04-30T09:10:00Z" }
}
```

**Response 404**

```json
{
  "error": { "code": "LOT_NOT_FOUND", "message": "해당 LOT를 찾을 수 없습니다.", "traceId": "trace_012" }
}
```

---

### PATCH /api/v1/lots/{lot_id}/status

LOT 상태 변경. 변경 이력 자동 생성.

- **인증**: 필요 — `admin`, `manager`, `operator`
- **Rate Limit**: Write

**Request Body**

```json
{
  "status": "IN_PROCESS",
  "reason": "입고 검사 완료. 공정 투입 승인.",
  "processId": "proc_laser_001"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `status` | string | Y | 변경할 상태 |
| `reason` | string | Y | 변경 사유 |
| `processId` | string | N | 투입 공정 ID (IN_PROCESS 시) |

**Response 200**

```json
{
  "data": {
    "id": "lot_abc001",
    "lotNumber": "LOT-2026-04-001",
    "previousStatus": "INSPECTION",
    "status": "IN_PROCESS",
    "statusChangedAt": "2026-04-30T10:00:00Z",
    "statusChangedBy": "usr_abc123",
    "historyId": "hist_xyz001"
  },
  "meta": { "requestId": "req_013", "timestamp": "2026-04-30T10:00:00Z" }
}
```

**Response 422**

```json
{
  "error": {
    "code": "LOT_STATUS_INVALID",
    "message": "RECEIVED 상태에서 SHIPPED로 직접 전환할 수 없습니다.",
    "traceId": "trace_013",
    "allowedTransitions": ["INSPECTION", "REJECTED"]
  }
}
```

---

### GET /api/v1/lots/{lot_id}/history

LOT 전 공정 이력 타임라인 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Response 200**

```json
{
  "data": {
    "lotId": "lot_abc001",
    "lotNumber": "LOT-2026-04-001",
    "timeline": [
      {
        "id": "hist_001",
        "sequence": 1,
        "eventType": "STATUS_CHANGE",
        "fromStatus": null,
        "toStatus": "RECEIVED",
        "description": "입고 등록",
        "performedBy": { "id": "usr_abc123", "name": "홍길동" },
        "timestamp": "2026-04-30T09:00:00Z",
        "metadata": {}
      },
      {
        "id": "hist_002",
        "sequence": 2,
        "eventType": "PROCESS_START",
        "processId": "proc_laser_001",
        "processName": "레이저 절단",
        "description": "레이저 절단 공정 시작",
        "performedBy": { "id": "usr_def456", "name": "김철수" },
        "timestamp": "2026-04-30T10:00:00Z",
        "equipmentId": "eq_laser_001"
      }
    ]
  },
  "meta": { "requestId": "req_014", "timestamp": "2026-04-30T10:05:00Z" }
}
```

---

### GET /api/v1/lots/{lot_id}/traceability

LOT 완전 역추적 리포트. 원자재 입고부터 출하까지 전 이력 포함.

- **인증**: 필요 — `admin`, `manager`
- **Rate Limit**: Standard (10 req/min — 무거운 쿼리)

**Response 200**

```json
{
  "data": {
    "lotId": "lot_abc001",
    "lotNumber": "LOT-2026-04-001",
    "generatedAt": "2026-04-30T10:10:00Z",
    "summary": {
      "totalDuration": "5일 3시간",
      "processCount": 6,
      "inspectionCount": 4,
      "defectRate": 0.015,
      "yieldRate": 0.985
    },
    "rawMaterial": {
      "supplierId": "sup_xyz789",
      "supplierName": "한국특수강(주)",
      "certificationNo": "CERT-2026-1234",
      "receivedDate": "2026-04-30"
    },
    "processes": [
      {
        "sequence": 1,
        "processId": "proc_laser_001",
        "processName": "레이저 절단",
        "startedAt": "2026-04-30T10:00:00Z",
        "completedAt": "2026-04-30T14:00:00Z",
        "operator": "김철수",
        "equipment": "LASER-001",
        "inputQty": 500,
        "outputQty": 490,
        "defectQty": 10,
        "yieldRate": 0.98
      }
    ],
    "qualityInspections": [],
    "claims": []
  },
  "meta": { "requestId": "req_015", "timestamp": "2026-04-30T10:10:00Z" }
}
```

---

### GET /api/v1/lots/{lot_id}/process-data

LOT에 연관된 공정 IoT 센서 데이터 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `process_id` | string | N | 특정 공정 ID 필터 |
| `date_from` | datetime | N | 시작 시각 (ISO 8601) |
| `date_to` | datetime | N | 종료 시각 (ISO 8601) |

**Response 200**

```json
{
  "data": {
    "lotId": "lot_abc001",
    "processData": [
      {
        "processId": "proc_laser_001",
        "processName": "레이저 절단",
        "equipmentId": "eq_laser_001",
        "recordedAt": "2026-04-30T10:15:00Z",
        "sensors": {
          "laserPower": { "value": 2500, "unit": "W" },
          "cuttingSpeed": { "value": 8000, "unit": "mm/min" },
          "gasFlow": { "value": 12.5, "unit": "L/min" },
          "temperature": { "value": 42.3, "unit": "°C" }
        }
      }
    ]
  },
  "pagination": { "total": 120, "page": 1, "limit": 20, "hasMore": true },
  "meta": { "requestId": "req_016", "timestamp": "2026-04-30T10:12:00Z" }
}
```

---

### GET /api/v1/lots/{lot_id}/quality

LOT 품질 검사 이력 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Response 200**

```json
{
  "data": {
    "lotId": "lot_abc001",
    "overallResult": "PASS",
    "inspections": [
      {
        "id": "insp_001",
        "inspectionType": "수입검사",
        "inspectedAt": "2026-04-30T09:30:00Z",
        "inspector": { "id": "usr_qc001", "name": "이영희" },
        "result": "PASS",
        "measurements": [
          { "item": "두께", "standard": "3.0±0.1mm", "measured": "3.02mm", "result": "PASS" },
          { "item": "표면조도", "standard": "Ra≤1.6", "measured": "Ra1.2", "result": "PASS" }
        ],
        "defectCount": 0,
        "notes": ""
      }
    ]
  },
  "meta": { "requestId": "req_017", "timestamp": "2026-04-30T10:15:00Z" }
}
```

---

## 공정 관리 (Processes)

### GET /api/v1/processes

공정 목록 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `is_active` | boolean | N | 활성 공정만 조회 |
| `category` | string | N | 공정 분류 (cutting, welding, inspection 등) |

**Response 200**

```json
{
  "data": [
    {
      "id": "proc_laser_001",
      "code": "PROC-001",
      "name": "레이저 절단",
      "category": "cutting",
      "description": "CNC 레이저 절단 공정",
      "standardCycleTime": 120,
      "unit": "min/lot",
      "equipmentIds": ["eq_laser_001", "eq_laser_002"],
      "isActive": true,
      "sequence": 1
    }
  ],
  "pagination": { "total": 12, "page": 1, "limit": 20, "hasMore": false },
  "meta": { "requestId": "req_020", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### POST /api/v1/process-results

공정 실적 등록 (MES 연동).

- **인증**: 필요 — `admin`, `manager`, `operator`
- **Rate Limit**: Write

**Request Body**

```json
{
  "lotId": "lot_abc001",
  "processId": "proc_laser_001",
  "equipmentId": "eq_laser_001",
  "operatorId": "usr_def456",
  "startedAt": "2026-04-30T10:00:00Z",
  "completedAt": "2026-04-30T12:00:00Z",
  "inputQty": 500,
  "outputQty": 490,
  "defectQty": 10,
  "defectReasons": [
    { "code": "DEF-001", "name": "치수불량", "count": 6 },
    { "code": "DEF-002", "name": "표면스크래치", "count": 4 }
  ],
  "parameters": {
    "laserPower": 2500,
    "cuttingSpeed": 8000,
    "assistGas": "N2"
  },
  "notes": "정상 완료"
}
```

**Response 201**

```json
{
  "data": {
    "id": "result_001",
    "lotId": "lot_abc001",
    "processId": "proc_laser_001",
    "processName": "레이저 절단",
    "equipmentId": "eq_laser_001",
    "startedAt": "2026-04-30T10:00:00Z",
    "completedAt": "2026-04-30T12:00:00Z",
    "duration": 120,
    "inputQty": 500,
    "outputQty": 490,
    "defectQty": 10,
    "yieldRate": 0.98,
    "createdAt": "2026-04-30T12:01:00Z"
  },
  "meta": { "requestId": "req_021", "timestamp": "2026-04-30T12:01:00Z" }
}
```

**Response 404**

```json
{
  "error": { "code": "PROCESS_NOT_FOUND", "message": "해당 공정을 찾을 수 없습니다.", "traceId": "trace_021" }
}
```

**Response 422**

```json
{
  "error": { "code": "PROCESS_DATA_INVALID", "message": "outputQty는 inputQty를 초과할 수 없습니다.", "traceId": "trace_022" }
}
```

---

### GET /api/v1/process-results

공정 실적 목록 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `lot_id` | string | N | LOT ID 필터 |
| `process_id` | string | N | 공정 ID 필터 |
| `equipment_id` | string | N | 설비 ID 필터 |
| `operator_id` | string | N | 작업자 ID 필터 |
| `date_from` | date | N | 시작일 |
| `date_to` | date | N | 종료일 |
| `page` | integer | N | 페이지 |
| `limit` | integer | N | 페이지 크기 |

**Response 200**

```json
{
  "data": [
    {
      "id": "result_001",
      "lotNumber": "LOT-2026-04-001",
      "processName": "레이저 절단",
      "equipmentName": "LASER-001",
      "operatorName": "김철수",
      "completedAt": "2026-04-30T12:00:00Z",
      "yieldRate": 0.98,
      "duration": 120
    }
  ],
  "pagination": { "total": 58, "page": 1, "limit": 20, "hasMore": true },
  "meta": { "requestId": "req_023", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### GET /api/v1/process-results/{id}

공정 실적 상세 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Response 200**

```json
{
  "data": {
    "id": "result_001",
    "lot": { "id": "lot_abc001", "lotNumber": "LOT-2026-04-001" },
    "process": { "id": "proc_laser_001", "name": "레이저 절단", "category": "cutting" },
    "equipment": { "id": "eq_laser_001", "name": "LASER-001" },
    "operator": { "id": "usr_def456", "name": "김철수" },
    "startedAt": "2026-04-30T10:00:00Z",
    "completedAt": "2026-04-30T12:00:00Z",
    "duration": 120,
    "inputQty": 500,
    "outputQty": 490,
    "defectQty": 10,
    "yieldRate": 0.98,
    "defectReasons": [
      { "code": "DEF-001", "name": "치수불량", "count": 6 },
      { "code": "DEF-002", "name": "표면스크래치", "count": 4 }
    ],
    "parameters": {
      "laserPower": 2500,
      "cuttingSpeed": 8000,
      "assistGas": "N2"
    },
    "notes": "정상 완료"
  },
  "meta": { "requestId": "req_024", "timestamp": "2026-04-30T09:05:00Z" }
}
```

---

### GET /api/v1/processes/{id}/analytics

공정별 수율/불량 분석.

- **인증**: 필요 — `admin`, `manager`, `viewer`
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `date_from` | date | Y | 분석 시작일 |
| `date_to` | date | Y | 분석 종료일 |
| `group_by` | string | N | 집계 단위 (day, week, month) |

**Response 200**

```json
{
  "data": {
    "processId": "proc_laser_001",
    "processName": "레이저 절단",
    "period": { "from": "2026-04-01", "to": "2026-04-30" },
    "summary": {
      "totalRuns": 120,
      "totalInputQty": 60000,
      "totalOutputQty": 58800,
      "totalDefectQty": 1200,
      "avgYieldRate": 0.98,
      "avgCycleTime": 118.5
    },
    "trend": [
      { "date": "2026-04-01", "yieldRate": 0.979, "defectRate": 0.021, "runCount": 4 },
      { "date": "2026-04-02", "yieldRate": 0.982, "defectRate": 0.018, "runCount": 5 }
    ],
    "defectBreakdown": [
      { "code": "DEF-001", "name": "치수불량", "count": 720, "ratio": 0.60 },
      { "code": "DEF-002", "name": "표면스크래치", "count": 480, "ratio": 0.40 }
    ]
  },
  "meta": { "requestId": "req_025", "timestamp": "2026-04-30T09:10:00Z" }
}
```

---

## 품질 관리 (Quality)

### POST /api/v1/quality/inspections

품질 검사 결과 등록.

- **인증**: 필요 — `admin`, `manager`, `operator` (QC 권한)
- **Rate Limit**: Write

**Request Body**

```json
{
  "lotId": "lot_abc001",
  "processResultId": "result_001",
  "inspectionType": "공정검사",
  "inspectedAt": "2026-04-30T13:00:00Z",
  "measurements": [
    { "item": "두께", "standard": "3.0±0.1mm", "measured": "3.02mm", "result": "PASS" },
    { "item": "평탄도", "standard": "≤0.5mm/m", "measured": "0.3mm/m", "result": "PASS" }
  ],
  "overallResult": "PASS",
  "defectCount": 0,
  "samplingSize": 50,
  "notes": "전수 합격"
}
```

**Response 201**

```json
{
  "data": {
    "id": "insp_001",
    "lotId": "lot_abc001",
    "inspectionType": "공정검사",
    "overallResult": "PASS",
    "defectCount": 0,
    "inspector": { "id": "usr_qc001", "name": "이영희" },
    "inspectedAt": "2026-04-30T13:00:00Z",
    "createdAt": "2026-04-30T13:01:00Z"
  },
  "meta": { "requestId": "req_030", "timestamp": "2026-04-30T13:01:00Z" }
}
```

---

### GET /api/v1/quality/inspections

품질 검사 이력 목록 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `lot_id` | string | N | LOT ID |
| `inspection_type` | string | N | 검사 유형 (수입검사, 공정검사, 출하검사) |
| `result` | string | N | 결과 (PASS, FAIL) |
| `inspector_id` | string | N | 검사자 ID |
| `date_from` | date | N | 시작일 |
| `date_to` | date | N | 종료일 |
| `page` | integer | N | 페이지 |
| `limit` | integer | N | 페이지 크기 |

**Response 200**

```json
{
  "data": [
    {
      "id": "insp_001",
      "lotNumber": "LOT-2026-04-001",
      "inspectionType": "공정검사",
      "overallResult": "PASS",
      "defectCount": 0,
      "inspectorName": "이영희",
      "inspectedAt": "2026-04-30T13:00:00Z"
    }
  ],
  "pagination": { "total": 87, "page": 1, "limit": 20, "hasMore": true },
  "meta": { "requestId": "req_031", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### PATCH /api/v1/quality/inspections/{id}

검사 결과 수정.

- **인증**: 필요 — `admin`, `manager`
- **Rate Limit**: Write

**Request Body**

```json
{
  "measurements": [
    { "item": "두께", "standard": "3.0±0.1mm", "measured": "3.05mm", "result": "PASS" }
  ],
  "overallResult": "PASS",
  "defectCount": 0,
  "notes": "재측정 후 정정"
}
```

**Response 200**

```json
{
  "data": {
    "id": "insp_001",
    "overallResult": "PASS",
    "updatedAt": "2026-04-30T14:00:00Z",
    "updatedBy": { "id": "usr_mgr001", "name": "박관리" }
  },
  "meta": { "requestId": "req_032", "timestamp": "2026-04-30T14:00:00Z" }
}
```

**Response 404**

```json
{
  "error": { "code": "INSPECTION_NOT_FOUND", "message": "해당 검사 이력을 찾을 수 없습니다.", "traceId": "trace_032" }
}
```

---

### POST /api/v1/quality/claims

클레임 접수.

- **인증**: 필요 — `admin`, `manager`, `sales`
- **Rate Limit**: Write

**Request Body**

```json
{
  "lotId": "lot_abc001",
  "customerId": "cust_001",
  "claimType": "치수불량",
  "severity": "HIGH",
  "description": "납품된 부품의 치수가 도면 기준을 벗어남",
  "defectQty": 15,
  "totalQty": 200,
  "receivedDate": "2026-04-30",
  "attachments": ["file_claim_photo_001", "file_claim_photo_002"]
}
```

**Response 201**

```json
{
  "data": {
    "id": "claim_001",
    "claimNo": "CLM-2026-04-001",
    "lotId": "lot_abc001",
    "lotNumber": "LOT-2026-04-001",
    "status": "RECEIVED",
    "severity": "HIGH",
    "description": "납품된 부품의 치수가 도면 기준을 벗어남",
    "receivedDate": "2026-04-30",
    "createdAt": "2026-04-30T15:00:00Z"
  },
  "meta": { "requestId": "req_033", "timestamp": "2026-04-30T15:00:00Z" }
}
```

**Response 404**

```json
{
  "error": { "code": "CLAIM_LOT_NOT_FOUND", "message": "클레임 대상 LOT를 찾을 수 없습니다.", "traceId": "trace_033" }
}
```

---

### GET /api/v1/quality/claims

클레임 목록 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `status` | string | N | 상태 (RECEIVED, INVESTIGATING, RESOLVED, CLOSED) |
| `severity` | string | N | 심각도 (LOW, MEDIUM, HIGH, CRITICAL) |
| `lot_id` | string | N | LOT ID |
| `customer_id` | string | N | 고객사 ID |
| `date_from` | date | N | 접수일 시작 |
| `date_to` | date | N | 접수일 종료 |
| `page` | integer | N | 페이지 |
| `limit` | integer | N | 페이지 크기 |

**Response 200**

```json
{
  "data": [
    {
      "id": "claim_001",
      "claimNo": "CLM-2026-04-001",
      "lotNumber": "LOT-2026-04-001",
      "customerName": "현대자동차(주)",
      "claimType": "치수불량",
      "severity": "HIGH",
      "status": "RECEIVED",
      "receivedDate": "2026-04-30"
    }
  ],
  "pagination": { "total": 12, "page": 1, "limit": 20, "hasMore": false },
  "meta": { "requestId": "req_034", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### PATCH /api/v1/quality/claims/{id}/status

클레임 상태 변경.

- **인증**: 필요 — `admin`, `manager`
- **Rate Limit**: Write

**Request Body**

```json
{
  "status": "INVESTIGATING",
  "assigneeId": "usr_qc001",
  "comment": "원인 분석 착수. 레이저 절단 파라미터 재검토 중.",
  "targetDate": "2026-05-05"
}
```

**Response 200**

```json
{
  "data": {
    "id": "claim_001",
    "claimNo": "CLM-2026-04-001",
    "previousStatus": "RECEIVED",
    "status": "INVESTIGATING",
    "assignee": { "id": "usr_qc001", "name": "이영희" },
    "targetDate": "2026-05-05",
    "updatedAt": "2026-04-30T15:30:00Z"
  },
  "meta": { "requestId": "req_035", "timestamp": "2026-04-30T15:30:00Z" }
}
```

**Response 404**

```json
{
  "error": { "code": "CLAIM_NOT_FOUND", "message": "해당 클레임을 찾을 수 없습니다.", "traceId": "trace_035" }
}
```

---

### GET /api/v1/quality/supplier-analysis

공급처별 품질 분석 리포트.

- **인증**: 필요 — `admin`, `manager`, `viewer`
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `date_from` | date | Y | 분석 시작일 |
| `date_to` | date | Y | 분석 종료일 |
| `supplier_id` | string | N | 특정 공급처 ID |

**Response 200**

```json
{
  "data": {
    "period": { "from": "2026-04-01", "to": "2026-04-30" },
    "suppliers": [
      {
        "supplierId": "sup_xyz789",
        "supplierName": "한국특수강(주)",
        "lotCount": 45,
        "totalQty": 22500,
        "defectQty": 337,
        "defectRate": 0.015,
        "claimCount": 2,
        "qualityScore": 92.5,
        "trend": "improving"
      }
    ]
  },
  "meta": { "requestId": "req_036", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

## 견적/BOM (Estimates)

### POST /api/v1/cad/upload

CAD 파일 업로드 및 AI 분석 요청 (비동기).

- **인증**: 필요 — `admin`, `manager`, `sales`
- **Rate Limit**: Heavy (10 req/min)
- **Content-Type**: `multipart/form-data`

**Request (multipart/form-data)**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `file` | file | Y | CAD 파일 (.dxf, .dwg, .step, .stp, .iges) |
| `estimateId` | string | N | 연결할 견적 ID |
| `notes` | string | N | 분석 요청 메모 |

**파일 제한**: 최대 50MB, 지원 포맷: DXF, DWG, STEP, STP, IGES

**Response 202** (분석 비동기 처리 시작)

```json
{
  "data": {
    "analysisId": "cad_analysis_001",
    "status": "PENDING",
    "fileName": "bracket_v3.dxf",
    "fileSize": 2048576,
    "estimatedDuration": 30,
    "pollUrl": "/api/v1/cad/analyses/cad_analysis_001",
    "uploadedAt": "2026-04-30T09:00:00Z"
  },
  "meta": { "requestId": "req_040", "timestamp": "2026-04-30T09:00:00Z" }
}
```

**Response 422**

```json
{
  "error": { "code": "CAD_PARSE_FAILED", "message": "지원하지 않는 파일 형식이거나 파일이 손상되었습니다.", "traceId": "trace_040" }
}
```

---

### GET /api/v1/cad/analyses/{id}

CAD 분석 결과 조회 (폴링).

- **인증**: 필요 — `admin`, `manager`, `sales`
- **Rate Limit**: Standard

**Response 200** (분석 완료)

```json
{
  "data": {
    "id": "cad_analysis_001",
    "status": "COMPLETED",
    "fileName": "bracket_v3.dxf",
    "analyzedAt": "2026-04-30T09:00:35Z",
    "confidence": 0.94,
    "objects": [
      {
        "objectId": "obj_001",
        "type": "PLATE",
        "material": "SUS304",
        "thickness": 3.0,
        "dimensions": { "width": 200, "height": 150, "unit": "mm" },
        "area": 30000,
        "areaUnit": "mm²",
        "processes": ["레이저 절단", "벤딩"],
        "quantity": 1,
        "confidence": 0.97
      },
      {
        "objectId": "obj_002",
        "type": "HOLE",
        "diameter": 8.5,
        "unit": "mm",
        "count": 4,
        "confidence": 0.99
      }
    ],
    "summary": {
      "totalObjects": 8,
      "estimatedProcesses": ["레이저 절단", "벤딩", "용접"],
      "materialSummary": [
        { "material": "SUS304", "thickness": "3T", "area": 30000 }
      ]
    }
  },
  "meta": { "requestId": "req_041", "timestamp": "2026-04-30T09:01:00Z" }
}
```

**Response 200** (분석 진행 중)

```json
{
  "data": {
    "id": "cad_analysis_001",
    "status": "PROCESSING",
    "progress": 65,
    "estimatedRemainingSeconds": 12
  },
  "meta": { "requestId": "req_041b", "timestamp": "2026-04-30T09:00:20Z" }
}
```

**Response 422**

```json
{
  "error": { "code": "CAD_CONFIDENCE_LOW", "message": "AI 인식 신뢰도가 기준(80%) 미달입니다. 수동 확인이 필요합니다.", "traceId": "trace_041" }
}
```

---

### PATCH /api/v1/cad/analyses/{id}/objects

CAD AI 인식 결과 수정.

- **인증**: 필요 — `admin`, `manager`, `sales`
- **Rate Limit**: Write

**Request Body**

```json
{
  "objects": [
    {
      "objectId": "obj_001",
      "material": "SUS316L",
      "thickness": 3.0,
      "processes": ["레이저 절단", "벤딩", "용접"],
      "quantity": 2
    }
  ]
}
```

**Response 200**

```json
{
  "data": {
    "id": "cad_analysis_001",
    "updatedObjects": ["obj_001"],
    "updatedAt": "2026-04-30T09:10:00Z"
  },
  "meta": { "requestId": "req_042", "timestamp": "2026-04-30T09:10:00Z" }
}
```

---

### POST /api/v1/estimates

견적 생성.

- **인증**: 필요 — `admin`, `manager`, `sales`
- **Rate Limit**: Write

**Request Body**

```json
{
  "customerId": "cust_001",
  "cadAnalysisId": "cad_analysis_001",
  "title": "브라켓 어셈블리 견적",
  "requestDate": "2026-04-30",
  "dueDate": "2026-05-07",
  "deliveryDate": "2026-05-31",
  "quantity": 500,
  "currency": "KRW",
  "notes": "긴급 견적 요청"
}
```

**Response 201**

```json
{
  "data": {
    "id": "est_001",
    "estimateNo": "EST-2026-04-001",
    "status": "DRAFT",
    "title": "브라켓 어셈블리 견적",
    "customerId": "cust_001",
    "customerName": "현대자동차(주)",
    "quantity": 500,
    "currency": "KRW",
    "dueDate": "2026-05-07",
    "createdBy": "usr_sales001",
    "createdAt": "2026-04-30T09:15:00Z"
  },
  "meta": { "requestId": "req_043", "timestamp": "2026-04-30T09:15:00Z" }
}
```

---

### GET /api/v1/estimates

견적 목록 조회.

- **인증**: 필요 — `admin`, `manager`, `sales`, `viewer`
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `status` | string | N | 상태 (DRAFT, SUBMITTED, APPROVED, REJECTED, CONFIRMED) |
| `customer_id` | string | N | 고객사 ID |
| `date_from` | date | N | 시작일 |
| `date_to` | date | N | 종료일 |
| `search` | string | N | 견적번호/제목 검색 |
| `page` | integer | N | 페이지 |
| `limit` | integer | N | 페이지 크기 |

**Response 200**

```json
{
  "data": [
    {
      "id": "est_001",
      "estimateNo": "EST-2026-04-001",
      "title": "브라켓 어셈블리 견적",
      "customerName": "현대자동차(주)",
      "status": "DRAFT",
      "quantity": 500,
      "totalAmount": null,
      "dueDate": "2026-05-07",
      "createdAt": "2026-04-30T09:15:00Z"
    }
  ],
  "pagination": { "total": 34, "page": 1, "limit": 20, "hasMore": true },
  "meta": { "requestId": "req_044", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### GET /api/v1/estimates/{id}

견적 상세 조회.

- **인증**: 필요 — `admin`, `manager`, `sales`, `viewer`
- **Rate Limit**: Standard

**Response 200**

```json
{
  "data": {
    "id": "est_001",
    "estimateNo": "EST-2026-04-001",
    "status": "DRAFT",
    "title": "브라켓 어셈블리 견적",
    "customer": { "id": "cust_001", "name": "현대자동차(주)", "code": "CUST-001" },
    "cadAnalysis": { "id": "cad_analysis_001", "fileName": "bracket_v3.dxf", "confidence": 0.94 },
    "quantity": 500,
    "currency": "KRW",
    "unitPrice": null,
    "totalAmount": null,
    "bom": null,
    "requestDate": "2026-04-30",
    "dueDate": "2026-05-07",
    "deliveryDate": "2026-05-31",
    "notes": "긴급 견적 요청",
    "createdBy": { "id": "usr_sales001", "name": "최영업" },
    "createdAt": "2026-04-30T09:15:00Z",
    "updatedAt": "2026-04-30T09:15:00Z"
  },
  "meta": { "requestId": "req_045", "timestamp": "2026-04-30T09:20:00Z" }
}
```

**Response 404**

```json
{
  "error": { "code": "ESTIMATE_NOT_FOUND", "message": "해당 견적을 찾을 수 없습니다.", "traceId": "trace_045" }
}
```

---

### POST /api/v1/estimates/{id}/bom/generate

BOM 자동 생성 (CAD 분석 기반 AI 생성).

- **인증**: 필요 — `admin`, `manager`, `sales`
- **Rate Limit**: Heavy (10 req/min)

**Request Body**

```json
{
  "includeTooling": true,
  "overheadRate": 0.15,
  "profitRate": 0.20
}
```

**Response 201**

```json
{
  "data": {
    "estimateId": "est_001",
    "bomId": "bom_001",
    "status": "GENERATED",
    "generatedAt": "2026-04-30T09:25:00Z",
    "items": [
      {
        "seq": 1,
        "itemCode": "MAT-SUS304-3T",
        "itemName": "SUS304 3T 원자재",
        "category": "MATERIAL",
        "unit": "kg",
        "quantity": 1.8,
        "unitPrice": 12000,
        "totalPrice": 21600
      },
      {
        "seq": 2,
        "itemCode": "PROC-LASER-CUT",
        "itemName": "레이저 절단 가공비",
        "category": "PROCESS",
        "unit": "min",
        "quantity": 8.5,
        "unitPrice": 3500,
        "totalPrice": 29750
      }
    ],
    "summary": {
      "materialCost": 21600,
      "processCost": 85000,
      "overheadCost": 16140,
      "profitMargin": 24548,
      "unitPrice": 147288,
      "totalAmount": 73644000
    }
  },
  "meta": { "requestId": "req_046", "timestamp": "2026-04-30T09:25:00Z" }
}
```

**Response 422**

```json
{
  "error": { "code": "ESTIMATE_LOCKED", "message": "수주 확정된 견적은 BOM을 재생성할 수 없습니다.", "traceId": "trace_046" }
}
```

---

### GET /api/v1/estimates/{id}/bom

BOM 조회.

- **인증**: 필요 — `admin`, `manager`, `sales`, `viewer`
- **Rate Limit**: Standard

**Response 200**

```json
{
  "data": {
    "estimateId": "est_001",
    "bomId": "bom_001",
    "version": 2,
    "generatedAt": "2026-04-30T09:25:00Z",
    "items": [
      {
        "seq": 1,
        "itemCode": "MAT-SUS304-3T",
        "itemName": "SUS304 3T 원자재",
        "category": "MATERIAL",
        "unit": "kg",
        "quantity": 1.8,
        "unitPrice": 12000,
        "totalPrice": 21600,
        "supplier": "한국특수강(주)"
      }
    ],
    "summary": {
      "materialCost": 21600,
      "processCost": 85000,
      "overheadCost": 16140,
      "profitMargin": 24548,
      "unitPrice": 147288,
      "totalAmount": 73644000,
      "currency": "KRW"
    }
  },
  "meta": { "requestId": "req_047", "timestamp": "2026-04-30T09:30:00Z" }
}
```

---

### PATCH /api/v1/estimates/{id}/status

견적 상태 변경 (수주 확정 등).

- **인증**: 필요 — `admin`, `manager`
- **Rate Limit**: Write

**Request Body**

```json
{
  "status": "CONFIRMED",
  "comment": "고객사 발주서 접수. 수주 확정.",
  "purchaseOrderNo": "PO-HYUNDAI-2026-1234",
  "confirmedAmount": 73644000
}
```

| 상태 전이 | 설명 |
|-----------|------|
| DRAFT → SUBMITTED | 견적 제출 |
| SUBMITTED → APPROVED | 내부 승인 |
| APPROVED → CONFIRMED | 수주 확정 (이후 수정 불가) |
| SUBMITTED → REJECTED | 반려 |

**Response 200**

```json
{
  "data": {
    "id": "est_001",
    "estimateNo": "EST-2026-04-001",
    "previousStatus": "APPROVED",
    "status": "CONFIRMED",
    "purchaseOrderNo": "PO-HYUNDAI-2026-1234",
    "confirmedAmount": 73644000,
    "confirmedAt": "2026-04-30T10:00:00Z",
    "confirmedBy": { "id": "usr_mgr001", "name": "박관리" }
  },
  "meta": { "requestId": "req_048", "timestamp": "2026-04-30T10:00:00Z" }
}
```

**Response 422**

```json
{
  "error": { "code": "ESTIMATE_LOCKED", "message": "이미 수주 확정된 견적입니다.", "traceId": "trace_048" }
}
```

---

## 설비 모니터링 (Equipment)

### 설비 상태 코드

| 코드 | 설명 |
|------|------|
| `RUNNING` | 가동 중 |
| `IDLE` | 대기 중 |
| `MAINTENANCE` | 점검 중 |
| `ERROR` | 오류/경보 |
| `OFFLINE` | 오프라인 |

---

### GET /api/v1/equipment

설비 목록 + 현재 상태 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `status` | string | N | 설비 상태 필터 |
| `category` | string | N | 설비 분류 (laser, press, welding 등) |
| `line` | string | N | 생산 라인 |

**Response 200**

```json
{
  "data": [
    {
      "id": "eq_laser_001",
      "code": "LASER-001",
      "name": "레이저 절단기 #1",
      "category": "laser",
      "line": "A라인",
      "status": "RUNNING",
      "currentLot": "LOT-2026-04-001",
      "operatingHours": 2345.5,
      "lastMaintenanceAt": "2026-04-15T08:00:00Z",
      "nextMaintenanceDue": "2026-05-15T08:00:00Z",
      "anomalyCount": 0,
      "availability": 0.932,
      "updatedAt": "2026-04-30T10:30:00Z"
    }
  ],
  "pagination": { "total": 18, "page": 1, "limit": 20, "hasMore": false },
  "meta": { "requestId": "req_050", "timestamp": "2026-04-30T10:30:00Z" }
}
```

---

### GET /api/v1/equipment/{id}/status

설비 실시간 상태 조회.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Response 200**

```json
{
  "data": {
    "equipmentId": "eq_laser_001",
    "code": "LASER-001",
    "name": "레이저 절단기 #1",
    "status": "RUNNING",
    "currentLot": {
      "id": "lot_abc001",
      "lotNumber": "LOT-2026-04-001",
      "processName": "레이저 절단",
      "startedAt": "2026-04-30T09:00:00Z",
      "progress": 67
    },
    "sensors": {
      "laserPower": { "value": 2485, "unit": "W", "status": "NORMAL" },
      "temperature": { "value": 43.1, "unit": "°C", "status": "NORMAL" },
      "vibration": { "value": 0.12, "unit": "mm/s", "status": "NORMAL" },
      "pressure": { "value": 6.8, "unit": "bar", "status": "NORMAL" }
    },
    "alarms": [],
    "updatedAt": "2026-04-30T10:30:05Z"
  },
  "meta": { "requestId": "req_051", "timestamp": "2026-04-30T10:30:05Z" }
}
```

**Response 503**

```json
{
  "error": { "code": "SENSOR_DATA_UNAVAILABLE", "message": "설비 센서 데이터를 수신할 수 없습니다. 네트워크 연결을 확인하세요.", "traceId": "trace_051" }
}
```

---

### GET /api/v1/equipment/{id}/sensor-history

설비 센서 이력 조회.

- **인증**: 필요 — `admin`, `manager`, `operator`
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `sensor` | string | N | 센서 종류 (temperature, vibration, power 등) |
| `date_from` | datetime | Y | 시작 시각 (ISO 8601) |
| `date_to` | datetime | Y | 종료 시각 (ISO 8601) |
| `interval` | string | N | 집계 간격 (1m, 5m, 1h, 1d) |

**Response 200**

```json
{
  "data": {
    "equipmentId": "eq_laser_001",
    "sensor": "temperature",
    "interval": "5m",
    "records": [
      { "timestamp": "2026-04-30T09:00:00Z", "value": 38.2, "unit": "°C", "status": "NORMAL" },
      { "timestamp": "2026-04-30T09:05:00Z", "value": 40.1, "unit": "°C", "status": "NORMAL" },
      { "timestamp": "2026-04-30T09:10:00Z", "value": 43.1, "unit": "°C", "status": "NORMAL" }
    ],
    "statistics": {
      "min": 38.2,
      "max": 52.3,
      "avg": 42.8,
      "stddev": 3.2
    }
  },
  "pagination": { "total": 288, "page": 1, "limit": 20, "hasMore": true },
  "meta": { "requestId": "req_052", "timestamp": "2026-04-30T10:35:00Z" }
}
```

---

### GET /api/v1/equipment/anomalies

이상 감지 목록 조회 (AI 기반).

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `equipment_id` | string | N | 설비 ID |
| `severity` | string | N | 심각도 (INFO, WARNING, CRITICAL) |
| `status` | string | N | 처리 상태 (ACTIVE, ACKNOWLEDGED, RESOLVED) |
| `date_from` | datetime | N | 시작 시각 |
| `date_to` | datetime | N | 종료 시각 |
| `page` | integer | N | 페이지 |
| `limit` | integer | N | 페이지 크기 |

**Response 200**

```json
{
  "data": [
    {
      "id": "anomaly_001",
      "equipmentId": "eq_laser_001",
      "equipmentName": "레이저 절단기 #1",
      "anomalyType": "TEMPERATURE_SPIKE",
      "severity": "WARNING",
      "description": "냉각수 온도 이상 상승 감지 (기준 50°C 초과)",
      "detectedValue": 52.3,
      "threshold": 50.0,
      "unit": "°C",
      "status": "ACTIVE",
      "detectedAt": "2026-04-30T10:15:00Z",
      "aiConfidence": 0.91
    }
  ],
  "pagination": { "total": 5, "page": 1, "limit": 20, "hasMore": false },
  "meta": { "requestId": "req_053", "timestamp": "2026-04-30T10:40:00Z" }
}
```

---

### PATCH /api/v1/equipment/{id}/status

설비 상태 수동 변경.

- **인증**: 필요 — `admin`, `manager`
- **Rate Limit**: Write

**Request Body**

```json
{
  "status": "MAINTENANCE",
  "reason": "정기 예방 점검",
  "estimatedDuration": 120,
  "assignedTo": "usr_maint001"
}
```

**Response 200**

```json
{
  "data": {
    "equipmentId": "eq_laser_001",
    "previousStatus": "IDLE",
    "status": "MAINTENANCE",
    "reason": "정기 예방 점검",
    "estimatedDuration": 120,
    "changedAt": "2026-04-30T11:00:00Z",
    "changedBy": { "id": "usr_mgr001", "name": "박관리" }
  },
  "meta": { "requestId": "req_054", "timestamp": "2026-04-30T11:00:00Z" }
}
```

**Response 404**

```json
{
  "error": { "code": "EQUIPMENT_NOT_FOUND", "message": "해당 설비를 찾을 수 없습니다.", "traceId": "trace_054" }
}
```

---

## 데이터허브 & AI (Hub)

### GET /api/v1/hub/search

통합 데이터 검색.

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `query` | string | Y | 검색어 |
| `types` | string | N | 데이터 유형 쉼표 구분 (lot,process,quality,estimate,equipment) |
| `date_from` | date | N | 날짜 범위 시작 |
| `date_to` | date | N | 날짜 범위 종료 |
| `page` | integer | N | 페이지 |
| `limit` | integer | N | 페이지 크기 (기본 20) |

**Response 200**

```json
{
  "data": [
    {
      "type": "lot",
      "id": "lot_abc001",
      "title": "LOT-2026-04-001",
      "description": "SUS304 스테인리스강판 3T — 입고 2026-04-30",
      "status": "IN_PROCESS",
      "relevanceScore": 0.98,
      "url": "/api/v1/lots/lot_abc001"
    },
    {
      "type": "quality",
      "id": "insp_001",
      "title": "LOT-2026-04-001 공정검사",
      "description": "공정검사 PASS — 2026-04-30",
      "relevanceScore": 0.85,
      "url": "/api/v1/quality/inspections/insp_001"
    }
  ],
  "pagination": { "total": 7, "page": 1, "limit": 20, "hasMore": false },
  "meta": { "requestId": "req_060", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### GET /api/v1/hub/export

데이터 다운로드.

- **인증**: 필요 — `admin`, `manager`, `viewer`
- **Rate Limit**: Export (5 req/min)

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `type` | string | Y | 데이터 유형 (lots, process-results, inspections, claims) |
| `format` | string | Y | 파일 형식 (xlsx, csv) |
| `date_from` | date | N | 시작일 |
| `date_to` | date | N | 종료일 |
| `filters` | string | N | 추가 필터 (JSON 인코딩) |

**Response 200**

응답은 파일 스트림으로 반환.

```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="lots_2026-04.xlsx"
```

**Response 429**

```json
{
  "error": { "code": "RATE_LIMIT_EXCEEDED", "message": "다운로드 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.", "traceId": "trace_061" },
  "retryAfter": 60
}
```

---

### POST /api/v1/hub/ai-query

AI 자연어 질의 (Server-Sent Events 스트리밍).

- **인증**: 필요 — 모든 역할
- **Rate Limit**: Heavy (10 req/min)
- **Response Content-Type**: `text/event-stream`

**Request Body**

```json
{
  "question": "이번 달 레이저 절단 공정의 불량률이 가장 높은 날은 언제이고 원인은 무엇인가요?",
  "context": {
    "dateFrom": "2026-04-01",
    "dateTo": "2026-04-30"
  },
  "stream": true
}
```

**Response 200** (SSE 스트림)

```
data: {"type":"start","queryId":"aiquery_001","timestamp":"2026-04-30T09:00:00Z"}

data: {"type":"thinking","content":"2026년 4월 레이저 절단 공정 데이터를 분석 중입니다..."}

data: {"type":"data_fetch","source":"process_results","count":120}

data: {"type":"content","content":"2026년 4월 레이저 절단 공정 분석 결과:\n\n**가장 높은 불량률 날짜**: 4월 17일 (불량률 4.8%)\n\n**주요 원인**:\n1. 레이저 출력 불안정 (LASER-001, 오전 10시~12시)\n2. 보조가스(N2) 압력 저하 감지\n\n**권고사항**: LASER-001 노즐 청소 및 가스 라인 점검 필요"}

data: {"type":"sources","items":[{"type":"process_result","id":"result_045","date":"2026-04-17"}]}

data: {"type":"end","queryId":"aiquery_001"}
```

---

### GET /api/v1/hub/ai-query/history

AI 질의 이력 조회.

- **인증**: 필요 — 모든 역할 (본인 이력만, admin은 전체)
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `page` | integer | N | 페이지 |
| `limit` | integer | N | 페이지 크기 |
| `date_from` | date | N | 시작일 |

**Response 200**

```json
{
  "data": [
    {
      "id": "aiquery_001",
      "question": "이번 달 레이저 절단 공정의 불량률이 가장 높은 날은 언제이고 원인은 무엇인가요?",
      "summary": "4월 17일 불량률 4.8% 최고, 레이저 출력 불안정 원인",
      "askedBy": { "id": "usr_mgr001", "name": "박관리" },
      "askedAt": "2026-04-30T09:00:00Z",
      "duration": 8.3
    }
  ],
  "pagination": { "total": 23, "page": 1, "limit": 20, "hasMore": true },
  "meta": { "requestId": "req_063", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### GET /api/v1/kpi/productivity

생산성 KPI 조회.

- **인증**: 필요 — `admin`, `manager`, `viewer`
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `date_from` | date | Y | 시작일 |
| `date_to` | date | Y | 종료일 |
| `group_by` | string | N | 집계 단위 (day, week, month) |
| `process_id` | string | N | 특정 공정 필터 |

**Response 200**

```json
{
  "data": {
    "period": { "from": "2026-04-01", "to": "2026-04-30" },
    "summary": {
      "oee": 0.847,
      "availability": 0.932,
      "performance": 0.912,
      "quality": 0.985,
      "totalProductionQty": 58800,
      "targetQty": 60000,
      "achievementRate": 0.98,
      "avgCycleTime": 118.5,
      "targetCycleTime": 120
    },
    "trend": [
      { "date": "2026-04-01", "oee": 0.843, "productionQty": 1960 },
      { "date": "2026-04-02", "oee": 0.851, "productionQty": 2010 }
    ],
    "byProcess": [
      { "processId": "proc_laser_001", "processName": "레이저 절단", "oee": 0.891, "avgYieldRate": 0.98 }
    ]
  },
  "meta": { "requestId": "req_064", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### GET /api/v1/kpi/quality

품질 KPI 조회.

- **인증**: 필요 — `admin`, `manager`, `viewer`
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `date_from` | date | Y | 시작일 |
| `date_to` | date | Y | 종료일 |
| `group_by` | string | N | 집계 단위 |

**Response 200**

```json
{
  "data": {
    "period": { "from": "2026-04-01", "to": "2026-04-30" },
    "summary": {
      "overallPassRate": 0.985,
      "totalInspections": 240,
      "passCount": 236,
      "failCount": 4,
      "defectRate": 0.015,
      "claimCount": 2,
      "claimRate": 0.003,
      "costOfQuality": 1250000
    },
    "byInspectionType": [
      { "type": "수입검사", "passRate": 0.991, "count": 45 },
      { "type": "공정검사", "passRate": 0.987, "count": 180 },
      { "type": "출하검사", "passRate": 0.999, "count": 15 }
    ],
    "topDefects": [
      { "code": "DEF-001", "name": "치수불량", "count": 45, "ratio": 0.52 },
      { "code": "DEF-002", "name": "표면스크래치", "count": 28, "ratio": 0.32 }
    ],
    "trend": [
      { "date": "2026-04-01", "passRate": 0.982, "defectRate": 0.018 }
    ]
  },
  "meta": { "requestId": "req_065", "timestamp": "2026-04-30T09:00:00Z" }
}
```

---

### GET /api/v1/dashboard/overview

경영진 종합 현황 대시보드.

- **인증**: 필요 — `admin`, `manager`, `viewer`
- **Rate Limit**: Standard

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `date` | date | N | 기준일 (기본: 오늘) |

**Response 200**

```json
{
  "data": {
    "asOf": "2026-04-30T10:45:00Z",
    "production": {
      "todayTarget": 2400,
      "todayActual": 1920,
      "achievementRate": 0.80,
      "activeLots": 12,
      "completedLotsToday": 5,
      "monthlyOee": 0.847
    },
    "quality": {
      "todayPassRate": 0.988,
      "activeClaims": 3,
      "pendingInspections": 7
    },
    "equipment": {
      "total": 18,
      "running": 14,
      "idle": 2,
      "maintenance": 1,
      "error": 1,
      "activeAnomalies": 2,
      "availabilityRate": 0.932
    },
    "estimates": {
      "pendingCount": 8,
      "confirmedThisMonth": 23,
      "confirmedAmountThisMonth": 1850000000
    },
    "alerts": [
      {
        "id": "alert_001",
        "severity": "WARNING",
        "type": "EQUIPMENT_ANOMALY",
        "message": "레이저 절단기 #1 온도 이상 감지",
        "timestamp": "2026-04-30T10:15:00Z",
        "url": "/api/v1/equipment/eq_laser_001/status"
      }
    ]
  },
  "meta": { "requestId": "req_066", "timestamp": "2026-04-30T10:45:00Z" }
}
```

---

## 공통 에러 응답 참조

### 401 Unauthorized

```json
{
  "error": { "code": "AUTH_REQUIRED", "message": "인증이 필요합니다.", "traceId": "trace_xxx" }
}
```

### 403 Forbidden

```json
{
  "error": { "code": "INSUFFICIENT_PERMISSION", "message": "해당 작업을 수행할 권한이 없습니다.", "traceId": "trace_xxx" }
}
```

### 422 Unprocessable Entity

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 데이터 유효성 검사에 실패했습니다.",
    "traceId": "trace_xxx",
    "fields": [
      { "field": "quantity", "message": "0보다 큰 값을 입력해야 합니다." }
    ]
  }
}
```

### 500 Internal Server Error

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "traceId": "trace_xxx"
  }
}
```

---

*본 문서는 원터치(Onetouch) AI+MES 시스템 v1.0 기준으로 작성되었습니다.*
