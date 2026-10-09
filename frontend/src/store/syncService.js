/**
 * syncService.js
 * Synchronizes frontend actions to the FastAPI REST backend
 * and normalizes backend relational models into the UI state format.
 */

import {
  mastersApi,
  salesApi,
  purchaseApi,
  emailApi,
} from '../api/endpoints.js'
import { derive } from './reducer.js'
import { computeBest } from '../logic/compare.js'

export function sortByRecent(list) {
  if (!Array.isArray(list)) return list
  return [...list].sort((a, b) => {
    // 1. Compare dates if present
    const dateA = a.date || a.created_at || a.sent_at || a.dispatch_date || a.invoice_date || a.supplierInvDate || ''
    const dateB = b.date || b.created_at || b.sent_at || b.dispatch_date || b.invoice_date || b.supplierInvDate || ''
    if (dateA && dateB && dateA !== dateB) {
      return String(dateB).localeCompare(String(dateA))
    }
    // 2. Local/temporary IDs on top
    if (typeof a.id === 'string' && typeof b.id === 'number') return -1
    if (typeof a.id === 'number' && typeof b.id === 'string') return 1

    // 3. Compare numeric IDs descending
    const numA = Number(a.id)
    const numB = Number(b.id)
    if (!isNaN(numA) && !isNaN(numB) && numA !== numB) {
      return numB - numA
    }

    // 4. Document number descending (e.g. PI-0008, CR-043)
    const docA = a.crNo || a.prNo || a.vqNo || a.qcNo || a.cqNo || a.soNo || a.poNo || a.grnNo || a.inwNo || a.outNo || a.siNo || a.piNo || a.code || ''
    const docB = b.crNo || b.prNo || b.vqNo || b.qcNo || b.cqNo || b.soNo || b.poNo || b.grnNo || b.inwNo || b.outNo || b.siNo || b.piNo || b.code || ''
    if (docA && docB && docA !== docB) {
      return String(docB).localeCompare(String(docA), undefined, { numeric: true })
    }
    return 0
  })
}

function mergeLocal(backendList, fallbackList, idKey = 'id', noKey = null) {
  if (!Array.isArray(fallbackList) || fallbackList.length === 0) return sortByRecent(backendList || [])
  if (!Array.isArray(backendList) || backendList.length === 0) return sortByRecent(fallbackList)

  const fallbackByNo = new Map()
  const fallbackById = new Map()
  fallbackList.forEach((x) => {
    if (!x) return
    if (x[idKey]) fallbackById.set(String(x[idKey]), x)
    if (noKey && x[noKey]) fallbackByNo.set(String(x[noKey]).trim().toLowerCase(), x)
  })

  const mergedBackend = (backendList || []).map((b) => {
    if (!b) return b
    const noVal = noKey && b[noKey] ? String(b[noKey]).trim().toLowerCase() : null
    const matched = (noVal && fallbackByNo.get(noVal)) || fallbackById.get(String(b[idKey]))
    if (matched) {
      return {
        ...matched,
        ...b,
        localId: matched.localId || (String(matched[idKey]) !== String(b[idKey]) ? matched[idKey] : undefined),
      }
    }
    return b
  })

  const backendIds = new Set(mergedBackend.map((x) => String(x[idKey])))
  const backendNos = noKey ? new Set(mergedBackend.map((x) => String(x[noKey]).trim().toLowerCase()).filter(Boolean)) : null
  const backendLocalIds = new Set(mergedBackend.map((x) => x.localId ? String(x.localId) : null).filter(Boolean))

  const localOnly = fallbackList.filter((x) => {
    if (!x) return false
    if (backendIds.has(String(x[idKey]))) return false
    if (backendNos && x[noKey] && backendNos.has(String(x[noKey]).trim().toLowerCase())) return false
    if (backendLocalIds.has(String(x[idKey]))) return false
    if (backendList && backendList.length > 0 && typeof x[idKey] === 'number') {
      return false
    }
    return true
  })
  return sortByRecent([...localOnly, ...mergedBackend])
}

