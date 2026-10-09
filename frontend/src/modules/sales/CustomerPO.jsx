import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Select, Input, InputNumber, Row, Col, Table, Alert } from 'antd'
import { Plus, Eye, ShoppingCart } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { customerName, itemName, itemCode, getCR, supplierName } from '../../store/selectors.js'
import { round2, sum } from '../../logic/pricing.js'
import { today } from '../../store/reducer.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, RowActions, FormModal,
  Field, FormSection, Money, Qty, DateField, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function CustomerPO() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [params, setParams] = useSearchParams()
  const [draft, setDraft] = useState(null)

  // Quotations the customer accepted that have not been converted yet.
  const openCqs = useMemo(
    () =>
      (state.customerQuotations || []).filter(
        (q) =>
          q.status === 'Accepted' &&
          !(state.salesOrders || []).some((so) => String(so.cqId) === String(q.id))
      ),
    [state]
  )

  // Options for quotation selector: accepted ones are selectable, others are disabled with reason
  const quotationOptions = useMemo(() => {
    return (state.customerQuotations || []).map((q) => {
      const isAlreadyOrdered = (state.salesOrders || []).some((so) => String(so.cqId) === String(q.id))
      const isAccepted = q.status === 'Accepted'
      let label = `${q.cqNo} — ${customerName(state, q.customerId)}`
      let disabled = false

      if (isAlreadyOrdered) {
        label += ' (Already Ordered)'
        disabled = true
      } else if (!isAccepted) {
        label += ` (${q.status || 'Unaccepted'} - Unaccepted)`
        disabled = true
      } else {
        label += ' (Accepted)'
      }

      return {
        value: q.id,
        label,
        disabled,
      }
    })
  }, [state])

  const startFor = (cqId) => {
    const cq = (state.customerQuotations || []).find((q) => String(q.id) === String(cqId))
    if (!cq) return
    setDraft((prev) => ({
      ...(prev || {}),
      cqId: cq.id,
      date: prev?.date || today(),
      customerPoNo: prev?.customerPoNo || '',
      customerPoDate: prev?.customerPoDate || today(),
      deliveryDate: prev?.deliveryDate || null,
      lines: (cq.lines || []).map((l) => ({
        itemId: l.itemId,
        qty: l.qty,
        price: l.customerPrice,
      })),
    }))
  }

  useEffect(() => {
    const cqId = params.get('cq')
    if (cqId && !draft) {
      startFor(cqId)
      setParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  const cq = draft ? (state.customerQuotations || []).find((q) => String(q.id) === String(draft.cqId)) : null
  const cr = cq ? getCR(state, cq.crId) : null
  const qc = cq ? (state.quotationComparisons || []).find((x) => String(x.id) === String(cq.qcId)) : null
  const vq = qc ? (state.vendorQuotations || []).find((v) => String(v.id) === String(qc.selectedVqId)) : null

  const save = () => {
    if (!draft.cqId) return toast.warning('Please select the accepted quotation.')
    if (!draft.customerPoNo || !draft.customerPoNo.trim()) {
      return toast.warning("Please enter the customer's PO number.")
    }
    dispatch({ type: 'SO_CREATE', payload: draft })
    toast.success('Customer PO saved — the supplier purchase order was raised automatically.')
    setDraft(null)
  }

  const rows = useMemo(
    () =>
      (state.salesOrders || []).map((so) => {
        const c = getCR(state, so.crId)
        const q = (state.customerQuotations || []).find((x) => String(x.id) === String(so.cqId))
        return { ...so, crNo: c ? c.crNo : '—', cqNo: q ? q.cqNo : '—', customer: customerName(state, so.customerId) }
      }),
    [state]
  )

  const columns = [
    {
      title: 'PO No',
      dataIndex: 'soNo',
      width: 110,
      sorter: true,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/sales/customer-po/${r.id}`)}>{v}</a>,
    },
    {
      title: 'Customer',
      dataIndex: 'customer',
      sorter: true,
      render: (v, r) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 550 }}>{v}</div>
          <div className="dim" style={{ fontSize: 11.5 }}>Their PO {r.customerPoNo}</div>
        </div>
      ),
    },
    {
      title: 'Quotation No',
      dataIndex: 'cqNo',
      width: 124,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/sales/quotation/${r.cqId}`)}>{v}</a>,
    },
    {
      title: 'Request No',
      dataIndex: 'crNo',
      width: 122,
      render: (v, r) => <RefChip onClick={() => nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip>,
    },
    { title: 'Date', dataIndex: 'date', width: 126, sorter: true, render: fmtDate },
    { title: 'Amount', dataIndex: 'total', width: 148, numeric: true, sorter: true, render: (v) => <Money value={v} strong /> },
    { title: 'Status', dataIndex: 'status', width: 124, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 78,
      fixed: 'right',
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Eye} label="View order" onClick={() => nav(`/sales/customer-po/${r.id}`)} />
        </RowActions>
      ),
    },
  ]

  const newBtn = (
    <Btn
      variant="primary"
      icon={Plus}
      onClick={() => {
        const firstOpen = openCqs[0]
        if (firstOpen) {
          startFor(firstOpen.id)
        } else {
          setDraft({
            cqId: null,
            date: today(),
            customerPoNo: '',
            customerPoDate: today(),
            deliveryDate: null,
            lines: [],
          })
        }
      }}
    >
      Record Customer PO
    </Btn>
  )

  return (
    <div>
      <PageHeader
        title="Purchase Order"
        subtitle="Record the customer's own purchase order against an accepted quotation. Saving raises the supplier PO automatically."
        actions={newBtn}
      />

      {!openCqs.length && (
        <Alert
          style={{ marginBottom: 14 }}
          type="info"
          showIcon
          message="No accepted quotation is waiting."
          description={
            <div style={{ marginTop: 4 }}>
              <span>Mark a customer quotation as Accepted in </span>
              <a onClick={() => nav('/sales/quotation')} style={{ fontWeight: 600 }}>Sales ➔ Customer Quotation</a>
              <span> to convert it into a purchase order, or click "+ Record Customer PO" to view and select quotations.</span>
            </div>
          }
        />
      )}

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1240}
        showRange
        searchKeys={['soNo', 'customerPoNo', 'crNo', 'cqNo', 'customer']}
        searchPlaceholder="Search PO no, customer PO, request…"
        filters={[
          { key: 'status', placeholder: 'Status', width: 158, options: ['Open', 'Dispatched', 'Invoiced'].map((x) => ({ value: x, label: x })) },
          {
            key: 'customerId',
            placeholder: 'Customer',
            width: 220,
            showSearch: true,
            options: state.customers.map((c) => ({ value: c.id, label: c.name })),
          },
        ]}
        empty={{
          icon: ShoppingCart,
          title: 'No customer orders yet',
          description: 'Once a customer accepts a quotation, record their purchase order here.',
          action: newBtn,
        }}
      />

      <FormModal
        open={!!draft}
        title="Record Customer PO"
        subtitle="Enter the order exactly as it appears on the customer's own document."
        onCancel={() => setDraft(null)}
        onOk={save}
        okText="Create Order"
        width={980}
        footerNote={vq ? `A purchase order will be raised on ${supplierName(state, vq.supplierId)} at their quoted rates.` : undefined}
      >
        {draft && (
          <>
            {!openCqs.length && (
              <Alert
                style={{ marginBottom: 16 }}
                type="warning"
                showIcon
                message="No accepted quotation is currently available."
                description={
                  <span>
                    To convert a quotation, mark it as Accepted in{' '}
                    <a onClick={() => nav('/sales/quotation')} style={{ fontWeight: 600 }}>Customer Quotation (Step 05)</a>, or{' '}
                    <a
                      onClick={() => {
                        const candidate = (state.customerQuotations || []).find(
                          (q) => !(state.salesOrders || []).some((so) => String(so.cqId) === String(q.id))
                        )
                        if (candidate) {
                          dispatch({ type: 'CQ_SET_STATUS', cqId: candidate.id, status: 'Accepted' })
                          startFor(candidate.id)
                          toast.success(`Marked ${candidate.cqNo} as Accepted for testing.`)
                        } else {
                          toast.info('No available quotations to accept.')
                        }
                      }}
                      style={{ fontWeight: 600 }}
                    >
                      click here to mark an available quotation as Accepted
                    </a>.
                  </span>
                }
              />
            )}
            <FormSection title="Order information">
              <Row gutter={16}>
                <Col xs={24} md={10}>
                  <Field label="Accepted quotation" required>
                    <Select
                      showSearch
                      optionFilterProp="label"
                      style={{ width: '100%' }}
                      placeholder="Select the accepted quotation"
                      value={draft.cqId || undefined}
                      onChange={startFor}
                      options={quotationOptions}
                    />
                  </Field>
                </Col>
                <Col xs={12} md={7}>
                  <Field label="Customer PO No" required help="As printed on their document.">
                    <Input value={draft.customerPoNo} onChange={(e) => setDraft({ ...draft, customerPoNo: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={12} md={7}>
                  <Field label="Customer PO date">
                    <DateField value={draft.customerPoDate} onChange={(v) => setDraft({ ...draft, customerPoDate: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="Request No">
                    <Input readOnly value={cr ? cr.crNo : ''} />
                  </Field>
                </Col>
                <Col xs={12} md={10}>
                  <Field label="Customer">
                    <Input readOnly value={cq ? customerName(state, cq.customerId) : ''} />
                  </Field>
                </Col>
                <Col xs={24} md={8}>
                  <Field label="Delivery date">
                    <DateField value={draft.deliveryDate} onChange={(v) => setDraft({ ...draft, deliveryDate: v })} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            <FormSection title="Item details">
              <div className="tbl-card" style={{ boxShadow: 'none' }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="itemId"
                  dataSource={draft.lines}
                  scroll={{ x: 720 }}
                  locale={{ emptyText: 'Select a quotation to load its lines' }}
                  columns={[
                    { title: '#', width: 46, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
                    { title: 'Code', width: 106, render: (_, l) => <span className="doc-no">{itemCode(state, l.itemId)}</span> },
                    { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
                    {
                      title: 'Quantity',
                      width: 108,
                      render: (_, l, i) => (
                        <InputNumber
                          size="small"
                          min={0}
                          style={{ width: '100%' }}
                          value={l.qty}
                          onChange={(v) => setDraft({ ...draft, lines: draft.lines.map((x, idx) => (idx === i ? { ...x, qty: v } : x)) })}
                        />
                      ),
                    },
                    {
                      title: 'Customer price',
                      width: 134,
                      render: (_, l, i) => (
                        <InputNumber
                          size="small"
                          min={0}
                          step={0.01}
                          style={{ width: '100%' }}
                          value={l.price}
                          onChange={(v) => setDraft({ ...draft, lines: draft.lines.map((x, idx) => (idx === i ? { ...x, price: v } : x)) })}
                        />
                      ),
                    },
                    {
                      title: 'Line total',
                      width: 140,
                      align: 'right',
                      className: 'col-num',
                      render: (_, l) => <Money value={round2(l.qty * l.price)} />,
                    },
                  ]}
                  summary={() =>
                    draft.lines.length ? (
                      <Table.Summary>
                        <Table.Summary.Row>
                          <Table.Summary.Cell index={0} colSpan={5} align="right"><strong>Order total</strong></Table.Summary.Cell>
                          <Table.Summary.Cell index={5} align="right">
                            <Money value={sum(draft.lines, (l) => l.qty * l.price)} strong />
                          </Table.Summary.Cell>
                        </Table.Summary.Row>
                      </Table.Summary>
                    ) : null
                  }
                />
              </div>
            </FormSection>

            {vq && (
              <Alert
                style={{ marginTop: 16 }}
                type="info"
                showIcon
                message={`On save, a purchase order will be raised on ${supplierName(state, vq.supplierId)} at their quoted rates (${vq.vqNo}), status Draft.`}
              />
            )}
          </>
        )}
      </FormModal>
    </div>
  )
}
