import React, { useMemo, useState } from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table, Radio, Input, InputNumber, Alert, Row, Col, Tooltip } from 'antd'
import { Check, Mail, Trophy, GitCompareArrows, Building2, CircleCheck } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { supplierName, itemName, itemCode, customerName, getCR } from '../../store/selectors.js'
import { vqTotals, isComplete, bestRatePerItem } from '../../logic/compare.js'
import { round2, defaultCustomerPrice, marginPct, sum } from '../../logic/pricing.js'
import { addDays, today } from '../../store/reducer.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import {
  DocHeader, Card, Grid, KV, Btn, Money, Qty, Pct, EmailPopup, Field, FormSection,
  DateField, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function ComparisonView() {
  const { id } = useParams()
  const nav = useNavigate()
  const { state, dispatch } = useApp()
  const toast = useToast()

  const qc = state.quotationComparisons.find((x) => x.id === id || String(x.id) === String(id) || String(x.qcNo) === String(id) || (x.localId && String(x.localId) === String(id)))
  const [sel, setSel] = useState(qc ? qc.selectedVqId : null)
  const [reason, setReason] = useState(qc ? qc.overrideReason : '')
  const [sendOpen, setSendOpen] = useState(false)
  const [priceLines, setPriceLines] = useState([])
  const [validTill, setValidTill] = useState(addDays(today(), 15))

  const pr = qc ? state.purchaseRequests.find((p) => p.id === qc.prId || String(p.id) === String(qc.prId)) : null
  const cr = pr ? getCR(state, pr.crId) : (qc && qc.crId ? getCR(state, qc.crId) : null)
  const cust = cr ? state.customers.find((c) => c.id === cr.customerId || String(c.id) === String(cr.customerId)) : null
  const vqs = useMemo(
    () => (qc ? (qc.vqIds || []).map((vid) => state.vendorQuotations.find((v) => v.id === vid || String(v.id) === String(vid))).filter(Boolean) : []),
    [qc, state.vendorQuotations]
  )
  const cellBest = useMemo(() => (pr ? bestRatePerItem(vqs, pr.lines) : {}), [vqs, pr])
  useDocLabel(qc ? qc.qcNo : null)

  if (!qc) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <p className="muted" style={{ fontSize: 15, marginBottom: 16 }}>Comparison not found or loading...</p>
        <Btn variant="primary" onClick={() => nav('/purchase/quotation-comparison')}>Back to Quotation Comparisons</Btn>
      </div>
    )
  }

  if (!pr) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <p className="muted" style={{ fontSize: 15, marginBottom: 16 }}>Linked Purchase Request not found or loading...</p>
        <Btn variant="primary" onClick={() => nav('/purchase/quotation-comparison')}>Back to Quotation Comparisons</Btn>
      </div>
    )
  }

  const approved = qc.status !== 'Draft'
  const selectedVq = state.vendorQuotations.find((v) => v.id === qc.selectedVqId || String(v.id) === String(qc.selectedVqId))
  const cq = state.customerQuotations.find((c) => c.qcId === qc.id || String(c.qcId) === String(qc.id))
  const rateOf = (vq, itemId) => (vq.lines || []).find((l) => l.itemId === itemId)

  /* ------------------------------ comparison grid ----------------------------- */
  const columns = [
    { title: 'S.No', width: 58, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
    {
      title: 'Item',
      width: 250,
      render: (_, l) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 550 }}>{itemName(state, l.itemId)}</div>
          <div className="dim" style={{ fontSize: 11.5 }}>{itemCode(state, l.itemId)}</div>
        </div>
      ),
    },
    { title: 'Qty', width: 84, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
    ...vqs.map((vq) => {
      const complete = isComplete(vq, pr.lines)
      const isBest = qc.bestVqId === vq.id
      return {
        title: (
          <div style={{ textAlign: 'center', padding: '2px 0' }}>
            <div style={{ fontWeight: 650, fontSize: 13 }}>{supplierName(state, vq.supplierId)}</div>
            <div className="dim" style={{ fontSize: 11 }}>{vq.vqNo} · {vq.deliveryDays} days</div>
            <div style={{ marginTop: 5, display: 'flex', gap: 5, justifyContent: 'center', flexWrap: 'wrap' }}>
              {isBest && (
                <span className="badge" style={{ background: 'var(--c-success-light)', color: '#15803D', borderColor: '#BBF7D0' }}>
                  <Trophy size={11} strokeWidth={2.4} /> Best
                </span>
              )}
              {!complete && (
                <Tooltip title="Not every item is quoted, so this offer cannot be recommended.">
                  <span className="badge" style={{ background: 'var(--c-danger-light)', color: '#B91C1C', borderColor: '#FECACA' }}>
                    Incomplete
                  </span>
                </Tooltip>
              )}
            </div>
            <Radio checked={sel === vq.id} disabled={approved} onChange={() => setSel(vq.id)} style={{ marginTop: 6 }}>
              Select
            </Radio>
          </div>
        ),
        className: isBest ? 'best-col' : undefined,
        children: [
          {
            title: 'Rate',
            width: 118,
            align: 'right',
            className: `col-num${isBest ? ' best-col' : ''}`,
            render: (_, l) => {
              const line = rateOf(vq, l.itemId)
              if (!line || line.notQuoted) return <span className="dim">not quoted</span>
              const cheapest = cellBest[l.itemId] === line.rate
              return cheapest ? (
                <Tooltip title="Cheapest rate for this item">
                  <span style={{ color: 'var(--c-success)', fontWeight: 700 }}><Money value={line.rate} /></span>
                </Tooltip>
              ) : (
                <Money value={line.rate} />
              )
            },
          },
          {
            title: 'Line total',
            width: 132,
            align: 'right',
            className: `col-num${isBest ? ' best-col' : ''}`,
            render: (_, l) => {
              const line = rateOf(vq, l.itemId)
              if (!line || line.notQuoted) return <span className="dim">—</span>
              return <Money value={round2(l.qty * line.rate)} />
            },
          },
        ],
      }
    }),
  ]

  const summaryRow = (label, render, strong) => (
    <Table.Summary.Row key={label}>
      <Table.Summary.Cell index={0} colSpan={3} align="right">
        {strong ? <strong>{label}</strong> : label}
      </Table.Summary.Cell>
      {vqs.map((vq, i) => (
        <Table.Summary.Cell
          key={vq.id}
          index={3 + i}
          colSpan={2}
          align="right"
          className={qc.bestVqId === vq.id ? 'best-col' : undefined}
        >
          {render(vq)}
        </Table.Summary.Cell>
      ))}
    </Table.Summary.Row>
  )

  /* ---------------------------------- approve --------------------------------- */
  const approve = () => {
    if (!sel) return toast.warning('Select a supplier column first.')
    if (sel !== qc.bestVqId && !reason.trim()) return toast.warning('Give a reason for not taking the recommended quotation.')
    dispatch({ type: 'QC_APPROVE', qcId: qc.id, selectedVqId: sel, overrideReason: reason })
    toast.success('Comparison approved — the winning quotation is marked selected.')
  }

  /* -------------------------- send quotation to customer ---------------------- */
  const openSend = () => {
    if (!selectedVq) return toast.warning('Please select and approve a quotation first.')
    const markup = cust ? cust.markupPct : 15
    setPriceLines(
      (selectedVq.lines || [])
        .filter((l) => !l.notQuoted)
        .map((l) => ({
          itemId: l.itemId,
          qty: l.qty,
          supplierRate: l.rate,
          customerPrice: defaultCustomerPrice(l.rate, markup),
          taxPct: l.taxPct,
        }))
    )
    setValidTill(addDays(today(), 15))
    setSendOpen(true)
  }

  const send = ({ subject, body }) => {
    if (priceLines.some((l) => !(Number(l.customerPrice) > 0))) return toast.warning('Every line needs a customer price.')
    dispatch({ type: 'QC_SEND_TO_CUSTOMER', qcId: qc.id, lines: priceLines, validTill, subject, body })
    toast.success('Quotation sent — a customer quotation was created in Sales.')
    setSendOpen(false)
  }

  const quoteTotal = sum(priceLines, (l) => l.qty * l.customerPrice)
  const costTotal = sum(priceLines, (l) => l.qty * l.supplierRate)

  return (
    <div>
      <DocHeader
        title="Quotation Comparison"
        docNo={qc.qcNo}
        status={qc.status}
        subtitle={cr ? `${pr?.prNo || ''} · ${cr.crNo || ''} · ${cust ? cust.name : ''}` : pr?.prNo}
        backTo="/purchase/quotation-comparison"
        actions={
          <>
            {!approved && (
              <Btn variant="primary" icon={Check} onClick={approve}>
                Approve Quotation
              </Btn>
            )}
            {qc.status === 'Approved' && (
              <Btn variant="teal" icon={Mail} onClick={openSend}>
                Send to Customer
              </Btn>
            )}
            {qc.status === 'Sent to Customer' && cq && (
              <Btn variant="secondary" icon={Mail} onClick={() => nav(`/sales/quotation/${cq.id}`)}>
                Open {cq.cqNo}
              </Btn>
            )}
          </>
        }
      />

      <Grid min={340}>
        <Card title="Comparing" icon={GitCompareArrows}>
          <KV
            items={[
              ['Purchase request', <a className="doc-no" onClick={() => nav(`/purchase/request/${pr.id}`)}>{pr.prNo}</a>],
              ['Customer request', cr ? <a className="doc-no" onClick={() => nav(`/sales/customer-request/${cr.id}`)}>{cr.crNo}</a> : '—'],
              ['Customer', cust ? cust.name : '—'],
              ['Markup on file', cust ? <Pct value={cust.markupPct} /> : '—'],
              ['Quotations compared', vqs.length],
              ['Approved on', qc.approvedAt ? fmtDate(qc.approvedAt) : <span className="dim">not approved</span>],
            ]}
          />
        </Card>

        <Card title="Selection" icon={CircleCheck}>
          {approved ? (
            <KV
              items={[
                [
                  'Recommended',
                  qc.bestVqId
                    ? supplierName(state, (state.vendorQuotations.find((v) => v.id === qc.bestVqId || String(v.id) === String(qc.bestVqId)) || {}).supplierId)
                    : '—',
                ],
                ['Selected supplier', selectedVq ? `${supplierName(state, selectedVq.supplierId)} — ${selectedVq.vqNo}` : '—'],
                ['Selected total', selectedVq ? <Money value={selectedVq.grandTotal} strong /> : '—'],
                ['Override reason', qc.overrideReason],
              ]}
            />
          ) : (
            <>
              <div className="muted" style={{ fontSize: 13, marginBottom: 10 }}>
                Please select a supplier column below to approve. Pick the recommended column (green) or override by picking a different column — a reason is then required.
              </div>
              <Field label="Reason for override">
                <Input.TextArea
                  rows={3}
                  placeholder="Why is the recommended quotation not being taken?"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  disabled={sel === qc.bestVqId}
                />
              </Field>
            </>
          )}
        </Card>
      </Grid>

      <Card title="Comparison grid" icon={Building2} pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          bordered
          pagination={false}
          rowKey={(r) => r.itemId}
          dataSource={pr.lines}
          columns={columns}
          scroll={{ x: 400 + vqs.length * 250 }}
          summary={() => (
            <Table.Summary>
              {summaryRow('Subtotal', (vq) => <Money value={vqTotals(vq).subtotal} />)}
              {summaryRow('Freight / other', (vq) => <Money value={vqTotals(vq).freight} />)}
              {summaryRow('Tax', (vq) => <Money value={vqTotals(vq).tax} muted />)}
              {summaryRow('Grand total', (vq) => <Money value={vqTotals(vq).grandTotal} strong />, true)}
              {summaryRow('Delivery days', (vq) => <span className="num">{vq.deliveryDays} days</span>)}
              {summaryRow('Payment terms', (vq) => <span className="muted">{vq.paymentTerms || '—'}</span>)}
            </Table.Summary>
          )}
        />
        <div className="card-pad" style={{ paddingTop: 14 }}>
          <div className="fld-help">
            The green column has the lowest grand total among quotations that cover every item. A green rate
            marks the cheapest supplier for that one item, so you can see where a supplier is cheap on part
            of the list only.
          </div>
        </div>
      </Card>

      {/* -------------------- send quotation to customer popup ------------------- */}
      <EmailPopup
        open={sendOpen}
        title="Send quotation to customer"
        okText="Send quotation"
        width={960}
        recipients={cust ? [cust.email] : []}
        defaultSubject={cr ? `Quotation for your enquiry ${cr.reference || cr.crNo}` : 'Quotation'}
        defaultBody={'Dear Sir,\n\nThank you for your enquiry. Please find our offer below. Prices are ex-works and exclusive of GST.\n\nRegards,\nSales & Sourcing Department\nToolShoppe Industrial Supply Pvt. Ltd.\ntdevendiran123@gmail.com'}
        onCancel={() => setSendOpen(false)}
        onSend={send}
      >
        <FormSection>
          <Row gutter={16}>
            <Col xs={12} md={7}>
              <Field label="Customer">
                <Input readOnly value={cust ? cust.name : ''} />
              </Field>
            </Col>
            <Col xs={12} md={5}>
              <Field label="Supplier chosen">
                <Input readOnly value={selectedVq ? supplierName(state, selectedVq.supplierId) : ''} />
              </Field>
            </Col>
            <Col xs={12} md={5}>
              <Field label="Markup applied">
                <Input readOnly value={cust ? `${cust.markupPct} %` : ''} />
              </Field>
            </Col>
            <Col xs={12} md={7}>
              <Field label="Valid till">
                <DateField value={validTill} onChange={setValidTill} />
              </Field>
            </Col>
          </Row>
        </FormSection>

        <FormSection title="Customer pricing">
          <div className="tbl-card" style={{ boxShadow: 'none' }}>
            <Table
              size="small"
              pagination={false}
              rowKey="itemId"
              dataSource={priceLines}
              scroll={{ x: 860 }}
              columns={[
                { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
                { title: 'Qty', width: 86, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
                {
                  title: 'Supplier rate',
                  width: 128,
                  align: 'right',
                  className: 'col-num',
                  render: (_, l) => (
                    <Tooltip title="Internal cost — never changed by this screen">
                      <span><Money value={l.supplierRate} muted /></span>
                    </Tooltip>
                  ),
                },
                {
                  title: 'Customer price',
                  width: 140,
                  render: (_, l, i) => (
                    <InputNumber
                      size="small"
                      min={0}
                      step={0.01}
                      style={{ width: '100%' }}
                      value={l.customerPrice}
                      onChange={(v) => setPriceLines((rows) => rows.map((r, idx) => (idx === i ? { ...r, customerPrice: v } : r)))}
                    />
                  ),
                },
                {
                  title: 'Margin %',
                  width: 104,
                  align: 'right',
                  className: 'col-num',
                  render: (_, l) => <Pct value={marginPct(l.customerPrice, l.supplierRate)} tone="auto" />,
                },
                {
                  title: 'Line total',
                  width: 136,
                  align: 'right',
                  className: 'col-num',
                  render: (_, l) => <Money value={round2(l.qty * l.customerPrice)} />,
                },
              ]}
              summary={() => (
                <Table.Summary>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={5} align="right"><strong>Quotation total (pre-tax)</strong></Table.Summary.Cell>
                    <Table.Summary.Cell index={5} align="right"><Money value={quoteTotal} strong /></Table.Summary.Cell>
                  </Table.Summary.Row>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={5} align="right">Expected margin</Table.Summary.Cell>
                    <Table.Summary.Cell index={5} align="right">
                      <Money value={round2(quoteTotal - costTotal)} tone="pos" strong />
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              )}
            />
          </div>
          <Alert
            style={{ marginTop: 12 }}
            type="info"
            showIcon
            message="Editing a customer price here changes the customer-facing offer only. The supplier rate stays exactly as quoted."
          />
        </FormSection>
      </EmailPopup>
    </div>
  )
}
