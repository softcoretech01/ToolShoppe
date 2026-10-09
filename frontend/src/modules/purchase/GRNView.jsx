import React from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table } from 'antd'
import { ReceiptText, PackageCheck, Link2 } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { itemName, itemCode, supplierName, getCR } from '../../store/selectors.js'
import { round2 } from '../../logic/pricing.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import { DocHeader, Card, Grid, KV, Btn, Money, Qty, StatusBadge, fmtDate } from '../../components/ui/index.js'

export default function GRNView() {
  const { id } = useParams()
  const nav = useNavigate()
  const s = useStore()
  const g = (s.grns || []).find((x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.grnNo) === String(id))
  useDocLabel(g ? g.grnNo : null)

  React.useEffect(() => {
    if (g && String(g.id) !== String(id) && typeof g.id !== 'undefined') {
      nav(`/purchase/grn/${g.id}`, { replace: true })
    }
  }, [g, id, nav])

  if (!g) return <Navigate to="/purchase/grn" replace />

  const po = (s.purchaseOrders || []).find((x) => String(x.id) === String(g.poId))
  const cr = getCR(s, g.crId)
  const inw = (s.inwards || []).find((x) => String(x.grnId) === String(g.id))
  const pi = (s.purchaseInvoices || []).find((x) => String(x.grnId) === String(g.id))

  return (
    <div>
      <DocHeader
        title="Goods Receipt Note"
        docNo={g.grnNo}
        status={g.status}
        subtitle={`${supplierName(s, g.supplierId)} · received ${fmtDate(g.date)}`}
        backTo="/purchase/grn"
        actions={
          !pi && (
            <Btn variant="primary" icon={ReceiptText} onClick={() => nav(`/purchase/invoice?grn=${g.id}`)}>
              Create Invoice
            </Btn>
          )
        }
      />

      <Grid min={340}>
        <Card title="Receipt information" icon={PackageCheck}>
          <KV
            items={[
              ['GRN no', <span className="doc-no">{g.grnNo}</span>],
              ['Date', fmtDate(g.date)],
              ['Supplier', supplierName(s, g.supplierId)],
              ['Supplier DC / invoice ref', g.supplierRef],
              ['Received by', g.receivedBy],
              ['Remarks', g.remarks],
            ]}
          />
        </Card>

        <Card title="References" icon={Link2}>
          <KV
            items={[
              ['Purchase order', <a className="doc-no" onClick={() => nav(`/purchase/purchase-order/${g.poId}`)}>{po ? po.poNo : '—'}</a>],
              ['Customer request', <a className="doc-no" onClick={() => nav(`/sales/customer-request/${g.crId}`)}>{cr ? cr.crNo : '—'}</a>],
              [
                'Inward',
                inw ? (
                  <span>
                    <a className="doc-no" onClick={() => nav('/purchase/inward')}>{inw.inwNo}</a>
                    <span style={{ marginLeft: 8 }}><StatusBadge status={inw.status} size="sm" /></span>
                  </span>
                ) : '—',
              ],
              [
                'Purchase invoice',
                pi ? <a className="doc-no" onClick={() => nav(`/purchase/invoice/${pi.id}`)}>{pi.piNo}</a> : <span className="dim">not raised yet</span>,
              ],
            ]}
          />
        </Card>

        <Card title="Receipt summary" icon={PackageCheck}>
          <KV
            items={[
              ['Lines received', g.lines.length],
              ['Total received', <Qty value={g.lines.reduce((a, l) => a + l.receivedQty, 0)} strong />],
              ['Total accepted', <Qty value={g.lines.reduce((a, l) => a + l.acceptedQty, 0)} strong />],
              ['Total rejected', <Qty value={g.lines.reduce((a, l) => a + l.rejectedQty, 0)} />],
              ['Accepted value', <Money value={g.total} strong />],
            ]}
          />
        </Card>
      </Grid>

      <Card title="Lines received" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          pagination={false}
          rowKey="itemId"
          dataSource={g.lines}
          scroll={{ x: 940 }}
          columns={[
            { title: 'S.No', width: 62, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
            { title: 'Code', width: 106, render: (_, l) => <span className="doc-no">{itemCode(s, l.itemId)}</span> },
            { title: 'Item', render: (_, l) => itemName(s, l.itemId) },
            { title: 'Received', width: 106, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.receivedQty} /> },
            { title: 'Accepted', width: 106, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.acceptedQty} /> },
            {
              title: 'Rejected',
              width: 102,
              align: 'right',
              className: 'col-num',
              render: (_, l) => (
                <span style={{ color: l.rejectedQty > 0 ? 'var(--c-danger)' : undefined }}>
                  <Qty value={l.rejectedQty} />
                </span>
              ),
            },
            { title: 'Rate', width: 116, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.rate} /> },
            { title: 'Accepted value', width: 150, align: 'right', className: 'col-num', render: (_, l) => <Money value={round2(l.acceptedQty * l.rate)} strong /> },
          ]}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={7} align="right"><strong>Total accepted value</strong></Table.Summary.Cell>
                <Table.Summary.Cell index={7} align="right"><Money value={g.total} strong /></Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>
    </div>
  )
}
