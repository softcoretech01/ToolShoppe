import React, { useState } from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { Table, Alert, Tag } from 'antd'
import { Boxes, PackagePlus, Link2, CheckCircle2 } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { itemName, itemCode, supplierName, getCR } from '../../store/selectors.js'
import { round2, sum } from '../../logic/pricing.js'
import { useDocLabel } from '../../app/docLabel.jsx'
import {
  DocHeader, Card, Grid, KV, Btn, Money, Qty, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function InwardView() {
  const { id } = useParams()
  const nav = useNavigate()
  const { state, dispatch } = useApp()
  const toast = useToast()
  const [posting, setPosting] = useState(false)

  const inw = (state.inwards || []).find(
    (x) => String(x.id) === String(id) || (x.localId && String(x.localId) === String(id)) || String(x.inwNo) === String(id)
  )
  useDocLabel(inw ? inw.inwNo : null)

  React.useEffect(() => {
    if (inw && String(inw.id) !== String(id) && typeof inw.id !== 'undefined') {
      nav(`/purchase/inward/${inw.id}`, { replace: true })
    }
  }, [inw, id, nav])

  if (!inw) return <Navigate to="/purchase/inward" replace />

  const grn = (state.grns || []).find((g) => g.id === inw.grnId)
  const poId = inw.poId || (grn ? grn.poId : null)
  const po = (state.purchaseOrders || []).find((p) => p.id === poId)
  const cr = getCR(state, inw.crId)
  const sup = inw.supplierName || supplierName(state, inw.supplierId || (grn ? grn.supplierId : null))

  // Correlate GRN items for rejected quantities
  const grnItemMap = new Map()
  if (grn && grn.lines) {
    grn.lines.forEach((gl) => grnItemMap.set(gl.itemId, gl))
  }

  const lines = (inw.lines || []).map((l) => {
    const gl = grnItemMap.get(l.itemId)
    const accepted = Number(l.acceptedQty ?? l.qty ?? 0)
    const rejected = Number(l.rejectedQty ?? (gl ? gl.rejectedQty : 0))
    return {
      ...l,
      acceptedQty: accepted,
      rejectedQty: rejected,
      rate: Number(l.rate ?? (gl ? gl.rate : 0)),
    }
  })

  const totalAccepted = inw.totalAcceptedQty != null ? Number(inw.totalAcceptedQty) : sum(lines, (l) => l.acceptedQty)
  const totalRejected = inw.totalRejectedQty != null ? Number(inw.totalRejectedQty) : sum(lines, (l) => l.rejectedQty)
  const totalValue = inw.value != null ? Number(inw.value) : sum(lines, (l) => l.acceptedQty * l.rate)

  const handlePost = async () => {
    if (posting) return
    setPosting(true)
    try {
      await dispatch({ type: 'INW_ADD_TO_STOCK', inwId: inw.id })
      toast.success(`${inw.inwNo} successfully posted to inventory!`)
    } catch (err) {
      toast.error(`Failed to post inventory: ${err?.message || err}`)
    } finally {
      setPosting(false)
    }
  }

  return (
    <div>
      <DocHeader
        title="Purchase Inward"
        docNo={inw.inwNo}
        status={inw.status}
        subtitle={`${sup} · received ${fmtDate(inw.receivedDate || inw.date)}`}
        backTo="/purchase/inward"
        actions={
          inw.status === 'Pending' && (
            <Btn
              variant="primary"
              icon={PackagePlus}
              loading={posting}
              disabled={posting}
              onClick={handlePost}
            >
              Post to Inventory
            </Btn>
          )
        }
      />

      {inw.status === 'Pending' ? (
        <Alert
          style={{ marginBottom: 16 }}
          type="warning"
          showIcon
          message="This Inward receipt is pending inventory posting. Accepted items are not yet available in on-hand stock for dispatch."
        />
      ) : (
        <Alert
          style={{ marginBottom: 16 }}
          type="success"
          showIcon
          message={`Accepted goods posted into inventory stock on ${fmtDate(inw.addedAt ? inw.addedAt.slice(0, 10) : inw.date)}. On-hand stock is allocated to ${cr ? cr.crNo : 'Customer Request'}.`}
        />
      )}

      <Grid min={340}>
        <Card title="Inward Receipt Details" icon={Boxes}>
          <KV
            items={[
              ['Inward Number', <span className="doc-no">{inw.inwNo}</span>],
              ['Supplier', <strong>{sup}</strong>],
              ['Received Date', fmtDate(inw.receivedDate || inw.date)],
              [
                'Inventory Status',
                inw.status === 'Pending' ? (
                  <Tag color="warning">Pending Post</Tag>
                ) : (
                  <Tag color="success">Posted to Stock</Tag>
                ),
              ],
              ['Total Accepted Qty', <strong style={{ color: '#047857' }}>{totalAccepted}</strong>],
              ['Total Rejected Qty', <strong style={{ color: totalRejected > 0 ? '#b91c1c' : 'inherit' }}>{totalRejected}</strong>],
              ['Total Value', <Money value={totalValue} strong />],
            ]}
          />
        </Card>

        <Card title="Linked Document References" icon={Link2}>
          <KV
            items={[
              [
                'GRN Number',
                grn ? (
                  <a className="doc-no" onClick={() => nav(`/purchase/grn/${grn.id}`)}>
                    {grn.grnNo}
                  </a>
                ) : (
                  <span>{inw.grnNo || '—'}</span>
                ),
              ],
              [
                'Supplier PO',
                po ? (
                  <a className="doc-no" onClick={() => nav(`/purchase/purchase-order/${po.id}`)}>
                    {po.poNo}
                  </a>
                ) : (
                  <span>{inw.poNo || '—'}</span>
                ),
              ],
              [
                'Customer Request (CR)',
                cr ? (
                  <a className="doc-no" onClick={() => nav(`/sales/customer-request/${cr.id}`)}>
                    {cr.crNo}
                  </a>
                ) : (
                  <span>{inw.crNo || '—'}</span>
                ),
              ],
            ]}
          />
        </Card>
      </Grid>

      <Card title="Received Items & Quality Breakdown" pad={false} className="card tbl-card" style={{ marginTop: 16 }}>
        <Table
          size="small"
          pagination={false}
          rowKey="itemId"
          dataSource={lines}
          columns={[
            {
              title: 'Code',
              width: 110,
              render: (_, l) => (
                <span className="doc-no">{itemCode(state, l.itemId)}</span>
              ),
            },
            {
              title: 'Item Name',
              render: (_, l) => itemName(state, l.itemId),
            },
            {
              title: 'Accepted Qty (Stock IN)',
              width: 160,
              align: 'right',
              render: (_, l) => (
                <span style={{ color: '#047857', fontWeight: 600 }}>
                  <Qty value={l.acceptedQty} />
                </span>
              ),
            },
            {
              title: 'Rejected Qty (Excluded)',
              width: 150,
              align: 'right',
              render: (_, l) => (
                <span style={{ color: l.rejectedQty > 0 ? '#b91c1c' : 'var(--c-text-muted)' }}>
                  {l.rejectedQty || 0}
                </span>
              ),
            },
            {
              title: 'Purchase Rate',
              width: 120,
              align: 'right',
              render: (_, l) => <Money value={l.rate} />,
            },
            {
              title: 'Value',
              width: 130,
              align: 'right',
              render: (_, l) => (
                <Money value={round2((l.acceptedQty || 0) * (l.rate || 0))} strong />
              ),
            },
          ]}
          summary={() => (
            <Table.Summary>
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={5} align="right">
                  <strong>Total Inward Value (Accepted Only)</strong>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <Money value={totalValue} strong />
                </Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>
    </div>
  )
}
