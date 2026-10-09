import React from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table } from 'antd'
import { ReceiptText, Building2, Link2, Truck } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { itemName, itemCode, getCR } from '../../store/selectors.js'
import { round2 } from '../../logic/pricing.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import { DocHeader, Card, Grid, KV, Btn, Money, Qty, fmtDate } from '../../components/ui/index.js'

export default function OutwardView() {
  const { id } = useParams()
  const nav = useNavigate()
  const s = useStore()
  const o = (s.outwards || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.outNo) === String(id))
  useDocLabel(o ? o.outNo : null)

  React.useEffect(() => {
    if (o && String(o.id) !== String(id) && typeof o.id !== 'undefined') {
      nav(`/sales/outward/${o.id}`, { replace: true })
    }
  }, [o, id, nav])

  if (!o) return <Navigate to="/sales/outward" replace />

  const so = (s.salesOrders || []).find((x) => String(x.id) === String(o.soId))
  const cr = getCR(s, o.crId)
  const cust = (s.customers || []).find((c) => String(c.id) === String(o.customerId))
  const si = (s.salesInvoices || []).find((x) => String(x.outId) === String(o.id))

  return (
    <div>
      <DocHeader
        title="Outward / Delivery Challan"
        docNo={o.outNo}
        status={o.status}
        subtitle={cust ? `${cust.name} · DC ${o.dcNo || '—'}` : undefined}
        backTo="/sales/outward"
        actions={
          !si && (
            <Btn variant="primary" icon={ReceiptText} onClick={() => nav(`/sales/invoice?out=${o.id}`)}>
              Create Invoice
            </Btn>
          )
        }
      />

      <Grid min={340}>
        <Card title="Delivered to" icon={Building2}>
          <KV
            items={[
              ['Customer', cust ? `${cust.code} — ${cust.name}` : '—'],
              ['Shipping address', cust ? cust.shippingAddress : ''],
              ['GSTIN', cust ? cust.gstin : ''],
            ]}
          />
        </Card>

        <Card title="Dispatch information" icon={Truck}>
          <KV
            items={[
              ['Dispatch date', fmtDate(o.date)],
              ['DC No', <span className="doc-no">{o.dcNo}</span>],
              ['Mode', o.mode],
              ['Vehicle / courier', o.vehicle],
              ['Remarks', o.remarks],
              ['Dispatch value', <Money value={o.value} strong />],
            ]}
          />
        </Card>

        <Card title="References" icon={Link2}>
          <KV
            items={[
              [
                'Customer PO',
                <a className="doc-no" onClick={() => nav(`/sales/customer-po/${o.soId}`)}>
                  {so ? `${so.soNo} (${so.customerPoNo})` : '—'}
                </a>,
              ],
              ['Customer request', <a className="doc-no" onClick={() => nav(`/sales/customer-request/${o.crId}`)}>{cr ? cr.crNo : '—'}</a>],
              [
                'Sales invoice',
                si ? <a className="doc-no" onClick={() => nav(`/sales/invoice/${si.id}`)}>{si.siNo}</a> : <span className="dim">not raised yet</span>,
              ],
            ]}
          />
        </Card>
      </Grid>

      <Card title="Items dispatched" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          pagination={false}
          rowKey="itemId"
          dataSource={o.lines}
          scroll={{ x: 760 }}
          columns={[
            { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
            { title: 'Code', width: 108, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
            { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
            { title: 'Quantity', width: 110, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
            { title: 'Price', width: 132, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.price} /> },
            { title: 'Line total', width: 148, align: 'right', className: 'col-num', render: (_, l) => <Money value={round2(l.qty * l.price)} strong /> },
          ]}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={5} align="right"><strong>Dispatch value (pre-tax)</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right"><Money value={o.value} strong /></Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>
    </div>
  )
}
