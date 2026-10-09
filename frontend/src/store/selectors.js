import { crMargin } from '../logic/stock.js'

const by = (arr, id) => (Array.isArray(arr) ? arr.find((x) => x && (x.id === id || (id != null && String(x.id) === String(id)))) : null)

export const getCustomer = (s, id) => by(s.customers, id)
export const getSupplier = (s, id) => by(s.suppliers, id)
export const getItem = (s, id) => by(s.items, id)
export const getCR = (s, id) => by(s.customerRequests, id)

export const customerName = (s, id) => (getCustomer(s, id) || {}).name || '—'
export const supplierName = (s, id) => (getSupplier(s, id) || {}).name || '—'
export const itemName = (s, id) => (getItem(s, id) || {}).name || '—'
export const itemCode = (s, id) => (getItem(s, id) || {}).code || '—'
export const itemUnit = (s, id) => (getItem(s, id) || {}).unit || ''
export const crNo = (s, id) => (getCR(s, id) || {}).crNo || '—'

export const prByCr = (s, crId) => (s.purchaseRequests || []).find((p) => p.crId === crId || (crId != null && String(p.crId) === String(crId)))
export const crOfPr = (s, prId) => {
  const pr = by(s.purchaseRequests, prId)
  return pr ? getCR(s, pr.crId) : null
}
export const vqsOfPr = (s, prId) => (s.vendorQuotations || []).filter((v) => v.prId === prId || (prId != null && String(v.prId) === String(prId)))
export const qcOfPr = (s, prId) => (s.quotationComparisons || []).find((q) => q.prId === prId || (prId != null && String(q.prId) === String(prId)))

export const activeCustomers = (s) => s.customers.filter((c) => c.active)
export const activeSuppliers = (s) => s.suppliers.filter((c) => c.active)
export const activeItems = (s) => s.items.filter((c) => c.active)

/** Everything linked to one Customer Request — powers the Track timeline. */
export function crChain(s, crId) {
  if (!s) return { margin: { margin: 0, salesValue: 0, purchaseValue: 0 } }
  const eq = (a, b) => a === b || (a != null && b != null && String(a) === String(b))
  const pr = (s.purchaseRequests || []).find((x) => x && eq(x.crId, crId))
  return {
    cr: getCR(s, crId),
    pr,
    vqs: pr ? (s.vendorQuotations || []).filter((v) => v && eq(v.prId, pr.id)) : [],
    qc: pr ? (s.quotationComparisons || []).find((q) => q && eq(q.prId, pr.id)) : undefined,
    cqs: (s.customerQuotations || []).filter((x) => x && eq(x.crId, crId)),
    sos: (s.salesOrders || []).filter((x) => x && eq(x.crId, crId)),
    pos: (s.purchaseOrders || []).filter((x) => x && eq(x.crId, crId)),
    grns: (s.grns || []).filter((x) => x && eq(x.crId, crId)),
    inwards: (s.inwards || []).filter((x) => x && eq(x.crId, crId)),
    outwards: (s.outwards || []).filter((x) => x && eq(x.crId, crId)),
    salesInvoices: (s.salesInvoices || []).filter((x) => x && eq(x.crId, crId)),
    purchaseInvoices: (s.purchaseInvoices || []).filter((x) => x && eq(x.crId, crId)),
    margin: crMargin(s.stockLedger, crId),
  }
}

/** Counts of open documents per stage — the Dashboard. */
export function dashboardCounts(s) {
  if (!s) return {}
  const crs = (s.customerRequests || []).filter((x) => x && x.id)
  const prs = (s.purchaseRequests || []).filter((x) => x && x.id)
  const vqs = (s.vendorQuotations || []).filter((x) => x && x.id)
  const qcs = (s.quotationComparisons || []).filter((x) => x && x.id)
  const cqs = (s.customerQuotations || []).filter((x) => x && x.id)
  const pos = (s.purchaseOrders || []).filter((x) => x && x.id)
  const inws = (s.inwards || []).filter((x) => x && x.id)
  const sos = (s.salesOrders || []).filter((x) => x && x.id)
  const outs = (s.outwards || []).filter((x) => x && x.id)
  const grns = (s.grns || []).filter((x) => x && x.id)

  return {
    openRequests: crs.filter((x) => x.stage === 'Requested').length,
    awaitingRfq: prs.filter((x) => x.status === 'Open').length,
    awaitingQuotes: prs.filter((x) => x.status === 'RFQ Sent').length,
    toCompare: prs.filter(
      (p) =>
        p &&
        vqs.filter((v) => v && v.prId === p.id).length >= 2 &&
        !(qcs.find((q) => q && q.prId === p.id) || {}).approvedAt
    ).length,
    quotesOut: cqs.filter((x) => x.status === 'Sent').length,
    posToSend: pos.filter((x) => x.status === 'Draft').length,
    awaitingGoods: pos.filter((x) => x.status === 'Sent' || x.status === 'Partially Received').length,
    inwardPending: inws.filter((x) => x.status === 'Pending').length,
    toDispatch: sos.filter((x) => x.status === 'Open').length,
    toInvoiceSales: outs.filter((x) => x.status === 'Dispatched').length,
    toInvoicePurchase: grns.filter((x) => x.status === 'Received').length,
    completed: crs.filter((x) => x.stage === 'Completed').length,
  }
}
