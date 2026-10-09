import React, { useState } from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table, Segmented, Row, Col, Input, Select, Tag } from 'antd'
import {
  Building2,
  Link2,
  ReceiptText,
  Printer,
  FileText,
  CreditCard,
  CheckCircle,
  Truck,
  IndianRupee,
} from 'lucide-react'
import { useStore, useApp } from '../../store/AppContext.jsx'
import { itemName, itemCode, getCR, getItem } from '../../store/selectors.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import {
  DocHeader,
  Card,
  Grid,
  KV,
  Money,
  Qty,
  Pct,
  fmtDate,
  Btn,
  FormModal,
  Field,
  FormSection,
  DateField,
  useToast,
} from '../../components/ui/index.js'
import { amountInWords, round2, inr } from '../../logic/pricing.js'
import { today } from '../../store/reducer.js'

export default function SalesInvoiceView() {
  const { id } = useParams()
  const nav = useNavigate()
  const { state: s, dispatch } = useApp()
  const toast = useToast()

  const [viewMode, setViewMode] = useState('tax_invoice') // 'overview' | 'tax_invoice'
  const [payModalOpen, setPayModalOpen] = useState(false)
  const [payDraft, setPayDraft] = useState({
    paymentDate: today(),
    paymentMode: 'NEFT',
    refNo: '',
    amount: '',
    remarks: '',
  })

  const si = (s.salesInvoices || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.siNo) === String(id))
  useDocLabel(si ? si.siNo : null)

  React.useEffect(() => {
    if (si && String(si.id) !== String(id) && typeof si.id !== 'undefined') {
      nav(`/sales/invoice/${si.id}`, { replace: true })
    }
  }, [si, id, nav])

  if (!si) return <Navigate to="/sales/invoice" replace />

  const cust = (s.customers || []).find((c) => String(c.id) === String(si.customerId))
  const so = (s.salesOrders || []).find((x) => String(x.id) === String(si.soId))
  const out = (s.outwards || []).find((x) => String(x.id) === String(si.outId))
  const cr = getCR(s, si.crId)

  const balanceDue = round2((Number(si.total) || 0) - (Number(si.paidAmount) || 0))

  const openPaymentModal = () => {
    setPayDraft({
      paymentDate: today(),
      paymentMode: 'NEFT',
      refNo: `UTR-${Date.now().toString().slice(-6)}`,
      amount: balanceDue > 0 ? balanceDue : Number(si.total) || 0,
      remarks: 'Payment received against Tax Invoice',
    })
    setPayModalOpen(true)
  }

  const handleRecordPayment = () => {
    if (!payDraft.amount || Number(payDraft.amount) <= 0) {
      return toast.warning('Please enter a valid payment amount.')
    }
    dispatch({
      type: 'SI_RECORD_PAYMENT',
      payload: {
        id: si.id,
        paymentDate: payDraft.paymentDate,
        paymentMode: payDraft.paymentMode,
        refNo: payDraft.refNo,
        amount: Number(payDraft.amount),
        remarks: payDraft.remarks,
      },
    })
    toast.success('Payment recorded successfully.')
    setPayModalOpen(false)
  }

  // Pre-calculate line item taxes for GST schedule
  const enrichedLines = (si.lines || []).map((l, idx) => {
    const item = getItem(s, l.itemId)
    const taxable = Number(l.taxable) || round2(l.qty * (l.rate || l.price || 0))
    const taxPct = Number(l.taxPct) || (item ? item.taxPct : 18)
    const taxAmt = Number(l.taxAmount) || round2((taxable * taxPct) / 100)
    // Inter-state check (ToolShoppe is in TN: code 33)
    const custState = (cust?.billingAddress || '').toLowerCase()
    const isInterstate = custState.includes('karnataka') || custState.includes('andhra') || custState.includes('maharashtra')
    
    return {
      sNo: idx + 1,
      code: itemCode(s, l.itemId),
      name: itemName(s, l.itemId),
      hsn: l.hsn || (item ? item.hsn : '8207'),
      qty: l.qty,
      unit: l.unit || (item ? item.unit : 'NOS'),
      rate: l.rate || l.price || 0,
      taxable,
      taxPct,
      taxAmt,
      isInterstate,
      cgstPct: isInterstate ? 0 : taxPct / 2,
      cgstAmt: isInterstate ? 0 : round2(taxAmt / 2),
      sgstPct: isInterstate ? 0 : taxPct / 2,
      sgstAmt: isInterstate ? 0 : round2(taxAmt / 2),
      igstPct: isInterstate ? taxPct : 0,
      igstAmt: isInterstate ? taxAmt : 0,
      total: Number(l.total) || round2(taxable + taxAmt),
    }
  })

  const totalTaxable = round2(enrichedLines.reduce((acc, l) => acc + l.taxable, 0))
  const totalCGST = round2(enrichedLines.reduce((acc, l) => acc + l.cgstAmt, 0))
  const totalSGST = round2(enrichedLines.reduce((acc, l) => acc + l.sgstAmt, 0))
  const totalIGST = round2(enrichedLines.reduce((acc, l) => acc + l.igstAmt, 0))
  const grandTotal = Number(si.total) || round2(totalTaxable + totalCGST + totalSGST + totalIGST)

  const headerActions = (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <Segmented
        className="no-print"
        value={viewMode}
        onChange={setViewMode}
        options={[
          { label: 'Official Tax Invoice', value: 'tax_invoice', icon: <FileText size={14} /> },
          { label: 'Data Overview', value: 'overview', icon: <ReceiptText size={14} /> },
        ]}
      />
      {si.status !== 'Paid' && (
        <Btn variant="primary" icon={CreditCard} onClick={openPaymentModal} className="no-print">
          Record Payment
        </Btn>
      )}
      <Btn variant="secondary" icon={Printer} onClick={() => window.print()} className="no-print">
        Print / PDF
      </Btn>
    </div>
  )

  return (
    <div>
      <DocHeader
        title="Sales Invoice"
        docNo={si.siNo}
        status={si.status}
        subtitle={cust ? `${cust.name} · due ${fmtDate(si.dueDate)}` : undefined}
        backTo="/sales/invoice"
        actions={headerActions}
        showPrint={false}
      />

      {/* Payment Success Banner if fully or partially paid */}
      {si.status === 'Paid' && (
        <div
          className="no-print"
          style={{
            background: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#065f46',
            borderRadius: 8,
            padding: '10px 16px',
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle size={18} color="#059669" />
            <span style={{ fontWeight: 600 }}>Payment Received in Full ({inr(si.total)})</span>
          </div>
          {si.payments && si.payments.length > 0 && (
            <span style={{ fontSize: 13, color: '#047857' }}>
              Ref: {si.payments[si.payments.length - 1].refNo} ({si.payments[si.payments.length - 1].mode})
            </span>
          )}
        </div>
      )}

      {/* -------------------- 1. OFFICIAL GST TAX INVOICE FORMAT -------------------- */}
      {(viewMode === 'tax_invoice' || typeof window !== 'undefined') && (
        <div
          className={`tax-invoice-sheet ${viewMode !== 'tax_invoice' ? 'print-only' : ''}`}
          style={{
            background: '#ffffff',
            border: '1px solid #cbd5e1',
            borderRadius: 8,
            padding: '32px 36px',
            maxWidth: 1020,
            margin: '0 auto 24px',
            boxShadow: '0 4px 18px rgba(0, 0, 0, 0.04)',
            color: '#0f172a',
            fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
          }}
        >
          {/* Header Title Banner */}
          <div
            style={{
              textAlign: 'center',
              borderBottom: '2px solid #0f766e',
              paddingBottom: 12,
              marginBottom: 16,
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, color: '#0f766e', textTransform: 'uppercase' }}>
              FORM GST INV-1 · ORIGINAL FOR RECIPIENT
            </div>
            <h2 style={{ margin: '4px 0 0', fontSize: 24, fontWeight: 800, color: '#0f172a' }}>TAX INVOICE</h2>
          </div>

          {/* Company & Invoice Top Section */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1.2fr 1fr',
              gap: 20,
              paddingBottom: 16,
              borderBottom: '1px solid #e2e8f0',
              marginBottom: 16,
            }}
          >
            <div>
              <div style={{ fontSize: 18, fontWeight: 800, color: '#0f766e' }}>
                TOOLSHOPPE INDUSTRIAL SUPPLY PVT. LTD.
              </div>
              <div style={{ fontSize: 12.5, color: '#475569', marginTop: 3, lineHeight: 1.4 }}>
                Plot No. 42, SIDCO Industrial Estate, Ambattur, Chennai - 600058, Tamil Nadu<br />
                <strong>GSTIN:</strong> 33AAAAA0000A1Z5 &nbsp;|&nbsp; <strong>State Code:</strong> 33 (Tamil Nadu)<br />
                <strong>Email:</strong> billing@toolshoppe.com &nbsp;|&nbsp; <strong>Phone:</strong> +91 44 2625 9000
              </div>
            </div>

            <div
              style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: 6,
                padding: '10px 14px',
                fontSize: 12.5,
              }}
            >
              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '4px 8px' }}>
                <span style={{ color: '#64748b' }}>Invoice No:</span>
                <strong style={{ color: '#0f766e', fontSize: 14 }}>{si.siNo}</strong>
                <span style={{ color: '#64748b' }}>Invoice Date:</span>
                <strong>{fmtDate(si.date)}</strong>
                <span style={{ color: '#64748b' }}>Due Date:</span>
                <strong>{fmtDate(si.dueDate)}</strong>
                <span style={{ color: '#64748b' }}>Payment Terms:</span>
                <span>{si.paymentTerms || '30 Days Net'}</span>
              </div>
            </div>
          </div>

          {/* 4-Column Metadata Matrix: Billed To / Shipped To / Dispatch Details / Order Details */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 16,
              fontSize: 12.5,
              marginBottom: 20,
            }}
          >
            {/* Bill To */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 6, padding: '10px 14px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6 }}>
                Details of Receiver (Billed To)
              </div>
              <div style={{ fontWeight: 700, fontSize: 13.5, color: '#0f172a' }}>{cust ? cust.name : '—'}</div>
              <div style={{ color: '#475569', marginTop: 2, whiteSpace: 'pre-line', lineHeight: 1.4 }}>
                {cust?.billingAddress || 'Industrial Area, Bangalore, Karnataka'}
              </div>
              <div style={{ marginTop: 6, fontSize: 12 }}>
                <strong>GSTIN:</strong> {cust?.gstin || '29ABCDE1234F1Z5'}<br />
                <strong>Contact:</strong> {cust?.contactPerson || 'Purchase Manager'} ({cust?.phone || '+91 98765 43210'})
              </div>
            </div>

            {/* Ship To & Dispatch Details */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 6, padding: '10px 14px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6 }}>
                Shipment & Reference Details
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '3px 8px' }}>
                <span style={{ color: '#64748b' }}>Delivery Challan:</span>
                <strong>{out ? `${out.outNo} (${out.dcNo || 'DC-POSTED'})` : '—'}</strong>
                <span style={{ color: '#64748b' }}>Dispatch Date:</span>
                <span>{out ? fmtDate(out.date) : '—'}</span>
                <span style={{ color: '#64748b' }}>Transport Mode:</span>
                <span>Road ({out?.vehicleNo || 'KA 01 AB 9988'})</span>
                <span style={{ color: '#64748b' }}>Customer PO No:</span>
                <strong>{so ? `${so.soNo} · ${so.customerPoNo}` : '—'}</strong>
                <span style={{ color: '#64748b' }}>Internal Ref:</span>
                <span>CR No: {cr ? cr.crNo : '—'}</span>
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: 12,
              marginBottom: 16,
              border: '1px solid #cbd5e1',
            }}
          >
            <thead>
              <tr style={{ background: '#f1f5f9', borderBottom: '1px solid #cbd5e1' }}>
                <th style={{ padding: '8px 6px', textAlign: 'center', width: 36 }}>#</th>
                <th style={{ padding: '8px 10px', textAlign: 'left' }}>Description of Goods</th>
                <th style={{ padding: '8px 8px', textAlign: 'center', width: 68 }}>HSN</th>
                <th style={{ padding: '8px 8px', textAlign: 'right', width: 64 }}>Qty</th>
                <th style={{ padding: '8px 8px', textAlign: 'right', width: 85 }}>Unit Rate</th>
                <th style={{ padding: '8px 8px', textAlign: 'right', width: 95 }}>Taxable (₹)</th>
                <th style={{ padding: '8px 8px', textAlign: 'right', width: 85 }}>CGST (₹)</th>
                <th style={{ padding: '8px 8px', textAlign: 'right', width: 85 }}>SGST (₹)</th>
                <th style={{ padding: '8px 10px', textAlign: 'right', width: 110 }}>Total (₹)</th>
              </tr>
            </thead>
            <tbody>
              {enrichedLines.map((l) => (
                <tr key={l.sNo} style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '8px 6px', textAlign: 'center', color: '#64748b' }}>{l.sNo}</td>
                  <td style={{ padding: '8px 10px' }}>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>{l.name}</div>
                    <div style={{ fontSize: 11, color: '#64748b' }}>Code: {l.code}</div>
                  </td>
                  <td style={{ padding: '8px 8px', textAlign: 'center', fontFamily: 'monospace' }}>{l.hsn}</td>
                  <td style={{ padding: '8px 8px', textAlign: 'right' }}>
                    <strong>{l.qty}</strong> <span style={{ fontSize: 10, color: '#64748b' }}>{l.unit}</span>
                  </td>
                  <td style={{ padding: '8px 8px', textAlign: 'right', fontFamily: 'monospace' }}>
                    {l.rate.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ padding: '8px 8px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                    {l.taxable.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ padding: '8px 8px', textAlign: 'right', fontFamily: 'monospace', color: '#475569' }}>
                    <div>{l.cgstAmt.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <div style={{ fontSize: 10, color: '#94a3b8' }}>({l.cgstPct}%)</div>
                  </td>
                  <td style={{ padding: '8px 8px', textAlign: 'right', fontFamily: 'monospace', color: '#475569' }}>
                    <div>{l.sgstAmt.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <div style={{ fontSize: 10, color: '#94a3b8' }}>({l.sgstPct}%)</div>
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 700, color: '#0f766e' }}>
                    {l.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ background: '#f8fafc', borderTop: '2px solid #cbd5e1', fontWeight: 700 }}>
                <td colSpan={5} style={{ padding: '8px 10px', textAlign: 'right' }}>
                  Total Taxable & Taxes:
                </td>
                <td style={{ padding: '8px 8px', textAlign: 'right', fontFamily: 'monospace' }}>
                  ₹ {totalTaxable.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
                <td style={{ padding: '8px 8px', textAlign: 'right', fontFamily: 'monospace' }}>
                  ₹ {totalCGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
                <td style={{ padding: '8px 8px', textAlign: 'right', fontFamily: 'monospace' }}>
                  ₹ {totalSGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
                <td style={{ padding: '8px 10px', textAlign: 'right', fontFamily: 'monospace', fontSize: 13, color: '#0f766e' }}>
                  ₹ {grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
              </tr>
            </tfoot>
          </table>

          {/* Amount In Words & Financial Summary */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1.4fr 1fr',
              gap: 20,
              padding: '12px 14px',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: 6,
              marginBottom: 18,
            }}
          >
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                Invoice Amount in Words
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', marginTop: 4 }}>
                {amountInWords(grandTotal)}
              </div>
              <div style={{ fontSize: 11.5, color: '#64748b', marginTop: 6 }}>
                Tax Amount in Words: {amountInWords(totalCGST + totalSGST + totalIGST)}
              </div>
            </div>

            <div style={{ fontSize: 12.5 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 6, borderBottom: '1px solid #e2e8f0', paddingBottom: 6 }}>
                <span>Subtotal (Taxable Value):</span>
                <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>₹ {totalTaxable.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 6, borderBottom: '1px solid #e2e8f0', padding: '6px 0', color: '#475569' }}>
                <span>Central GST (CGST):</span>
                <span style={{ fontFamily: 'monospace' }}>₹ {totalCGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 6, borderBottom: '1px solid #e2e8f0', padding: '6px 0', color: '#475569' }}>
                <span>State GST (SGST):</span>
                <span style={{ fontFamily: 'monospace' }}>₹ {totalSGST.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 6, paddingTop: 6, fontSize: 14, fontWeight: 800, color: '#0f766e' }}>
                <span>Grand Total (INR):</span>
                <span style={{ fontFamily: 'monospace' }}>₹ {grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>
          </div>

          {/* Bank Details & Terms & Authorized Signatory */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 20,
              fontSize: 12,
              borderTop: '1px solid #cbd5e1',
              paddingTop: 16,
            }}
          >
            <div>
              <div style={{ fontWeight: 700, color: '#334155', marginBottom: 4 }}>Company Bank Account Details:</div>
              <div style={{ color: '#475569', lineHeight: 1.5 }}>
                <strong>Bank Name:</strong> HDFC Bank Ltd<br />
                <strong>A/c Name:</strong> ToolShoppe Industrial Supply Pvt. Ltd.<br />
                <strong>A/c Number:</strong> 5020 0012 3456 78<br />
                <strong>IFSC Code:</strong> HDFC0000240<br />
                <strong>Branch:</strong> Ambattur Industrial Estate, Chennai
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 10 }}>
                <strong>Declaration:</strong> We declare that this invoice shows the actual price of the goods described
                and that all particulars are true and correct.
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', alignItems: 'flex-end', textAlign: 'right' }}>
              <div>
                <div style={{ fontWeight: 700, color: '#0f172a' }}>For TOOLSHOPPE INDUSTRIAL SUPPLY PVT. LTD.</div>
                <div style={{ fontSize: 11, color: '#64748b' }}>Authorised Signatory</div>
              </div>
              <div style={{ marginTop: 42, borderTop: '1px dashed #94a3b8', width: 180, textAlign: 'center', paddingTop: 4, color: '#64748b', fontSize: 11 }}>
                Authorised Signatory
              </div>
            </div>
          </div>
        </div>
      )}

      {/* -------------------- 2. STANDARD DATA OVERVIEW -------------------- */}
      {viewMode === 'overview' && (
        <>
          <Grid min={340}>
            <Card title="Bill to" icon={Building2}>
              <KV
                items={[
                  ['Customer', cust ? cust.name : '—'],
                  ['Address', cust ? cust.billingAddress : ''],
                  ['GSTIN', cust ? cust.gstin : ''],
                  ['Contact', cust ? `${cust.contactPerson} · ${cust.phone}` : ''],
                ]}
              />
            </Card>

            <Card title="Invoice information" icon={ReceiptText}>
              <KV
                items={[
                  ['Invoice no', <span className="doc-no">{si.siNo}</span>],
                  ['Invoice date', fmtDate(si.date)],
                  ['Payment terms', si.paymentTerms],
                  ['Due date', fmtDate(si.dueDate)],
                  [
                    'Payment status',
                    <Tag color={si.status === 'Paid' ? 'green' : si.status === 'Partially Paid' ? 'orange' : 'blue'}>
                      {si.status}
                    </Tag>,
                  ],
                ]}
              />
            </Card>

            <Card title="References" icon={Link2}>
              <KV
                items={[
                  [
                    'Customer PO',
                    <a className="doc-no" onClick={() => nav(`/sales/customer-po/${si.soId}`)}>
                      {so ? `${so.soNo} (${so.customerPoNo})` : '—'}
                    </a>,
                  ],
                  [
                    'Outward',
                    <a className="doc-no" onClick={() => nav(`/sales/outward/${si.outId}`)}>
                      {out ? `${out.outNo} — DC ${out.dcNo || 'DC-001'}` : '—'}
                    </a>,
                  ],
                  [
                    'Customer request',
                    <a className="doc-no" onClick={() => nav(`/sales/customer-request/${si.crId}`)}>
                      {cr ? cr.crNo : '—'}
                    </a>,
                  ],
                ]}
              />
            </Card>
          </Grid>

          <Card title="Invoice lines" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
            <Table
              size="small"
              pagination={false}
              rowKey="itemId"
              dataSource={si.lines}
              scroll={{ x: 1020 }}
              columns={[
                { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
                { title: 'Code', width: 106, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
                { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
                { title: 'HSN', width: 102, dataIndex: 'hsn', render: (v) => <span className="num muted">{v || '8207'}</span> },
                { title: 'Qty', width: 92, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
                { title: 'Rate', width: 116, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.rate || l.price} /> },
                { title: 'Taxable', width: 128, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.taxable} /> },
                { title: 'Tax %', width: 88, align: 'right', className: 'col-num', render: (_, l) => <Pct value={l.taxPct} /> },
                { title: 'Tax amount', width: 124, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.taxAmount} muted /> },
                { title: 'Total', width: 140, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.total} strong /> },
              ]}
              summary={() => (
                <Table.Summary>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={9} align="right">Taxable value</Table.Summary.Cell>
                    <Table.Summary.Cell index={9} align="right"><Money value={si.subtotal} /></Table.Summary.Cell>
                  </Table.Summary.Row>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={9} align="right">GST (CGST + SGST)</Table.Summary.Cell>
                    <Table.Summary.Cell index={9} align="right"><Money value={si.tax} /></Table.Summary.Cell>
                  </Table.Summary.Row>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={9} align="right"><strong>Invoice total</strong></Table.Summary.Cell>
                    <Table.Summary.Cell index={9} align="right"><Money value={si.total} strong /></Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              )}
            />
          </Card>
        </>
      )}

      {/* -------------------- RECORD PAYMENT MODAL -------------------- */}
      <FormModal
        open={payModalOpen}
        title={`Record Payment for ${si.siNo}`}
        subtitle={`Invoice Total: ${inr(si.total)} · Outstanding: ${inr(balanceDue)}`}
        onCancel={() => setPayModalOpen(false)}
        onOk={handleRecordPayment}
        okText="Confirm Payment"
        width={560}
      >
        <FormSection title="Payment Details">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Field label="Payment Date" required>
                <DateField value={payDraft.paymentDate} onChange={(v) => setPayDraft({ ...payDraft, paymentDate: v })} />
              </Field>
            </Col>
            <Col xs={24} md={12}>
              <Field label="Payment Mode" required>
                <Select
                  value={payDraft.paymentMode}
                  onChange={(v) => setPayDraft({ ...payDraft, paymentMode: v })}
                  style={{ width: '100%' }}
                  options={[
                    { value: 'NEFT', label: 'NEFT / RTGS Bank Transfer' },
                    { value: 'UPI', label: 'UPI / Immediate Payment' },
                    { value: 'Cheque', label: 'Cheque Deposit' },
                    { value: 'Cash', label: 'Cash Receipt' },
                  ]}
                />
              </Field>
            </Col>
            <Col xs={24} md={12}>
              <Field label="Amount Received (₹)" required>
                <Input
                  type="number"
                  value={payDraft.amount}
                  onChange={(e) => setPayDraft({ ...payDraft, amount: e.target.value })}
                  placeholder="Enter amount"
                />
              </Field>
            </Col>
            <Col xs={24} md={12}>
              <Field label="UTR / Transaction Ref">
                <Input
                  value={payDraft.refNo}
                  onChange={(e) => setPayDraft({ ...payDraft, refNo: e.target.value })}
                  placeholder="e.g. UTR-889922"
                />
              </Field>
            </Col>
            <Col xs={24}>
              <Field label="Remarks">
                <Input.TextArea
                  rows={2}
                  value={payDraft.remarks}
                  onChange={(e) => setPayDraft({ ...payDraft, remarks: e.target.value })}
                  placeholder="Optional bank or remittance remarks"
                />
              </Field>
            </Col>
          </Row>
        </FormSection>
      </FormModal>
    </div>
  )
}
