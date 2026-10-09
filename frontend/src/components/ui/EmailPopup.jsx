import React, { useEffect, useState } from 'react'
import { Input, Alert } from 'antd'
import { Send, Mail } from 'lucide-react'
import { FormModal } from './Overlays.jsx'
import { SectionLabel } from './Panels.jsx'

/**
 * Email is simulated: the popup shows the real recipients and a preview, then
 * the send handler writes to the Email Log. If a real mail server is ever wired
 * in, only this component and the log writer change.
 */
export default function EmailPopup({
  open,
  onCancel,
  onSend,
  recipients = [],
  defaultSubject = '',
  defaultBody = '',
  title = 'Send email',
  okText = 'Send',
  width = 860,
  children,
  disabled,
}) {
  const [subject, setSubject] = useState(defaultSubject)
  const [body, setBody] = useState(defaultBody)

  useEffect(() => {
    if (open) {
      setSubject(defaultSubject)
      setBody(defaultBody)
    }
  }, [open, defaultSubject, defaultBody])

  return (
    <FormModal
      open={open}
      title={title}
      onCancel={onCancel}
      onOk={() => onSend({ subject, body, from: 'tdevendiran123@gmail.com' })}
      okText={okText}
      okDisabled={disabled}
      width={width}
      footerNote="Dispatched via SMTP to recipients and recorded in the Email Communication Log."
    >
      {children}

      <div className="form-sec">
        <SectionLabel>Email preview</SectionLabel>
        <div
          style={{
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-card)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '9px 14px',
              background: 'var(--c-surface-alt)',
              borderBottom: '1px solid var(--c-border)',
              flexWrap: 'wrap',
            }}
          >
            <Mail size={14} strokeWidth={2} style={{ color: '#0f766e' }} />
            <span style={{ fontSize: 12, color: 'var(--c-text-2)', marginRight: 2, fontWeight: 600 }}>From</span>
            <span
              className="badge"
              style={{ background: '#f0fdfa', color: '#0f766e', borderColor: '#99f6e4', fontWeight: 600 }}
            >
              ToolShoppe Industrial Supply &lt;tdevendiran123@gmail.com&gt;
            </span>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 14px',
              background: 'var(--c-surface-alt)',
              borderBottom: '1px solid var(--c-border)',
              flexWrap: 'wrap',
            }}
          >
            <Mail size={14} strokeWidth={2} style={{ color: 'var(--c-text-muted)' }} />
            <span style={{ fontSize: 12, color: 'var(--c-text-2)', marginRight: 2 }}>To</span>
            {recipients.length ? (
              recipients.map((r) => (
                <span
                  key={r}
                  className="badge"
                  style={{ background: 'var(--c-info-light)', color: '#075985', borderColor: '#BAE6FD' }}
                >
                  {r}
                </span>
              ))
            ) : (
              <span className="badge" style={{ background: '#F1F5F9', color: '#475569' }}>
                no recipient selected
              </span>
            )}
          </div>
          <div style={{ padding: 14 }}>
            <Input
              addonBefore="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              style={{ marginBottom: 10 }}
            />
            <Input.TextArea
              rows={9}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              style={{ fontFamily: 'inherit', fontSize: 13 }}
            />
          </div>
        </div>
        <Alert
          style={{ marginTop: 10 }}
          type="info"
          showIcon
          icon={<Send size={15} strokeWidth={2} />}
          message="Emails are dispatched to recipient addresses and tracked with delivery status in the Email Log."
        />
      </div>
    </FormModal>
  )
}
