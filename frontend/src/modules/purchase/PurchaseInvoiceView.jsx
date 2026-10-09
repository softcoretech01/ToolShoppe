import React from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table } from 'antd'
import { Building2, Link2, ReceiptText } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { itemName, itemCode, getCR } from '../../store/selectors.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import { DocHeader, Card, Grid, KV, Money, Qty, Pct, fmtDate } from '../../components/ui/index.js'

export default function PurchaseInvoiceView() {
  const { id } = useParams()
  const nav = useNavigate()
  const s = useStore()
  const pi = (s.purchaseInvoices || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.piNo) === String(id))
  useDocLabel(pi ? pi.piNo : null)

  React.useEffect(() => {
    if (pi && String(pi.id) !== String(id) && typeof pi.id !== 'undefined') {
      nav(`/purchase/invoice/${pi.id}`, { replace: true })
    }
  }, [pi, id, nav])

  if (!pi) return <Navigate to="/purchase/invoice" replace />

  const sup = (s.suppliers || []).find((c) => String(c.id) === String(pi.supplierId))
  const po = (s.purchaseOrders || []).find((x) => String(x.id) === String(pi.poId))
  const grn = (s.grns || []).find((x) => String(x.id) === String(pi.grnId))
  const cr = getCR(s, pi.crId)

  return (
    <div>
      <DocHeader
        title="Purchase Invoice"
        docNo={pi.piNo}
        status={pi.status}
        subtitle={sup ? `${sup.name} · their invoice ${pi.supplierInvNo}` : undefined}
        backTo="/purchase/invoice"
      />

      <Grid min={340}>
        <Card title="Supplier" icon={Building2}>
          <KV
            items={[
              ['Name', sup ? sup.name : '—'],
              ['Address', sup ? sup.address : ''],
              ['GSTIN', sup ? sup.gstin : ''],
              ['Their invoice no', <span className="doc-no">{pi.supplierInvNo}</span>],
              ['Their invoice date', fmtDate(pi.supplierInvDate)],
            ]}
          />
        </Card>

        <Card title="Booking" icon={ReceiptText}>
          <KV
            items={[
              ['Invoice no', <span className="doc-no">{pi.piNo}</span>],
              ['Booked on', fmtDate(pi.date)],
              ['Due date', fmtDate(pi.dueDate)],
              ['Invoice total', <Money value={pi.total} strong />],
            ]}
          />
        </Card>

        <Card title="References" icon={Link2}>
          <KV
            items={[
              ['Purchase order', <a className="doc-no" onClick={() => nav(`/purchase/purchase-order/${pi.poId}`)}>{po ? po.poNo : '—'}</a>],
              ['Goods receipt', <a className="doc-no" onClick={() => nav(`/purchase/grn/${pi.grnId}`)}>{grn ? grn.grnNo : '—'}</a>],
              ['Customer request', <a className="doc-no" onClick={() => nav(`/sales/customer-request/${pi.crId}`)}>{cr ? cr.crNo : '—'}</a>],
            ]}
          />
        </Card>
      </Grid>

      <Card title="Invoice lines" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          pagination={false}
          rowKey="itemId"
          dataSource={pi.lines}
          scroll={{ x: 940 }}
          columns={[
            { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
            { title: 'Code', width: 106, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
            { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
            { title: 'Qty', width: 96, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
            { title: 'Rate', width: 116, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.rate} /> },
            { title: 'Taxable', width: 128, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.taxable} /> },
            { title: 'Tax %', width: 88, align: 'right', className: 'col-num', render: (_, l) => <Pct value={l.taxPct} /> },
            { title: 'Tax amount', width: 126, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.taxAmount} muted /> },
            { title: 'Total', width: 140, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.total} strong /> },
          ]}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={8} align="right">Taxable value</Table.Summary.Cell>
                <Table.Summary.Cell index={8} align="right"><Money value={pi.subtotal} /></Table.Summary.Cell>
              </Table.Summary.Row>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={8} align="right">GST</Table.Summary.Cell>
                <Table.Summary.Cell index={8} align="right"><Money value={pi.tax} /></Table.Summary.Cell>
              </Table.Summary.Row>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={8} align="right"><strong>Invoice total</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={8} align="right"><Money value={pi.total} strong /></Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>
    </div>
  )
}
