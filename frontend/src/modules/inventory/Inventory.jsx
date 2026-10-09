import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tabs, Select, DatePicker, Table } from 'antd'
import dayjs from 'dayjs'
import {
  Download, X, Boxes, ArrowDownToLine, ArrowUpFromLine, TrendingUp, Package, Layers,
} from 'lucide-react'
import { useStore } from '../../store/AppContext.jsx'
import { customerName, supplierName, itemName, itemCode, getCR } from '../../store/selectors.js'
import { stockSummary, crMargin } from '../../logic/stock.js'
import { round2, sum } from '../../logic/pricing.js'
import {
  PageHeader, Card, StatusBadge, RefChip, Btn, KpiCard, Money, Qty, Pct,
  EmptyState, fmtDate, nf,
} from '../../components/ui/index.js'

const { RangePicker } = DatePicker

export default function Inventory() {
  const s = useStore()
  const nav = useNavigate()
  const [tab, setTab] = useState('ledger')
  const [f, setF] = useState({ crId: null, itemId: null, customerId: null, supplierId: null, range: null })

  const setF1 = (k, v) => setF((p) => ({ ...p, [k]: v }))
  const clear = () => setF({ crId: null, itemId: null, customerId: null, supplierId: null, range: null })
  const dirty = Object.values(f).some((v) => v !== null)

  /* -------------------- one filtered ledger drives every tab ------------------- */
  const ledger = useMemo(
    () =>
      s.stockLedger.filter((r) => {
        if (f.crId && r.crId !== f.crId) return false
        if (f.itemId && r.itemId !== f.itemId) return false
        if (f.customerId && !(r.type === 'OUT' && r.partyId === f.customerId)) return false
        if (f.supplierId && !(r.type === 'IN' && r.partyId === f.supplierId)) return false
        if (f.range && f.range[0] && f.range[1]) {
          const d = dayjs(r.date)
          if (d.isBefore(f.range[0], 'day') || d.isAfter(f.range[1], 'day')) return false
        }
        return true
      }),
    [s.stockLedger, f]
  )

  const inRows = ledger.filter((r) => r.type === 'IN')
  const outRows = ledger.filter((r) => r.type === 'OUT')
  const inValue = round2(sum(inRows, (r) => r.value))
  const outValue = round2(sum(outRows, (r) => r.value))

  const stock = useMemo(() => stockSummary(ledger, s.items), [ledger, s.items])
  const onHandItems = stock.filter((r) => r.onHand > 0)
  const stockValue = round2(sum(stock, (r) => r.stockValue))
  const totalQty = round2(sum(stock, (r) => r.onHand))

  /* --------------------------- running-balance ledger ------------------------- */
  const ledgerRows = useMemo(() => {
    const sorted = [...ledger].sort((a, b) => String(a.date).localeCompare(String(b.date)) || String(a.id).localeCompare(String(b.id)))
    const bal = {}
    return sorted.map((r) => {
      const key = `${r.itemId}|${r.crId}`
      bal[key] = round2((bal[key] || 0) + (r.type === 'IN' ? r.qty : -r.qty))
      const doc =
        r.type === 'IN'
          ? s.inwards.find((i) => i.id === r.refId)
          : s.outwards.find((o) => o.id === r.refId)
      const cr = getCR(s, r.crId)
      return {
        key: r.id,
        date: r.date,
        ref: doc ? (r.type === 'IN' ? doc.inwNo : doc.outNo) : '—',
        refId: doc ? doc.id : null,
        type: r.type,
        crNo: cr ? cr.crNo : '—',
        crId: r.crId,
        party: r.type === 'IN' ? supplierName(s, r.partyId) : customerName(s, r.partyId),
        item: itemName(s, r.itemId),
        itemCode: itemCode(s, r.itemId),
        qtyIn: r.type === 'IN' ? r.qty : null,
        qtyOut: r.type === 'OUT' ? r.qty : null,
        rate: r.rate,
        value: r.value,
        balance: bal[key],
      }
    })
  }, [ledger, s])

  /* -------------------------------- per-CR margin ----------------------------- */
  const perCr = s.customerRequests
    .filter((cr) => (f.crId ? cr.id === f.crId : true))
    .filter((cr) => (f.customerId ? cr.customerId === f.customerId : true))
    .map((cr) => {
      const m = crMargin(s.stockLedger, cr.id)
      const po = s.purchaseOrders.find((p) => p.crId === cr.id)
      return {
        key: cr.id,
        crId: cr.id,
        crNo: cr.crNo,
        customer: customerName(s, cr.customerId),
        supplier: po ? supplierName(s, po.supplierId) : '—',
        ...m,
        stage: cr.stage,
      }
    })

  /* ------------------------------------ CSV ----------------------------------- */
  const exportCsv = () => {
    const sets = {
      ledger: [
        ['Date', 'Reference', 'Type', 'Party', 'Request', 'Item', 'Qty In', 'Qty Out', 'Rate', 'Value', 'Balance'],
        ledgerRows.map((r) => [r.date, r.ref, r.type, r.party, r.crNo, r.item, r.qtyIn ?? '', r.qtyOut ?? '', r.rate, r.value, r.balance]),
      ],
      stock: [
        ['Item code', 'Item', 'UOM', 'Qty in', 'Qty out', 'On hand', 'Avg cost', 'Stock value'],
        stock.map((r) => [r.itemCode, r.itemName, r.unit, r.qtyIn, r.qtyOut, r.onHand, r.avgCost, r.stockValue]),
      ],
      margin: [
        ['Request', 'Customer', 'Supplier', 'Purchase value', 'Sales value', 'Margin', 'Margin %', 'Status'],
        perCr.map((r) => [r.crNo, r.customer, r.supplier, r.purchaseValue, r.salesValue, r.margin, r.marginPct, r.stage]),
      ],
    }
    const [head, body] = sets[tab] || sets.ledger
    const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
    const csv = [head, ...body].map((row) => row.map(esc).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `inventory-${tab}-${dayjs().format('YYYYMMDD-HHmm')}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const crLink = (v, r) => <RefChip onClick={() => r.crId && nav(`/sales/customer-request/${r.crId}`)}>{v}</RefChip>

  const TypeTag = ({ type }) => (
    <span
      className="badge"
      style={
        type === 'IN'
          ? { background: 'var(--c-info-light)', color: '#075985', borderColor: '#BAE6FD' }
          : { background: 'var(--c-warning-light)', color: '#B45309', borderColor: '#FDE68A' }
      }
    >
      {type === 'IN' ? <ArrowDownToLine size={11} strokeWidth={2.4} /> : <ArrowUpFromLine size={11} strokeWidth={2.4} />}
      {type === 'IN' ? 'Inward' : 'Outward'}
    </span>
  )

  const tabs = [
    {
      key: 'ledger',
      label: `Stock ledger (${ledgerRows.length})`,
      children: ledgerRows.length ? (
        <Table
          size="small"
          rowKey="key"
          dataSource={ledgerRows}
          pagination={ledgerRows.length > 15 ? { pageSize: 15, size: 'small', showTotal: (t, r) => `${r[0]}–${r[1]} of ${t}` } : false}
          scroll={{ x: 1620 }}
          columns={[
            { title: 'Date', dataIndex: 'date', width: 122, render: fmtDate, sorter: (a, b) => String(a.date).localeCompare(String(b.date)) },
            {
              title: 'Reference',
              dataIndex: 'ref',
              width: 118,
              render: (v, r) => (
                <a className="doc-no" onClick={() => (r.type === 'OUT' && r.refId ? nav(`/sales/outward/${r.refId}`) : nav('/purchase/inward'))}>
                  {v}
                </a>
              ),
            },
            { title: 'Transaction', dataIndex: 'type', width: 128, render: (v) => <TypeTag type={v} /> },
            { title: 'Customer / Supplier', dataIndex: 'party', width: 230 },
            { title: 'Request', dataIndex: 'crNo', width: 118, render: crLink },
            {
              title: 'Item',
              dataIndex: 'item',
              width: 260,
              render: (v, r) => (
                <div style={{ minWidth: 0 }}>
                  <div>{v}</div>
                  <div className="dim" style={{ fontSize: 11.5 }}>{r.itemCode}</div>
                </div>
              ),
            },
            {
              title: 'Qty In',
              dataIndex: 'qtyIn',
              width: 100,
              align: 'right',
              className: 'col-num',
              render: (v) => (v == null ? <span className="dim">—</span> : <span style={{ color: 'var(--c-info)', fontWeight: 600 }}><Qty value={v} /></span>),
            },
            {
              title: 'Qty Out',
              dataIndex: 'qtyOut',
              width: 104,
              align: 'right',
              className: 'col-num',
              render: (v) => (v == null ? <span className="dim">—</span> : <span style={{ color: 'var(--c-warning)', fontWeight: 600 }}><Qty value={v} /></span>),
            },
            { title: 'Rate', dataIndex: 'rate', width: 118, align: 'right', className: 'col-num', render: (v) => <Money value={v} /> },
            { title: 'Value', dataIndex: 'value', width: 142, align: 'right', className: 'col-num', render: (v) => <Money value={v} /> },
            {
              title: 'Balance',
              dataIndex: 'balance',
              width: 112,
              align: 'right',
              className: 'col-num',
              render: (v) => <Qty value={v} strong />,
            },
          ]}
        />
      ) : (
        <EmptyState
          icon={Boxes}
          title="The stock ledger is empty"
          description="Add an inward to inventory and every movement will appear here with its running balance."
          action={<Btn variant="primary" onClick={() => nav('/purchase/inward')}>Go to Inward</Btn>}
        />
      ),
    },
    {
      key: 'stock',
      label: `Stock summary (${stock.length})`,
      children: stock.length ? (
        <Table
          size="small"
          rowKey="key"
          dataSource={stock}
          pagination={stock.length > 15 ? { pageSize: 15, size: 'small' } : false}
          scroll={{ x: 940 }}
          columns={[
            { title: 'Code', dataIndex: 'itemCode', width: 112, render: (v) => <span className="doc-no">{v}</span> },
            { title: 'Item', dataIndex: 'itemName', render: (v) => <span style={{ fontWeight: 550 }}>{v}</span> },
            { title: 'UOM', dataIndex: 'unit', width: 82 },
            { title: 'Qty in', dataIndex: 'qtyIn', width: 106, align: 'right', className: 'col-num', render: (v) => <Qty value={v} /> },
            { title: 'Qty out', dataIndex: 'qtyOut', width: 108, align: 'right', className: 'col-num', render: (v) => <Qty value={v} /> },
            {
              title: 'On hand',
              dataIndex: 'onHand',
              width: 112,
              align: 'right',
              className: 'col-num',
              sorter: (a, b) => a.onHand - b.onHand,
              render: (v) => (
                <span style={{ color: v > 0 ? 'var(--c-warning)' : 'var(--c-text-muted)', fontWeight: 650 }}>
                  <Qty value={v} />
                </span>
              ),
            },
            { title: 'Avg cost', dataIndex: 'avgCost', width: 124, align: 'right', className: 'col-num', render: (v) => <Money value={v} /> },
            { title: 'Stock value', dataIndex: 'stockValue', width: 146, align: 'right', className: 'col-num', render: (v) => <Money value={v} strong /> },
          ]}
        />
      ) : (
        <EmptyState icon={Package} title="No stock records" description="Nothing has moved through inventory yet." />
      ),
    },
    {
      key: 'margin',
      label: 'Per-request margin',
      children: perCr.length ? (
        <Table
          size="small"
          rowKey="key"
          dataSource={perCr}
          pagination={perCr.length > 15 ? { pageSize: 15, size: 'small' } : false}
          scroll={{ x: 1120 }}
          columns={[
            { title: 'Request', dataIndex: 'crNo', width: 118, render: crLink },
            { title: 'Customer', dataIndex: 'customer', render: (v) => <span style={{ fontWeight: 550 }}>{v}</span> },
            { title: 'Supplier', dataIndex: 'supplier' },
            { title: 'Purchase value', dataIndex: 'purchaseValue', width: 150, align: 'right', className: 'col-num', render: (v) => <Money value={v} /> },
            { title: 'Sales value', dataIndex: 'salesValue', width: 144, align: 'right', className: 'col-num', render: (v) => <Money value={v} /> },
            {
              title: 'Margin',
              dataIndex: 'margin',
              width: 140,
              align: 'right',
              className: 'col-num',
              sorter: (a, b) => a.margin - b.margin,
              render: (v) => <Money value={v} tone={v > 0 ? 'pos' : v < 0 ? 'neg' : undefined} strong />,
            },
            { title: 'Margin %', dataIndex: 'marginPct', width: 116, align: 'right', className: 'col-num', render: (v) => <Pct value={v} tone="auto" /> },
            { title: 'Status', dataIndex: 'stage', width: 140, render: (v) => <StatusBadge status={v} /> },
          ]}
        />
      ) : (
        <EmptyState icon={TrendingUp} title="No orders to measure yet" description="Margin appears once an order has both inward and outward movements." />
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Inventory"
        subtitle="Stock exists only between the supplier delivery and the customer shipment of the same order — on hand should return to zero as each order closes."
        actions={
          <Btn variant="secondary" icon={Download} onClick={exportCsv}>
            Export CSV
          </Btn>
        }
      />

      <div className="kpi-grid" style={{ marginBottom: 16 }}>
        <div style={{ cursor: 'pointer' }} onClick={() => setTab('stock')}>
          <KpiCard label="Total items" value={stock.length} icon={Layers} tone="primary" hint={`${onHandItems.length} with stock on hand (Click to view)`} />
        </div>
        <div style={{ cursor: 'pointer' }} onClick={() => setTab('stock')}>
          <KpiCard label="Total stock quantity" value={nf(totalQty, 2)} icon={Package} tone={totalQty > 0 ? 'warning' : 'neutral'} hint="held against open orders (Click to view)" />
        </div>
        <div style={{ cursor: 'pointer' }} onClick={() => setTab('stock')}>
          <KpiCard label="Stock value" value={`₹ ${nf(stockValue, 0)}`} icon={Boxes} tone={stockValue > 0 ? 'teal' : 'neutral'} hint="at average inward cost (Click to view)" />
        </div>
        <div style={{ cursor: 'pointer' }} onClick={() => setTab('ledger')}>
          <KpiCard label="Total inward" value={`₹ ${nf(inValue, 0)}`} icon={ArrowDownToLine} tone="info" hint={`${inRows.length} movement${inRows.length === 1 ? '' : 's'} (Click to view)`} />
        </div>
        <div style={{ cursor: 'pointer' }} onClick={() => setTab('ledger')}>
          <KpiCard label="Total outward" value={`₹ ${nf(outValue, 0)}`} icon={ArrowUpFromLine} tone="success" hint={`${outRows.length} movement${outRows.length === 1 ? '' : 's'} (Click to view)`} />
        </div>
      </div>

      <div className="tbl-card">
        <div className="filterbar no-print">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Request No"
            style={{ width: 168 }}
            value={f.crId}
            onChange={(v) => setF1('crId', v)}
            options={s.customerRequests.map((c) => ({ value: c.id, label: c.crNo }))}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Item"
            style={{ width: 244 }}
            value={f.itemId}
            onChange={(v) => setF1('itemId', v)}
            options={s.items.map((i) => ({ value: i.id, label: `${i.code} — ${i.name}` }))}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Customer"
            style={{ width: 208 }}
            value={f.customerId}
            onChange={(v) => setF1('customerId', v)}
            options={s.customers.map((c) => ({ value: c.id, label: c.name }))}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Supplier"
            style={{ width: 208 }}
            value={f.supplierId}
            onChange={(v) => setF1('supplierId', v)}
            options={s.suppliers.map((c) => ({ value: c.id, label: c.name }))}
          />

          {dirty && (
            <Btn variant="text" size="small" icon={X} onClick={clear}>
              Clear
            </Btn>
          )}
        </div>

        <div style={{ padding: '4px 16px 8px' }}>
          <Tabs activeKey={tab} onChange={setTab} items={tabs} />
        </div>
      </div>
    </div>
  )
}
