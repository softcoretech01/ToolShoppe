import { reducer, addDays, today } from './reducer.js'
import { seedMasters } from './seed.js'
import { defaultCustomerPrice } from '../logic/pricing.js'

/**
 * The demo data is not hand-written JSON — it is produced by replaying the
 * very same reducer actions the UI dispatches. Whatever the automation does
 * in the app, it did to build this seed, so the two can never drift apart.
 */
export function buildDemoState() {
  let s = seedMasters()
  const run = (a) => { s = reducer(s, a) }

  const cust = (code) => s.customers.find((x) => x.code === code)
  const sup = (code) => s.suppliers.find((x) => x.code === code)
  const item = (code) => s.items.find((x) => x.code === code)
  const last = (coll) => s[coll][0]
  const d = (n) => addDays(today(), -n)

  /* ================= Three customer requests ================= */
  run({
    type: 'CR_CREATE',
    payload: {
      date: d(24),
      customerId: cust('CUS-001').id,
      requiredBy: d(4),
      reference: 'BEW/ENQ/2026/084',
      remarks: 'Tool room replenishment. Brand equivalents acceptable.',
      lines: [
        { itemId: item('ITM-0001').id, description: item('ITM-0001').description, qty: 10, unit: 'Set', remarks: '' },
        { itemId: item('ITM-0007').id, description: item('ITM-0007').description, qty: 5, unit: 'Nos', remarks: 'Calibration certificate required' },
        { itemId: item('ITM-0010').id, description: item('ITM-0010').description, qty: 20, unit: 'Box', remarks: '' },
      ],
    },
  })
  const cr1 = last('customerRequests')
  const pr1 = s.purchaseRequests.find((p) => p.crId === cr1.id)

  run({
    type: 'CR_CREATE',
    payload: {
      date: d(9),
      customerId: cust('CUS-002').id,
      requiredBy: addDays(today(), 12),
      reference: 'SAC/RFQ/5521',
      remarks: 'Hand tools for the new assembly line.',
      lines: [
        { itemId: item('ITM-0004').id, description: item('ITM-0004').description, qty: 25, unit: 'Nos', remarks: '' },
        { itemId: item('ITM-0005').id, description: item('ITM-0005').description, qty: 25, unit: 'Nos', remarks: '1000V insulated only' },
        { itemId: item('ITM-0006').id, description: item('ITM-0006').description, qty: 10, unit: 'Set', remarks: '' },
      ],
    },
  })
  const cr2 = last('customerRequests')
  const pr2 = s.purchaseRequests.find((p) => p.crId === cr2.id)

  run({
    type: 'CR_CREATE',
    payload: {
      date: d(1),
      customerId: cust('CUS-003').id,
      requiredBy: addDays(today(), 20),
      reference: 'KF/2026/PUR/019',
      remarks: 'Consumables for the fabrication shop.',
      lines: [
        { itemId: item('ITM-0011').id, description: item('ITM-0011').description, qty: 40, unit: 'Box', remarks: '' },
        { itemId: item('ITM-0012').id, description: item('ITM-0012').description, qty: 30, unit: 'Box', remarks: '' },
      ],
    },
  })

  /* ========== CR-0001: the full cycle, Requested -> Completed ========== */
  run({
    type: 'PR_SEND_RFQ',
    prId: pr1.id,
    supplierIds: [sup('SUP-002').id, sup('SUP-004').id, sup('SUP-001').id],
    subject: `Request for Quotation - ${pr1.prNo} (Ref ${cr1.crNo})`,
    body: rfqBody(s, pr1),
  })

  const vq = (supCode, rows, freight, deliveryDays, quoteRef, terms) =>
    run({
      type: 'VQ_SAVE',
      payload: {
        prId: pr1.id,
        supplierId: sup(supCode).id,
        quoteRef,
        quoteDate: d(21),
        validTill: addDays(today(), 10),
        deliveryDays,
        paymentTerms: terms,
        freight,
        lines: pr1.lines.map((l) => {
          const r = rows[l.itemId] !== undefined ? rows[l.itemId] : null
          return {
            itemId: l.itemId,
            qty: l.qty,
            rate: r === null ? 0 : r,
            taxPct: s.items.find((i) => i.id === l.itemId).taxPct,
            notQuoted: r === null,
          }
        }),
      },
    })

  const [i1, i7, i10] = [item('ITM-0001').id, item('ITM-0007').id, item('ITM-0010').id]
  vq('SUP-002', { [i1]: 1180, [i7]: 2380, [i10]: 295 }, 250, 6, 'GIS/Q/2026/771', '30 days')
  vq('SUP-004', { [i1]: 1240, [i7]: 2210, [i10]: 320 }, 0, 9, 'PMA-QT-2261', '15 days')
  vq('SUP-001', { [i1]: 1150, [i7]: null, [i10]: 290 }, 180, 4, 'SVT/2026/449', 'Advance')

  run({ type: 'QC_CREATE', prId: pr1.id })
  const qc1 = s.quotationComparisons.find((q) => q.prId === pr1.id)
  run({ type: 'QC_APPROVE', qcId: qc1.id, selectedVqId: qc1.bestVqId, overrideReason: '' })

  const selVq = s.vendorQuotations.find((v) => v.id === qc1.bestVqId)
  const markup1 = cust('CUS-001').markupPct
  run({
    type: 'QC_SEND_TO_CUSTOMER',
    qcId: qc1.id,
    validTill: addDays(today(), 10),
    lines: selVq.lines.map((l) => ({
      itemId: l.itemId,
      qty: l.qty,
      supplierRate: l.rate,
      customerPrice: defaultCustomerPrice(l.rate, markup1),
      taxPct: l.taxPct,
    })),
    subject: `Quotation for your enquiry ${cr1.reference}`,
    body: 'Dear Sir,\n\nThank you for your enquiry. Please find our offer attached. Prices are ex-works and exclusive of GST.\n\nRegards,\nToolsphoppe',
  })
  const cq1 = s.customerQuotations.find((q) => q.crId === cr1.id)
  run({ type: 'CQ_SET_STATUS', cqId: cq1.id, status: 'Accepted' })

  run({
    type: 'SO_CREATE',
    payload: {
      cqId: cq1.id,
      date: d(16),
      customerPoNo: 'BEW/PO/2026/117',
      customerPoDate: d(16),
      deliveryDate: d(4),
      lines: cq1.lines.map((l) => ({ itemId: l.itemId, qty: l.qty, price: l.customerPrice })),
    },
  })
  const so1 = s.salesOrders.find((x) => x.crId === cr1.id)
  const po1 = s.purchaseOrders.find((x) => x.crId === cr1.id)

  run({
    type: 'PO_SEND',
    poId: po1.id,
    subject: `Purchase Order ${po1.poNo}`,
    body: poBody(s, po1),
  })

  run({
    type: 'GRN_CREATE',
    payload: {
      poId: po1.id,
      date: d(8),
      supplierRef: 'GIS/DC/2026/1188',
      receivedBy: 'Stores - Mani',
      remarks: 'All items received in good condition.',
      lines: po1.lines.map((l) => ({
        itemId: l.itemId,
        receivedQty: l.qty,
        acceptedQty: l.qty,
        rejectedQty: 0,
        rate: l.rate,
      })),
    },
  })
  const grn1 = s.grns.find((x) => x.crId === cr1.id)
  const inw1 = s.inwards.find((x) => x.crId === cr1.id)
  run({ type: 'INW_ADD_TO_STOCK', inwId: inw1.id })

  run({
    type: 'OUT_CREATE',
    payload: {
      soId: so1.id,
      date: d(6),
      dcNo: 'TS/DC/2026/0341',
      mode: 'Road',
      vehicle: 'TN 09 BX 4471',
      remarks: 'Delivered to Plant 2 stores.',
      lines: so1.lines.map((l) => ({ itemId: l.itemId, qty: l.qty, price: l.price })),
    },
  })
  const out1 = s.outwards.find((x) => x.crId === cr1.id)

  run({
    type: 'SI_CREATE',
    payload: {
      outId: out1.id,
      date: d(6),
      paymentTerms: cust('CUS-001').paymentTerms,
      dueDate: addDays(d(6), 30),
    },
  })
  run({
    type: 'PI_CREATE',
    payload: {
      grnId: grn1.id,
      date: d(7),
      supplierInvNo: 'GIS/2026/3391',
      supplierInvDate: d(8),
      dueDate: addDays(d(8), 30),
    },
  })

  /* ===== CR-0002: RFQ sent, two quotations in — ready to compare ===== */
  run({
    type: 'PR_SEND_RFQ',
    prId: pr2.id,
    supplierIds: [sup('SUP-001').id, sup('SUP-003').id],
    subject: `Request for Quotation - ${pr2.prNo} (Ref ${cr2.crNo})`,
    body: rfqBody(s, pr2),
  })
  const [i4, i5, i6] = [item('ITM-0004').id, item('ITM-0005').id, item('ITM-0006').id]
  const vq2 = (supCode, rows, freight, deliveryDays, quoteRef, terms) =>
    run({
      type: 'VQ_SAVE',
      payload: {
        prId: pr2.id,
        supplierId: sup(supCode).id,
        quoteRef,
        quoteDate: d(6),
        validTill: addDays(today(), 20),
        deliveryDays,
        paymentTerms: terms,
        freight,
        lines: pr2.lines.map((l) => ({
          itemId: l.itemId,
          qty: l.qty,
          rate: rows[l.itemId],
          taxPct: s.items.find((i) => i.id === l.itemId).taxPct,
          notQuoted: false,
        })),
      },
    })
  vq2('SUP-001', { [i4]: 640, [i5]: 385, [i6]: 745 }, 150, 5, 'SVT/2026/512', '30 days')
  vq2('SUP-003', { [i4]: 615, [i5]: 398, [i6]: 720 }, 0, 8, 'MHA/Q/2026/88', '15 days')

  /* CR-0003 is left at Requested so the RFQ step can be demonstrated. */

  /* ===== CR-0004: Quotation accepted by Bharat Engineering Works, ready for Customer PO (SP-06) ===== */
  run({
    type: 'CR_CREATE',
    payload: {
      date: d(4),
      customerId: cust('CUS-001').id,
      requiredBy: addDays(today(), 10),
      reference: 'BEW/REQ/2026/099',
      remarks: 'Replenishment tools per test SP-06.',
      lines: [
        { itemId: item('ITM-0001').id, description: item('ITM-0001').description, qty: 10, unit: 'Set', remarks: '' },
      ],
    },
  })
  const cr4 = last('customerRequests')
  const pr4 = s.purchaseRequests.find((p) => p.crId === cr4.id)
  run({
    type: 'PR_SEND_RFQ',
    prId: pr4.id,
    supplierIds: [sup('SUP-002').id],
    subject: `Request for Quotation - ${pr4.prNo} (Ref ${cr4.crNo})`,
    body: rfqBody(s, pr4),
  })
  run({
    type: 'VQ_SAVE',
    payload: {
      prId: pr4.id,
      supplierId: sup('SUP-002').id,
      quoteRef: 'GIS/Q/2026/77',
      quoteDate: d(3),
      validTill: addDays(today(), 15),
      deliveryDays: 5,
      paymentTerms: '30 days',
      freight: 100,
      lines: [{ itemId: item('ITM-0001').id, qty: 10, rate: 850, taxPct: 18, notQuoted: false }],
    },
  })
  const vq4 = s.vendorQuotations.find((v) => v.prId === pr4.id)
  run({ type: 'QC_CREATE', prId: pr4.id })
  const qc4 = s.quotationComparisons.find((q) => q.prId === pr4.id)
  run({
    type: 'QC_APPROVE',
    qcId: qc4.id,
    selectedVqId: vq4.id,
    overrideReason: 'Approved for test order',
  })
  run({
    type: 'QC_SEND_TO_CUSTOMER',
    qcId: qc4.id,
    validTill: addDays(today(), 15),
    lines: [{ itemId: item('ITM-0001').id, qty: 10, supplierRate: 850, customerPrice: 978, taxPct: 18 }],
    subject: `Quotation for ${cr4.reference}`,
    body: 'Please find our offer attached.',
  })
  const cq4 = s.customerQuotations.find((q) => q.crId === cr4.id)
  run({ type: 'CQ_SET_STATUS', cqId: cq4.id, status: 'Accepted' })

  /* ===== CR-0005: Order with inward stock on hand (10 Qty), ready for Outward (SP-08) ===== */
  run({
    type: 'CR_CREATE',
    payload: {
      date: d(8),
      customerId: cust('CUS-001').id,
      requiredBy: addDays(today(), 5),
      reference: 'BEW/REQ/2026/088',
      remarks: 'Tools order for assembly shop. Ready for dispatch test.',
      lines: [
        { itemId: item('ITM-0001').id, description: item('ITM-0001').description, qty: 10, unit: 'Set', remarks: '' },
      ],
    },
  })
  const cr5 = last('customerRequests')
  const pr5 = s.purchaseRequests.find((p) => p.crId === cr5.id)
  run({
    type: 'PR_SEND_RFQ',
    prId: pr5.id,
    supplierIds: [sup('SUP-002').id],
    subject: `Request for Quotation - ${pr5.prNo}`,
    body: rfqBody(s, pr5),
  })
  run({
    type: 'VQ_SAVE',
    payload: {
      prId: pr5.id,
      supplierId: sup('SUP-002').id,
      quoteRef: 'GIS/Q/2026/88',
      quoteDate: d(6),
      validTill: addDays(today(), 15),
      deliveryDays: 3,
      paymentTerms: '30 days',
      freight: 50,
      lines: [{ itemId: item('ITM-0001').id, qty: 10, rate: 850, taxPct: 18, notQuoted: false }],
    },
  })
  const vq5 = s.vendorQuotations.find((v) => v.prId === pr5.id)
  run({ type: 'QC_CREATE', prId: pr5.id })
  const qc5 = s.quotationComparisons.find((q) => q.prId === pr5.id)
  run({
    type: 'QC_APPROVE',
    qcId: qc5.id,
    selectedVqId: vq5.id,
    overrideReason: 'Approved for test order',
  })
  run({
    type: 'QC_SEND_TO_CUSTOMER',
    qcId: qc5.id,
    validTill: addDays(today(), 15),
    lines: [{ itemId: item('ITM-0001').id, qty: 10, supplierRate: 850, customerPrice: 978, taxPct: 18 }],
    subject: `Quotation for ${cr5.reference}`,
    body: 'Please find our offer attached.',
  })
  const cq5 = s.customerQuotations.find((q) => q.crId === cr5.id)
  run({ type: 'CQ_SET_STATUS', cqId: cq5.id, status: 'Accepted' })
  run({
    type: 'SO_CREATE',
    payload: {
      cqId: cq5.id,
      date: d(4),
      customerPoNo: 'PO-BEW-2026-088',
      customerPoDate: d(4),
      deliveryDate: addDays(today(), 3),
      lines: cq5.lines.map((l) => ({ itemId: l.itemId, qty: l.qty, price: l.customerPrice })),
    },
  })
  const so5 = s.salesOrders.find((x) => x.crId === cr5.id)
  const po5 = s.purchaseOrders.find((x) => x.crId === cr5.id)
  run({
    type: 'PO_SEND',
    poId: po5.id,
    subject: `Purchase Order ${po5.poNo}`,
    body: poBody(s, po5),
  })
  run({
    type: 'GRN_CREATE',
    payload: {
      poId: po5.id,
      date: d(2),
      supplierRef: 'GIS/DC/2026/889',
      receivedBy: 'Stores - Mani',
      remarks: 'All 10 items received in perfect condition.',
      lines: po5.lines.map((l) => ({
        itemId: l.itemId,
        receivedQty: l.qty,
        acceptedQty: l.qty,
        rejectedQty: 0,
        rate: l.rate,
      })),
    },
  })
  const inw5 = s.inwards.find((x) => x.crId === cr5.id)
  run({ type: 'INW_ADD_TO_STOCK', inwId: inw5.id })

  return s
}

