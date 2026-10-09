import React, { useState } from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table, Switch, Alert } from 'antd'
import {
  Check, X, Mail, ShoppingCart, Building2, FileCheck2, Lock, TrendingUp,
} from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { itemName, itemCode, supplierName, getCR } from '../../store/selectors.js'
import { round2, sum } from '../../logic/pricing.js'
import { marginPct } from '../../logic/pricing.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import {
  DocHeader, Card, Grid, KV, Btn, Money, Qty, Pct, EmailPopup, useConfirm, useToast, fmtDate, inr,
} from '../../components/ui/index.js'

export default function QuotationView() {
  const { id } = useParams()
  const nav = useNavigate()
  const { state, dispatch } = useApp()
  const confirm = useConfirm()
  const toast = useToast()
  const [showSourcing, setShowSourcing] = useState(false)
  const [resend, setResend] = useState(false)

  const cq = (state.customerQuotations || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.cqNo) === String(id))
  useDocLabel(cq ? cq.cqNo : null)

  React.useEffect(() => {
    if (cq && String(cq.id) !== String(id) && typeof cq.id !== 'undefined') {
      nav(`/sales/quotation/${cq.id}`, { replace: true })
    }
  }, [cq, id, nav])

  if (!cq) return <Navigate to="/sales/quotation" replace />

  const cust = (state.customers || []).find((c) => String(c.id) === String(cq.customerId))
  const cr = getCR(state, cq.crId)
  const qc = (state.quotationComparisons || []).find((x) => String(x.id) === String(cq.qcId))
  const vq = qc ? (state.vendorQuotations || []).find((v) => String(v.id) === String(qc.selectedVqId)) : null
  const so = (state.salesOrders || []).find((x) => String(x.cqId) === String(cq.id))

  const subtotal = round2(sum(cq.lines, (l) => l.qty * l.customerPrice))
  const tax = round2(sum(cq.lines, (l) => (l.qty * l.customerPrice * (l.taxPct || 0)) / 100))
  const cost = round2(sum(cq.lines, (l) => l.qty * l.supplierRate))

  const setStatus = (status, tone) =>
    confirm({
      title: status === 'Accepted' ? 'Mark quotation as accepted?' : 'Mark quotation as rejected?',
      description:
        status === 'Accepted'
          ? 'The customer has confirmed this offer. You will then be able to record their purchase order.'
          : 'The customer has declined this offer. The request will not move forward.',
      okText: status === 'Accepted' ? 'Mark Accepted' : 'Mark Rejected',
      tone,
      onConfirm: () => {
        dispatch({ type: 'CQ_SET_STATUS', cqId: cq.id, status })
        toast.success(`Quotation marked ${status.toLowerCase()}.`)
      },
    })

  const lineCols = [
    { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
    { title: 'Code', width: 108, render: (_, l) => <span className="doc-no">{itemCode(state, l.itemId)}</span> },
    { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
    { title: 'Quantity', width: 104, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
    { title: 'Price', width: 132, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.customerPrice} /> },
    {
      title: 'Line total',
      width: 148,
      align: 'right',
      className: 'col-num',
      render: (_, l) => <Money value={round2(l.qty * l.customerPrice)} strong />,
    },
  ]

  return (
    <div>
      <DocHeader
        title="Customer Quotation"
        docNo={cq.cqNo}
        status={cq.status}
        subtitle={cust ? `${cust.name} · valid till ${fmtDate(cq.validTill)}` : undefined}
        backTo="/sales/quotation"
        actions={
          <>
            <Btn
              variant={cq.status === 'Draft' ? 'primary' : 'secondary'}
              icon={Mail}
              onClick={() => setResend(true)}
            >
              {cq.status === 'Draft' ? 'Send to Customer' : 'Resend'}
            </Btn>
            {cq.status === 'Sent' && (
              <>
                <Btn variant="success" icon={Check} onClick={() => setStatus('Accepted', 'primary')}>
                  Mark Accepted
                </Btn>
                <Btn variant="dangerGhost" icon={X} onClick={() => setStatus('Rejected', 'danger')}>
                  Mark Rejected
                </Btn>
              </>
            )}
            {cq.status === 'Accepted' && !so && (
              <Btn variant="primary" icon={ShoppingCart} onClick={() => nav(`/sales/customer-po?cq=${cq.id}`)}>
                Create Customer PO
              </Btn>
            )}
            {so && (
              <Btn variant="secondary" icon={ShoppingCart} onClick={() => nav(`/sales/customer-po/${so.id}`)}>
                Open {so.soNo}
              </Btn>
            )}
          </>
        }
      />

      <Grid min={340}>
        <Card title="Customer" icon={Building2}>
          <KV
            items={[
              ['Name', cust ? `${cust.code} — ${cust.name}` : '—'],
              ['Contact', cust ? `${cust.contactPerson} · ${cust.phone}` : ''],
              ['Email', cust ? cust.email : ''],
              ['Billing address', cust ? cust.billingAddress : ''],
              ['GSTIN', cust ? cust.gstin : ''],
            ]}
          />
        </Card>

        <Card title="Quotation information" icon={FileCheck2}>
          <KV
            items={[
              ['Quotation no', <span className="doc-no">{cq.cqNo}</span>],
              ['Date', fmtDate(cq.date)],
              ['Valid till', fmtDate(cq.validTill)],
              ['Against request', <a className="doc-no" onClick={() => nav(`/sales/customer-request/${cq.crId}`)}>{cr ? cr.crNo : '—'}</a>],
              ['Customer reference', cr ? cr.reference : ''],
              ['Payment terms', cust ? cust.paymentTerms : ''],
            ]}
          />
        </Card>

        <Card title="Financial summary" icon={TrendingUp}>
          <KV
            items={[
              ['Subtotal (pre-tax)', <Money value={subtotal} strong />],
              ['GST (added on invoice)', <Money value={tax} muted />],
              ['Grand total', <Money value={round2(subtotal + tax)} strong />],
            ]}
          />
          <div className="fld-help" style={{ marginTop: 10 }}>
            Quotation prices are quoted pre-tax. GST is applied when the sales invoice is raised.
          </div>
        </Card>
      </Grid>

      <Card title="Items offered" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          pagination={false}
          rowKey="itemId"
          dataSource={cq.lines}
          columns={lineCols}
          scroll={{ x: 760 }}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={5} align="right"><strong>Subtotal</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right"><Money value={subtotal} strong /></Table.Summary.Cell>
              </Table.Summary.Row>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={5} align="right">GST (shown on the invoice)</Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right"><Money value={tax} muted /></Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>

      {/* --------------------------- internal sourcing -------------------------- */}
      <Card
        title="Sourcing"
        subtitle="Internal only — never part of the customer document"
        icon={Lock}
        className="card no-print"
        style={{ marginTop: 16 }}
        extra={
          <Switch size="small" checked={showSourcing} onChange={setShowSourcing} checkedChildren="shown" unCheckedChildren="hidden" />
        }
      >
        {showSourcing ? (
          <>
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 14 }}
              message="Supplier rates and margin are for internal use. They are never shown to the customer."
            />
            <Grid min={300}>
              <KV
                items={[
                  ['Selected supplier', vq ? supplierName(state, vq.supplierId) : '—'],
                  ['Their quotation', vq ? `${vq.vqNo} · ${vq.deliveryDays} days` : '—'],
                  ['Purchase cost', <Money value={cost} />],
                  ['Quoted to customer', <Money value={subtotal} />],
                  [
                    'Expected margin',
                    <span>
                      <Money value={round2(subtotal - cost)} tone="pos" strong />
                      <span className="dim" style={{ marginLeft: 8 }}><Pct value={marginPct(subtotal, cost)} /></span>
                    </span>,
                  ],
                ]}
              />
              <div className="tbl-card" style={{ boxShadow: 'none' }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="itemId"
                  dataSource={cq.lines}
                  columns={[
                    { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
                    { title: 'Cost', width: 116, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.supplierRate} /> },
                    { title: 'Price', width: 116, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.customerPrice} /> },
                    {
                      title: 'Margin',
                      width: 104,
                      align: 'right',
                      className: 'col-num',
                      render: (_, l) => <Pct value={marginPct(l.customerPrice, l.supplierRate)} tone="auto" />,
                    },
                  ]}
                />
              </div>
            </Grid>
          </>
        ) : (
          <div className="muted" style={{ fontSize: 13 }}>
            Supplier rates and expected margin are hidden. Toggle to reveal them.
          </div>
        )}
      </Card>

      <EmailPopup
        open={resend}
        title={cq.status === 'Draft' ? `Send quotation ${cq.cqNo}` : `Resend quotation ${cq.cqNo}`}
        okText={cq.status === 'Draft' ? 'Send to Customer' : 'Resend quotation'}
        recipients={cust ? [cust.email] : []}
        defaultSubject={`Quotation ${cq.cqNo} — ${cr ? cr.reference || cr.crNo : ''}`}
        defaultBody={`Dear Sir,\n\nPlease find our quotation ${cq.cqNo} dated ${fmtDate(cq.date)}, valid till ${fmtDate(
          cq.validTill
        )}. Total value ${inr(subtotal)} (excluding GST).\n\nRegards,\nSales & Sourcing Department\nToolShoppe Industrial Supply Pvt. Ltd.\ntdevendiran123@gmail.com`}
        onCancel={() => setResend(false)}
        onSend={({ subject, body }) => {
          dispatch({ type: 'CQ_RESEND', cqId: cq.id, subject, body })
          toast.success(cq.status === 'Draft' ? 'Quotation sent to customer successfully!' : 'Quotation email resent — see the Email Log.')
          setResend(false)
        }}
      />
    </div>
  )
}
