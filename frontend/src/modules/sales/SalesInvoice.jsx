import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Select, Input, Row, Col, Table, Alert } from 'antd'
import { Plus, Eye, ReceiptText } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { customerName, itemName, getCR, getItem } from '../../store/selectors.js'
import { round2, sum } from '../../logic/pricing.js'
import { today, addDays } from '../../store/reducer.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, RowActions, FormModal,
  Field, FormSection, Money, Qty, Pct, DateField, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function SalesInvoice() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [params, setParams] = useSearchParams()
  const [draft, setDraft] = useState(null)

  const openOuts = useMemo(() => state.outwards.filter((o) => o.status === 'Dispatched'), [state])

  const startFor = (outId) => {
    const out = state.outwards.find((o) => o.id === outId)
    if (!out) return
    const cust = state.customers.find((c) => c.id === out.customerId)
    setDraft({ outId, date: today(), paymentTerms: cust ? cust.paymentTerms : '', dueDate: addDays(today(), 30) })
  }

  useEffect(() => {
    const outId = params.get('out')
    if (outId && !draft) {
      startFor(outId)
      setParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  const out = draft ? state.outwards.find((o) => o.id === draft.outId) : null
  const preview = out
    ? out.lines.map((l) => {
        const item = getItem(state, l.itemId)
        const taxable = round2(l.qty * l.price)
        const taxPct = item ? item.taxPct : 0
        return { ...l, taxable, taxPct, taxAmount: round2((taxable * taxPct) / 100) }
      })
    : []

  const save = () => {
    if (!draft.outId) return toast.warning('Please select the outward to invoice.')
    dispatch({ type: 'SI_CREATE', payload: draft })
    toast.success('Sales invoice created successfully.')
    setDraft(null)
  }

  const rows = useMemo(
    () =>
      state.salesInvoices.map((si) => {
        const so = state.salesOrders.find((x) => x.id === si.soId)
        const o = state.outwards.find((x) => x.id === si.outId)
        const cr = getCR(state, si.crId)
        return {
          ...si,
          soNo: so ? so.soNo : '—',
          outNo: o ? o.outNo : '—',
          crNo: cr ? cr.crNo : '—',
          customer: customerName(state, si.customerId),
        }
      }),
    [state]
  )

  const columns = [
    {
      title: 'Invoice No',
      dataIndex: 'siNo',
      width: 116,
      sorter: true,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/sales/invoice/${r.id}`)}>{v}</a>,
    },
    {
      title: 'Customer',
      dataIndex: 'customer',
      width: 170,
      ellipsis: true,
      sorter: true,
      render: (v) => <span style={{ fontWeight: 550 }}>{v}</span>,
    },
    { title: 'Outward No', dataIndex: 'outNo', width: 105, render: (v, r) => <a className="doc-no" onClick={() => nav(`/sales/outward/${r.outId}`)}>{v}</a> },
    { title: 'Request No', dataIndex: 'crNo', width: 105, render: (v, r) => <RefChip onClick={() => nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip> },
    { title: 'Date', dataIndex: 'date', width: 115, sorter: true, render: fmtDate },
    { title: 'Taxable', dataIndex: 'subtotal', width: 110, numeric: true, render: (v) => <Money value={v} /> },
    { title: 'Tax', dataIndex: 'tax', width: 95, numeric: true, render: (v) => <Money value={v} muted /> },
    { title: 'Amount', dataIndex: 'total', width: 115, numeric: true, sorter: true, render: (v) => <Money value={v} strong /> },
    { title: 'Due date', dataIndex: 'dueDate', width: 110, render: fmtDate },
    { title: 'Status', dataIndex: 'status', width: 95, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 75,
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Eye} label="View invoice" onClick={() => nav(`/sales/invoice/${r.id}`)} />
        </RowActions>
      ),
    },
  ]

  const newBtn = (
    <Btn
      variant="primary"
      icon={Plus}
      disabled={!openOuts.length}
      onClick={() => setDraft({ outId: null, date: today(), paymentTerms: '', dueDate: addDays(today(), 30) })}
    >
      Create Invoice
    </Btn>
  )

  return (
    <div>
      <PageHeader
        title="Invoice"
        subtitle="Raised from an outward at the customer prices, with item-level GST added."
        actions={newBtn}
      />

      {!openOuts.length && state.salesInvoices.length > 0 && (
        <Alert style={{ marginBottom: 14 }} type="info" showIcon message="Every dispatch has been invoiced. Post a new outward to raise another invoice." />
      )}

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1180}
        showRange
        searchKeys={['siNo', 'soNo', 'outNo', 'crNo', 'customer']}
        searchPlaceholder="Search invoice, outward, request…"
        filters={[
          {
            key: 'customerId',
            placeholder: 'Customer',
            width: 220,
            showSearch: true,
            options: state.customers.map((c) => ({ value: c.id, label: c.name })),
          },
        ]}
        empty={{
          icon: ReceiptText,
          title: 'No sales invoices yet',
          description: 'Dispatch an order first — the invoice is raised directly from the outward.',
          action: newBtn,
        }}
      />

      <FormModal
        open={!!draft}
        title="New sales invoice"
        subtitle="Lines, prices and tax are taken from the dispatch — nothing is re-keyed."
        onCancel={() => setDraft(null)}
        onOk={save}
        okText="Create invoice"
        width={940}
      >
        {draft && (
          <>
            <FormSection title="Invoice information">
              <Row gutter={16}>
                <Col xs={24} md={10}>
                  <Field label="Outward" required>
                    <Select
                      showSearch
                      optionFilterProp="label"
                      style={{ width: '100%' }}
                      placeholder="Select the dispatch to invoice"
                      value={draft.outId || undefined}
                      onChange={startFor}
                      options={openOuts.map((o) => {
                        const cr = getCR(state, o.crId)
                        return { value: o.id, label: `${o.outNo} — ${cr ? cr.crNo : ''} — ${customerName(state, o.customerId)}` }
                      })}
                    />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Invoice date">
                    <DateField value={draft.date} onChange={(v) => setDraft({ ...draft, date: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Due date">
                    <DateField value={draft.dueDate} onChange={(v) => setDraft({ ...draft, dueDate: v })} />
                  </Field>
                </Col>
                <Col xs={24} md={12}>
                  <Field label="Payment terms">
                    <Input value={draft.paymentTerms} onChange={(e) => setDraft({ ...draft, paymentTerms: e.target.value })} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            {out && (
              <FormSection title="Invoice preview">
                <div className="tbl-card" style={{ boxShadow: 'none' }}>
                  <Table
                    size="small"
                    pagination={false}
                    rowKey="itemId"
                    dataSource={preview}
                    scroll={{ x: 800 }}
                    columns={[
                      { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
                      { title: 'Qty', width: 86, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.qty} /> },
                      { title: 'Rate', width: 118, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.price} /> },
                      { title: 'Taxable', width: 128, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.taxable} /> },
                      { title: 'Tax %', width: 90, align: 'right', className: 'col-num', render: (_, l) => <Pct value={l.taxPct} /> },
                      { title: 'Tax', width: 118, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.taxAmount} muted /> },
                      { title: 'Total', width: 134, align: 'right', className: 'col-num', render: (_, l) => <Money value={round2(l.taxable + l.taxAmount)} strong /> },
                    ]}
                    summary={() => (
                      <Table.Summary>
                        <Table.Summary.Row>
                          <Table.Summary.Cell index={0} colSpan={6} align="right"><strong>Invoice total</strong></Table.Summary.Cell>
                          <Table.Summary.Cell index={6} align="right">
                            <Money value={sum(preview, (l) => l.taxable + l.taxAmount)} strong />
                          </Table.Summary.Cell>
                        </Table.Summary.Row>
                      </Table.Summary>
                    )}
                  />
                </div>
              </FormSection>
            )}
          </>
        )}
      </FormModal>
    </div>
  )
}