export function rfqBody(s, pr) {
  const cr = s.customerRequests.find((x) => x.id === pr.crId)
  const rows = pr.lines
    .map((l, i) => {
      const it = s.items.find((x) => x.id === l.itemId)
      return `${i + 1}. ${it ? it.name : ''} — ${l.qty} ${l.unit || (it && it.unit) || ''}`
    })
    .join('\n')
  return [
    'Dear Sir / Madam,',
    '',
    `Kindly send us your best quotation for the following requirement (our reference ${pr.prNo}):`,
    '',
    rows,
    '',
    cr && cr.requiredBy ? `Required by: ${cr.requiredBy}` : '',
    'Please confirm unit rate, GST, delivery period and validity.',
    '',
    'Regards,',
    'Purchase & Sourcing Department',
    'ToolShoppe Industrial Supply Pvt. Ltd.',
    'tdevendiran123@gmail.com',
  ]
    .filter(Boolean)
    .join('\n')
}

export function poBody(s, po) {
  const supplier = s.suppliers.find((x) => x.id === po.supplierId)
  const rows = po.lines
    .map((l, i) => {
      const it = s.items.find((x) => x.id === l.itemId)
      return `${i + 1}. ${it ? it.name : ''} — ${l.qty} x ${l.rate}`
    })
    .join('\n')
  return [
    `Dear ${supplier ? supplier.contactPerson : 'Sir'},`,
    '',
    `Please treat this as our Purchase Order ${po.poNo} dated ${po.date}, placed against your quotation.`,
    '',
    rows,
    '',
    `Expected delivery: ${po.expectedDelivery}`,
    'Kindly acknowledge receipt of this order.',
    '',
    'Regards,',
    'Purchase & Sourcing Department',
    'ToolShoppe Industrial Supply Pvt. Ltd.',
    'tdevendiran123@gmail.com',
  ].join('\n')
}
