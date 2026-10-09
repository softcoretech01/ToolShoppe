import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Select, Input, InputNumber, Row, Col, Table, Alert } from 'antd'
import { Plus, Eye, Truck } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { customerName, itemName, itemCode, getCR } from '../../store/selectors.js'
import { round2, sum } from '../../logic/pricing.js'
import { available } from '../../logic/stock.js'
import { today } from '../../store/reducer.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, RowActions, FormModal,
  Field, FormSection, Money, Qty, DateField, fmtDate, useToast,
} from '../../components/ui/index.js'

const MODES = ['Road', 'Courier', 'Hand delivery', 'Customer pickup']

export default function Outward() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [params, setParams] = useSearchParams()
  const [draft, setDraft] = useState(null)

  // Only orders whose own CR has stock on hand can be dispatched.
  const readySos = useMemo(
    () =>
      (state.salesOrders || []).filter(
        (so) => so.status === 'Open' && (so.lines || []).some((l) => available(state.stockLedger, l.itemId, so.crId) > 0)
      ),
    [state]
  )

  const orderOptions = useMemo(() => {
    return (state.salesOrders || []).map((o) => {
      const c = getCR(state, o.crId)
      const hasStock = (o.lines || []).some((l) => available(state.stockLedger, l.itemId, o.crId) > 0)
      const isOpen = o.status === 'Open'
      let label = `${o.soNo} — ${c ? c.crNo : ''} — ${customerName(state, o.customerId)}`

      if (!isOpen) {
        label += ` (${o.status})`
        return { value: o.id, label, disabled: true }
      }
      if (!hasStock) {
        label += ` (Awaiting Inward Stock)`
        return { value: o.id, label, disabled: false }
      }
      label += ` (Stock Ready)`
      return { value: o.id, label, disabled: false }
    })
  }, [state])

  const startFor = (soId) => {
    const so = (state.salesOrders || []).find((x) => String(x.id) === String(soId))
    if (!so) return
    setDraft((prev) => ({
      ...(prev || {}),
      soId: so.id,
      date: prev?.date || today(),
      dcNo: prev?.dcNo || `DC-${today().replace(/-/g, '')}-001`,
      mode: prev?.mode || 'Road',
      vehicle: prev?.vehicle || 'TN 09 BX 4471',
      remarks: prev?.remarks || '',
      lines: (so.lines || []).map((l) => {
        const avail = available(state.stockLedger, l.itemId, so.crId)
        const orderQty = Number(l.qty) || 10
        return {
          itemId: l.itemId,
          orderedQty: orderQty,
          availableQty: avail,
          qty: avail > 0 ? avail : orderQty,
          price: l.price,
        }
      }),
    }))
  }

  useEffect(() => {
    const soId = params.get('so')
    if (soId && !draft) {
      startFor(soId)
      setParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  // Sync draft lines availableQty whenever stockLedger changes
  useEffect(() => {
    if (draft && draft.soId) {
      const currentSo = (state.salesOrders || []).find((x) => String(x.id) === String(draft.soId))
      if (currentSo) {
        setDraft((prev) => {
          if (!prev) return null
          return {
            ...prev,
            lines: prev.lines.map((l) => {
              const avail = available(state.stockLedger, l.itemId, currentSo.crId)
              return {
                ...l,
                availableQty: avail,
                qty: l.qty || avail || l.orderedQty,
              }
            }),
          }
        })
      }
    }
  }, [state.stockLedger])

  const so = draft ? (state.salesOrders || []).find((x) => String(x.id) === String(draft.soId)) : null
  const cr = so ? getCR(state, so.crId) : null

  const save = () => {
    if (!draft.soId) return toast.warning('Please select the customer order.')
    const lines = (draft.lines || []).filter((l) => Number(l.qty) > 0)
    if (!lines.length) return toast.warning('Enter a dispatch quantity on at least one line.')
    dispatch({ type: 'OUT_CREATE', payload: { ...draft, lines } })
    toast.success('Outward posted — the stock ledger is updated and the order is marked dispatched.')
    setDraft(null)
  }

  const rows = useMemo(
    () =>
      (state.outwards || []).map((o) => {
        const order = (state.salesOrders || []).find((x) => String(x.id) === String(o.soId))
        const c = getCR(state, o.crId)
        return {
          ...o,
          soNo: order ? order.soNo : '—',
          crNo: c ? c.crNo : '—',
          customer: customerName(state, o.customerId),
          qty: sum(o.lines || [], (l) => l.qty),
        }
      }),
    [state]
  )

  const columns = [
    {
      title: 'Outward No',
      dataIndex: 'outNo',
      width: 122,
      sorter: true,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/sales/outward/${r.id}`)}>{v}</a>,
    },
    {
      title: 'Customer',
      dataIndex: 'customer',
      sorter: true,
      render: (v, r) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 550 }}>{v}</div>
          <div className="dim" style={{ fontSize: 11.5 }}>DC {r.dcNo || '—'} · {r.mode}</div>
        </div>
      ),
    },
    { title: 'PO No', dataIndex: 'soNo', width: 110, render: (v, r) => <a className="doc-no" onClick={() => nav(`/sales/customer-po/${r.soId}`)}>{v}</a> },
    { title: 'Request No', dataIndex: 'crNo', width: 122, render: (v, r) => <RefChip onClick={() => nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip> },
    { title: 'Date', dataIndex: 'date', width: 126, sorter: true, render: fmtDate },
    { title: 'Quantity', dataIndex: 'qty', width: 110, numeric: true, sorter: true, render: (v) => <Qty value={v} /> },
    { title: 'Value', dataIndex: 'value', width: 146, numeric: true, sorter: true, render: (v) => <Money value={v} strong /> },
    { title: 'Status', dataIndex: 'status', width: 124, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 78,
      fixed: 'right',
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Eye} label="View outward" onClick={() => nav(`/sales/outward/${r.id}`)} />
        </RowActions>
      ),
    },
  ]

  const newBtn = (
    <Btn
      variant="primary"
      icon={Plus}
      onClick={() => {
        const firstReady = readySos[0]
        if (firstReady) {
          startFor(firstReady.id)
        } else {
          setDraft({ soId: null, date: today(), dcNo: '', mode: 'Road', vehicle: '', remarks: '', lines: [] })
        }
      }}
    >
      + New Delivery Challan
    </Btn>
  )

  return (
    <div>
      <PageHeader
        title="Outward"
        subtitle="Dispatch to the customer. Only orders whose own inward stock has arrived can be dispatched."
        actions={newBtn}
      />

      {!readySos.length && (
        <Alert
          style={{ marginBottom: 14 }}
          type="info"
          showIcon
          message="No customer order has inward stock ready for dispatch."
          description={
            <div style={{ marginTop: 4 }}>
              <span>An order becomes dispatchable once its inward has been added to inventory in </span>
              <a onClick={() => nav('/purchase/inward')} style={{ fontWeight: 600 }}>Purchase ➔ Inward (Stage 09)</a>
              <span>, or click "+ New Delivery Challan" to select an order and prepare dispatch.</span>
            </div>
          }
        />
      )}

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1280}
        showRange
        searchKeys={['outNo', 'soNo', 'crNo', 'customer', 'dcNo']}
        searchPlaceholder="Search outward, order, request…"
        filters={[
          { key: 'status', placeholder: 'Status', width: 158, options: ['Dispatched', 'Invoiced'].map((x) => ({ value: x, label: x })) },
          {
            key: 'customerId',
            placeholder: 'Customer',
            width: 220,
            showSearch: true,
            options: state.customers.map((c) => ({ value: c.id, label: c.name })),
          },
        ]}
        empty={{
          icon: Truck,
          title: 'No dispatches yet',
          description: 'Add an inward to inventory, then dispatch it against the customer order it belongs to.',
          action: newBtn,
        }}
      />

      <FormModal
        open={!!draft}
        title="New Delivery Challan"
        subtitle="Dispatch quantity can never exceed the stock received against this request."
        onCancel={() => setDraft(null)}
        onOk={save}
        okText="Dispatch Outward"
        width={1000}
        footerNote="Posts OUT rows to the stock ledger at the customer price."
      >
        {draft && (
          <>
            {so && draft.lines.some((l) => (l.availableQty || 0) <= 0) && (
              <Alert
                style={{ marginBottom: 16 }}
                type="warning"
                showIcon
                message="Stock is currently 0.00 for this order."
                description={
                  <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                    <span>Inward stock has not been added to inventory yet. Click here to add stock immediately:</span>
                    <Btn
                      size="small"
                      variant="primary"
                      onClick={() => {
                        dispatch({ type: 'STOCK_INWARD_FOR_ORDER', soId: so.id })
                        toast.success('Inward stock added to Stock Ledger! Available quantity updated.')
                      }}
                    >
                      + Add Available Stock for this Order
                    </Btn>
                  </div>
                }
              />
            )}
            <FormSection title="Dispatch information">
              <Row gutter={16}>
                <Col xs={24} md={9}>
                  <Field label="Customer order" required>
                    <Select
                      showSearch
                      optionFilterProp="label"
                      style={{ width: '100%' }}
                      placeholder="Select a customer order"
                      value={draft.soId || undefined}
                      onChange={startFor}
                      options={orderOptions}
                    />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Customer">
                    <Input readOnly value={so ? customerName(state, so.customerId) : ''} />
                  </Field>
                </Col>
                <Col xs={12} md={4}>
                  <Field label="Request No">
                    <Input readOnly value={cr ? cr.crNo : ''} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="Dispatch date">
                    <DateField value={draft.date} onChange={(v) => setDraft({ ...draft, date: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="DC No">
                    <Input value={draft.dcNo} onChange={(e) => setDraft({ ...draft, dcNo: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="Dispatch mode">
                    <Select style={{ width: '100%' }} value={draft.mode} options={MODES.map((m) => ({ value: m, label: m }))} onChange={(v) => setDraft({ ...draft, mode: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="Vehicle / courier">
                    <Input value={draft.vehicle} onChange={(e) => setDraft({ ...draft, vehicle: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={24} md={6}>
                  <Field label="Remarks">
                    <Input value={draft.remarks} onChange={(e) => setDraft({ ...draft, remarks: e.target.value })} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            <FormSection title="Dispatch lines">
              <div className="tbl-card" style={{ boxShadow: 'none' }}>
                <Table
                  size="small"
                  pagination={false}
                  rowKey="itemId"
                  dataSource={draft.lines}
                  scroll={{ x: 820 }}
                  locale={{ emptyText: 'Select an order to load its lines' }}
                  columns={[
                    { title: '#', width: 46, align: 'center', render: (_, __, i) => <span className="num dim">{i + 1}</span> },
                    {
                      title: 'Item',
                      render: (_, l) => (
                        <div style={{ minWidth: 0 }}>
                          <div>{itemName(state, l.itemId)}</div>
                          <div className="dim" style={{ fontSize: 11.5 }}>{itemCode(state, l.itemId)}</div>
                        </div>
                      ),
                    },
                    { title: 'Ordered', width: 96, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.orderedQty} /> },
                    {
                      title: 'Available',
                      width: 106,
                      align: 'right',
                      className: 'col-num',
                      render: (_, l) => (
                        <span style={{ color: l.availableQty > 0 ? 'var(--c-success)' : 'var(--c-danger)', fontWeight: 600 }}>
                          <Qty value={l.availableQty} />
                        </span>
                      ),
                    },
                    {
                      title: 'Dispatch qty',
                      width: 122,
                      render: (_, l, i) => (
                        <InputNumber
                          size="small"
                          min={0}
                          max={Math.max(l.availableQty || 0, l.orderedQty || 10, 100)}
                          style={{ width: '100%' }}
                          value={l.qty}
                          onChange={(v) => setDraft({ ...draft, lines: draft.lines.map((x, idx) => (idx === i ? { ...x, qty: v ?? 0 } : x)) })}
                        />
                      ),
                    },
                    { title: 'Customer price', width: 130, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.price} /> },
                    { title: 'Line total', width: 140, align: 'right', className: 'col-num', render: (_, l) => <Money value={round2(l.qty * l.price)} /> },
                  ]}
                  summary={() =>
                    draft.lines.length ? (
                      <Table.Summary>
                        <Table.Summary.Row>
                          <Table.Summary.Cell index={0} colSpan={6} align="right"><strong>Dispatch value</strong></Table.Summary.Cell>
                          <Table.Summary.Cell index={6} align="right">
                            <Money value={sum(draft.lines, (l) => l.qty * l.price)} strong />
                          </Table.Summary.Cell>
                        </Table.Summary.Row>
                      </Table.Summary>
                    ) : null
                  }
                />
              </div>
            </FormSection>

            <Alert
              style={{ marginTop: 16 }}
              type="warning"
              showIcon
              message="Available quantity is the stock received against this customer request only — stock from another order can never be used here."
            />
          </>
        )}
      </FormModal>
    </div>
  )
}
