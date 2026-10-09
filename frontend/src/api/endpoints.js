import api, { setToken } from './client.js'

export const authApi = {
  login: async (username, password) => {
    const res = await api.post('/api/v1/auth/login', { username, password })
    if (res && res.access_token) {
      setToken(res.access_token)
    }
    return res
  },
  getMe: () => api.get('/api/v1/auth/me'),
  logout: () => {
    setToken(null)
  },
}

export const mastersApi = {
  // Customers
  getCustomers: (params) => api.get('/api/v1/customers', { params }),
  createCustomer: (data) => api.post('/api/v1/customers', data),
  updateCustomer: (id, data) => api.put(`/api/v1/customers/${id}`, data),
  deleteCustomer: (id) => api.delete(`/api/v1/customers/${id}`),
  toggleCustomer: (id) => api.patch(`/api/v1/customers/${id}/toggle-status`),

  // Suppliers
  getSuppliers: (params) => api.get('/api/v1/suppliers', { params }),
  createSupplier: (data) => api.post('/api/v1/suppliers', data),
  updateSupplier: (id, data) => api.put(`/api/v1/suppliers/${id}`, data),
  toggleSupplier: (id) => api.patch(`/api/v1/suppliers/${id}/toggle-status`),

  // Items
  getItems: (params) => api.get('/api/v1/items', { params }),
  createItem: (data) => api.post('/api/v1/items', data),
  updateItem: (id, data) => api.put(`/api/v1/items/${id}`, data),
  toggleItem: (id) => api.patch(`/api/v1/items/${id}/toggle-status`),
}

export const salesApi = {
  // 01. Customer Request
  getCustomerRequests: (params) => api.get('/api/v1/sales/customer-request', { params }),
  getCustomerRequestById: (id) => api.get(`/api/v1/sales/customer-request/${id}`),
  createCustomerRequest: (data) => api.post('/api/v1/sales/customer-request', data),
  updateCustomerRequest: (id, data) => api.put(`/api/v1/sales/customer-request/${id}`, data),

  // 05. Customer Quotation
  getCustomerQuotations: (params) => api.get('/api/v1/sales/quotation', { params }),
  getCustomerQuotationById: (id) => api.get(`/api/v1/sales/quotation/${id}`),
  createQuotationFromComparison: (comparisonId) => api.post(`/api/v1/sales/quotation/create-from-comparison/${comparisonId}`),
  updateCustomerQuotation: (id, data) => api.put(`/api/v1/sales/quotation/${id}`, data),
  sendCustomerQuotation: (data) => api.post('/api/v1/sales/quotation/send', data),
  acceptCustomerQuotation: (id) => api.patch(`/api/v1/sales/quotation/${id}/accept`),
  rejectCustomerQuotation: (id) => api.patch(`/api/v1/sales/quotation/${id}/reject`),
  resendCustomerQuotation: (id, data) => api.post(`/api/v1/sales/quotation/${id}/resend`, data),

  // 06. Customer PO (Sales Order)
  getCustomerOrders: (params) => api.get('/api/v1/sales/customer-order', { params }),
  getCustomerOrderById: (id) => api.get(`/api/v1/sales/customer-order/${id}`),
  createCustomerOrder: (data) => api.post('/api/v1/sales/customer-order', data),

  // 10. Outward (Delivery Challan)
  getOutwards: (params) => api.get('/api/v1/sales/outward', { params }),
  getOutwardById: (id) => api.get(`/api/v1/sales/outward/${id}`),
  createOutward: (data) => api.post('/api/v1/sales/outward', data),

  // 11. Sales Invoice
  getSalesInvoices: (params) => api.get('/api/v1/sales/invoices', { params }),
  getSalesInvoiceById: (id) => api.get(`/api/v1/sales/invoices/${id}`),
  createSalesInvoice: (data) => api.post('/api/v1/sales/invoices', data),
}

