import React from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table } from 'antd'
import { ClipboardList, Building2, Send, FileText } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { customerName, itemName, itemCode, supplierName, getCR } from '../../store/selectors.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import {
  DocHeader, Card, Grid, KV, StatusBadge, RefChip, Money, Qty, EmptyState, fmtDate,
} from '../../components/ui/index.js'

export default function RequestView() {
  const { id } = useParams()
  const nav = useNavigate()
  const s = useStore()
  const pr = (s.purchaseRequests || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.prNo) === String(id))
  useDocLabel(pr ? pr.prNo : null)

  React.useEffect(() => {
    if (pr && String(pr.id) !== String(id) && typeof pr.id !== 'undefined') {
      nav(`/purchase/request/${pr.id}`, { replace: true })
    }
  }, [pr, id, nav])

  if (!pr) return <Navigate to="/purchase/request" replace />

  const cr = getCR(s, pr.crId)
  const vqs = (s.vendorQuotations || []).filter((v) => String(v.prId) === String(pr.id))
  const asked = (s.suppliers || []).filter((x) => (pr.rfqSupplierIds || []).map(String).includes(String(x.id)))

  return (
    <div>
      <DocHeader
        title="Purchase Request"
        docNo={pr.prNo}
        status={pr.status}
        subtitle={cr ? `Raised from ${cr.crNo} for ${customerName(s, cr.customerId)}` : undefined}
        backTo="/purchase/request"
      />

      <Grid min={340}>
        <Card title="Request information" icon={ClipboardList}>
          <KV
            items={[
              ['PR no', <span className="doc-no">{pr.prNo}</span>],
              ['Date', fmtDate(pr.date)],
              ['RFQ sent on', pr.rfqSentAt ? fmtDate(pr.rfqSentAt) : <span className="dim">not sent yet</span>],
              ['Quotations received', vqs.length],
            ]}
          />
        </Card>

        <Card title="Customer demand" icon={Building2}>
          <KV
            items={[
              ['Customer request', <a className="doc-no" onClick={() => nav(`/sales/customer-request/${pr.crId}`)}>{cr ? cr.crNo : '—'}</a>],
              ['Customer', cr ? customerName(s, cr.customerId) : '—'],
              ['Their reference', cr ? cr.reference : ''],
              ['Required by', cr ? fmtDate(cr.requiredBy) : '—'],
            ]}
          />
        </Card>

        <Card title="RFQ sent to" icon={Send}>
          {asked.length ? (
            <div style={{ display: 'grid', gap: 8 }}>
              {asked.map((a) => (
                <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, fontSize: 13 }}>
                  <span style={{ fontWeight: 550 }}>{a.name}</span>
                  <span className="dim" style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.email}</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState compact icon={Send} title="No RFQ sent yet" description="Send the quotation request from the list screen." />
          )}
        </Card>
      </Grid>

      <Card title="Items" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          pagination={false}
          rowKey={(r) => r.itemId}
          dataSource={pr.lines}
          scroll={{ x: 640 }}
          columns={[
            { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
            { title: 'Code', width: 108, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
            { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
            { title: 'Quantity', width: 118, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
            { title: 'UOM', width: 82, dataIndex: 'unit' },
          ]}
        />
      </Card>

      <Card title="Quotations received" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        {vqs.length ? (
          <Table
            size="small"
            pagination={false}
            rowKey="id"
            dataSource={vqs}
            scroll={{ x: 900 }}
            columns={[
              { title: 'Quotation No', dataIndex: 'vqNo', width: 130, render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/vendor-quotation/${r.id}`)}>{v}</a> },
              { title: 'Supplier', render: (_, r) => supplierName(s, r.supplierId) },
              { title: 'Their ref', dataIndex: 'quoteRef', width: 150 },
              { title: 'Quote date', dataIndex: 'quoteDate', width: 128, render: fmtDate },
              { title: 'Amount', dataIndex: 'grandTotal', width: 150, align: 'right', className: 'col-num', render: (v) => <Money value={v} strong /> },
              { title: 'Delivery', dataIndex: 'deliveryDays', width: 108, align: 'right', className: 'col-num', render: (v) => <span className="num">{v} days</span> },
              { title: 'Status', dataIndex: 'status', width: 118, render: (v) => <StatusBadge status={v} /> },
            ]}
          />
        ) : (
          <EmptyState
            icon={FileText}
            title="No vendor quotations entered yet"
            description="Once suppliers reply, key their offers in from the Vendor Quotation screen."
          />
        )}
      </Card>
    </div>
  )
}
