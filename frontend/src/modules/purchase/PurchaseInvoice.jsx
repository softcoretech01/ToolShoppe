import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Select, Input, Row, Col, Table, Alert } from 'antd'
import { Plus, Eye, ReceiptText } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { supplierName, itemName, getCR, getItem } from '../../store/selectors.js'
import { round2, sum } from '../../logic/pricing.js'
import { today, addDays } from '../../store/reducer.js'
import {
  DataTable, PageHeader, StatusBadge, RefChip, Btn, IconBtn, RowActions, FormModal,
  Field, FormSection, Money, Qty, Pct, DateField, fmtDate, useToast,
} from '../../components/ui/index.js'

export default function PurchaseInvoice() {
  const { state, dispatch } = useApp()
  const toast = useToast()
  const nav = useNavigate()
  const [params, setParams] = useSearchParams()
  const [draft, setDraft] = useState(null)

  const openGrns = useMemo(() => {
    return (state.grns || []).filter((g) => {
      if (draft && String(g.id) === String(draft.grnId)) return true
      return g.status === 'Received'
    })
  }, [state.grns, draft])

  const startFor = (grnId) => {
    const g = state.grns.find((x) => x.id === grnId)
    if (!g) return
    setDraft({ grnId, date: today(), supplierInvNo: '', supplierInvDate: g.date, dueDate: addDays(today(), 30) })
  }

  useEffect(() => {
    const grnId = params.get('grn')
    if (grnId && !draft) {
      startFor(grnId)
      setParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  const grn = draft ? state.grns.find((g) => g.id === draft.grnId) : null
  const preview = grn
    ? grn.lines
        .filter((l) => l.acceptedQty > 0)
        .map((l) => {
          const item = getItem(state, l.itemId)
          const taxable = round2(l.acceptedQty * l.rate)
          const taxPct = item ? item.taxPct : 0
          return { ...l, taxable, taxPct, taxAmount: round2((taxable * taxPct) / 100) }
        })
    : []

  const save = () => {
    if (!draft.grnId) return toast.warning('Please select the GRN to invoice.')
    if (!draft.supplierInvNo.trim()) return toast.warning("Please enter the supplier's invoice number.")
    dispatch({ type: 'PI_CREATE', payload: draft })
    toast.success('Purchase invoice recorded successfully.')
    setDraft(null)
  }

  const rows = useMemo(
    () =>
      state.purchaseInvoices.map((pi) => {
        const po = state.purchaseOrders.find((x) => x.id === pi.poId)
        const g = state.grns.find((x) => x.id === pi.grnId)
        const cr = getCR(state, pi.crId)
        return {
          ...pi,
          poNo: po ? po.poNo : '—',
          grnNo: g ? g.grnNo : '—',
          crNo: cr ? cr.crNo : '—',
          supplier: supplierName(state, pi.supplierId),
        }
      }),
    [state]
  )

  const columns = [
    {
      title: 'Invoice No',
      dataIndex: 'piNo',
      width: 108,
      sorter: true,
      render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/invoice/${r.id}`)}>{v}</a>,
    },
    {
      title: 'Supplier',
      dataIndex: 'supplier',
      width: 170,
      ellipsis: true,
      sorter: true,
      render: (v, r) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 550, overflow: 'hidden', textOverflow: 'ellipsis' }}>{v}</div>
          <div className="dim" style={{ fontSize: 11.5 }}>Their inv {r.supplierInvNo}</div>
        </div>
      ),
    },
    { title: 'PO No', dataIndex: 'poNo', width: 95, render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/purchase-order/${r.poId}`)}>{v}</a> },
    { title: 'GRN No', dataIndex: 'grnNo', width: 95, render: (v, r) => <a className="doc-no" onClick={() => nav(`/purchase/grn/${r.grnId}`)}>{v}</a> },
    { title: 'Request No', dataIndex: 'crNo', width: 105, render: (v, r) => <RefChip onClick={() => nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip> },
    { title: 'Date', dataIndex: 'date', width: 115, sorter: true, render: fmtDate },
    { title: 'Amount', dataIndex: 'total', width: 120, numeric: true, sorter: true, render: (v) => <Money value={v} strong /> },
    { title: 'Due date', dataIndex: 'dueDate', width: 115, render: fmtDate },
    { title: 'Status', dataIndex: 'status', width: 100, render: (v) => <StatusBadge status={v} /> },
    {
      title: 'Actions',
      width: 75,
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Eye} label="View invoice" onClick={() => nav(`/purchase/invoice/${r.id}`)} />
        </RowActions>
      ),
    },
  ]

  const newBtn = (
    <Btn
      variant="primary"
      icon={Plus}
      disabled={!openGrns.length}
      onClick={() => setDraft({ grnId: null, date: today(), supplierInvNo: '', supplierInvDate: today(), dueDate: addDays(today(), 30) })}
    >
      Create Invoice
    </Btn>
  )

  return (
    <div>
      <PageHeader
        title="Invoice"
        subtitle="Recorded against a GRN at the supplier's rates, using their own invoice number."
        actions={newBtn}
      />

      {!openGrns.length && state.purchaseInvoices.length > 0 && (
        <Alert style={{ marginBottom: 14 }} type="info" showIcon message="Every GRN has been invoiced. Record a new goods receipt to raise another purchase invoice." />
      )}

      <DataTable
        columns={columns}
        data={rows}
        scrollX={1060}
        showRange
        searchKeys={['piNo', 'poNo', 'grnNo', 'crNo', 'supplier', 'supplierInvNo']}
        searchPlaceholder="Search invoice, PO, GRN, supplier…"
        filters={[
          {
            key: 'supplierId',
            placeholder: 'Supplier',
            width: 226,
            showSearch: true,
            options: state.suppliers.map((c) => ({ value: c.id, label: c.name })),
          },
        ]}
        empty={{
          icon: ReceiptText,
          title: 'No purchase invoices yet',
          description: "Record a goods receipt first, then book the supplier's invoice against it.",
          action: newBtn,
        }}
      />

      <FormModal
        open={!!draft}
        title="New purchase invoice"
        subtitle="Only accepted quantities are billed — rejected goods are excluded automatically."
        onCancel={() => setDraft(null)}
        onOk={save}
        okText="Record invoice"
        width={940}
      >
        {draft && (
          <>
            <FormSection title="Invoice information">
              <Row gutter={16}>
                <Col xs={24} md={10}>
                  <Field label="GRN" required>
                    <Select
                      showSearch
                      optionFilterProp="label"
                      style={{ width: '100%' }}
                      placeholder="Select the goods receipt"
                      value={draft.grnId || undefined}
                      onChange={startFor}
                      options={openGrns.map((g) => {
                        const po = (state.purchaseOrders || []).find((p) => String(p.id) === String(g.poId))
                        const crId = g.crId || (po ? po.crId : null)
                        const cr = getCR(state, crId)
                        const sup = supplierName(state, g.supplierId || (po ? po.supplierId : null))
                        const parts = [g.grnNo]
                        if (po && po.poNo) parts.push(po.poNo)
                        if (cr && cr.crNo) parts.push(cr.crNo)
                        if (sup && sup !== '—') parts.push(sup)
                        return { value: g.id, label: parts.join(' — ') }
                      })}
                    />
                  </Field>
                </Col>
                <Col xs={12} md={7}>
                  <Field label="Supplier invoice no" required>
                    <Input value={draft.supplierInvNo} onChange={(e) => setDraft({ ...draft, supplierInvNo: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={12} md={7}>
                  <Field label="Supplier invoice date">
                    <DateField value={draft.supplierInvDate} onChange={(v) => setDraft({ ...draft, supplierInvDate: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="Booking date">
                    <DateField value={draft.date} onChange={(v) => setDraft({ ...draft, date: v })} />
                  </Field>
                </Col>
                <Col xs={12} md={6}>
                  <Field label="Due date">
                    <DateField value={draft.dueDate} onChange={(v) => setDraft({ ...draft, dueDate: v })} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            {grn && (
              <FormSection title="Invoice preview (accepted quantities only)">
                <div className="tbl-card" style={{ boxShadow: 'none' }}>
                  <Table
                    size="small"
                    pagination={false}
                    rowKey="itemId"
                    dataSource={preview}
                    scroll={{ x: 800 }}
                    columns={[
                      { title: 'Item', render: (_, l) => itemName(state, l.itemId) },
                      { title: 'Qty', width: 86, align: 'right', className: 'col-num', render: (_, l) => <Qty value={l.acceptedQty} /> },
                      { title: 'Rate', width: 118, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.rate} /> },
                      { title: 'Taxable', width: 128, align: 'right', className: 'col-num', render: (_, l) => <Money value={l.taxable} /> },
                      { title: 'Tax %', width: 88, align: 'right', className: 'col-num', render: (_, l) => <Pct value={l.taxPct} /> },
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
