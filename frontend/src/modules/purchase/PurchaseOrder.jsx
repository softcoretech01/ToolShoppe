import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Input, Row, Col } from 'antd'
import { Send, Eye, FileText } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { supplierName, itemName, getCR } from '../../store/selectors.js'
import { round2 } from '../../logic/pricing.js'
import { poBody } from '../../store/seedRunner.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, EmailPopup,
  Field, FormSection, Money, Qty, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function PurchaseOrder() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [sending, setSending] = useState(null)

  const rows = useMemo(
    () =>
      state.purchaseOrders.map((po) => {
        const cr = getCR(state, po.crId)
        const so = state.salesOrders.find((x) => x.id === po.soId)
        const vq = state.vendorQuotations.find((v) => v.id === po.vqId)
        return {
          ...po,
          crNo: cr ? cr.crNo : '—',
          soNo: so ? so.soNo : '—',
          vqNo: vq ? vq.vqNo : '—',
          prNo: (state.purchaseRequests.find((p) => p.crId === po.crId) || {}).prNo || '—',
          supplier: supplierName(state, po.supplierId),
        }
      }),
    [state]
  )

  const supplier = sending ? state.suppliers.find((x) => x.id === sending.supplierId) : null
  const vq = sending ? state.vendorQuotations.find((v) => v.id === sending.vqId) : null

  const columns = [
    {
      title: 'PO No',
      dataIndex: 'poNo',
      width: 108,
      sorter: true,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/purchase-order/${r.id}`)}>{v}</a>,
    },
    { title: 'PR No', dataIndex: 'prNo', width: 104, render: (v) => <span className="muted num">{v}</span> },
    {
      title: 'Supplier',
      dataIndex: 'supplier',
      width: 170,
      ellipsis: true,
      sorter: true,
      render: (v) => <span style={{ fontWeight: 550 }}>{v}</span>,
    },
    { title: 'Quotation No', dataIndex: 'vqNo', width: 128, render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/vendor-quotation/${r.vqId}`)}>{v}</a> },
    { title: 'Request No', dataIndex: 'crNo', width: 122, render: (v, r) => <RefChip onClick={() => nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip> },
    { title: 'Date', dataIndex: 'date', width: 120, sorter: true, render: fmtDate },
    { title: 'Amount', dataIndex: 'total', width: 140, numeric: true, sorter: true, render: (v) => <Money value={v} strong /> },
    { title: 'Expected delivery', dataIndex: 'expectedDelivery', width: 140, render: fmtDate },
    { title: 'Status', dataIndex: 'status', width: 140, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 170,
      fixed: 'right',
      render: (_, r) => (
        <div style={{ display: 'inline-flex', gap: 6, alignItems: 'center', whiteSpace: 'nowrap' }}>
          <IconBtn icon={Eye} label="View order" onClick={() => nav(`/purchase/purchase-order/${r.id}`)} />
          {r.status === 'Draft' && (
            <Btn variant="primary" size="small" icon={Send} onClick={() => setSending(r)}>
              Send PO
            </Btn>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Purchase Order"
        subtitle="Raised automatically when a customer PO is saved, at the rates of the selected supplier quotation."
      />

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1280}
        showRange
        searchKeys={['poNo', 'crNo', 'soNo', 'vqNo', 'supplier']}
        searchPlaceholder="Search PO, request, supplier…"
        filters={[
          {
            key: 'status',
            placeholder: 'Status',
            width: 186,
            options: ['Draft', 'Sent', 'Partially Received', 'Received', 'Closed'].map((x) => ({ value: x, label: x })),
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
          icon: FileText,
          title: 'No purchase orders yet',
          description: 'A supplier PO is raised automatically the moment a customer purchase order is recorded.',
          action: <Btn variant="primary" onClick={() => nav('/sales/customer-po')}>Go to Customer PO</Btn>,
        }}
      />

      <EmailPopup
        open={!!sending}
        title={sending ? `Send purchase order ${sending.poNo}` : ''}
        okText="Send PO"
        width={900}
        recipients={supplier ? [supplier.email] : []}
        defaultSubject={sending ? `Purchase Order ${sending.poNo} — Toolsphoppe` : ''}
        defaultBody={sending ? poBody(state, state.purchaseOrders.find((p) => p.id === sending.id)) : ''}
        onCancel={() => setSending(null)}
        onSend={({ subject, body }) => {
          dispatch({ type: 'PO_SEND', poId: sending.id, subject, body })
          toast.success('Purchase order sent to the supplier.')
          setSending(null)
        }}
      >
        {sending && (
          <>
            <FormSection>
              <Row gutter={16}>
                <Col xs={24} md={8}>
                  <Field label="Supplier">
                    <Input readOnly value={supplier ? supplier.name : ''} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Their quotation">
                    <Input readOnly value={vq ? vq.vqNo : ''} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Delivery quoted">
                    <Input readOnly value={vq ? `${vq.deliveryDays} days` : ''} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="Expected delivery">
                    <Input readOnly value={fmtDate(sending.expectedDelivery)} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            <FormSection title="Order lines">
              <div className="tbl-card" style={{ boxShadow: 'none' }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="itemId"
                  dataSource={sending.lines}
                  scroll={{ x: 640 }}
                  columns={[
                    { title: '#', width: 46, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
                    { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
                    { title: 'Qty', width: 96, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
                    { title: 'Rate', width: 122, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.rate} /> },
                    { title: 'Line total', width: 140, align: 'right', className: 'col-num', render: (_, l) => <Money value={round2(l.qty * l.rate)} /> },
                  ]}
                  summary={() => (
                    <Table.Summary>
                      <Table.Summary.Row>
                        <Table.Summary.Cell index={0} colSpan={4} align="right"><strong>PO total</strong></Table.Summary.Cell>
                        <Table.Summary.Cell index={4} align="right"><Money value={sending.total} strong /></Table.Summary.Cell>
                      </Table.Summary.Row>
                    </Table.Summary>
                  )}
                />
              </div>
            </FormSection>
          </>
        )}
      </EmailPopup>
    </div>
  )
}
