import React from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table, Progress } from 'antd'
import { PackageCheck, Building2, Link2, FileText } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { itemName, itemCode, supplierName, getCR } from '../../store/selectors.js'
import { round2 } from '../../logic/pricing.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import { DocHeader, Card, Grid, KV, Btn, Money, Qty, fmtDate } from '../../components/ui/index.js'

export default function PurchaseOrderView() {
  const { id } = useParams()
  const nav = useNavigate()
  const s = useStore()
  const po = (s.purchaseOrders || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.poNo) === String(id))
  useDocLabel(po ? po.poNo : null)

  React.useEffect(() => {
    if (po && String(po.id) !== String(id) && typeof po.id !== 'undefined') {
      nav(`/purchase/purchase-order/${po.id}`, { replace: true })
    }
  }, [po, id, nav])

  if (!po) return <Navigate to="/purchase/purchase-order" replace />

  const cr = getCR(s, po.crId)
  const so = (s.salesOrders || []).find((x) => String(x.id) === String(po.soId))
  const vq = (s.vendorQuotations || []).find((v) => String(v.id) === String(po.vqId))
  const sup = (s.suppliers || []).find((x) => String(x.id) === String(po.supplierId))
  const grns = (s.grns || []).filter((g) => String(g.poId) === String(po.id))
  const pis = (s.purchaseInvoices || []).filter((p) => String(p.poId) === String(po.id))

  const ordered = po.lines.reduce((a, l) => a + l.qty, 0)
  const received = po.lines.reduce((a, l) => a + (l.receivedQty || 0), 0)
  const pct = ordered ? Math.round((received / ordered) * 100) : 0

  return (
    <div>
      <DocHeader
        title="Purchase Order"
        docNo={po.poNo}
        status={po.status}
        subtitle={sup ? `${sup.name} · expected ${fmtDate(po.expectedDelivery)}` : undefined}
        backTo="/purchase/purchase-order"
        actions={
          (po.status === 'Sent' || po.status === 'Partially Received') && (
            <Btn variant="primary" icon={PackageCheck} onClick={() => nav(`/purchase/grn?po=${po.id}`)}>
              Create GRN
            </Btn>
          )
        }
      />

      <Grid min={340}>
        <Card title="Supplier" icon={Building2}>
          <KV
            items={[
              ['Name', sup ? `${sup.code} — ${sup.name}` : '—'],
              ['Contact', sup ? `${sup.contactPerson} · ${sup.phone}` : ''],
              ['Email', sup ? sup.email : ''],
              ['Address', sup ? sup.address : ''],
              ['GSTIN', sup ? sup.gstin : ''],
            ]}
          />
        </Card>

        <Card title="Order information" icon={FileText}>
          <KV
            items={[
              ['PO no', <span className="doc-no">{po.poNo}</span>],
              ['Date', fmtDate(po.date)],
              ['Expected delivery', fmtDate(po.expectedDelivery)],
              ['Sent on', po.sentAt ? fmtDate(po.sentAt.slice(0, 10)) : <span className="dim">not sent yet</span>],
              ['Order value (pre-tax)', <Money value={po.total} strong />],
              [
                'Received',
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, maxWidth: 240 }}>
                  <Progress percent={pct} size="small" strokeColor="var(--c-primary)" style={{ flex: 1, margin: 0 }} />
                </div>,
              ],
            ]}
          />
        </Card>

        <Card title="References" icon={Link2}>
          <KV
            items={[
              ['Against quotation', <a className="doc-no" onClick={() => nav(`/purchase/vendor-quotation/${po.vqId}`)}>{vq ? vq.vqNo : '—'}</a>],
              ['Customer PO', <a className="doc-no" onClick={() => nav(`/sales/customer-po/${po.soId}`)}>{so ? so.soNo : '—'}</a>],
              ['Customer request', <a className="doc-no" onClick={() => nav(`/sales/customer-request/${po.crId}`)}>{cr ? cr.crNo : '—'}</a>],
              [
                'Goods receipts',
                grns.length
                  ? grns.map((g) => (
                      <a key={g.id} className="doc-no" style={{ marginRight: 10 }} onClick={() => nav(`/purchase/grn/${g.id}`)}>{g.grnNo}</a>
                    ))
                  : <span className="dim">nothing received yet</span>,
              ],
              [
                'Purchase invoices',
                pis.length
                  ? pis.map((p) => (
                      <a key={p.id} className="doc-no" style={{ marginRight: 10 }} onClick={() => nav(`/purchase/invoice/${p.id}`)}>{p.piNo}</a>
                    ))
                  : <span className="dim">not invoiced yet</span>,
              ],
            ]}
          />
        </Card>
      </Grid>

      <Card title="Order lines" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          pagination={false}
          rowKey="itemId"
          dataSource={po.lines}
          scroll={{ x: 880 }}
          columns={[
            { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
            { title: 'Code', width: 106, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
            { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
            { title: 'Ordered', width: 100, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
            {
              title: 'Received',
              width: 104,
              align: 'right',
              className: 'col-num',
              render: (_, l) => (
                <span style={{ color: (l.receivedQty || 0) >= l.qty ? 'var(--c-success)' : undefined, fontWeight: (l.receivedQty || 0) >= l.qty ? 600 : 400 }}>
                  <Qty value={l.receivedQty || 0} />
                </span>
              ),
            },
            { title: 'Rate', width: 118, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.rate} /> },
            { title: 'Line total', width: 144, align: 'right', className: 'col-num', render: (_, l) => <Money value={round2(l.qty * l.rate)} strong /> },
          ]}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={6} align="right"><strong>PO total (pre-tax)</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={6} align="right"><Money value={po.total} strong /></Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>
    </div>
  )
}
