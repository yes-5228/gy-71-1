import { request } from './http'

export function fetchContracts(status = '') {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return request(`/contracts${query}`)
}

export function fetchContract(id) {
  return request(`/contracts/${id}`)
}

export function createContract(payload) {
  return request('/contracts', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateContract(id, payload) {
  return request(`/contracts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

export function renewContract(id, payload) {
  return request(`/contracts/${id}/renew`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function fetchRenewalHistory(id) {
  return request(`/contracts/${id}/renewal-history`)
}
