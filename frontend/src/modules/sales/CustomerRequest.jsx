import React, { useState } from 'react'
import { Input, InputNumber, Row, Col, Select, Alert } from 'antd'
import { useNavigate } from 'react-router-dom'
import { Plus, Pencil, Eye, Waypoints, FileText } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { customerName, getItem } from '../../store/selectors.js'
import { CR_STAGES, today } from '../../store/reducer.js'
import { sum } from '../../logic/pricing.js'
import { UNITS } from '../../store/seed.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, RowActions, FormModal,
  Field, FormSection, Qty, LineItems, Lookup, DateField, fmtDate, useToast,
} from '../../components/ui/index.js'

const emptyLine = () => ({ itemId: null, description: '', qty: 1, unit: 'Nos', remarks: '' })

export default function CustomerRequest() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [draft, setDraft] = useState(null)

  const start = (cr) =>
    setDraft(
      cr
        ? { ...cr, lines: cr.lines.map((l) => ({ ...l })) }
        : { customerId: null, date: today(), requiredBy: null, reference: '', remarks: '', lines: [emptyLine()] }
    )

  const set = (patch) => setDraft((d) => ({ ...d, ...patch }))

  const save = () => {
    if (!draft.customerId) return toast.warning('Please select a customer.')
    const lines = draft.lines.filter((l) => l.itemId && Number(l.qty) > 0)
    if (!lines.length) return toast.warning('Add at least one item line with a quantity.')
    if (draft.id) {
      dispatch({ type: 'CR_UPDATE', payload: { ...draft, lines } })
      toast.success('Customer request updated.')
    } else {
      dispatch({ type: 'CR_CREATE', payload: { ...draft, lines } })
      toast.success('Request saved — a purchase request was created automatically.')
    }
    setDraft(null)
  }

  const columns = [
    {
      title: 'Request No',
      dataIndex: 'crNo',
      width: 118,
      sorter: true,
      render: (v, r) => (
        <a className="doc-no" onClick={() => nav(`/sales/customer-request/${r.id}`)}>{v}</a>
      ),
    },
    { title: 'Date', dataIndex: 'date', width: 126, sorter: true, render: fmtDate },
    {
      title: 'Customer',
      sorter: true,
      dataIndex: 'customer',
      render: (v, r) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 550 }}>{v}</div>
          {r.reference && <div className="dim" style={{ fontSize: 11.5 }}>Ref {r.reference}</div>}
        </div>
      ),
    },
    { title: 'Required by', dataIndex: 'requiredBy', width: 128, render: fmtDate },
    { title: 'Items', width: 82, numeric: true, render: (_, r) => <span className="num">{r.lines.length}</span> },
    { title: 'Quantity', width: 108, numeric: true, render: (_, r) => <Qty value={sum(r.lines, (l) => l.qty)} /> },
    { title: 'Status', dataIndex: 'stage', width: 138, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 106,
      fixed: 'right',
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Waypoints} label="Track chain" onClick={() => nav(`/sales/customer-request/${r.id}`)} />
          <IconBtn icon={Eye} label="View" onClick={() => nav(`/sales/customer-request/${r.id}`)} />
          <IconBtn
            icon={Pencil}
            label={r.stage === 'Requested' ? 'Edit' : 'Locked once the RFQ is sent'}
            disabled={r.stage !== 'Requested'}
            onClick={() => start(r)}
          />
        </RowActions>
      ),
    },
  ]

  const rows = state.customerRequests.map((r) => ({ ...r, customer: customerName(state, r.customerId) }))

  return (
    <div>
      <PageHeader
        title="Customer Request"
        subtitle="Step 1 of the chain. Saving a request creates the matching purchase request automatically."
        actions={
          <Btn variant="primary" icon={Plus} onClick={() => start(null)}>
            New Request
          </Btn>
        }
      />

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1180}
        showRange
        searchKeys={['crNo', 'reference', 'customer', (r) => String(r.id), (r) => String(r.crNo)]}
        searchPlaceholder="Search request no, customer, reference…"
        filters={[
          { key: 'stage', placeholder: 'Status', width: 170, options: CR_STAGES.map((x) => ({ value: x, label: x })) },
          {
            key: 'customerId',
            placeholder: 'Customer',
            width: 220,
            showSearch: true,
            options: state.customers.map((x) => ({ value: x.id, label: x.name })),
          },
        ]}
        empty={{
          icon: FileText,
          title: 'No customer requests found',
          description: 'A customer request is what starts the whole back-to-back chain.',
          action: <Btn variant="primary" icon={Plus} onClick={() => start(null)}>New Request</Btn>,
        }}
      />

      <FormModal
        open={!!draft}
        title={draft?.id ? `Edit request ${draft.crNo}` : 'New customer request'}
        subtitle="Capture what the customer is asking for. The system numbers the document on save."
        onCancel={() => setDraft(null)}
        onOk={save}
        okText={draft?.id ? 'Update request' : 'Save request'}
        width={1000}
        footerNote="A purchase request with the same lines is created automatically."
      >
        {draft && (
          <>
            <FormSection title="Request information">
              <Row gutter={16}>
                <Col xs={24} md={9}>
                  <Field label="Customer" required>
                    <Lookup kind="customer" value={draft.customerId} onChange={(v) => set({ customerId: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Request date">
                    <DateField value={draft.date} onChange={(v) => set({ date: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Required by">
                    <DateField value={draft.requiredBy} onChange={(v) => set({ requiredBy: v })} />
                  </Field>
                </Col>
                <Col xs={24} md={5}>
                  <Field label="Customer reference">
                    <Input value={draft.reference} onChange={(e) => set({ reference: e.target.value })} placeholder="Their enquiry no." />
                  </Field>
                </Col>
                <Col xs={24}>
                  <Field label="Remarks">
                    <Input value={draft.remarks} onChange={(e) => set({ remarks: e.target.value })} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            <FormSection title="Item details">
              <LineItems
                rows={draft.lines}
                onChange={(lines) => set({ lines })}
                newRow={emptyLine}
                scrollX={760}
                columns={[
                  {
                    title: 'Item',
                    width: 250,
                    render: (row, i, setRow) => (
                      <Lookup
                        kind="item"
                        size="small"
                        value={row.itemId}
                        onChange={(v) => {
                          const it = getItem(state, v)
                          setRow(i, { itemId: v, unit: it ? it.unit : row.unit, description: it ? it.description : '' })
                        }}
                      />
                    ),
                  },
                  {
                    title: 'Description',
                    render: (row, i, setRow) => (
                      <Input size="small" value={row.description} onChange={(e) => setRow(i, { description: e.target.value })} />
                    ),
                  },
                  {
                    title: 'Quantity',
                    width: 104,
                    render: (row, i, setRow) => (
                      <InputNumber size="small" min={0} style={{ width: '100%' }} value={row.qty} onChange={(v) => setRow(i, { qty: v })} />
                    ),
                  },
                  {
                    title: 'UOM',
                    width: 96,
                    render: (row, i, setRow) => (
                      <Select size="small" style={{ width: '100%' }} value={row.unit} options={UNITS.map((u) => ({ value: u, label: u }))} onChange={(v) => setRow(i, { unit: v })} />
                    ),
                  },
                  {
                    title: 'Remarks',
                    width: 180,
                    render: (row, i, setRow) => (
                      <Input size="small" value={row.remarks} onChange={(e) => setRow(i, { remarks: e.target.value })} />
                    ),
                  },
                ]}
              />
            </FormSection>

            <Alert
              style={{ marginTop: 16 }}
              type="info"
              showIcon
              message="On save the system generates the request number and creates a purchase request with the same lines, ready for RFQ."
            />
          </>
        )}
      </FormModal>
    </div>
  )
}
