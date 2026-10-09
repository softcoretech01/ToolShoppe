import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Alert, Tag, Tooltip } from 'antd'
import { PackagePlus, Eye, Boxes, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { supplierName, itemName, itemCode, getCR } from '../../store/selectors.js'
import { round2, sum } from '../../logic/pricing.js'
import {
  DataTable, PageHeader, RefChip, Btn, IconBtn, FormModal, ViewDrawer, DrawerSection, KV,
  Money, Qty, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function Inward() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [confirmRow, setConfirmRow] = useState(null)
  const [viewRow, setViewRow] = useState(null)
  const [postingId, setPostingId] = useState(null)

  const rows = useMemo(
    () =>
      state.inwards.map((i) => {
        const grn = state.grns.find((g) => g.id === i.grnId)
        const poId = i.poId || (grn ? grn.poId : null)
        const po = state.purchaseOrders.find((p) => p.id === poId)
        const cr = getCR(state, i.crId)

        // Correlate GRN items for rejected quantities if not directly on lines
        const grnItemMap = new Map()
        if (grn && grn.lines) {
          grn.lines.forEach((gl) => grnItemMap.set(gl.itemId, gl))
        }

        const lines = (i.lines || []).map((l) => {
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

        const totalAccepted = i.totalAcceptedQty != null ? Number(i.totalAcceptedQty) : sum(lines, (l) => l.acceptedQty)
        const totalRejected = i.totalRejectedQty != null ? Number(i.totalRejectedQty) : sum(lines, (l) => l.rejectedQty)

        return {
          ...i,
          grnNo: i.grnNo || (grn ? grn.grnNo : '—'),
          grnId: i.grnId,
          poNo: i.poNo || (po ? po.poNo : '—'),
          poId,
          crNo: i.crNo || (cr ? cr.crNo : '—'),
          supplier: i.supplierName || supplierName(state, i.supplierId || (grn ? grn.supplierId : null)),
          receivedDate: i.receivedDate || i.date || (grn ? grn.date : null),
          acceptedQty: totalAccepted,
          rejectedQty: totalRejected,
          lines,
        }
      }),
    [state]
  )

  const pending = rows.filter((r) => r.status === 'Pending').length

  const handlePostInventory = async (row) => {
    if (!row || postingId) return
    setPostingId(row.id)
    try {
      await dispatch({ type: 'INW_ADD_TO_STOCK', inwId: row.id })
      toast.success(`${row.inwNo} posted to inventory — ${row.acceptedQty} accepted items now in stock for ${row.crNo}.`)
      setConfirmRow(null)
      if (viewRow && viewRow.id === row.id) {
        setViewRow((prev) => (prev ? { ...prev, status: 'Added', addedAt: new Date().toISOString() } : null))
      }
    } catch (err) {
      toast.error(`Failed to post inventory: ${err?.message || err}`)
    } finally {
      setPostingId(null)
    }
  }

  const columns = [
    {
      title: 'Inward No',
      dataIndex: 'inwNo',
      width: 118,
      sorter: (a, b) => (a.inwNo || '').localeCompare(b.inwNo || ''),
      render: (v, r) => (
        <a className="doc-no" onClick={() => setViewRow(r)} style={{ cursor: 'pointer' }}>
          {v}
        </a>
      ),
    },
    {
      title: 'GRN No',
      dataIndex: 'grnNo',
      width: 114,
      render: (v, r) =>
        r.grnId ? (
          <a className="doc-no" onClick={() => nav(`/purchase/grn/${r.grnId}`)}>
            {v}
          </a>
        ) : (
          <span>{v}</span>
        ),
    },
    {
      title: 'Supplier Name',
      dataIndex: 'supplier',
      width: 170,
      ellipsis: true,
      sorter: (a, b) => (a.supplier || '').localeCompare(b.supplier || ''),
      render: (v) => <span style={{ fontWeight: 600, color: 'var(--c-text)' }}>{v}</span>,
    },
    {
      title: 'PO No',
      dataIndex: 'poNo',
      width: 106,
      render: (v, r) =>
        r.poId ? (
          <a className="doc-no" onClick={() => nav(`/purchase/purchase-order/${r.poId}`)}>
            {v}
          </a>
        ) : (
          <span className="muted">{v}</span>
        ),
    },
    {
      title: 'CR Number',
      dataIndex: 'crNo',
      width: 124,
      render: (v, r) => (
        <RefChip onClick={() => r.crId && nav(`/sales/customer-request/${r.crId}`)}>
          {v}
        </RefChip>
      ),
    },
    {
      title: 'Received Date',
      dataIndex: 'receivedDate',
      width: 120,
      sorter: (a, b) => (a.receivedDate || '').localeCompare(b.receivedDate || ''),
      render: fmtDate,
    },
    {
      title: 'Accepted Qty',
      dataIndex: 'acceptedQty',
      width: 120,
      align: 'right',
      sorter: (a, b) => a.acceptedQty - b.acceptedQty,
      render: (v) => (
        <Tooltip title="Accepted quantities added to inventory stock">
          <span style={{ color: '#047857', fontWeight: 600 }}>
            <Qty value={v} />
          </span>
        </Tooltip>
      ),
    },
    {
      title: 'Rejected Qty',
      dataIndex: 'rejectedQty',
      width: 115,
      align: 'right',
      sorter: (a, b) => a.rejectedQty - b.rejectedQty,
      render: (v) => (
        <Tooltip title="Rejected goods are excluded and not posted to inventory">
          {v > 0 ? (
            <span style={{ color: '#b91c1c', fontWeight: 600 }}>{v}</span>
          ) : (
            <span className="muted">0</span>
          )}
        </Tooltip>
      ),
    },
    {
      title: 'Total Value',
      dataIndex: 'value',
      width: 135,
      align: 'right',
      sorter: (a, b) => a.value - b.value,
      render: (v) => <Money value={v} strong />,
    },
    {
      title: 'Inward Status',
      dataIndex: 'status',
      width: 150,
      render: (v) =>
        v === 'Pending' ? (
          <span
            className="badge"
            style={{
              background: '#fef3c7',
              color: '#92400e',
              borderColor: '#fde68a',
              fontWeight: 600,
            }}
          >
            Pending Post
          </span>
        ) : (
          <span
            className="badge"
            style={{
              background: '#dcfce7',
              color: '#166534',
              borderColor: '#bbf7d0',
              fontWeight: 600,
            }}
          >
            Posted to Stock
          </span>
        ),
    },
    {
      title: 'Available Actions',
      width: 220,
      fixed: 'right',
      render: (_, r) => (
        <div style={{ display: 'inline-flex', gap: 6, alignItems: 'center', whiteSpace: 'nowrap' }}>
          <IconBtn
            icon={Eye}
            label="View Inward"
            onClick={() => setViewRow(r)}
            aria-label="View Inward"
          />

          {r.status === 'Pending' ? (
            <Btn
              variant="primary"
              size="small"
              icon={PackagePlus}
              loading={postingId === r.id}
              disabled={postingId === r.id}
              onClick={() => setConfirmRow(r)}
            >
              Add to Stock
            </Btn>
          ) : (
            <span className="dim" style={{ fontSize: 12 }}>
              in stock since {fmtDate(r.addedAt ? r.addedAt.slice(0, 10) : r.date)}
            </span>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Purchase Inward & Inventory Receipt"
        subtitle="Receipt records generated from GRNs. Adding to inventory posts accepted quantities into the stock ledger tagged with the customer request."
      />

      {pending > 0 && (
        <Alert
          style={{ marginBottom: 14 }}
          type="warning"
          showIcon
          message={
            <span>
              <strong>{pending} Inward record{pending === 1 ? '' : 's'} pending inventory posting.</strong> Stock
              is not available for dispatch until it is posted to inventory. Only accepted quantities will be added.
            </span>
          }
        />
      )}

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1450}
        showRange
        searchKeys={['inwNo', 'grnNo', 'poNo', 'crNo', 'supplier']}
        searchPlaceholder="Search Inward, GRN, PO, CR number, supplier…"
        filters={[
          {
            key: 'status',
            placeholder: 'Inventory status',
            width: 174,
            options: [
              { value: 'Pending', label: 'Pending (Not Posted)' },
              { value: 'Added', label: 'Added (Posted to Stock)' },
            ],
          },
          {
            key: 'supplierId',
            placeholder: 'Supplier',
            width: 226,
            showSearch: true,
            options: state.suppliers.map((c) => ({ value: c.id, label: c.name })),
          },
        ]}
        empty={{
          icon: Boxes,
          title: 'No Inward records found',
          description: 'Record a goods receipt (GRN) and the inward appears here ready to be posted to stock.',
          action: (
            <Btn variant="primary" onClick={() => nav('/purchase/grn')}>
              Go to GRN
            </Btn>
          ),
        }}
      />

      {/* Confirmation Modal to Post to Inventory */}
      <FormModal
        open={!!confirmRow}
        title={confirmRow ? `Post ${confirmRow.inwNo} to Inventory` : ''}
        subtitle={confirmRow ? `Adds accepted goods to stock for ${confirmRow.crNo}` : ''}
        onCancel={() => setConfirmRow(null)}
        onOk={() => handlePostInventory(confirmRow)}
        okText={postingId ? 'Posting...' : 'Post to Inventory'}
        okDisabled={postingId !== null}
        width={780}
        footerNote="Creates IN movements in the stock ledger for accepted quantities only. This action cannot be reversed."
      >
        {confirmRow && (
          <>
            <Alert
              style={{ marginBottom: 14 }}
              type="info"
              showIcon
              message={`Only accepted quantities (${confirmRow.acceptedQty}) will be added to inventory stock. Rejected quantities (${confirmRow.rejectedQty}) are completely excluded from warehouse stock.`}
            />

            <div className="tbl-card" style={{ boxShadow: 'none' }}>
              <Table
                size="small"
                pagination={false}
                rowKey="itemId"
                dataSource={confirmRow.lines}
                scroll={{ x: 620 }}
                columns={[
                  {
                    title: 'Item Code',
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
                    width: 150,
                    align: 'right',
                    render: (_, l) => (
                      <span style={{ color: '#047857', fontWeight: 600 }}>
                        <Qty value={l.acceptedQty} />
                      </span>
                    ),
                  },
                  {
                    title: 'Rejected Qty (Excluded)',
                    width: 140,
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
                    title: 'Posted Value',
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
                        <strong>Total Posted Inward Value</strong>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={5} align="right">
                        <Money value={confirmRow.value} strong />
                      </Table.Summary.Cell>
                    </Table.Summary.Row>
                  </Table.Summary>
                )}
              />
            </div>
          </>
        )}
      </FormModal>

      {/* Comprehensive View Drawer */}
      <ViewDrawer
        open={!!viewRow}
        onClose={() => setViewRow(null)}
        title="Inward Receipt Details"
        docNo={viewRow?.inwNo}
        subtitle={viewRow ? `Supplier: ${viewRow.supplier}` : ''}
        width={760}
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            {viewRow?.status === 'Pending' && (
              <Btn
                variant="primary"
                icon={PackagePlus}
                loading={postingId === viewRow.id}
                disabled={postingId === viewRow.id}
                onClick={() => {
                  const target = viewRow
                  setViewRow(null)
                  setConfirmRow(target)
                }}
              >
                Post to Inventory
              </Btn>
            )}
            <Btn variant="secondary" onClick={() => setViewRow(null)}>
              Close
            </Btn>
          </div>
        }
      >
        {viewRow && (
          <>
            <DrawerSection title="Inward Document Information">
              <KV
                items={[
                  ['Inward Number', <span className="doc-no">{viewRow.inwNo}</span>],
                  [
                    'GRN Reference',
                    viewRow.grnId ? (
                      <a
                        className="doc-no"
                        onClick={() => {
                          setViewRow(null)
                          nav(`/purchase/grn/${viewRow.grnId}`)
                        }}
                      >
                        {viewRow.grnNo}
                      </a>
                    ) : (
                      <span>{viewRow.grnNo}</span>
                    ),
                  ],
                  [
                    'Supplier PO Number',
                    viewRow.poId ? (
                      <a
                        className="doc-no"
                        onClick={() => {
                          setViewRow(null)
                          nav(`/purchase/purchase-order/${viewRow.poId}`)
                        }}
                      >
                        {viewRow.poNo}
                      </a>
                    ) : (
                      <span>{viewRow.poNo}</span>
                    ),
                  ],
                  [
                    'Customer Request (CR)',
                    viewRow.crId ? (
                      <RefChip
                        onClick={() => {
                          setViewRow(null)
                          nav(`/sales/customer-request/${viewRow.crId}`)
                        }}
                      >
                        {viewRow.crNo}
                      </RefChip>
                    ) : (
                      <span>{viewRow.crNo}</span>
                    ),
                  ],
                  ['Supplier', <strong>{viewRow.supplier}</strong>],
                  ['Received Date', fmtDate(viewRow.receivedDate)],
                  [
                    'Inventory Status',
                    viewRow.status === 'Pending' ? (
                      <Tag color="warning">Pending — Not Yet Posted to Stock</Tag>
                    ) : (
                      <Tag color="success">
                        Posted to Stock (Stock IN active since {fmtDate(viewRow.addedAt ? viewRow.addedAt.slice(0, 10) : viewRow.date)})
                      </Tag>
                    ),
                  ],
                  ['Total Accepted Qty', <strong style={{ color: '#047857' }}>{viewRow.acceptedQty}</strong>],
                  ['Total Rejected Qty', <strong style={{ color: viewRow.rejectedQty > 0 ? '#b91c1c' : 'inherit' }}>{viewRow.rejectedQty}</strong>],
                  ['Total Inward Value', <Money value={viewRow.value} strong />],
                ]}
              />
            </DrawerSection>

            <DrawerSection title="Item Receipt & Quality Details">
              <Alert
                style={{ marginBottom: 12 }}
                type="info"
                showIcon
                message="Only accepted quantities are posted to inventory stock. Rejected quantities are excluded and not available for customer dispatch."
              />

              <div className="tbl-card" style={{ boxShadow: 'none' }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="itemId"
                  dataSource={viewRow.lines}
                  columns={[
                    {
                      title: 'Item Code',
                      width: 100,
                      render: (_, l) => (
                        <span className="doc-no">{itemCode(state, l.itemId)}</span>
                      ),
                    },
                    {
                      title: 'Item Name',
                      render: (_, l) => itemName(state, l.itemId),
                    },
                    {
                      title: 'Accepted Qty (In Stock)',
                      width: 140,
                      align: 'right',
                      render: (_, l) => (
                        <span style={{ color: '#047857', fontWeight: 600 }}>
                          <Qty value={l.acceptedQty} />
                        </span>
                      ),
                    },
                    {
                      title: 'Rejected Qty',
                      width: 110,
                      align: 'right',
                      render: (_, l) => (
                        <span style={{ color: l.rejectedQty > 0 ? '#b91c1c' : 'var(--c-text-muted)' }}>
                          {l.rejectedQty || 0}
                        </span>
                      ),
                    },
                    {
                      title: 'Unit Rate',
                      width: 110,
                      align: 'right',
                      render: (_, l) => <Money value={l.rate} />,
                    },
                    {
                      title: 'Line Total',
                      width: 120,
                      align: 'right',
                      render: (_, l) => (
                        <Money value={round2((l.acceptedQty || 0) * (l.rate || 0))} strong />
                      ),
                    },
                  ]}
                />
              </div>
            </DrawerSection>
          </>
        )}
      </ViewDrawer>
    </div>
  )
}
