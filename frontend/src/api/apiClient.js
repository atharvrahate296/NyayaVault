/**
 * NyayaVault API Client
 * Connects frontend directly to FastAPI backend (/api/v1)
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

let authToken = localStorage.getItem('nyayavault_token') || null;

export function setAuthToken(token) {
  authToken = token;
  if (token) {
    localStorage.setItem('nyayavault_token', token);
  } else {
    localStorage.removeItem('nyayavault_token');
  }
}

export function getAuthToken() {
  return authToken;
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    ...options.headers,
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  // If body is not FormData, add JSON content-type
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      const message = errJson?.error?.message || errJson?.detail || `Request failed with status ${res.status}`;
      const err = new Error(message);
      err.status = res.status;
      err.data = errJson;
      throw err;
    }

    // If not JSON, treat as a binary/blob response (images, video, audio, pdf, etc.)
    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      return await res.blob();
    }

    return await res.json();

    return await res.json();
  } catch (error) {
    console.error(`API Error on [${options.method || 'GET'} ${endpoint}]:`, error);
    throw error;
  }
}

export const api = {
  // 1. Auth & Profile
  login: (email, password) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  signup: (registrationData) =>
    request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(registrationData),
    }),
  getMe: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),
  getRegistrationRequests: (status = 'PENDING') =>
    request(`/auth/registration-requests?request_status=${encodeURIComponent(status)}`),
  approveRegistrationRequest: (id) =>
    request(`/auth/registration-requests/${id}/approve`, { method: 'POST' }),
  rejectRegistrationRequest: (id, reason) =>
    request(`/auth/registration-requests/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  // 2. Cases
  getCases: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/cases${qs ? `?${qs}` : ''}`);
  },
  getCase: (id) => request(`/cases/${id}`),
  createCase: (caseData) =>
    request('/cases', {
      method: 'POST',
      body: JSON.stringify(caseData),
    }),
  updateCase: (id, updateData) =>
    request(`/cases/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updateData),
    }),
  assignCaseOfficer: (id, userId, roleInCase) =>
    request(`/cases/${id}/assign`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, role_in_case: roleInCase }),
    }),
  getCaseDocuments: (id) => request(`/cases/${id}/documents`),
  getCaseEvidence: (id) => request(`/cases/${id}/evidence`),
  getCaseActivity: (id) => request(`/cases/${id}/activity`),

  // 3. Documents
  getDocuments: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/documents${qs ? `?${qs}` : ''}`);
  },
  getDocument: (id) => request(`/documents/${id}`),
  uploadDocument: (formData) =>
    request('/documents', {
      method: 'POST',
      body: formData,
    }),
  getDocumentVersions: (id) => request(`/documents/${id}/versions`),
  uploadNewVersion: (id, formData) =>
    request(`/documents/${id}/versions`, {
      method: 'POST',
      body: formData,
    }),
  downloadDocument: (id, versionId = null) =>
    request(`/documents/${id}/download${versionId ? `?version_id=${versionId}` : ''}`),
  createDocumentDownloadUrl: (id, versionId = null) =>
    request(`/documents/${id}/download-url${versionId ? `?version_id=${versionId}` : ''}`),

  // 4. Integrity & Blockchain
  getIntegrity: (versionId) => request(`/integrity/${versionId}`),
  verifyIntegrity: (versionId) =>
    request(`/integrity/verify/${versionId}`, { method: 'POST' }),
  simulateTamper: (versionId) =>
    request(`/integrity/simulate-tamper/${versionId}`, { method: 'POST' }),
  restoreIntegrity: (versionId) =>
    request(`/integrity/restore/${versionId}`, { method: 'POST' }),
  getBlockchainTransactions: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/blockchain/transactions${qs ? `?${qs}` : ''}`);
  },
  getBlockchainRecord: (versionId) => request(`/blockchain/records/${versionId}`),

  // 5. Evidence & Chain of Custody
  getEvidence: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/evidence${qs ? `?${qs}` : ''}`);
  },
  getEvidenceDetail: (id) => request(`/evidence/${id}`),
  createEvidence: (evidenceData) =>
    request('/evidence', {
      method: 'POST',
      body: JSON.stringify(evidenceData),
    }),
  transferEvidence: (id, transferData) =>
    request(`/evidence/${id}/transfer`, {
      method: 'POST',
      body: JSON.stringify(transferData),
    }),
  getEvidenceCustody: (id) => request(`/evidence/${id}/custody`),

  // 6. Certificates
  getCertificates: () => request('/certificates'),
  generateCertificate: (certData) =>
    request('/certificates/generate', {
      method: 'POST',
      body: JSON.stringify(certData),
    }),
  downloadCertificate: (certId) => request(`/certificates/${certId}/download`),
  createCertificateDownloadUrl: (certId) => request(`/certificates/${certId}/download-url`),

  // 7. AI & Search
  search: (q, mode = 'hybrid', filters = {}) => {
    const params = new URLSearchParams({ q, mode, ...filters }).toString();
    return request(`/search?${params}`);
  },
  getPendingAIReviews: () => request('/ai/reviews/pending'),
  getDocumentAIExtractions: (docId) => request(`/ai/extractions/${docId}`),
  submitAIReview: (extractionId, reviewData) =>
    request(`/ai/review/${extractionId}`, {
      method: 'POST',
      body: JSON.stringify(reviewData),
    }),

  // 8. Signatures
  getSignatures: (resourceId) => request(`/signatures/${resourceId}`),
  signResource: (signData) =>
    request('/signatures', {
      method: 'POST',
      body: JSON.stringify(signData),
    }),
  verifySignature: (signatureId, expectedHash) =>
    request('/signatures/verify', {
      method: 'POST',
      body: JSON.stringify({ signature_id: signatureId, expected_hash: expectedHash }),
    }),

  // 9. Audit & Security
  getAuditTrail: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/audit${qs ? `?${qs}` : ''}`);
  },
  verifyAuditChain: () => request('/audit/verify-chain'),
  getSecurityEvents: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/security/events${qs ? `?${qs}` : ''}`);
  },
  getSecurityAlerts: (status = null) =>
    request(`/security/alerts${status ? `?status=${status}` : ''}`),
  resolveSecurityAlert: (alertId, notes = '') =>
    request(`/security/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    }),

  // 10. Notifications
  getNotifications: () => request('/notifications'),
  markNotificationRead: (id) =>
    request(`/notifications/${id}/read`, { method: 'PATCH' }),
  markAllNotificationsRead: () =>
    request('/notifications/read-all', { method: 'POST' }),

  // 11. Access Control & RBAC / ABAC
  getRoles: () => request('/roles'),
  getPermissions: () => request('/permissions'),
  updateRolePermissions: (roleName, permissions) =>
    request(`/roles/${encodeURIComponent(roleName)}/permissions`, {
      method: 'POST',
      body: JSON.stringify({ permissions }),
    }),
  getPolicies: () => request('/policies'),
  evaluatePolicy: (evalData) =>
    request('/policies/evaluate', {
      method: 'POST',
      body: JSON.stringify(evalData),
    }),

  // 12. Analytics & Health
  getDashboardAnalytics: () => request('/analytics/dashboard'),
  getOperationalAnalytics: (windowDays = 30, options = {}) =>
    request(`/analytics/operational?window_days=${windowDays}`, options),
  getHealth: () => request('/health'),
};