export const purchaseApi = {
  // 02. Purchase Request
  getPurchaseRequests: (params) => api.get('/api/v1/purchase/request', { params }),
  getPurchaseRequestById: (id) => api.get(`/api/v1/purchase/request/${id}`),
  sendRFQ: (data) => api.post('/api/v1/purchase/rfq/send', data),

  // 03. Vendor Quotation
  getVendorQuotations: (params) => api.get('/api/v1/purchase/vendor-quotation', { params }),
  getVendorQuotationById: (id) => api.get(`/api/v1/purchase/vendor-quotation/${id}`),
  createVendorQuotation: (data) => api.post('/api/v1/purchase/vendor-quotation', data),

  // 04. Comparison
  getComparison: (prId) => api.get(`/api/v1/purchase/compare/${prId}`),
  approveComparison: (prId, data) => api.post(`/api/v1/purchase/compare/${prId}/approve`, data),

  // 07. Supplier Purchase Order
  getPurchaseOrders: (params) => api.get('/api/v1/purchase/purchase-order', { params }),
  getPurchaseOrderById: (id) => api.get(`/api/v1/purchase/purchase-order/${id}`),
  sendPurchaseOrder: (id, data) => api.post(`/api/v1/purchase/purchase-order/${id}/send`, data),

  // 08. GRN
  getGRNs: (params) => api.get('/api/v1/purchase/grn', { params }),
  getGRNById: (id) => api.get(`/api/v1/purchase/grn/${id}`),
  createGRN: (data) => api.post('/api/v1/purchase/grn', data),

  // 09. Inward
  getInwards: (params) => api.get('/api/v1/purchase/inward', { params }),
  getInwardById: (id) => api.get(`/api/v1/purchase/inward/${id}`),
  inwardStock: (id) => api.post(`/api/v1/purchase/inward/${id}/add`),

  // 12. Purchase Invoice
  getPurchaseInvoices: (params) => api.get('/api/v1/purchase/invoices', { params }),
  getPurchaseInvoiceById: (id) => api.get(`/api/v1/purchase/invoices/${id}`),
  createPurchaseInvoice: (data) => api.post('/api/v1/purchase/invoices', data),
}

export const analyticsApi = {
  getInventorySummary: () => api.get('/api/v1/inventory/summary'),
  getStockLedger: () => api.get('/api/v1/inventory/ledger'),
  getDashboardSummary: () => api.get('/api/v1/dashboard/summary'),
  getEmailLogs: (params) => api.get('/api/v1/email-logs', { params }),
  getOrderTracking: (crId) => api.get(`/api/v1/track/${crId}`),
}

/**
 * Fetch all ERP collections from the backend in parallel.
 * Maps backend responses cleanly to the frontend state structure.
 */
export async function fetchAllBackendData() {
  const [
    customersRes,
    suppliersRes,
    itemsRes,
    crRes,
    prRes,
    vqRes,
    cqRes,
    soRes,
    poRes,
    grnRes,
    inwRes,
    outRes,
    siRes,
    piRes,
    invRes,
    emailRes,
    ledgerRes,
  ] = await Promise.allSettled([
    mastersApi.getCustomers({ limit: 500 }),
    mastersApi.getSuppliers({ limit: 500 }),
    mastersApi.getItems({ limit: 500 }),
    salesApi.getCustomerRequests({ limit: 500 }),
    purchaseApi.getPurchaseRequests({ limit: 500 }),
    purchaseApi.getVendorQuotations({ limit: 500 }),
    salesApi.getCustomerQuotations({ limit: 500 }),
    salesApi.getCustomerOrders({ limit: 500 }),
    purchaseApi.getPurchaseOrders({ limit: 500 }),
    purchaseApi.getGRNs({ limit: 500 }),
    purchaseApi.getInwards({ limit: 500 }),
    salesApi.getOutwards({ limit: 500 }),
    salesApi.getSalesInvoices({ limit: 500 }),
    purchaseApi.getPurchaseInvoices({ limit: 500 }),
    analyticsApi.getInventorySummary(),
    analyticsApi.getEmailLogs({ limit: 100 }),
    analyticsApi.getStockLedger(),
  ])

  const unbox = (res) => {
    if (res.status === 'fulfilled' && res.value) {
      if (Array.isArray(res.value)) return res.value
      if (Array.isArray(res.value.items)) return res.value.items
      if (Array.isArray(res.value.customers)) return res.value.customers
      if (Array.isArray(res.value.suppliers)) return res.value.suppliers
      if (Array.isArray(res.value.logs)) return res.value.logs
      return res.value
    }
    return []
  }

  return {
    customers: unbox(customersRes),
    suppliers: unbox(suppliersRes),
    items: unbox(itemsRes),
    customerRequests: unbox(crRes),
    purchaseRequests: unbox(prRes),
    vendorQuotations: unbox(vqRes),
    customerQuotations: unbox(cqRes),
    salesOrders: unbox(soRes),
    purchaseOrders: unbox(poRes),
    grns: unbox(grnRes),
    inwards: unbox(inwRes),
    outwards: unbox(outRes),
    salesInvoices: unbox(siRes),
    purchaseInvoices: unbox(piRes),
    inventory: unbox(invRes),
    emailLog: unbox(emailRes),
    ledger: unbox(ledgerRes),
  }
}

export const emailApi = {
  sendLiveEmail: (data) => api.post('/api/v1/email-logs/send-live', data),
}

