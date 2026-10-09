import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Tag, Alert } from 'antd'
import { Send, Eye, GitCompareArrows, ClipboardList } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { customerName, itemName, getCR } from '../../store/selectors.js'
import { rfqBody } from '../../store/seedRunner.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, RowActions,
  EmailPopup, SectionLabel, Qty, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function PurchaseRequest() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [rfqPr, setRfqPr] = useState(null)
  const [picked, setPicked] = useState([])
  const [pendingCompare, setPendingCompare] = useState(null)

  // QC_CREATE mints the comparison — jump to it once the store has it.
  useEffect(() => {
    if (!pendingCompare) return
    const qc = state.quotationComparisons.find((q) => q.prId === pendingCompare)
    if (qc) {
      setPendingCompare(null)
      nav(`/purchase/quotation-comparison/${qc.id}`)
    }
  }, [pendingCompare, state.quotationComparisons, nav])

  const rows = useMemo(
    () =>
      state.purchaseRequests.map((pr) => {
        const cr = getCR(state, pr.crId)
        const vqs = state.vendorQuotations.filter((v) => v.prId === pr.id)
        return {
          ...pr,
          crNo: cr ? cr.crNo : '—',
          customerId: cr ? cr.customerId : null,
          customer: cr ? customerName(state, cr.customerId) : '—',
          requiredBy: cr ? cr.requiredBy : null,
          askedCount: (pr.rfqSupplierIds || []).length,
          quoteCount: vqs.length,
        }
      }),
    [state]
  )

  const openRfq = (pr) => {
    setPicked(state.suppliers.filter((s) => s.active && !(pr.rfqSupplierIds || []).includes(s.id)).map((s) => s.id))
    setRfqPr(pr)
  }

  const sendRfq = ({ subject, body }) => {
    if (!picked.length) return toast.warning('Tick at least one supplier.')
    dispatch({ type: 'PR_SEND_RFQ', prId: rfqPr.id, supplierIds: picked, subject, body })
    toast.success(`Quotation request sent to ${picked.length} supplier${picked.length === 1 ? '' : 's'}.`)
    setRfqPr(null)
  }

  const compare = (pr) => {
    dispatch({ type: 'QC_CREATE', prId: pr.id })
    setPendingCompare(pr.id)
  }

  const columns = [
    {
      title: 'PR No',
      dataIndex: 'prNo',
      width: 108,
      sorter: true,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/request/${r.id}`)}>{v}</a>,
    },
    {
      title: 'Customer Request',
      dataIndex: 'crNo',
      width: 148,
      render: (v, r) => <RefChip onClick={() => nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip>,
    },
    {
      title: 'Customer',
      dataIndex: 'customer',
      width: 170,
      ellipsis: true,
      sorter: true,
      render: (v) => <span style={{ fontWeight: 550 }}>{v}</span>,
    },
    { title: 'Date', dataIndex: 'date', width: 120, sorter: true, render: fmtDate },
    { title: 'Items', width: 78, numeric: true, render: (_, r) => <span className="num">{r.lines.length}</span> },
    {
      title: 'Suppliers asked',
      dataIndex: 'askedCount',
      width: 130,
      numeric: true,
      sorter: true,
      render: (v) => <span className="num">{v}</span>,
    },
    {
      title: 'Quotes received',
      dataIndex: 'quoteCount',
      width: 130,
      numeric: true,
      sorter: true,
      render: (v) => (
        <span className="num" style={{ fontWeight: v >= 2 ? 650 : 400, color: v >= 2 ? 'var(--c-success)' : undefined }}>
          {v}
        </span>
      ),
    },
    { title: 'Status', dataIndex: 'status', width: 120, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 270,
      fixed: 'right',
      render: (_, r) => (
        <div style={{ display: 'inline-flex', gap: 6, alignItems: 'center', whiteSpace: 'nowrap' }}>
          <IconBtn icon={Eye} label="View request" onClick={() => nav(`/purchase/request/${r.id}`)} />
          {r.status !== 'Ordered' && (
            <Btn variant="outline" size="small" icon={Send} onClick={() => openRfq(r)}>
              Send RFQ
            </Btn>
          )}
          {r.quoteCount >= 1 && r.status !== 'Ordered' && (
            <Btn variant="primary" size="small" icon={GitCompareArrows} onClick={() => compare(r)}>
              {r.quoteCount >= 2 ? 'Compare' : 'Proceed'}
            </Btn>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Request (PR)"
        subtitle="Created automatically from every customer request. Requests arrive from Sales — there is nothing to key in here."
      />

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1320}
        showRange
        searchKeys={['prNo', 'crNo', 'customer']}
        searchPlaceholder="Search PR no, request no, customer…"
        filters={[
          { key: 'status', placeholder: 'Status', width: 158, options: ['Open', 'RFQ Sent', 'Quoted', 'Ordered'].map((x) => ({ value: x, label: x })) },
          {
            key: 'customerId',
            placeholder: 'Customer',
            width: 220,
            showSearch: true,
            options: state.customers.map((c) => ({ value: c.id, label: c.name })),
          },
        ]}
        empty={{
          icon: ClipboardList,
          title: 'No purchase requests are pending',
          description: 'A purchase request appears here the moment a customer request is saved in Sales.',
          action: <Btn variant="primary" onClick={() => nav('/sales/customer-request')}>Go to Customer Request</Btn>,
        }}
      />

      {/* ------------------------------ RFQ popup ------------------------------ */}
      <EmailPopup
        open={!!rfqPr}
        title={rfqPr ? `Send quotation request — ${rfqPr.prNo}` : ''}
        okText="Send RFQ"
        width={900}
        recipients={state.suppliers.filter((s) => picked.includes(s.id)).map((s) => s.email)}
        defaultSubject={rfqPr ? `Request for Quotation - ${rfqPr.prNo} (Ref ${rfqPr.crNo})` : ''}
        defaultBody={rfqPr ? rfqBody(state, state.purchaseRequests.find((p) => p.id === rfqPr.id)) : ''}
        onCancel={() => setRfqPr(null)}
        onSend={sendRfq}
        disabled={!picked.length}
      >
        {rfqPr && (
          <>
            <div className="form-sec" style={{ borderTop: 'none', paddingTop: 0, marginTop: 0 }}>
              <SectionLabel>Items on this request</SectionLabel>
              <div className="tbl-card" style={{ boxShadow: 'none' }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey={(r) => r.itemId}
                  dataSource={rfqPr.lines}
                  columns={[
                    { title: '#', width: 46, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
                    { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
                    {
                      title: 'Quantity',
                      width: 130,
                      align: 'right',
                      className: 'col-num',
                      render: (_, l) => <Qty value={l.qty} unit={l.unit} />,
                    },
                  ]}
                />
              </div>
            </div>

            <div className="form-sec">
              <SectionLabel>Suppliers to ask</SectionLabel>
              <div className="tbl-card" style={{ boxShadow: 'none' }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="id"
                  dataSource={state.suppliers.filter((s) => s.active)}
                  scroll={{ x: 720 }}
                  rowSelection={{ selectedRowKeys: picked, onChange: setPicked }}
                  columns={[
                    { title: 'Code', dataIndex: 'code', width: 88, render: (v) => <span className="doc-no">{v}</span> },
                    { title: 'Supplier', dataIndex: 'name', render: (v) => <span style={{ fontWeight: 550 }}>{v}</span> },
                    { title: 'Email', dataIndex: 'email', width: 218, render: (v) => <span className="muted">{v}</span> },
                    {
                      title: 'Categories',
                      dataIndex: 'categories',
                      width: 236,
                      render: (v) => (
                        <span style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {(v || []).map((c) => <Tag key={c} style={{ marginInlineEnd: 0, fontSize: 11.5 }}>{c}</Tag>)}
                        </span>
                      ),
                    },
                    { title: 'Lead time', dataIndex: 'leadTimeDays', width: 104, align: 'right', className: 'col-num', render: (v) => <span className="num">{v} days</span> },
                  ]}
                />
              </div>
              {(rfqPr.rfqSupplierIds || []).length > 0 && (
                <Alert
                  style={{ marginTop: 12 }}
                  type="warning"
                  showIcon
                  message={`An RFQ was already sent for this request on ${fmtDate(rfqPr.rfqSentAt)}. Ticking a supplier again sends another copy.`}
                />
              )}
            </div>
          </>
        )}
      </EmailPopup>
    </div>
  )
}
