import React, { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Segmented, Spin, Table, Tag } from 'antd'
import { Mail, Eye, Send, FileCheck2, FileText, Inbox, RefreshCw, PlusCircle } from 'lucide-react'
import { useStore } from '../store/AppContext.jsx'
import api from '../api/client.js'
import {
  DataTable, PageHeader, Btn, IconBtn, RowActions, ViewDrawer, DrawerSection, KV,
  fmtDateTime,
} from '../components/ui/index.js'
import { TONE } from '../theme/tokens.js'

const REF = {
  PR: { label: 'RFQ to supplier', tone: 'info', icon: Send },
  CQ: { label: 'Quotation to customer', tone: 'teal', icon: FileCheck2 },
  PO: { label: 'Purchase order', tone: 'primary', icon: FileText },
  RFQ: { label: 'RFQ to supplier', tone: 'info', icon: Send },
  'Customer Quotation': { label: 'Quotation to customer', tone: 'teal', icon: FileCheck2 },
  'Purchase Order': { label: 'Purchase order', tone: 'primary', icon: FileText },
}

function formatRecipients(val) {
  if (Array.isArray(val)) return val.filter(Boolean).join(', ')
  if (typeof val === 'string') return val
  return '—'
}

export default function EmailLog() {
  const s = useStore()
  const nav = useNavigate()
  const [open, setOpen] = useState(null)
  const [activeTab, setActiveTab] = useState('sent') // 'sent' | 'inbox'
  const [inboxEmails, setInboxEmails] = useState([])
  const [loadingInbox, setLoadingInbox] = useState(false)

  const fetchInbox = async () => {
    setLoadingInbox(true)
    try {
      const res = await api.get('/api/v1/email-logs/inbox?limit=25')
      const list = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : [])
      setInboxEmails(list)
    } catch (err) {
      console.warn('Failed to fetch Gmail inbox messages:', err)
    } finally {
      setLoadingInbox(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'inbox') {
      fetchInbox()
    }
  }, [activeTab])

  const rows = useMemo(() => {
    const list = s?.emailLog || []
    return list.map((e) => {
      let doc = '—'
      let routePath = null
      const type = e.refType || (e.document_type === 'Customer Quotation' ? 'CQ' : e.document_type === 'Purchase Order' ? 'PO' : 'PR')
      const refId = e.refId || e.document_id

      if (type === 'PR' || type === 'RFQ') {
        const pr = (s?.purchaseRequests || []).find((x) => x.id === refId || x.prNo === refId)
        doc = pr ? pr.prNo : (refId ? (String(refId).startsWith('PR-') ? refId : `PR-${String(refId).padStart(3, '0')}`) : '—')
        routePath = pr ? `/purchase/request/${pr.id}` : (refId ? `/purchase/request/${refId}` : null)
      } else if (type === 'CQ' || type === 'Customer Quotation') {
        const cq = (s?.customerQuotations || []).find((x) => x.id === refId || x.cqNo === refId)
        doc = cq ? cq.cqNo : (refId ? (String(refId).startsWith('CQ-') ? refId : `CQ-${String(refId).padStart(3, '0')}`) : '—')
        routePath = cq ? `/sales/quotation/${cq.id}` : (refId ? `/sales/quotation/${refId}` : null)
      } else if (type === 'PO' || type === 'Purchase Order') {
        const po = (s?.purchaseOrders || []).find((x) => x.id === refId || x.poNo === refId)
        doc = po ? po.poNo : (refId ? (String(refId).startsWith('PO-') ? refId : `PO-${String(refId).padStart(3, '0')}`) : '—')
        routePath = po ? `/purchase/purchase-order/${po.id}` : (refId ? `/purchase/purchase-order/${refId}` : null)
      }

      const from = e.from || e.sender || 'tdevendiran123@gmail.com'
      const recipients = formatRecipients(e.to || e.recipient)
      const sentAt = e.sentAt || e.sent_at || ''
      const status = e.status || 'Sent'
      const errorMessage = e.error_message || e.errorMessage || null

      return {
        ...e,
        refType: type,
        doc,
        routePath,
        from,
        recipients,
        sentAt,
        status,
        errorMessage,
      }
    })
  }, [s])

  const sentColumns = [
    { title: 'Sent at', dataIndex: 'sentAt', width: 170, sorter: true, render: fmtDateTime },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 110,
      render: (v, r) => {
        if (v === 'Sent') return <Tag color="success">Sent</Tag>
        if (v === 'Simulated') return <Tag color="blue">Simulated</Tag>
        return <Tag color="error" title={r.errorMessage || 'Failed'}>Failed</Tag>
      },
    },
    {
      title: 'From',
      dataIndex: 'from',
      width: 195,
      render: (v) => (
        <span style={{ fontSize: 12, color: '#0f766e', fontWeight: 600 }}>
          {v || 'tdevendiran123@gmail.com'}
        </span>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'refType',
      width: 190,
      render: (v) => {
        const r = REF[v] || { label: v || 'Email', tone: 'neutral', icon: Mail }
        const t = TONE[r.tone] || TONE.neutral
        const Icon = r.icon || Mail
        return (
          <span className="badge" style={{ background: t.bg, color: t.fg, borderColor: t.border }}>
            <Icon size={12} strokeWidth={2.2} />
            {r.label}
          </span>
        )
      },
    },
    {
      title: 'Document',
      dataIndex: 'doc',
      width: 120,
      render: (v, r) => (
        <a className="doc-no" onClick={() => r.routePath && nav(r.routePath)} style={{ cursor: r.routePath ? 'pointer' : 'default' }}>
          {v}
        </a>
      ),
    },
    { title: 'Recipient', dataIndex: 'recipients', width: 230, render: (v) => <span className="muted">{v}</span> },
    {
      title: 'Subject',
      dataIndex: 'subject',
      render: (v, r) => (
        <a onClick={() => setOpen(r)} style={{ color: 'var(--c-text)', cursor: 'pointer' }}>{v || '—'}</a>
      ),
    },
    {
      title: 'Actions',
      width: 78,
      fixed: 'right',
      render: (_, r) => (
        <RowActions>
          <IconBtn icon={Eye} label="Open message" onClick={() => setOpen(r)} />
        </RowActions>
      ),
    },
  ]

  const inboxColumns = [
    {
      title: 'Date',
      dataIndex: 'date',
      width: 190,
      render: (v) => <span className="num muted" style={{ fontSize: 12 }}>{v}</span>,
    },
    {
      title: 'From (Supplier)',
      dataIndex: 'sender',
      width: 250,
      render: (v) => <strong style={{ color: '#0f172a', fontSize: 12.5 }}>{v}</strong>,
    },
    {
      title: 'Subject & Preview',
      dataIndex: 'subject',
      render: (v, r) => (
        <div>
          <div style={{ fontWeight: 600, color: '#0f766e', cursor: 'pointer' }} onClick={() => setOpen({ ...r, isInbox: true })}>
            {v || '(No Subject)'}
          </div>
          <div style={{ fontSize: 12, color: '#64748b', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 450 }}>
            {r.preview || r.body}
          </div>
        </div>
      ),
    },
    {
      title: 'Actions',
      width: 160,
      fixed: 'right',
      render: (_, r) => (
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <IconBtn icon={Eye} label="View Reply" onClick={() => setOpen({ ...r, isInbox: true })} />
          <Btn
            size="small"
            variant="outline"
            icon={PlusCircle}
            onClick={() => nav('/purchase/vendor-quotation/new')}
          >
            Record Quote
          </Btn>
        </div>
      ),
    },
  ]

  const headerActions = (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <Segmented
        value={activeTab}
        onChange={setActiveTab}
        options={[
          { label: 'Sent Dispatches (Outbox)', value: 'sent', icon: <Send size={14} /> },
          { label: 'Live Gmail Inbox (Replies)', value: 'inbox', icon: <Inbox size={14} /> },
        ]}
      />
      {activeTab === 'inbox' && (
        <Btn variant="secondary" icon={RefreshCw} onClick={fetchInbox} disabled={loadingInbox}>
          Refresh
        </Btn>
      )}
    </div>
  )

  return (
    <div>
      <PageHeader
        title="Email Communication Hub"
        subtitle={
          activeTab === 'sent'
            ? 'Track real dispatches sent to suppliers and customers via tdevendiran123@gmail.com.'
            : 'Live incoming replies and quotations received in tdevendiran123@gmail.com inbox.'
        }
        actions={headerActions}
      />

      {activeTab === 'sent' ? (
        <>
          <Alert
            style={{ marginBottom: 14 }}
            type="success"
            showIcon
            message="Live Gmail SMTP Connected: Outgoing RFQs, Quotations, and POs are delivered live via tdevendiran123@gmail.com."
          />

          <DataTable
            columns={sentColumns}
            data={rows}
            scrollX={1180}
            searchKeys={['subject', 'recipients', 'doc', 'body', 'from']}
            searchPlaceholder="Search subject, recipient, document…"
            pageSize={12}
            filters={[
              {
                key: 'refType',
                placeholder: 'Type',
                width: 216,
                options: Object.entries(REF)
                  .filter(([k]) => ['PR', 'CQ', 'PO'].includes(k))
                  .map(([value, r]) => ({ value, label: r.label })),
              },
            ]}
            empty={{
              icon: Mail,
              title: 'Nothing sent yet',
              description: 'Send a quotation request, a customer quotation or a purchase order and it is recorded here.',
            }}
          />
        </>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span style={{ fontWeight: 600, color: '#0f172a' }}>Live Gmail Inbox (tdevendiran123@gmail.com)</span>
              <span style={{ fontSize: 12, color: '#64748b', marginLeft: 8 }}>· Fetched via secure IMAP</span>
            </div>
            {loadingInbox && <Spin size="small" />}
          </div>

          <Table
            size="small"
            pagination={{ pageSize: 10 }}
            rowKey={(r, i) => r.id || i}
            loading={loadingInbox}
            dataSource={inboxEmails}
            columns={inboxColumns}
            scroll={{ x: 800 }}
          />
        </div>
      )}

      {/* Message Details Drawer */}
      <ViewDrawer
        open={!!open}
        onClose={() => setOpen(null)}
        title={open?.isInbox ? 'Incoming Supplier Message' : ((REF[open?.refType] || {}).label || open?.refType || 'Email')}
        docNo={open?.doc || 'Gmail Inbox'}
        subtitle={open ? open.subject : ''}
        width={720}
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            {open?.isInbox && (
              <Btn
                variant="primary"
                icon={PlusCircle}
                onClick={() => {
                  setOpen(null)
                  nav('/purchase/vendor-quotation/new')
                }}
              >
                Record as Vendor Quotation
              </Btn>
            )}
            <Btn variant="secondary" onClick={() => setOpen(null)}>Close</Btn>
          </div>
        }
      >
        {open && (
          <>
            <DrawerSection title="Message details">
              <KV
                items={
                  open.isInbox
                    ? [
                        ['From (Supplier)', <strong style={{ color: '#0f172a' }}>{open.sender}</strong>],
                        ['Date', open.date],
                        ['Subject', open.subject || '(No Subject)'],
                      ]
                    : [
                        ['From', <span style={{ color: '#0f766e', fontWeight: 600 }}>{open.from || 'tdevendiran123@gmail.com'} &nbsp;(ToolShoppe Industrial Supply)</span>],
                        ['Sent at', fmtDateTime(open.sentAt)],
                        ['Status', (
                          <span>
                            <Tag color={open.status === 'Sent' ? 'success' : open.status === 'Simulated' ? 'blue' : 'error'}>
                              {open.status || 'Sent'}
                            </Tag>
                            {open.errorMessage && (
                              <div style={{ color: '#dc2626', fontSize: 12, marginTop: 4, fontFamily: 'monospace' }}>
                                {open.errorMessage}
                              </div>
                            )}
                          </span>
                        )],
                        ['To', open.recipients || formatRecipients(open.to || open.recipient)],
                        ['Subject', open.subject || '—'],
                        ['Document', open.routePath ? <a className="doc-no" onClick={() => nav(open.routePath)}>{open.doc}</a> : <span>{open.doc}</span>],
                      ]
                }
              />
            </DrawerSection>
            <DrawerSection title="Message Content">
              <pre
                style={{
                  background: 'var(--c-surface-alt)',
                  border: '1px solid var(--c-border)',
                  borderRadius: 'var(--r-card)',
                  padding: 16,
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit',
                  fontSize: 13,
                  margin: 0,
                  lineHeight: 1.6,
                }}
              >
                {open.body || 'No content'}
              </pre>
            </DrawerSection>
          </>
        )}
      </ViewDrawer>
    </div>
  )
}
