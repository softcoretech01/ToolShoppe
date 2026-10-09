import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Dropdown, Badge, Tooltip } from 'antd'
import {
  PanelLeftClose, PanelLeftOpen, ChevronRight, Bell, RotateCw,
  ChevronDown, LogOut, Settings, Mail,
} from 'lucide-react'
import { breadcrumbFor } from './nav.js'
import { useApp } from '../store/AppContext.jsx'
import { dashboardCounts } from '../store/selectors.js'
import { useConfirm, useToast } from '../components/ui/index.js'

/** Clean white topbar: toggle, breadcrumb, context note, alerts and user menu. */
export default function Topbar({ collapsed, onToggle, docLabel }) {
  const loc = useLocation()
  const nav = useNavigate()
  const { state, backendConnected, refreshFromBackend, logout } = useApp()
  const toast = useToast()

  const crumbs = breadcrumbFor(loc.pathname, docLabel)
  const c = dashboardCounts(state)
  const pending =
    c.awaitingRfq + c.toCompare + c.posToSend + c.inwardPending + c.toDispatch + c.toInvoiceSales + c.toInvoicePurchase

  const openCrs = state.customerRequests.filter((x) => x.stage !== 'Completed').length

  const alerts = [
    ['Purchase requests awaiting RFQ', c.awaitingRfq, '/purchase/request'],
    ['Comparisons ready to approve', c.toCompare, '/purchase/quotation-comparison'],
    ['Purchase orders to send', c.posToSend, '/purchase/purchase-order'],
    ['Inward waiting for stock posting', c.inwardPending, '/purchase/inward'],
    ['Orders ready to dispatch', c.toDispatch, '/sales/outward'],
    ['Sales invoices to raise', c.toInvoiceSales, '/sales/invoice'],
    ['Purchase invoices to raise', c.toInvoicePurchase, '/purchase/invoice'],
  ].filter(([, n]) => n > 0)

  const bellMenu = {
    items: alerts.length
      ? alerts.map(([label, n, to]) => ({
          key: to,
          label: (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 260 }}>
              <span style={{ flex: 1 }}>{label}</span>
              <span className="badge" style={{ background: 'var(--c-warning-light)', color: '#B45309', borderColor: '#FDE68A' }}>
                {n}
              </span>
            </div>
          ),
          onClick: () => nav(to),
        }))
      : [{ key: 'none', label: <span className="muted">Nothing needs attention right now.</span>, disabled: true }],
  }



  return (
    <header className="tb no-print">
      <Tooltip title={collapsed ? 'Expand menu' : 'Collapse menu'}>
        <button type="button" className="icon-btn" onClick={onToggle} aria-label="Toggle navigation">
          {collapsed ? <PanelLeftOpen size={18} strokeWidth={1.9} /> : <PanelLeftClose size={18} strokeWidth={1.9} />}
        </button>
      </Tooltip>

      <nav className="tb-crumbs" aria-label="Breadcrumb">
        {crumbs.map((cr, i) => (
          <React.Fragment key={`${cr.label}-${i}`}>
            {i > 0 && (
              <span className="crumb-sep">
                <ChevronRight size={14} strokeWidth={2} />
              </span>
            )}
            {cr.to && i < crumbs.length - 1 ? (
              <Link to={cr.to} className={i === 0 ? 'crumb-hide' : undefined}>
                {cr.label}
              </Link>
            ) : (
              <span className={i === crumbs.length - 1 ? 'crumb-cur' : 'crumb-hide'}>{cr.label}</span>
            )}
          </React.Fragment>
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      <div className="tb-note">
        {openCrs} open order{openCrs === 1 ? '' : 's'} · {pending} action{pending === 1 ? '' : 's'} pending
      </div>

      <Dropdown menu={bellMenu} trigger={['click']} placement="bottomRight">
        <span>
          <Tooltip title="Needs attention">
            <button type="button" className="icon-btn" aria-label="Alerts">
              <Badge count={alerts.length} size="small" offset={[2, -2]} color="#F97316">
                <Bell size={18} strokeWidth={1.9} />
              </Badge>
            </button>
          </Tooltip>
        </span>
      </Dropdown>

      <Tooltip title={backendConnected ? 'Backend Live & Synced (Click to Refresh)' : 'Connecting to API (Click to Reconnect)'}>
        <button
          type="button"
          className="icon-btn"
          onClick={async () => {
            toast.info(backendConnected ? 'Synchronizing with backend API...' : 'Connecting to backend API...')
            const ok = await refreshFromBackend()
            if (ok) {
              toast.success('FastAPI backend connected & synced!')
            } else {
              toast.warning('Backend unreachable, retrying automatically...')
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 12,
            padding: '4px 10px',
            width: 'auto',
            borderRadius: 16,
            background: backendConnected ? '#ECFDF5' : '#FEF2F2',
            color: backendConnected ? '#059669' : '#DC2626',
            border: `1px solid ${backendConnected ? '#A7F3D0' : '#FECACA'}`,
            fontWeight: 500,
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: backendConnected ? '#10B981' : '#EF4444',
            }}
          />
          <span>{backendConnected ? 'FastAPI Live' : 'Reconnecting...'}</span>
          <RotateCw size={12} strokeWidth={2} />
        </button>
      </Tooltip>

      <Dropdown
        menu={{
          items: [
            {
              key: 'role',
              label: <span className="muted" style={{ fontSize: 12 }}>Role: Administrator</span>,
              disabled: true,
            },
            { type: 'divider' },
            {
              key: 'logout',
              icon: <LogOut size={14} />,
              label: 'Sign Out',
              danger: true,
              onClick: () => logout(),
            },
          ],
        }}
        trigger={['click']}
        placement="bottomRight"
      >
        <div className="tb-user" style={{ cursor: 'pointer' }}>
          <div className="tb-avatar">AD</div>
          <div className="tb-umeta">
            <div className="tb-uname">Admin</div>
            <div className="tb-urole">Administrator</div>
          </div>
          <ChevronDown size={14} style={{ color: '#9CA3AF', marginLeft: 4 }} />
        </div>
      </Dropdown>
    </header>
  )
}
