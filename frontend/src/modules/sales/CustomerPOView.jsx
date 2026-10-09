import React from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table, Alert } from 'antd'
import { Truck, Building2, Link2, ShoppingCart, FileText, PackageCheck } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { itemName, itemCode, supplierName, getCR } from '../../store/selectors.js'
import { round2 } from '../../logic/pricing.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import {
  DocHeader, Card, Grid, KV, Btn, Money, Qty, StatusBadge, fmtDate,
} from '../../components/ui/index.js'

export default function CustomerPOView() {
  const { id } = useParams()
  const nav = useNavigate()
  const s = useStore()
  const so = (s.salesOrders || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.soNo) === String(id))
  useDocLabel(so ? so.soNo : null)

  React.useEffect(() => {
    if (so && String(so.id) !== String(id) && typeof so.id !== 'undefined') {
      nav(`/sales/customer-po/${so.id}`, { replace: true })
    }
  }, [so, id, nav])

  if (!so) return <Navigate to="/sales/customer-po" replace />

  const cr = getCR(s, so.crId)
  const cq = (s.customerQuotations || []).find((x) => String(x.id) === String(so.cqId))
  const po = (s.purchaseOrders || []).find((x) => String(x.soId) === String(so.id))
  const cust = (s.customers || []).find((c) => String(c.id) === String(so.customerId))
  const outs = (s.outwards || []).filter((o) => String(o.soId) === String(so.id))
  const grns = (s.grns || []).filter((g) => po && String(g.poId) === String(po.id))
  const inw = (s.inwards || []).find((i) => (grns.some((g) => String(g.id) === String(i.grnId))) || (so && String(i.crId) === String(so.crId)))

  return (
    <div>
      <DocHeader
        title="Customer Purchase Order"
        docNo={so.soNo}
        status={so.status}
        subtitle={cust ? `${cust.name} · their PO ${so.customerPoNo}` : undefined}
        backTo="/sales/customer-po"
        actions={
          so.status === 'Open' && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {po && po.status === 'Draft' && (
                <Btn variant="primary" icon={FileText} onClick={() => nav(`/purchase/purchase-order/${po.id}`)}>
                  Next Step: Send Supplier PO ({po.poNo})
                </Btn>
              )}
              {po && po.status === 'Sent' && grns.length === 0 && (
                <Btn variant="primary" icon={PackageCheck} onClick={() => nav(`/purchase/grn?po=${po.id}`)}>
                  Next Step: Record GRN
                </Btn>
              )}
              {inw && inw.status === 'Pending' && (
                <Btn variant="primary" icon={PackageCheck} onClick={() => nav(`/purchase/inward`)}>
                  Next Step: Add Inward to Stock
                </Btn>
              )}
              <Btn
                variant={po && (po.status === 'Draft' || (po.status === 'Sent' && grns.length === 0) || (inw && inw.status === 'Pending')) ? 'secondary' : 'primary'}
                icon={Truck}
                onClick={() => nav(`/sales/outward?so=${so.id}`)}
              >
                Post Outward
              </Btn>
            </div>
          )
        }
      />

      <Grid min={340}>
        <Card title="Customer" icon={Building2}>
          <KV
            items={[
              ['Name', cust ? `${cust.code} — ${cust.name}` : '—'],
              ['Their PO No', <span className="doc-no">{so.customerPoNo}</span>],
              ['Their PO date', fmtDate(so.customerPoDate)],
              ['Delivery date', fmtDate(so.deliveryDate)],
              ['Shipping address', cust ? cust.shippingAddress : ''],
            ]}
          />
        </Card>

        <Card title="Order information" icon={ShoppingCart}>
          <KV
            items={[
              ['Order no', <span className="doc-no">{so.soNo}</span>],
              ['Date', fmtDate(so.date)],
              ['Order value (pre-tax)', <Money value={so.total} strong />],
              ['Status', <StatusBadge status={so.status} />],
            ]}
          />
        </Card>

        <Card title="References" icon={Link2}>
          <KV
            items={[
              ['Customer request', <a className="doc-no" onClick={() => nav(`/sales/customer-request/${so.crId}`)}>{cr ? cr.crNo : '—'}</a>],
              ['Quotation', <a className="doc-no" onClick={() => nav(`/sales/quotation/${so.cqId}`)}>{cq ? cq.cqNo : '—'}</a>],
              [
                'Supplier PO',
                po ? (
                  <span>
                    <a className="doc-no" onClick={() => nav(`/purchase/purchase-order/${po.id}`)}>{po.poNo}</a>
                    <span className="dim" style={{ marginLeft: 8 }}>{supplierName(s, po.supplierId)}</span>
                  </span>
                ) : '—',
              ],
              [
                'Outward',
                outs.length
                  ? outs.map((o) => (
                      <a key={o.id} className="doc-no" onClick={() => nav(`/sales/outward/${o.id}`)} style={{ marginRight: 10 }}>
                        {o.outNo}
                      </a>
                    ))
                  : <span className="dim">not dispatched yet</span>,
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
          dataSource={so.lines}
          scroll={{ x: 760 }}
          columns={[
            { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
            { title: 'Code', width: 108, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
            { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
            { title: 'Quantity', width: 108, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
            { title: 'Customer price', width: 140, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.price} /> },
            { title: 'Line total', width: 148, align: 'right', className: 'col-num', render: (_, l) => <Money value={round2(l.qty * l.price)} strong /> },
          ]}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={5} align="right"><strong>Order total (pre-tax)</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right"><Money value={so.total} strong /></Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>

      {po && (
        <Card title="Back-to-Back Sourcing & Fulfillment Flow" icon={Link2} style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', fontSize: 13, marginBottom: 8 }}>
            <span style={{ fontWeight: 600, color: '#0969da' }}>1. Customer PO ({so.soNo} · Confirmed)</span>
            <span>➔</span>
            <span style={{ fontWeight: 600, color: po.status === 'Draft' ? '#cf222e' : '#1a7f37' }}>
              <a onClick={() => nav(`/purchase/purchase-order/${po.id}`)} style={{ textDecoration: 'underline', color: 'inherit' }}>
                2. Supplier PO ({po.poNo}: {po.status})
              </a>
            </span>
            <span>➔</span>
            <span style={{ fontWeight: 600, color: grns.length > 0 ? '#1a7f37' : '#57606a' }}>
              {grns.length > 0 ? (
                <a onClick={() => nav(`/purchase/grn/${grns[0].id}`)} style={{ textDecoration: 'underline', color: 'inherit' }}>
                  3. GRN ({grns[0].grnNo})
                </a>
              ) : (
                `3. GRN (${po.status === 'Sent' ? 'Ready to Record' : 'Pending PO Send'})`
              )}
            </span>
            <span>➔</span>
            <span style={{ fontWeight: 600, color: inw?.status === 'Added' ? '#1a7f37' : inw ? '#cf222e' : '#57606a' }}>
              <a onClick={() => nav('/purchase/inward')} style={{ textDecoration: 'underline', color: 'inherit' }}>
                4. Inward Stock ({inw ? inw.inwNo + ' · ' + inw.status : 'Pending GRN'})
              </a>
            </span>
            <span>➔</span>
            <span style={{ fontWeight: 600, color: outs.length > 0 ? '#1a7f37' : '#57606a' }}>
              5. Outward DC ({outs.length > 0 ? outs[0].outNo : 'Ready after Inward'})
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 12, color: '#57606a' }}>
            {po.status === 'Draft'
              ? `💡 Standard Flow: Since ToolShoppe operates on back-to-back trading, click 'Next Step: Send Supplier PO' above to send the PO to ${supplierName(s, po.supplierId)}. Once they deliver goods to your gate, record the GRN and Inward stock before dispatching.`
              : po.status === 'Sent' && grns.length === 0
              ? `💡 Next Step: Supplier PO ${po.poNo} was sent. When the shipment arrives at your warehouse, click 'Next Step: Record GRN' to accept the physical items.`
              : inw && inw.status === 'Pending'
              ? `💡 Next Step: GRN received. Open Purchase > Inward and click 'Add to Stock' to post items into active inventory.`
              : `💡 Stock has been verified or bypassed. You can generate customer delivery challans (Outward) and tax invoices.`}
          </p>
        </Card>
      )}
    </div>
  )
}