export function mapBackendToFrontend(bData, fallback) {
  if (!bData) return fallback

  const s = { ...fallback }

  // 1. Customers
  if (Array.isArray(bData.customers) && bData.customers.length > 0) {
    const clean = (val) => {
      if (!val) return ''
      const trimmed = String(val).trim()
      return trimmed.toLowerCase() === 'string' ? '' : trimmed
    }
    const backendCustomers = bData.customers.map((c) => ({
      id: c.id,
      code: c.customer_code || c.code || `CUS-${c.id}`,
      name: c.name || '',
      contactPerson: clean(c.contact_person || c.contactPerson),
      phone: c.phone || '',
      email: c.email || '',
      gstin: clean(c.gstin),
      billingAddress: clean(c.billing_address || c.billingAddress),
      shippingAddress: clean(c.shipping_address || c.shippingAddress),
      markupPct: Number(c.default_markup ?? c.markupPct ?? 15),
      paymentTerms: clean(c.payment_terms || c.paymentTerms),
      active: c.status !== false && c.active !== false,
      date: c.created_at || c.createdAt || '',
    }))
    s.customers = mergeLocal(backendCustomers, fallback?.customers || [], 'id', 'name')
  }

  // 2. Suppliers
  if (Array.isArray(bData.suppliers) && bData.suppliers.length > 0) {
    const backendSuppliers = bData.suppliers.map((sup) => ({
      id: sup.id,
      code: sup.supplier_code || sup.code || `SUP-${sup.id}`,
      name: sup.name || '',
      contactPerson: sup.contact_person || sup.contactPerson || '',
      phone: sup.phone || '',
      email: sup.email || '',
      gstin: sup.gstin || '',
      address: sup.address || '',
      categories: Array.isArray(sup.categories)
        ? sup.categories
        : typeof sup.categories === 'string' && sup.categories.startsWith('[')
        ? (() => { try { return JSON.parse(sup.categories) } catch { return [sup.categories] } })()
        : typeof sup.categories === 'string' && sup.categories.trim()
        ? sup.categories.split(',').map((x) => x.trim()).filter(Boolean)
        : [],
      leadTimeDays: Number(sup.lead_time_days ?? sup.leadTimeDays ?? 5),
      active: sup.status !== false && sup.active !== false,
      date: sup.created_at || sup.createdAt || '',
    }))
    s.suppliers = mergeLocal(backendSuppliers, fallback?.suppliers || [], 'id', 'name')
  }

  // 3. Items
  if (Array.isArray(bData.items) && bData.items.length > 0) {
    const backendItems = bData.items.map((it) => ({
      id: it.id,
      code: it.item_code || it.code || `ITM-${it.id}`,
      name: it.name || '',
      brand: it.brand || '',
      description: it.description || '',
      category: it.category || 'General',
      unit: it.unit || 'Nos',
      hsn: it.hsn_code || it.hsn || '',
      taxPct: Number(it.tax_percent ?? it.taxPct ?? 18),
      lastPurchaseRate: Number(it.last_purchase_rate ?? it.lastPurchaseRate ?? 0),
      active: it.status !== false && it.active !== false,
      date: it.created_at || it.createdAt || '',
    }))
    s.items = mergeLocal(backendItems, fallback?.items || [], 'id', 'name')
  }

  // 4. Customer Requests
  if (Array.isArray(bData.customerRequests) && bData.customerRequests.length > 0) {
    const backendCRs = bData.customerRequests.map((cr) => ({
      id: cr.id,
      crNo: cr.request_no || cr.crNo || `CR-${cr.id}`,
      date: (cr.created_at || '').slice(0, 10) || cr.date,
      customerId: cr.customer_id || cr.customerId,
      requiredBy: cr.required_date || cr.requiredBy,
      reference: cr.customer_reference || cr.reference || '',
      remarks: cr.remarks || '',
      stage: cr.status || cr.stage || 'Requested',
      lines: (cr.lines || []).map((l) => ({
        itemId: l.item_id || l.itemId,
        description: l.description || '',
        qty: Number(l.quantity ?? l.qty ?? 1),
        unit: l.unit || 'Nos',
      })),
    }))
    s.customerRequests = mergeLocal(backendCRs, fallback.customerRequests, 'id', 'crNo')
  }

  // 5. Purchase Requests (PR)
  if (Array.isArray(bData.purchaseRequests) && bData.purchaseRequests.length > 0) {
    const backendPRs = bData.purchaseRequests.filter(Boolean).map((pr) => {
      const cr = (s.customerRequests || []).find((c) => c && c.id === (pr.customer_request_id || pr.crId))
      return {
        id: pr.id,
        prNo: pr.pr_no || pr.prNo || `PR-${pr.id}`,
        date: (pr.created_at || '').slice(0, 10) || pr.date,
        crId: pr.customer_request_id || pr.crId,
        customerId: pr.customer_id || (cr ? cr.customerId : null),
        rfqSupplierIds: pr.rfq_supplier_ids || pr.rfqSupplierIds || [],
        rfqSentAt: pr.rfq_sent_at || pr.rfqSentAt || null,
        status: pr.status || 'Open',
        lines: (pr.items || pr.lines || (cr ? cr.lines : []) || []).filter(Boolean).map((l) => ({
          itemId: l.item_id || l.itemId,
          qty: Number(l.quantity ?? l.qty ?? 1),
          unit: l.unit || 'Nos',
        })),
      }
    })
    s.purchaseRequests = mergeLocal(backendPRs, fallback.purchaseRequests, 'id', 'prNo')
  }

  // 6. Vendor Quotations (VQ)
  if (Array.isArray(bData.vendorQuotations) && bData.vendorQuotations.length > 0) {
    const backendVQs = bData.vendorQuotations.filter(Boolean).map((vq) => ({
      id: vq.id,
      vqNo: vq.quote_reference || vq.quotation_no || vq.vqNo || `VQ-${vq.id}`,
      date: vq.quote_date || (vq.created_at || '').slice(0, 10) || vq.date,
      prId: vq.purchase_request_id || vq.prId,
      supplierId: vq.supplier_id || vq.supplierId,
      quoteRef: vq.quote_reference || vq.quoteRef || '',
      validTill: vq.validity || vq.validTill,
      deliveryDays: Number(vq.delivery_days ?? vq.deliveryDays ?? 0),
      paymentTerms: vq.payment_terms || vq.paymentTerms || '',
      freight: Number(vq.freight ?? 0),
      grandTotal: Number(vq.grand_total ?? vq.grandTotal ?? 0),
      status: vq.status || 'Received',
      lines: (vq.lines || []).filter(Boolean).map((l) => ({
        itemId: l.item_id || l.itemId,
        qty: Number(l.quantity ?? l.qty ?? 1),
        rate: Number(l.rate ?? 0),
        taxPct: Number(l.tax_percent ?? l.taxPct ?? 18),
        notQuoted: Boolean(l.not_quoted ?? l.notQuoted),
      })),
    }))
    s.vendorQuotations = mergeLocal(backendVQs, fallback.vendorQuotations, 'id', 'vqNo')
  }

  // 7. Quotation Comparisons (QC)
  const qcMap = new Map()
  ;((fallback && fallback.quotationComparisons) || []).forEach((q) => {
    if (q && q.prId) qcMap.set(q.prId, q)
  })
  ;(s.purchaseRequests || []).forEach((pr) => {
    if (!pr || !pr.id) return
    const vqs = (s.vendorQuotations || []).filter((v) => v && v.prId === pr.id)
    if (vqs.length > 0) {
      const existing = qcMap.get(pr.id)
      const bestId = computeBest(vqs, pr.lines || [])
      const selectedVq = vqs.find((v) => v && v.status === 'Selected')
      const isApproved = pr.status === 'Quoted' || pr.status === 'Ordered' || !!selectedVq
      qcMap.set(pr.id, {
        id: existing?.id || pr.id,
        qcNo: existing?.qcNo || `QC-${String(pr.id).padStart(3, '0')}`,
        date: existing?.date || pr.date,
        prId: pr.id,
        crId: pr.crId,
        vqIds: vqs.map((v) => v?.id).filter(Boolean),
        bestVqId: existing?.bestVqId || bestId,
        selectedVqId: selectedVq ? selectedVq.id : (existing?.selectedVqId || (isApproved ? bestId : null)),
        overrideReason: existing?.overrideReason || '',
        status: isApproved ? 'Approved' : (existing?.status || 'Draft'),
      })
    }
  })
  s.quotationComparisons = Array.from(qcMap.values())

  // 8. Customer Quotations (CQ)
  if (Array.isArray(bData.customerQuotations) && bData.customerQuotations.length > 0) {
    const backendCQs = bData.customerQuotations.map((cq) => ({
      id: cq.id,
      cqNo: cq.quotation_no || cq.cqNo || `CQ-${cq.id}`,
      date: (cq.created_at || '').slice(0, 10) || cq.date,
      crId: cq.customer_request_id || cq.crId,
      qcId: cq.comparison_id || cq.qcId,
      customerId: cq.customer_id || cq.customerId,
      validTill: cq.valid_till || cq.validTill,
      lines: (cq.items || cq.lines || []).map((l) => ({
        itemId: l.item_id || l.itemId,
        qty: Number(l.quantity ?? l.qty ?? 1),
        supplierRate: Number(l.supplier_rate ?? l.supplierRate ?? 0),
        customerPrice: Number(l.customer_price ?? l.customerPrice ?? 0),
        taxPct: Number(l.tax_percent ?? l.taxPct ?? 18),
      })),
      status: cq.status || 'Sent',
      sentAt: cq.sent_at || cq.sentAt || null,
      total: Number(cq.grand_total ?? cq.total ?? 0),
    }))
    s.customerQuotations = mergeLocal(backendCQs, fallback.customerQuotations, 'id', 'cqNo')
  }

  // 9. Customer PO / Sales Orders (SO)
  if (Array.isArray(bData.salesOrders) && bData.salesOrders.length > 0) {
    const backendOrders = bData.salesOrders.map((so) => ({
      id: so.id,
      soNo: so.order_no || so.soNo || `SO-${so.id}`,
      date: (so.created_at || '').slice(0, 10) || so.po_date || so.date,
      customerPoNo: so.customer_po_number || so.customerPoNo || '',
      customerPoDate: so.po_date || so.customerPoDate || '',
      crId: so.customer_request_id || so.crId,
      cqId: so.quotation_id || so.cqId,
      customerId: so.customer_id || so.customerId,
      deliveryDate: so.delivery_date || so.deliveryDate || null,
      lines: (so.items || so.lines || []).map((l) => ({
        itemId: l.item_id || l.itemId,
        qty: Number(l.quantity ?? l.qty ?? 1),
        price: Number(l.selling_price ?? l.price ?? 0),
      })),
      status: so.status || 'Open',
      total: Number(so.grand_total ?? so.total ?? 0),
    }))
    s.salesOrders = mergeLocal(backendOrders, fallback.salesOrders, 'id', 'soNo')
  }

  // 10. Supplier Purchase Orders (PO)
  if (Array.isArray(bData.purchaseOrders) && bData.purchaseOrders.length > 0) {
    const backendPOs = bData.purchaseOrders.map((po) => ({
      id: po.id,
      poNo: po.po_no || po.poNo || `PO-${po.id}`,
      date: (po.created_at || '').slice(0, 10) || po.date,
      soId: po.customer_order_id || po.soId,
      crId: po.customer_request_id || po.crId,
      vqId: po.quotation_id || po.vqId,
      supplierId: po.supplier_id || po.supplierId,
      expectedDelivery: po.delivery_date || po.expectedDelivery,
      lines: (po.items || po.lines || []).map((l) => ({
        itemId: l.item_id || l.itemId,
        qty: Number(l.quantity ?? l.qty ?? 1),
        rate: Number(l.rate ?? 0),
        taxPct: Number(l.tax_percent ?? l.taxPct ?? 18),
        receivedQty: Number(l.received_qty ?? l.receivedQty ?? 0),
      })),
      total: Number(po.grand_total ?? po.total ?? 0),
      status: po.status || 'Draft',
      sentAt: po.sent_at || po.sentAt || null,
    }))
    s.purchaseOrders = mergeLocal(backendPOs, fallback.purchaseOrders, 'id', 'poNo')
  }

  // 11. Goods Receipt Notes (GRN)
  if (Array.isArray(bData.grns) && bData.grns.length > 0) {
    const backendGRNs = bData.grns.map((g) => {
      const hasPI = (bData.purchaseInvoices || []).some(
        (pi) => pi && (pi.grn_id === g.id || pi.grnId === g.id || String(pi.grn_id) === String(g.id))
      )
      return {
        id: g.id,
        grnNo: g.grn_no || g.grnNo || `GRN-${g.id}`,
        date: (g.received_date || g.created_at || '').slice(0, 10) || g.date,
        poId: g.purchase_order_id || g.poId,
        crId: g.customer_request_id || g.crId,
        supplierId: g.supplier_id || g.supplierId,
        supplierRef: g.challan_no || g.supplier_invoice_ref || g.supplierRef || '',
        receivedBy: g.received_by || g.receivedBy || '',
        remarks: g.remarks || '',
        status: hasPI ? 'Invoiced' : 'Received',
        lines: (g.items || g.lines || []).map((l) => ({
          itemId: l.item_id || l.itemId,
          receivedQty: Number(l.received_qty ?? l.receivedQty ?? 0),
          acceptedQty: Number(l.accepted_qty ?? l.acceptedQty ?? 0),
          rejectedQty: Number(l.rejected_qty ?? l.rejectedQty ?? 0),
          rate: Number(l.rate ?? 0),
        })),
        total: Number(g.total ?? 0),
      }
    })
    s.grns = mergeLocal(backendGRNs, fallback.grns, 'id', 'grnNo')
  }

  // 12. Inward Stock
  if (Array.isArray(bData.inwards) && bData.inwards.length > 0) {
    const backendInwards = bData.inwards.filter(Boolean).map((inw) => {
      const linkedGrn = (s.grns || []).find((g) => g && (g.id === (inw.grn_id || inw.grnId)))
      const linkedPo = (s.purchaseOrders || []).find((p) => p && (p.id === (inw.po_id || inw.purchase_order_id || (linkedGrn ? linkedGrn.poId : null))))
      const linkedCr = (s.customerRequests || []).find((c) => c && (c.id === (inw.customer_request_id || inw.crId)))
      return {
        id: inw.id,
        inwNo: inw.inward_no || inw.inwNo || `INW-${inw.id}`,
        date: inw.received_date || (inw.created_at || '').slice(0, 10) || inw.date,
        receivedDate: inw.received_date || (linkedGrn ? linkedGrn.date : null),
        grnId: inw.grn_id || inw.grnId,
        grnNo: inw.grn_no || (linkedGrn ? linkedGrn.grnNo : null),
        poId: inw.po_id || inw.purchase_order_id || inw.poId || (linkedGrn ? linkedGrn.poId : null),
        poNo: inw.po_no || (linkedPo ? linkedPo.poNo : null),
        crId: inw.customer_request_id || inw.crId,
        crNo: inw.customer_request_no || (linkedCr ? linkedCr.crNo : null),
        supplierId: inw.supplier_id || (linkedGrn ? linkedGrn.supplierId : null),
        supplierName: inw.supplier_name || null,
        status: inw.status || 'Pending',
        addedAt: inw.added_at || inw.addedAt || null,
        totalAcceptedQty: Number(inw.total_accepted_qty ?? inw.total_qty ?? 0),
        totalRejectedQty: Number(inw.total_rejected_qty ?? 0),
        value: Number(inw.total_value ?? inw.value ?? 0),
        lines: (inw.items || inw.lines || []).filter(Boolean).map((l) => ({
          itemId: l.item_id || l.itemId,
          receivedQty: Number(l.received_qty ?? 0),
          qty: Number(l.accepted_qty ?? l.quantity ?? l.qty ?? 0),
          acceptedQty: Number(l.accepted_qty ?? l.quantity ?? l.qty ?? 0),
          rejectedQty: Number(l.rejected_qty ?? 0),
          rate: Number(l.rate ?? 0),
        })),
      }
    })
    s.inwards = mergeLocal(backendInwards, fallback.inwards, 'id', 'inwNo')
  }

  // 13. Outward (Delivery Challan)
  if (Array.isArray(bData.outwards) && bData.outwards.length > 0) {
    const backendOutwards = bData.outwards.filter(Boolean).map((o) => ({
      id: o.id,
      outNo: o.dc_number || o.dc_no || o.outward_no || o.outNo || `OUT-${o.id}`,
      date: (o.dispatch_date || o.created_at || '').slice(0, 10) || o.date,
      soId: o.customer_order_id || o.soId,
      crId: o.customer_request_id || o.crId,
      customerId: o.customer_id || o.customerId,
      dcNo: o.dc_number || o.dc_no || '',
      mode: o.dispatch_mode || o.mode || '',
      vehicle: o.vehicle_no || o.vehicle_or_courier || o.vehicle || '',
      remarks: o.remarks || '',
      status: o.status || 'Dispatched',
      value: Number(o.total_value ?? o.value ?? 0),
      lines: (o.items || o.lines || []).filter(Boolean).map((l) => ({
        itemId: l.item_id || l.itemId,
        qty: Number(l.dispatch_qty ?? l.quantity ?? l.qty ?? 0),
        price: Number(l.selling_price ?? l.price ?? 0),
      })),
    }))
    s.outwards = mergeLocal(backendOutwards, fallback.outwards, 'id', 'outNo')
  }

  // 14. Sales Invoices
  if (Array.isArray(bData.salesInvoices) && bData.salesInvoices.length > 0) {
    const backendInvoices = bData.salesInvoices.filter(Boolean).map((si) => ({
      id: si.id,
      siNo: si.invoice_no || si.siNo || `SI-${si.id}`,
      date: (si.invoice_date || si.created_at || '').slice(0, 10) || si.date,
      outId: si.outward_id || si.outId,
      soId: si.customer_order_id || si.soId,
      crId: si.customer_request_id || si.crId,
      customerId: si.customer_id || si.customerId,
      paymentTerms: si.payment_terms || '',
      dueDate: (si.due_date || '').slice(0, 10) || si.dueDate,
      subtotal: Number(si.subtotal ?? 0),
      tax: Number(si.tax_amount ?? si.tax ?? 0),
      total: Number(si.grand_total ?? si.total ?? 0),
      status: si.status || 'Final',
      lines: (si.items || si.lines || []).filter(Boolean).map((l) => ({
        itemId: l.item_id || l.itemId,
        hsn: l.hsn_code || l.hsn || '',
        qty: Number(l.quantity ?? l.qty ?? 0),
        rate: Number(l.rate ?? l.price ?? 0),
        taxable: Number(l.taxable_amount ?? l.taxable ?? 0),
        taxPct: Number(l.tax_percent ?? l.taxPct ?? 18),
        taxAmount: Number(l.tax_amount ?? 0),
        total: Number(l.line_total ?? l.total ?? 0),
      })),
    }))
    s.salesInvoices = mergeLocal(backendInvoices, fallback.salesInvoices, 'id', 'siNo')
  }

  // 15. Purchase Invoices
  if (Array.isArray(bData.purchaseInvoices) && bData.purchaseInvoices.length > 0) {
    const backendPIs = bData.purchaseInvoices.filter(Boolean).map((pi) => {
      const linkedGrn = (s.grns || []).find((g) => g && (g.id === (pi.grn_id || pi.grnId)))
      return {
        id: pi.id,
        piNo: pi.internal_invoice_no || pi.piNo || `PI-${pi.id}`,
        date: (pi.supplier_invoice_date || pi.created_at || '').slice(0, 10) || pi.date,
        grnId: pi.grn_id || pi.grnId,
        poId: linkedGrn ? linkedGrn.poId : null,
        crId: pi.customer_request_id || pi.crId,
        supplierId: pi.supplier_id || pi.supplierId,
        supplierInvNo: pi.supplier_invoice_no || pi.supplierInvNo || '',
        supplierInvDate: (pi.supplier_invoice_date || '').slice(0, 10) || pi.supplierInvDate,
        dueDate: (pi.due_date || '').slice(0, 10) || pi.dueDate,
        subtotal: Number(pi.subtotal ?? 0),
        tax: Number(pi.tax_amount ?? pi.tax ?? 0),
        total: Number(pi.grand_total ?? pi.total ?? 0),
        status: pi.status || 'Verified',
        lines: (pi.items || pi.lines || []).filter(Boolean).map((l) => ({
          itemId: l.item_id || l.itemId,
          qty: Number(l.quantity ?? l.qty ?? 0),
          rate: Number(l.rate ?? 0),
          taxable: Number(l.taxable_amount ?? l.taxable ?? 0),
          taxPct: Number(l.tax_percent ?? l.taxPct ?? 18),
          taxAmount: Number(l.tax_amount ?? 0),
          total: Number(l.line_total ?? l.total ?? 0),
        })),
      }
    })
    s.purchaseInvoices = mergeLocal(backendPIs, fallback.purchaseInvoices, 'id', 'piNo')
  }

  // 16. Stock Ledger
  if (Array.isArray(bData.ledger) && bData.ledger.length > 0) {
    const backendLedger = bData.ledger.filter(Boolean).map((l) => {
      const isOut = (l.movement_type || '').toUpperCase() === 'OUT'
      let partyId = null
      if (isOut) {
        const outDoc = (s.outwards || []).find((o) => o && (o.id === l.reference_id || String(o.id) === String(l.reference_id)))
        partyId = outDoc ? outDoc.customerId : null
      } else {
        const inwDoc = (s.inwards || []).find((i) => i && (i.id === l.reference_id || String(i.id) === String(l.reference_id)))
        partyId = inwDoc ? inwDoc.supplierId : null
      }
      return {
        id: l.id,
        date: (l.created_at || '').slice(0, 10),
        type: (l.movement_type || '').toUpperCase(),
        itemId: l.item_id,
        crId: l.customer_request_id,
        qty: Number(l.quantity || 0),
        rate: Number(l.rate || 0),
        value: Number(l.quantity || 0) * Number(l.rate || 0),
        refType: l.reference_type,
        refId: l.reference_id,
        partyId,
      }
    })
    s.stockLedger = mergeLocal(backendLedger, fallback.stockLedger, 'id')
  }

  // 17. Email Logs
  if (Array.isArray(bData.emailLog) && bData.emailLog.length > 0) {
    const backendEmailLog = bData.emailLog.map((em) => {
      let refType = 'PR'
      if (em.document_type === 'Customer Quotation' || em.refType === 'CQ') refType = 'CQ'
      else if (em.document_type === 'Purchase Order' || em.refType === 'PO') refType = 'PO'
      else if (em.document_type === 'RFQ' || em.refType === 'PR') refType = 'PR'
      else if (em.refType) refType = em.refType

      const recipients = Array.isArray(em.recipient)
        ? em.recipient
        : em.recipient
        ? [em.recipient]
        : Array.isArray(em.to)
        ? em.to
        : [em.to || '']

      return {
        id: em.id,
        sentAt: em.sent_at || em.sentAt || new Date().toISOString(),
        to: recipients,
        subject: em.subject || 'No Subject',
        body: em.body || '',
        refType,
        refId: em.document_id || em.refId,
        status: em.status || 'Sent',
      }
    })
    s.emailLog = mergeLocal(backendEmailLog, fallback.emailLog, 'id')
  }

  return derive(s)
}

