import React, { useState } from 'react'
import { Input, InputNumber, Row, Col, Switch, Select, Tag } from 'antd'
import { Plus, Pencil, Eye, Store, Power, PowerOff } from 'lucide-react'
import { useApp } from '../../store/AppContext.jsx'
import { CATEGORIES } from '../../store/seed.js'
import {
  DataTable, PageHeader, StatusBadge, Btn, IconBtn, RowActions, FormModal,
  ViewDrawer, DrawerSection, Field, FormSection, KV, useConfirm, useToast,
} from '../../components/ui/index.js'

const blank = {
  name: '', contactPerson: '', phone: '', email: '', gstin: '',
  address: '', categories: [], leadTimeDays: 7, active: true,
}

export default function Suppliers() {
  const { state, dispatch } = useApp()
  const confirm = useConfirm()
  const toast = useToast()
  const [draft, setDraft] = useState(null)
  const [view, setView] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const set = (patch) => setDraft((d) => ({ ...d, ...patch }))

  const save = async () => {
    if (!draft.name.trim()) return toast.warning('Please enter the supplier name.')
    const phoneDigits = (draft.phone || '').replace(/\D/g, '')
    if (!phoneDigits) return toast.warning('Please enter the 10-digit mobile number.')
    if (phoneDigits.length !== 10) return toast.warning('Mobile number must be exactly 10 digits.')
    if (!/^\S+@\S+\.\S+$/.test(draft.email || '')) return toast.warning('Please enter a valid email address.')
    const isDup = (state.suppliers || []).some(
      (s) => s.name && s.name.trim().toLowerCase() === draft.name.trim().toLowerCase() && String(s.id) !== String(draft.id)
    )
    if (isDup) return toast.warning(`A supplier named "${draft.name.trim()}" already exists.`)
    const isDupEmail = (state.suppliers || []).some(
      (s) => s.email && s.email.trim().toLowerCase() === draft.email.trim().toLowerCase() && String(s.id) !== String(draft.id)
    )
    if (isDupEmail) return toast.warning(`A supplier with email "${draft.email.trim()}" already exists.`)

    const updatedDraft = { ...draft, phone: phoneDigits }
    setSubmitting(true)
    try {
      await dispatch({
        type: 'MASTER_SAVE',
        collection: 'suppliers',
        codeType: 'SUP',
        record: updatedDraft,
        throwOnError: true,
      })
      toast.success(draft.id ? 'Supplier updated successfully.' : 'Supplier created successfully.')
      setDraft(null)
    } catch (err) {
      if (!draft.id) {
        dispatch({ type: 'MASTER_DELETE', collection: 'suppliers', id: updatedDraft.name })
      }
      toast.error(err?.message || 'Failed to save supplier. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const toggle = (r) =>
    confirm({
      title: r.active ? 'Deactivate supplier?' : 'Reactivate supplier?',
      description: r.active
        ? `${r.name} will no longer receive RFQs or appear on new purchase orders.`
        : `${r.name} will appear in RFQ and quotation screens again.`,
      okText: r.active ? 'Deactivate' : 'Reactivate',
      tone: r.active ? 'warning' : 'primary',
      onConfirm: () => {
        dispatch({ type: 'MASTER_TOGGLE', collection: 'suppliers', id: r.id })
        toast.success(r.active ? 'Supplier deactivated.' : 'Supplier reactivated.')
      },
    })

  const columns = [
    {
      title: 'Supplier',
      dataIndex: 'name',
      sorter: true,
      render: (v, r) => (
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 550 }}>{v}</div>
          <div className="dim" style={{ fontSize: 11.5 }}>{r.leadTimeDays} days lead time</div>
        </div>
      ),
    },
    { title: 'Contact', dataIndex: 'contactPerson', width: 150 },
    { title: 'Phone', dataIndex: 'phone', width: 148, render: (v) => <span className="num">{v}</span> },
    { title: 'Email', dataIndex: 'email', width: 226, render: (v) => <span className="muted">{v}</span> },
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
        title="Suppliers"
        subtitle="The email address recorded here is the one every RFQ and purchase order popup sends to."
        actions={
          <Btn variant="primary" icon={Plus} onClick={() => setDraft({ ...blank })}>
            New Supplier
          </Btn>
        }
      />

      <DataTable
        columns={columns}
        data={state.suppliers}
        scrollX={1060}
        searchKeys={['code', 'name', 'contactPerson', 'email', 'gstin', 'phone']}
        searchPlaceholder="Search code, name, email…"
        filters={[
          {
            key: 'category',
            placeholder: 'Category supplied',
            width: 196,
            options: CATEGORIES.map((c) => ({ value: c, label: c })),
            match: (r, v) => (r.categories || []).includes(v),
          },
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
          icon: Store,
          title: 'No suppliers yet',
          description: 'Add the vendors you buy from so requests for quotation can be sent out.',
          action: <Btn variant="primary" icon={Plus} onClick={() => setDraft({ ...blank })}>New Supplier</Btn>,
        }}
      />

      <FormModal
        open={!!draft}
        title={draft?.id ? `Edit supplier ${draft.code}` : 'New supplier'}
        subtitle="Fields marked with an asterisk are required."
        onCancel={() => !submitting && setDraft(null)}
        onOk={save}
        confirmLoading={submitting}
        okText={draft?.id ? 'Save changes' : 'Create supplier'}
        width={860}
      >
        {draft && (
          <>
            <FormSection title="Supplier information">
              <Row gutter={16}>
                <Col xs={24} md={14}>
                  <Field label="Supplier name" required>
                    <Input value={draft.name} onChange={(e) => set({ name: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={24} md={10}>
                  <Field label="Contact person">
                    <Input value={draft.contactPerson} onChange={(e) => set({ contactPerson: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={24} md={8}>
                  <Field label="Mobile number" required help="Must be exactly 10 digits">
                    <Input
                      value={draft.phone}
                      maxLength={10}
                      placeholder="10-digit mobile number"
                      onChange={(e) => set({ phone: e.target.value.replace(/\D/g, '').slice(0, 10) })}
                    />
                  </Field>
                </Col>
                <Col xs={24} md={9}>
                  <Field label="Email" required help="RFQs and purchase orders are sent to this address.">
                    <Input value={draft.email} onChange={(e) => set({ email: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={24} md={7}>
                  <Field label="GSTIN">
                    <Input value={draft.gstin} onChange={(e) => set({ gstin: e.target.value })} />
                  </Field>
                </Col>
                <Col xs={24}>
                  <Field label="Address">
                    <Input.TextArea rows={2} value={draft.address} onChange={(e) => set({ address: e.target.value })} />
                  </Field>
                </Col>
              </Row>
            </FormSection>

            <FormSection title="Supply profile">
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Field label="Categories supplied" help="Shown on the RFQ popup so buyers pick the right vendors.">
                    <Select
                      mode="multiple"
                      style={{ width: '100%' }}
                      value={draft.categories}
                      onChange={(v) => set({ categories: v })}
                      options={CATEGORIES.map((c) => ({ value: c, label: c }))}
                    />
                  </Field>
                </Col>
                <Col xs={24} md={6}>
                  <Field label="Lead time (days)">
                    <InputNumber min={0} max={365} style={{ width: '100%' }} value={draft.leadTimeDays} onChange={(v) => set({ leadTimeDays: v })} />
                  </Field>
                </Col>
                <Col xs={24} md={6}>
                  <Field label="Active">
                    <div style={{ paddingTop: 6 }}>
                      <Switch checked={draft.active} onChange={(v) => set({ active: v })} />
                      <span className="muted" style={{ marginLeft: 10, fontSize: 13 }}>
                        {draft.active ? 'Available' : 'Hidden from new RFQs'}
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
        title="Supplier"
        docNo={view?.name}
        status={view ? (view.active ? 'Active' : 'Inactive') : undefined}
        subtitle={view?.code}
        actions={
          view && (
            <>
              <Btn variant="secondary" onClick={() => setView(null)}>Close</Btn>
              <Btn variant="primary" icon={Pencil} onClick={() => { setDraft({ ...view }); setView(null) }}>
                Edit supplier
              </Btn>
            </>
          )
        }
      >
        {view && (
          <>
            <DrawerSection title="Contact">
              <KV
                items={[
                  ['Code', <span className="doc-no">{view.code}</span>],
                  ['Contact person', view.contactPerson],
                  ['Phone', view.phone],
                  ['Email', view.email],
                  ['GSTIN', view.gstin],
                  ['Address', view.address],
                ]}
              />
            </DrawerSection>
            <DrawerSection title="Supply profile">
              <KV
                items={[
                  [
                    'Categories',
                    <span style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {(view.categories || []).map((x) => <Tag key={x} style={{ marginInlineEnd: 0 }}>{x}</Tag>)}
                    </span>,
                  ],
                  ['Lead time', `${view.leadTimeDays} days`],
                ]}
              />
            </DrawerSection>
            <DrawerSection title="Activity">
              <KV
                items={[
                  ['Quotations submitted', state.vendorQuotations.filter((x) => x.supplierId === view.id).length],
                  ['Quotations won', state.vendorQuotations.filter((x) => x.supplierId === view.id && x.status === 'Selected').length],
                  ['Purchase orders', state.purchaseOrders.filter((x) => x.supplierId === view.id).length],
                  ['Goods receipts', state.grns.filter((x) => x.supplierId === view.id).length],
                ]}
              />
            </DrawerSection>
          </>
        )}
      </ViewDrawer>
    </div>
  )
}
