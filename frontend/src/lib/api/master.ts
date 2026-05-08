import apiClient from './client'
import type {
  Supplier,
  Customer,
  RawMaterial,
  ProcessTypeRecord,
  EquipmentRecord,
  PaginatedResponse,
} from '@/types'

// ============================================================
// 기준정보 API 함수들
// ============================================================

export interface ListParams {
  page?: number
  limit?: number
  search?: string
  is_active?: boolean
}

// Suppliers (공급업체)
export const suppliersApi = {
  list: (params?: ListParams & { grade?: string }) =>
    apiClient
      .get<PaginatedResponse<Supplier>>('/api/v1/master/suppliers', { params })
      .then((r) => r.data),
  get: (id: string) =>
    apiClient
      .get<Supplier>(`/api/v1/master/suppliers/${id}`)
      .then((r) => r.data),
  create: (body: Partial<Supplier>) =>
    apiClient
      .post<Supplier>('/api/v1/master/suppliers', body)
      .then((r) => r.data),
  update: (id: string, body: Partial<Supplier>) =>
    apiClient
      .patch<Supplier>(`/api/v1/master/suppliers/${id}`, body)
      .then((r) => r.data),
  deactivate: (id: string) =>
    apiClient.delete(`/api/v1/master/suppliers/${id}`),
}

// Customers (고객사)
export const customersApi = {
  list: (params?: ListParams) =>
    apiClient
      .get<PaginatedResponse<Customer>>('/api/v1/master/customers', { params })
      .then((r) => r.data),
  get: (id: string) =>
    apiClient
      .get<Customer>(`/api/v1/master/customers/${id}`)
      .then((r) => r.data),
  create: (body: Partial<Customer>) =>
    apiClient
      .post<Customer>('/api/v1/master/customers', body)
      .then((r) => r.data),
  update: (id: string, body: Partial<Customer>) =>
    apiClient
      .patch<Customer>(`/api/v1/master/customers/${id}`, body)
      .then((r) => r.data),
}

// Raw Materials (원자재)
export const materialsApi = {
  list: (params?: ListParams & { category?: string; supplier_id?: string }) =>
    apiClient
      .get<PaginatedResponse<RawMaterial>>('/api/v1/master/materials', {
        params,
      })
      .then((r) => r.data),
  get: (id: string) =>
    apiClient
      .get<RawMaterial>(`/api/v1/master/materials/${id}`)
      .then((r) => r.data),
  create: (body: Partial<RawMaterial>) =>
    apiClient
      .post<RawMaterial>('/api/v1/master/materials', body)
      .then((r) => r.data),
  update: (id: string, body: Partial<RawMaterial>) =>
    apiClient
      .patch<RawMaterial>(`/api/v1/master/materials/${id}`, body)
      .then((r) => r.data),
}

// Process Types (공정유형)
export const processTypesApi = {
  list: (params?: ListParams & { process_type?: string }) =>
    apiClient
      .get<PaginatedResponse<ProcessTypeRecord>>('/api/v1/master/processes', {
        params,
      })
      .then((r) => r.data),
  get: (id: string) =>
    apiClient
      .get<ProcessTypeRecord>(`/api/v1/master/processes/${id}`)
      .then((r) => r.data),
  create: (body: Partial<ProcessTypeRecord>) =>
    apiClient
      .post<ProcessTypeRecord>('/api/v1/master/processes', body)
      .then((r) => r.data),
  update: (id: string, body: Partial<ProcessTypeRecord>) =>
    apiClient
      .patch<ProcessTypeRecord>(`/api/v1/master/processes/${id}`, body)
      .then((r) => r.data),
}

// Equipment (설비)
export const equipmentApi = {
  list: (params?: ListParams & { status?: string; process_id?: string }) =>
    apiClient
      .get<PaginatedResponse<EquipmentRecord>>('/api/v1/master/equipment', {
        params,
      })
      .then((r) => r.data),
  get: (id: string) =>
    apiClient
      .get<EquipmentRecord>(`/api/v1/master/equipment/${id}`)
      .then((r) => r.data),
  create: (body: Partial<EquipmentRecord>) =>
    apiClient
      .post<EquipmentRecord>('/api/v1/master/equipment', body)
      .then((r) => r.data),
  update: (id: string, body: Partial<EquipmentRecord>) =>
    apiClient
      .patch<EquipmentRecord>(`/api/v1/master/equipment/${id}`, body)
      .then((r) => r.data),
  updateStatus: (id: string, status: string, reason?: string) =>
    apiClient
      .patch<EquipmentRecord>(`/api/v1/master/equipment/${id}/status`, {
        status,
        reason,
      })
      .then((r) => r.data),
}