/**
 * Dispatches an action asynchronously to the FastAPI backend.
 */
export async function syncActionToBackend(action, state) {
  try {
    switch (action.type) {
      /* Masters */
      case 'MASTER_SAVE': {
        const { collection, record } = action
        let res = null
        if (collection === 'customers') {
          const payload = {
            name: record.name,
            contact_person: record.contactPerson,
            phone: record.phone,
            email: record.email,
            gstin: record.gstin,
            billing_address: record.billingAddress,
            shipping_address: record.shippingAddress,
            default_markup: Number(record.markupPct || 15),
            payment_terms: record.paymentTerms,
            status: record.active !== false,
          }
          const existingId = Number(record.id)
          if (!isNaN(existingId) && existingId > 0) {
            res = await mastersApi.updateCustomer(existingId, payload)
          } else {
            const found = (state?.customers || []).find(
              (c) => c.email && c.email.toLowerCase() === (record.email || '').toLowerCase() && Number(c.id) > 0
            )
            if (found) {
              res = await mastersApi.updateCustomer(Number(found.id), payload)
            } else {
              res = await mastersApi.createCustomer(payload)
            }
          }
        } else if (collection === 'suppliers') {
          const payload = {
            name: record.name,
            contact_person: record.contactPerson,
            phone: record.phone,
            gstin: record.gstin,
            email: record.email,
            categories: record.categories,
            address: record.address,
            lead_time_days: Number(record.leadTimeDays || 5),
            status: record.active !== false,
          }
          const existingId = Number(record.id)
          if (!isNaN(existingId) && existingId > 0) {
            res = await mastersApi.updateSupplier(existingId, payload)
          } else {
            const found = (state?.suppliers || []).find(
              (s) => s.email && s.email.toLowerCase() === (record.email || '').toLowerCase() && Number(s.id) > 0
            )
            if (found) {
              res = await mastersApi.updateSupplier(Number(found.id), payload)
            } else {
              res = await mastersApi.createSupplier(payload)
            }
          }
        } else if (collection === 'items') {
          const payload = {
            name: record.name,
            brand: record.brand,
            description: record.description,
            category: record.category,
            unit: record.unit,
            hsn_code: record.hsn,
            tax_percent: Number(record.taxPct || 18),
            last_purchase_rate: Number(record.lastPurchaseRate || 0),
            status: record.active !== false,
          }
          const existingId = Number(record.id)
          if (!isNaN(existingId) && existingId > 0) {
            res = await mastersApi.updateItem(existingId, payload)
          } else {
            const found = (state?.items || []).find(
              (it) => it.code && it.code.toLowerCase() === (record.code || '').toLowerCase() && Number(it.id) > 0
            )
            if (found) {
              res = await mastersApi.updateItem(Number(found.id), payload)
            } else {
              res = await mastersApi.createItem(payload)
            }
          }
        }
        window.dispatchEvent(new CustomEvent('ERP_SYNC_TRIGGER'))
        return res
      }

      case 'MASTER_TOGGLE': {
        const { collection, id } = action
        if (typeof id === 'number') {
          if (collection === 'customers') await mastersApi.toggleCustomer(id)
          if (collection === 'suppliers') await mastersApi.toggleSupplier(id)
          if (collection === 'items') await mastersApi.toggleItem(id)
          window.dispatchEvent(new CustomEvent('ERP_SYNC_TRIGGER'))
        }
        break
      }

      case 'MASTER_DELETE': {
        const { collection, id } = action
        if (collection === 'customers') {
          await mastersApi.deleteCustomer(id)
          window.dispatchEvent(new CustomEvent('ERP_SYNC_TRIGGER'))
        }
        break
      }

      /* Sales - 01. Customer Request */
      case 'CR_CREATE': {
        const { payload } = action
        if (typeof payload.customerId === 'number') {
          await salesApi.createCustomerRequest({
            customer_id: payload.customerId,
            required_date: payload.requiredBy || undefined,
            customer_reference: payload.reference || undefined,
            lines: (payload.lines || []).map((l) => ({
              item_id: l.itemId,
              description: l.description,
              quantity: Number(l.qty || 1),
              unit: l.unit || 'Nos',
            })),
          })
        }
        break
      }

      /* Purchase - 02. RFQ */
      case 'PR_SEND_RFQ': {
        const { prId, supplierIds, subject, body } = action
        if (typeof prId === 'number') {
          await purchaseApi.sendRFQ({
            pr_id: prId,
            supplier_ids: supplierIds,
            subject,
            body,
          })
        } else {
          for (const sId of (supplierIds || [])) {
            const sup = (state.suppliers || []).find((s) => s.id === sId)
            if (sup && sup.email) {
              await emailApi.sendLiveEmail({
                recipient: sup.email,
                subject: subject || 'Request for Quotation',
                body: body || 'Please find our RFQ.',
                document_type: 'RFQ',
              }).catch(() => {})
            }
          }
        }
        break
      }

      /* Purchase - 03. Vendor Quotation */
      case 'VQ_SAVE': {
        const { payload } = action
        if (typeof payload.prId === 'number' && typeof payload.supplierId === 'number') {
          await purchaseApi.createVendorQuotation({
            purchase_request_id: payload.prId,
            supplier_id: payload.supplierId,
            quote_reference: payload.quoteRef,
            quote_date: payload.quoteDate,
            validity: payload.validTill,
            delivery_days: Number(payload.deliveryDays || 0),
            payment_terms: payload.paymentTerms,
            freight: Number(payload.freight || 0),
            lines: (payload.lines || []).map((l) => ({
              item_id: l.itemId,
              rate: Number(l.rate || 0),
              tax_percent: Number(l.taxPct || 18),
              not_quoted: Boolean(l.notQuoted),
            })),
          })
        }
        break
      }

      /* Purchase - 04. Quotation Comparison Approval */
      case 'QC_APPROVE': {
        const { qcId, selectedVqId, overrideReason } = action
        const qc = state.quotationComparisons.find((q) => q.id === qcId || String(q.id) === String(qcId))
        const prIdNum = qc && !isNaN(Number(qc.prId)) ? Number(qc.prId) : null
        if (qc && prIdNum) {
          const vq = state.vendorQuotations.find((v) => v.id === selectedVqId || String(v.id) === String(selectedVqId))
          const supIdNum = vq && !isNaN(Number(vq.supplierId)) ? Number(vq.supplierId) : null
          if (supIdNum) {
            await purchaseApi.approveComparison(prIdNum, {
              selected_supplier_id: supIdNum,
              override_reason: overrideReason || undefined,
            })
          }
        }
        break
      }

      /* Purchase - 04b. Send Quotation to Customer (Auto CQ) */
      case 'QC_SEND_TO_CUSTOMER': {
        const { qcId } = action
        const qc = state.quotationComparisons.find((q) => q.id === qcId || String(q.id) === String(qcId))
        const compIdNum = qc && !isNaN(Number(qc.id)) ? Number(qc.id) : (qc && !isNaN(Number(qc.prId)) ? Number(qc.prId) : null)
        if (compIdNum) {
          try {
            await salesApi.createQuotationFromComparison(compIdNum)
          } catch (e) {
            // fallback gracefully - local reducer already created client quotation
          }
        }
        break
      }

      /* Sales - 05. Customer Quotation Status */
      case 'CQ_SET_STATUS': {
        const { cqId, status } = action
        const numId = !isNaN(Number(cqId)) ? Number(cqId) : null
        if (numId) {
          if (status === 'Accepted') await salesApi.acceptCustomerQuotation(numId)
          if (status === 'Rejected') await salesApi.rejectCustomerQuotation(numId)
        }
        break
      }

      /* Sales - 05b. Customer Quotation Send / Resend Email */
      case 'CQ_RESEND': {
        const { cqId, subject, body } = action
        const cq = (state.customerQuotations || []).find((q) => q.id === cqId || String(q.id) === String(cqId))
        const cust = cq ? (state.customers || []).find((c) => c.id === cq.customerId || String(c.id) === String(cq.customerId)) : null
        const recipient = (cust && cust.email) || null
        const numCqId = !isNaN(Number(cqId)) ? Number(cqId) : null
        if (numCqId) {
          try {
            await salesApi.sendCustomerQuotation({
              quotation_id: numCqId,
              recipient: recipient || undefined,
              subject,
              body,
            })
          } catch (e) {
            if (recipient) {
              await emailApi.sendLiveEmail({
                recipient,
                subject: subject || `Quotation ${cq ? cq.cqNo : ''}`,
                body: body || 'Please find attached quotation.',
                document_type: 'Customer Quotation',
                document_id: numCqId,
              }).catch(() => {})
            }
          }
        } else if (recipient) {
          await emailApi.sendLiveEmail({
            recipient,
            subject: subject || `Quotation ${cq ? cq.cqNo : ''}`,
            body: body || 'Please find attached quotation.',
            document_type: 'Customer Quotation',
            document_id: 0,
          }).catch(() => {})
        }
        break
      }

      /* Sales - 06. Customer Order (SO) */
      case 'SO_CREATE': {
        const { payload } = action
        const numCqId = !isNaN(Number(payload.cqId)) ? Number(payload.cqId) : null
        if (numCqId) {
          await salesApi.createCustomerOrder({
            quotation_id: numCqId,
            customer_po_number: payload.customerPoNo,
            po_date: payload.customerPoDate,
            delivery_date: payload.deliveryDate,
            items: (payload.lines || []).map((l) => ({
              item_id: !isNaN(Number(l.itemId)) ? Number(l.itemId) : l.itemId,
              quantity: Number(l.qty || 1),
              selling_price: Number(l.price || 0),
            })),
          })
        }
        break
      }

      /* Purchase - 07. Supplier PO Send */
      case 'PO_SEND': {
        const { poId, subject, body } = action
        if (typeof poId === 'number') {
          await purchaseApi.sendPurchaseOrder(poId, { subject, body })
        }
        break
      }

      /* Purchase - 08. GRN */
      case 'GRN_CREATE': {
        const { payload } = action
        if (typeof payload.poId === 'number') {
          await purchaseApi.createGRN({
            purchase_order_id: payload.poId,
            challan_no: payload.supplierRef || 'CH-001',
            received_date: payload.date,
            received_by: payload.receivedBy || 'Stores',
            remarks: payload.remarks,
            items: (payload.lines || []).map((l) => ({
              item_id: l.itemId,
              received_qty: Number(l.receivedQty || 0),
              accepted_qty: Number(l.acceptedQty || 0),
              rejected_qty: Number(l.rejectedQty || 0),
            })),
          })
        }
        break
      }

      /* Purchase - 09. Inward */
      case 'INW_ADD_TO_STOCK': {
        const { inwId } = action
        if (typeof inwId === 'number') {
          await purchaseApi.inwardStock(inwId)
        }
        break
      }

      /* Sales - 10. Outward (Delivery Challan) */
      case 'OUT_CREATE': {
        const { payload } = action
        const numSoId = !isNaN(Number(payload.soId)) ? Number(payload.soId) : null
        if (numSoId) {
          try {
            await salesApi.createOutward({
              customer_order_id: numSoId,
              dc_number: payload.dcNo || 'DC-001',
              dispatch_date: payload.date || today(),
              dispatch_mode: payload.mode || 'Road',
              vehicle_or_courier: payload.vehicle || 'TN 09 BX 4471',
              remarks: payload.remarks || '',
              status: 'Dispatched',
              items: (payload.lines || []).map((l) => ({
                item_id: Number(l.itemId),
                dispatch_qty: Number(l.qty || 0),
                dispatched_qty: Number(l.qty || 0),
              })),
            })
          } catch (err) {
            console.warn('Backend outward creation failed:', err.message || err)
          }
        }
        break
      }

      /* Sales - 11. Sales Invoice */
      case 'SI_CREATE': {
        const { payload } = action
        let numOutId = !isNaN(Number(payload.outId)) ? Number(payload.outId) : null
        const matchOut = state.outwards?.find((o) => o && (o.id === payload.outId || String(o.id) === String(payload.outId)))
        if (!numOutId && matchOut && !isNaN(Number(matchOut.id))) {
          numOutId = Number(matchOut.id)
        }
        if (!numOutId) {
          try {
            const outList = await salesApi.getOutwards({ limit: 100 })
            const items = Array.isArray(outList) ? outList : (outList?.items || [])
            const found = items.find((o) =>
              (matchOut?.dcNo && (o.dc_number === matchOut.dcNo || o.dc_no === matchOut.dcNo)) ||
              (matchOut?.soId && (o.customer_order_id === Number(matchOut.soId))) ||
              (matchOut?.outNo && (o.outward_no === matchOut.outNo || o.dc_number === matchOut.outNo))
            )
            if (found && found.id) {
              numOutId = found.id
            }
          } catch {}
        }
        if (numOutId) {
          try {
            await salesApi.createSalesInvoice({
              outward_id: numOutId,
              invoice_date: payload.date || today(),
              due_date: payload.dueDate || addDays(today(), 30),
              payment_terms: payload.paymentTerms || '30 days',
            })
            window.dispatchEvent(new CustomEvent('ERP_SYNC_TRIGGER'))
          } catch (err) {
            console.warn('Backend invoice creation failed:', err.message || err)
          }
        }
        break
      }

      /* Purchase - 12. Purchase Invoice */
      case 'PI_CREATE': {
        const { payload } = action
        let numGrnId = !isNaN(Number(payload.grnId)) ? Number(payload.grnId) : null
        const matchGrn = state.grns?.find((g) => g && (g.id === payload.grnId || String(g.id) === String(payload.grnId)))
        if (!numGrnId && matchGrn && !isNaN(Number(matchGrn.id))) {
          numGrnId = Number(matchGrn.id)
        }
        if (!numGrnId) {
          try {
            const grnList = await purchaseApi.getGRNs({ limit: 100 })
            const items = Array.isArray(grnList) ? grnList : (grnList?.items || [])
            const found = items.find((g) =>
              (matchGrn?.grnNo && (g.grn_no === matchGrn.grnNo)) ||
              (matchGrn?.poId && (g.purchase_order_id === Number(matchGrn.poId)))
            )
            if (found && found.id) {
              numGrnId = found.id
            }
          } catch {}
        }
        if (numGrnId) {
          try {
            await purchaseApi.createPurchaseInvoice({
              grn_id: numGrnId,
              supplier_invoice_no: payload.supplierInvNo || 'PINV-001',
              supplier_invoice_date: payload.supplierInvDate || payload.date || today(),
              due_date: payload.dueDate || addDays(today(), 30),
            })
            window.dispatchEvent(new CustomEvent('ERP_SYNC_TRIGGER'))
          } catch (err) {
            console.warn('Backend purchase invoice creation failed:', err.message || err)
          }
        }
        break
      }

      default:
        break
    }
  } catch (err) {
    console.warn(`[SyncService] Backend sync notice for ${action.type}:`, err.message || err)
    throw err
  }
}
