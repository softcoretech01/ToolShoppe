import React, { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ChevronRight, Wrench, LogOut, RotateCw, Mail } from 'lucide-react'
import { Tooltip } from 'antd'
import { NAV, matchNav } from './nav.js'
import { useApp } from '../store/AppContext.jsx'
import { useConfirm, useToast } from '../components/ui/index.js'

/** Deep-navy premium sidebar. Sections expand/collapse; active item is obvious. */
export default function Sidebar({ collapsed, counts, onNavigate }) {
  const nav = useNavigate()
  const loc = useLocation()
  const { logout, resetDemo, backendConnected } = useApp()
  const confirm = useConfirm()
  const toast = useToast()

  const active = matchNav(loc.pathname)
  const activeKey = active ? active.key : null
  const parentKey = active && active.parent ? active.parent.key : null

  const [open, setOpen] = useState(() => (parentKey ? [parentKey] : []))

  // Following a link from another module opens that module's section.
  useEffect(() => {
    if (parentKey) setOpen((o) => (o.includes(parentKey) ? o : [...o, parentKey]))
  }, [parentKey])

  const go = (key) => {
    nav(key)
    if (onNavigate) onNavigate()
  }

  const badgeOf = (item) => {
    const n = item.badge ? counts[item.badge] : 0
    return n > 0 ? <span className="sb-pill">{n > 99 ? '99+' : n}</span> : null
  }

  const leaf = (item, isSub) => {
    const Icon = item.icon
    const isActive = activeKey === item.key
    const btn = (
      <button
        key={item.key}
        type="button"
        className={`sb-item${isActive ? ' is-active' : ''}`}
        onClick={() => go(item.key)}
      >
        <span className="sb-ic">
          <Icon size={18} strokeWidth={isActive ? 2.2 : 1.9} />
        </span>
        <span className="sb-lb">{item.label}</span>
        {badgeOf(item)}
      </button>
    )
    return collapsed ? (
      <Tooltip key={item.key} title={item.label} placement="right">
        {btn}
      </Tooltip>
    ) : (
      btn
    )
  }

  return (
    <div className={`sb${collapsed ? ' sb-collapsed' : ''}`}>
      <div className="sb-brand">
        <div className="sb-mark">
          <Wrench size={19} strokeWidth={2.2} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="sb-name">Toolsphoppe</div>
          <div className="sb-tag">Sales · Purchase · Inventory</div>
        </div>
      </div>

      <nav className="sb-scroll">
        {NAV.map((item) => {
          if (!item.children) return leaf(item)

          const isOpen = open.includes(item.key) || collapsed
          const hasActive = parentKey === item.key
          const Icon = item.icon
          const groupCount = item.children.reduce((a, c) => a + (c.badge ? counts[c.badge] || 0 : 0), 0)

          return (
            <div className="sb-group" key={item.key}>
              {!collapsed && (
                <button
                  type="button"
                  className={`sb-item${isOpen ? ' is-open' : ''}${hasActive ? ' is-parent-active' : ''}`}
                  onClick={() =>
                    setOpen((o) => (o.includes(item.key) ? o.filter((k) => k !== item.key) : [...o, item.key]))
                  }
                >
                  <span className="sb-ic">
                    <Icon size={18} strokeWidth={1.9} />
                  </span>
                  <span className="sb-lb">
                    {item.index ? `${item.index}. ` : ''}
                    {item.label}
                  </span>
                  {!isOpen && groupCount > 0 && <span className="sb-pill">{groupCount}</span>}
                  <ChevronRight size={15} strokeWidth={2.2} className="sb-chev" />
                </button>
              )}
              {collapsed && <div style={{ height: 8 }} />}
              {isOpen && <div className="sb-sub">{item.children.map((c) => leaf(c, true))}</div>}
            </div>
          )
        })}
      </nav>

      <div className="sb-foot">
        {!collapsed && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 12 }}>
            <button
              type="button"
              className="sb-item"
              onClick={() =>
                confirm({
                  title: 'Reset Demo Data?',
                  description: 'This will restore all demo documents and master records to their initial clean state.',
                  okText: 'Reset',
                  tone: 'warning',
                  onConfirm: () => {
                    resetDemo()
                    toast.success('Demo data restored successfully.')
                  },
                })
              }
            >
              <span className="sb-ic"><RotateCw size={15} strokeWidth={2} /></span>
              <span className="sb-lb">Reset Demo</span>
            </button>
            <button type="button" className="sb-item" onClick={() => logout()}>
              <span className="sb-ic"><LogOut size={15} strokeWidth={2} /></span>
              <span className="sb-lb">Sign out</span>
            </button>
          </div>
        )}
        {!collapsed && (
          <div className="dim" style={{ fontSize: 11, padding: '0 16px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: backendConnected ? '#10B981' : '#9CA3AF',
                display: 'inline-block',
              }}
            />
            <span>{backendConnected ? 'ToolShoppe ERP · Live' : 'ToolShoppe ERP'}</span>
          </div>
        )}
      </div>
    </div>
  )
}
