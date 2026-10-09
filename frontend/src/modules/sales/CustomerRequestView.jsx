import React from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table } from 'antd'
import { Check, Circle, FileText, Building2, TrendingUp, Link2, PackageSearch } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { crChain, customerName, supplierName, itemName, itemCode } from '../../store/selectors.js'
import { CR_STAGES } from '../../store/reducer.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import { TONE, color } from '../../theme/tokens.js'
import {
  DocHeader, Card, Grid, KV, StatusBadge, RefChip, Money, Qty, Pct,
  EmptyState, fmtDate,
} from '../../components/ui/index.js'

export default function CustomerRequestView() {
  const { id } = useParams()
  const nav = useNavigate()
  const s = useStore()
  const cr = (s.customerRequests || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.crNo) === String(id))
  useDocLabel(cr ? cr.crNo : null)

  React.useEffect(() => {
    if (cr && String(cr.id) !== String(id) && typeof cr.id !== 'undefined') {
      nav(`/sales/customer-request/${cr.id}`, { replace: true })
    }
  }, [cr, id, nav])

  if (!cr) return <Navigate to="/sales/customer-request" replace />

  const ch = crChain(s, cr.id)
  const stageIndex = CR_STAGES.indexOf(cr.stage)
  const cust = s.customers.find((c) => String(c.id) === String(cr.customerId))

  const docs = []
  const push = (label, no, date, status, to) => docs.push({ key: `${label}-${no}`, label, no, date, status, to })
  push('Customer Request', cr.crNo, cr.date, cr.stage, null)
  if (ch.pr) push('Purchase Request', ch.pr.prNo, ch.pr.date, ch.pr.status, `/purchase/request/${ch.pr.id}`)
  ch.vqs.forEach((v) =>
    push(`Vendor Quotation — ${supplierName(s, v.supplierId)}`, v.vqNo, v.quoteDate, v.status, `/purchase/vendor-quotation/${v.id}`)
  )
  if (ch.qc) push('Quotation Comparison', ch.qc.qcNo, ch.qc.date, ch.qc.status, `/purchase/quotation-comparison/${ch.qc.id}`)
  ch.cqs.forEach((q) => push('Customer Quotation', q.cqNo, q.date, q.status, `/sales/quotation/${q.id}`))
  ch.sos.forEach((o) => push('Customer PO', o.soNo, o.date, o.status, `/sales/customer-po/${o.id}`))
  ch.pos.forEach((o) => push('Supplier PO', o.poNo, o.date, o.status, `/purchase/purchase-order/${o.id}`))
  ch.grns.forEach((g) => push('GRN', g.grnNo, g.date, g.status, `/purchase/grn/${g.id}`))
  ch.inwards.forEach((i) => push('Inward', i.inwNo, i.date, i.status, '/purchase/inward'))
  ch.outwards.forEach((o) => push('Outward', o.outNo, o.date, o.status, `/sales/outward/${o.id}`))
  ch.salesInvoices.forEach((i) => push('Sales Invoice', i.siNo, i.date, i.status, `/sales/invoice/${i.id}`))
  ch.purchaseInvoices.forEach((i) => push('Purchase Invoice', i.piNo, i.date, i.status, `/purchase/invoice/${i.id}`))

  return (
    <div>
      <DocHeader
        title="Customer Request"
        docNo={cr.crNo}
        status={cr.stage}
        subtitle="The golden thread — every document below carries this request number."
        backTo="/sales/customer-request"
      />

      {/* ---------------------------- stage timeline --------------------------- */}
      <Card title="Workflow" icon={PackageSearch} pad={false}>
        <div style={{ padding: '18px 20px 20px', overflowX: 'auto' }}>
          <div style={{ display: 'flex', minWidth: 720 }}>
            {CR_STAGES.map((st, i) => {
              const done = i < stageIndex
              const current = i === stageIndex
              const tone = current ? TONE.primary : done ? TONE.success : TONE.neutral
              return (
                <div key={st} style={{ flex: 1, minWidth: 0, position: 'relative' }}>
                  {i > 0 && (
                    <div
                      style={{
                        position: 'absolute', top: 13, left: 'calc(-50% + 14px)', right: 'calc(50% + 14px)',
                        height: 2, background: i <= stageIndex ? color.success : '#E2E8F0',
                      }}
                    />
                  )}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <div
                      style={{
                        width: 28, height: 28, borderRadius: '50%', display: 'grid', placeItems: 'center',
                        background: done ? color.success : current ? color.primary : '#fff',
                        border: `2px solid ${done ? color.success : current ? color.primary : '#E2E8F0'}`,
                        color: done || current ? '#fff' : '#94A3B8',
                        zIndex: 1, flex: 'none',
                        boxShadow: current ? '0 0 0 4px rgba(79,70,229,0.14)' : 'none',
                      }}
                    >
                      {done ? <Check size={15} strokeWidth={3} /> : <Circle size={7} strokeWidth={4} fill="currentColor" />}
                    </div>
                    <div
                      style={{
                        fontSize: 11.5, textAlign: 'center', lineHeight: 1.3, padding: '0 4px',
                        color: current ? tone.fg : done ? '#334155' : 'var(--c-text-muted)',
                        fontWeight: current ? 650 : 500,
                      }}
                    >
                      {st}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </Card>

      <Grid min={340} style={{ marginTop: 16 }}>
        <Card title="Request information" icon={FileText}>
          <KV
            items={[
              ['Request no', <span className="doc-no">{cr.crNo}</span>],
              ['Date', fmtDate(cr.date)],
              ['Required by', fmtDate(cr.requiredBy)],
              ['Customer reference', cr.reference],
              ['Remarks', cr.remarks],
            ]}
          />
        </Card>

        <Card title="Customer" icon={Building2}>
          <KV
            items={[
              ['Name', cust ? `${cust.code} — ${cust.name}` : '—'],
              ['Contact', cust ? `${cust.contactPerson} · ${cust.phone}` : ''],
              ['Email', cust ? cust.email : ''],
              ['GSTIN', cust ? cust.gstin : ''],
              ['Default markup', cust ? <Pct value={cust.markupPct} /> : ''],
            ]}
          />
        </Card>

        <Card title="Financial summary" icon={TrendingUp}>
          <KV
            items={[
              ['Purchase value', <Money value={ch.margin.purchaseValue} />],
              ['Sales value', <Money value={ch.margin.salesValue} />],
              [
                'Margin',
                <span>
                  <Money value={ch.margin.margin} tone={ch.margin.margin >= 0 ? 'pos' : 'neg'} strong />
                  <span className="dim" style={{ marginLeft: 8 }}>
                    <Pct value={ch.margin.marginPct} />
                  </span>
                </span>,
              ],
            ]}
          />
          <div className="fld-help" style={{ marginTop: 10 }}>
            Taken from the stock ledger — inward at the supplier rate, outward at the customer price,
            both tagged {cr.crNo}.
          </div>
        </Card>
      </Grid>

      <Card title="Items requested" icon={FileText} pad={false} style={{ marginTop: 16 }} className="card tbl-card">
        <Table
          size="small"
          pagination={false}
          rowKey={(r) => r.itemId}
          dataSource={cr.lines}
          scroll={{ x: 780 }}
          columns={[
            { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
            { title: 'Code', width: 108, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
            { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
            { title: 'Description', dataIndex: 'description', render: (v) => <span className="muted">{v}</span> },
            { title: 'Quantity', width: 108, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
            { title: 'UOM', width: 78, dataIndex: 'unit' },
            { title: 'Remarks', width: 190, dataIndex: 'remarks', render: (v) => <span className="muted">{v}</span> },
          ]}
        />
      </Card>

      <Card title="References" subtitle="Every document created from this request" icon={Link2} pad={false} style={{ marginTop: 16 }} className="card tbl-card">
        {docs.length ? (
          <Table
            size="small"
            pagination={false}
            dataSource={docs}
            rowKey="key"
            scroll={{ x: 760 }}
            columns={[
              { title: 'Document', dataIndex: 'label', width: 280 },
              {
                title: 'Number',
                dataIndex: 'no',
                width: 130,
                render: (v, r) => (r.to ? <a className="doc-no" onClick={() => nav(r.to)}>{v}</a> : <span className="doc-no">{v}</span>),
              },
              { title: 'Date', dataIndex: 'date', width: 136, render: fmtDate },
              { title: 'Status', dataIndex: 'status', width: 160, render: (v) => <StatusBadge status={v} /> },
              { title: 'Request', width: 118, render: () => <RefChip>{cr.crNo}</RefChip> },
            ]}
          />
        ) : (
          <EmptyState title="No linked documents yet" description="Send the request for quotation to start the chain." />
        )}
      </Card>
    </div>
  )
}
