import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, GitCompareArrows, Trophy } from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { supplierName, getCR } from '../../store/selectors.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, RowActions, Money, fmtDate,
} from '../../components/ui/index.js'

export default function Comparison() {
  const s = useStore()
  const nav = useNavigate()

  const rows = useMemo(
    () =>
      s.quotationComparisons.map((qc) => {
        const pr = s.purchaseRequests.find((p) => p.id === qc.prId || String(p.id) === String(qc.prId))
        const cr = pr ? getCR(s, pr.crId) : (qc.crId ? getCR(s, qc.crId) : null)
        const sel = s.vendorQuotations.find((v) => v.id === qc.selectedVqId || String(v.id) === String(qc.selectedVqId))
        const best = s.vendorQuotations.find((v) => v.id === qc.bestVqId || String(v.id) === String(qc.bestVqId))
        return {
          ...qc,
          prNo: pr ? pr.prNo : '—',
          crNo: cr ? cr.crNo : '—',
          crId: cr ? cr.id : null,
          compared: (qc.vqIds || []).length,
          suppliers: (qc.vqIds || [])
            .map((vid) => s.vendorQuotations.find((v) => v.id === vid || String(v.id) === String(vid)))
            .filter(Boolean)
            .map((v) => supplierName(s, v.supplierId))
            .join(', '),
          best: best ? supplierName(s, best.supplierId) : '—',
          selected: sel ? supplierName(s, sel.supplierId) : '—',
          selectedTotal: sel ? sel.grandTotal : 0,
          override: sel && best && String(sel.id) !== String(best.id),
        }
      }),
    [s]
  )

  const columns = [
    {
      title: 'Comparison No',
      dataIndex: 'qcNo',
      width: 138,
      sorter: true,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/quotation-comparison/${r.id}`)}>{v}</a>,
    },
    { title: 'PR No', dataIndex: 'prNo', width: 106, render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/request/${r.prId}`)}>{v}</a> },
    { title: 'Request No', dataIndex: 'crNo', width: 122, render: (v, r) => <RefChip onClick={() => r.crId && nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip> },
    { title: 'Quotes', dataIndex: 'compared', width: 88, numeric: true, sorter: true, render: (v) => <span className="num">{v}</span> },
    { title: 'Suppliers', dataIndex: 'suppliers', render: (_, r) => <span className="muted" style={{ fontSize: 12.5 }}>{r.compared} supplier{r.compared === 1 ? '' : 's'}</span> },
    {
      title: 'Recommended',
      dataIndex: 'best',
      width: 196,
      render: (v) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <Trophy size={14} strokeWidth={2} style={{ color: 'var(--c-success)', flex: 'none' }} />
          {v}
        </span>
      ),
    },
    {
      title: 'Selected',
      dataIndex: 'selected',
      width: 196,
      render: (v, r) => (
        <span>
          {v}
          {r.override && (
            <span className="badge" style={{ marginLeft: 6, background: 'var(--c-warning-light)', color: '#B45309', borderColor: '#FDE68A', fontSize: 11 }}>
              override
            </span>
          )}
        </span>
      ),
    },
    { title: 'Best Amount', dataIndex: 'selectedTotal', width: 152, numeric: true, sorter: true, render: (v) => <Money value={v} strong /> },
    { title: 'Status', dataIndex: 'status', width: 158, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 78,
      fixed: 'right',
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Eye} label="Open comparison" onClick={() => nav(`/purchase/quotation-comparison/${r.id}`)} />
        </RowActions>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Quotation Comparison"
        subtitle="Created when Compare is clicked on a purchase request. One comparison per request, with the lowest complete total recommended."
      />
      <DataTable
        columns={columns}
        data={rows}
        scrollX={1560}
        showRange
        searchKeys={['qcNo', 'prNo', 'crNo', 'best', 'selected', 'suppliers']}
        searchPlaceholder="Search comparison, PR, supplier…"
        filters={[
          { key: 'status', placeholder: 'Status', width: 182, options: ['Draft', 'Approved', 'Sent to Customer'].map((x) => ({ value: x, label: x })) },
        ]}
        empty={{
          icon: GitCompareArrows,
          title: 'No comparisons yet',
          description: 'Open a purchase request with two or more quotations and click Compare to build one.',
          action: <Btn variant="primary" onClick={() => nav('/purchase/request')}>Go to Purchase Requests</Btn>,
        }}
      />
    </div>
  )
}
