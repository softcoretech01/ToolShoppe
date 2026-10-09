import React, { useState } from 'react'
import { Input, InputNumber, Row, Col, Switch, Select } from 'antd'
import { Plus, Pencil, Eye, Wrench, Power, PowerOff } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { CATEGORIES, UNITS } from '../../store/seed.js'
import { available } from '../../logic/stock.js'
import {
  DataTable, PageHeader, StatusBadge, Btn, IconBtn, RowActions, FormModal,
  ViewDrawer, DrawerSection, Field, FormSection, KV, Money, Pct, Qty,
  useConfirm, useToast,
} from '../../components/ui/index.js'

const blank = {
  name: '', description: '', category: 'Cutting tools', brand: '', unit: 'Nos',
  hsn: '', taxPct: 18, lastPurchaseRate: 0, active: true,
}

export default function Items() {
  const { state, dispatch } = useApp()
  const confirm = useConfirm()
  const toast = useToast()
  const [draft, setDraft] = useState(null)
  const [view, setView] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const set = (patch) => setDraft((d) => ({ ...d, ...patch }))

  const save = async () => {
    if (!draft.name.trim()) return toast.warning('Please enter the item name.')
    if (!draft.category) return toast.warning('Please choose a category.')
    const isDup = (state.items || []).some(
      (i) => i.name && i.name.trim().toLowerCase() === draft.name.trim().toLowerCase() && String(i.id) !== String(draft.id)
    )
    if (isDup) return toast.warning(`An item named "${draft.name.trim()}" already exists.`)

    setSubmitting(true)
    try {
      await dispatch({
        type: 'MASTER_SAVE',
        collection: 'items',
        codeType: 'ITM',
        record: draft,
        throwOnError: true,
      })
      toast.success(draft.id ? 'Item updated successfully.' : 'Item created successfully.')
      setDraft(null)
    } catch (err) {
      if (!draft.id) {
        dispatch({ type: 'MASTER_DELETE', collection: 'items', id: draft.name })
      }
      toast.error(err?.message || 'Failed to save item. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const toggle = (r) =>
    confirm({
      title: r.active ? 'Deactivate item?' : 'Reactivate item?',
      description: r.active
        ? `${r.name} will no longer be selectable on new documents. Existing documents keep it.`
        : `${r.name} will be selectable on new documents again.`,
      okText: r.active ? 'Deactivate' : 'Reactivate',
      tone: r.active ? 'warning' : 'primary',
      onConfirm: () => {
        dispatch({ type: 'MASTER_TOGGLE', collection: 'items', id: r.id })
        toast.success(r.active ? 'Item deactivated.' : 'Item reactivated.')
      },
    })

  /** On-hand across every CR — items are only ever held against an order. */
  const onHand = (itemId) => {
    const crs = [...new Set(state.stockLedger.filter((r) => r.itemId === itemId).map((r) => r.crId))]
    return crs.reduce((a, crId) => a + available(state.stockLedger, itemId, crId), 0)
  }

  const columns = [
    { title: 'Code', dataIndex: 'code', width: 100, sorter: true, render: (v) => <span className="doc-no">{v}</span> },
    {
      title: 'Item',
      dataIndex: 'name',
      sorter: true,
      render: (v, r) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 550 }}>{v}</div>
          <div className="dim" style={{ fontSize: 11.5, overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.description}</div>
        </div>
      ),
    },
    { title: 'Category', dataIndex: 'category', width: 132, sorter: true },
    { title: 'UOM', dataIndex: 'unit', width: 76 },
    {
      title: 'Last purchase rate',
      dataIndex: 'lastPurchaseRate',
      width: 152,
      numeric: true,
      sorter: true,
      render: (v) => <Money value={v} />,
    },
    { title: 'Status', width: 106, render: (_, r) => <StatusBadge status={r.active ? 'Active' : 'Inactive'} /> },
    {
      title: 'Actions',
      width: 116,
      fixed: 'right',
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Eye} label="View" onClick={() => setView(r)} />
          <IconBtn icon={Pencil} label="Edit" onClick={() => setDraft({ ...r })} />
          <IconBtn
            icon={r.active ? PowerOff : Power}
            label={r.active ? 'Deactivate' : 'Reactivate'}
            danger={r.active}
            onClick={() => toggle(r)}
          />
        </RowActions>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Items"
        subtitle="The last purchase rate is written back automatically every time a goods receipt is saved."
        actions={
          <Btn variant="primary" icon={Plus} onClick={() => setDraft({ ...blank })}>
            New Item
          </Btn>
        }
      />

      <DataTable
        columns={columns}
        data={state.items}
        scrollX={800}
        searchKeys={['code', 'name', 'description', 'brand', 'hsn']}
        searchPlaceholder="Search code, name, brand…"
        pageSize={12}
        filters={[
          { key: 'category', placeholder: 'Category', width: 180, options: CATEGORIES.map((c) => ({ value: c, label: c })) },
          { key: 'unit', placeholder: 'UOM', width: 120, options: UNITS.map((c) => ({ value: c, label: c })) },
          {
            key: 'active',
            placeholder: 'Status',
            width: 146,
            options: [
              { value: 'y', label: 'Active' },
              { value: 'n', label: 'Inactive' },
            ],
            match: (r, v) => (v === 'y' ? r.active : !r.active),
          },
        ]}
        empty={{
          icon: Wrench,
          title: 'No items yet',
          description: 'Build the catalogue of tools you trade in before raising a customer request.',
          action: <Btn variant="primary" icon={Plus} onClick={() => setDraft({ ...blank })}>New Item</Btn>,
        }}
      />

      <FormModal
        open={!!draft}
        title={draft?.id ? `Edit item ${draft.code}` : 'New item'}
        subtitle="Fields marked with an asterisk are required."
        onCancel={() => !submitting && setDraft(null)}
        onOk={save}
        confirmLoading={submitting}
        okText={draft?.id ? 'Save changes' : 'Create item'}
        width={860}
      >
        {draft && (
          <>
            <FormSection title="Item information">
              <Row gutter={16}>
                <Col xs={24} md={14}>
                  <Field label="Item name" required>
                    <Input value={draft.name} onChange={(e) => set({ name: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={24} md={10}>
                  <Field label="Brand">
                    <Input value={draft.brand} onChange={(e) => set({ brand: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={24}>
                  <Field label="Description">
                    <Input value={draft.description} onChange={(e) => set({ description: e.target.value })} placeholder="Specification shown on quotations and orders" />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            <FormSection title="Classification">
              <Row gutter={16}>
                <Col xs={24} md={9}>
                  <Field label="Category" required>
                    <Select style={{ width: '100%' }} value={draft.category} onChange={(v) => set({ category: v })} options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Unit of measure" required>
                    <Select style={{ width: '100%' }} value={draft.unit} onChange={(v) => set({ unit: v })} options={UNITS.map((c) => ({ value: c, label: c }))} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="HSN code">
                    <Input value={draft.hsn} onChange={(e) => set({ hsn: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={12} md={5}>
                  <Field label="Tax %">
                    <InputNumber min={0} max={100} style={{ width: '100%' }} value={draft.taxPct} onChange={(v) => set({ taxPct: v })} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            <FormSection title="Pricing">
              <Row gutter={16}>
                <Col xs={24} md={10}>
                  <Field label="Last purchase rate" help="Updated automatically from every goods receipt.">
                    <InputNumber min={0} step={0.01} style={{ width: '100%' }} value={draft.lastPurchaseRate} onChange={(v) => set({ lastPurchaseRate: v })} prefix="₹" />
                  </Field>
                </Col>
                <Col xs={24} md={6}>
                  <Field label="Active">
                    <div style={{ paddingTop: 6 }}>
                      <Switch checked={draft.active} onChange={(v) => set({ active: v })} />
                      <span className="muted" style={{ marginLeft: 10, fontSize: 13 }}>
                        {draft.active ? 'Available' : 'Hidden from new documents'}
                      </span>
                    </div>
                  </Field>
                </Col>
              </Row>
            </FormSection>
          </>
        )}
      </FormModal>

      <ViewDrawer
        open={!!view}
        onClose={() => setView(null)}
        title="Item"
        docNo={view?.name}
        status={view ? (view.active ? 'Active' : 'Inactive') : undefined}
        subtitle={view ? `${view.code} · ${view.category}` : undefined}
        actions={
          view && (
            <>
              <Btn variant="secondary" onClick={() => setView(null)}>Close</Btn>
              <Btn variant="primary" icon={Pencil} onClick={() => { setDraft({ ...view }); setView(null) }}>
                Edit item
              </Btn>
            </>
          )
        }
      >
        {view && (
          <>
            <DrawerSection title="Item information">
              <KV
                items={[
                  ['Code', <span className="doc-no">{view.code}</span>],
                  ['Description', view.description],
                  ['Brand', view.brand],
                  ['Category', view.category],
                ]}
              />
            </DrawerSection>
            <DrawerSection title="Commercial">
              <KV
                items={[
                  ['Unit of measure', view.unit],
                  ['HSN code', view.hsn],
                  ['Tax rate', <Pct value={view.taxPct} />],
                  ['Last purchase rate', <Money value={view.lastPurchaseRate} strong />],
                ]}
              />
            </DrawerSection>
            <DrawerSection title="Stock position">
              <KV
                items={[
                  ['On hand (all orders)', <Qty value={onHand(view.id)} unit={view.unit} strong />],
                  ['Inward movements', state.stockLedger.filter((r) => r.itemId === view.id && r.type === 'IN').length],
                  ['Outward movements', state.stockLedger.filter((r) => r.itemId === view.id && r.type === 'OUT').length],
                ]}
              />
              <div className="fld-help" style={{ marginTop: 8 }}>
                Stock is held per item and per customer request — it exists only between the supplier
                delivery and the customer shipment of the same order.
              </div>
            </DrawerSection>
          </>
        )}
      </ViewDrawer>
    </div>
  )
}
