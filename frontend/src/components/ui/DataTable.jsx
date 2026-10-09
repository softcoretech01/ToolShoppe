import React, { useMemo, useState } from 'react'
import { Table } from 'antd'
import dayjs from 'dayjs'
import FilterBar from './FilterBar.jsx'
import { EmptyState, ErrorState, TableSkeleton } from './States.jsx'

/**
 * The single list surface for the whole ERP. Every module screen renders its
 * grid through this component, so search, filters, sorting, pagination and the
 * loading / empty / error states look and behave identically everywhere.
 *
 * Column extras honoured here:
 *   numeric: true  → right-aligned, tabular figures
 *   sorter:  true  → auto string/number sorter on dataIndex
 */
export function defaultSortRecent(list) {
  if (!Array.isArray(list)) return list
  return [...list].sort((a, b) => {
    // 1. Compare dates if present
    const dateA = a.date || a.created_at || a.sent_at || a.dispatch_date || a.invoice_date || a.supplierInvDate || ''
    const dateB = b.date || b.created_at || b.sent_at || b.dispatch_date || b.invoice_date || b.supplierInvDate || ''
    if (dateA && dateB && dateA !== dateB) {
      return String(dateB).localeCompare(String(dateA))
    }
    // 2. Local/temporary IDs on top
    if (typeof a.id === 'string' && typeof b.id === 'number') return -1
    if (typeof a.id === 'number' && typeof b.id === 'string') return 1

    // 3. Compare numeric IDs descending
    const numA = Number(a.id)
    const numB = Number(b.id)
    if (!isNaN(numA) && !isNaN(numB) && numA !== numB) {
      return numB - numA
    }

    // 4. Document number descending (e.g. PI-0008, CR-043)
    const docA = a.crNo || a.prNo || a.vqNo || a.qcNo || a.cqNo || a.soNo || a.poNo || a.grnNo || a.inwNo || a.outNo || a.siNo || a.piNo || a.code || ''
    const docB = b.crNo || b.prNo || b.vqNo || b.qcNo || b.cqNo || b.soNo || b.poNo || b.grnNo || b.inwNo || b.outNo || b.siNo || b.piNo || b.code || ''
    if (docA && docB && docA !== docB) {
      return String(docB).localeCompare(String(docA), undefined, { numeric: true })
    }
    return 0
  })
}

export default function DataTable({
  columns,
  data,
  rowKey = 'id',
  serial = true,
  searchKeys = [],
  searchPlaceholder = 'Search…',
  filters = [],
  showRange = false,
  rangeKey = 'date',
  toolbarExtra,
  loading = false,
  error = null,
  onRetry,
  empty = {},
  pageSize = 10,
  scrollX,
  size = 'small',
  summary,
  ...rest
}) {
  const [q, setQ] = useState('')
  const [sel, setSel] = useState({})
  const [range, setRange] = useState(null)

  const clear = () => {
    setQ('')
    setSel({})
    setRange(null)
  }

  const rows = useMemo(() => {
    let out = data || []
    const term = q.trim().toLowerCase()
    if (term && searchKeys.length) {
      out = out.filter((r) =>
        searchKeys.some((k) => {
          const v = typeof k === 'function' ? k(r) : r[k]
          return String(v ?? '').toLowerCase().includes(term)
        })
      )
    }
    filters.forEach((f) => {
      const v = sel[f.key]
      if (v === undefined || v === null || v === '') return
      out = out.filter((r) =>
        f.match ? f.match(r, v) : r[f.key] === v || (r[f.key] != null && v != null && String(r[f.key]) === String(v))
      )
    })
    if (showRange && range && range[0] && range[1]) {
      out = out.filter((r) => {
        const d = dayjs(r[rangeKey])
        return !d.isBefore(range[0], 'day') && !d.isAfter(range[1], 'day')
      })
    }
    return defaultSortRecent(out)
  }, [data, q, sel, range, filters, searchKeys, showRange, rangeKey])

  const cols = useMemo(() => {
    const built = columns.map((c) => {
      const out = { ...c }
      if (c.numeric) {
        out.align = 'right'
        out.className = `col-num ${c.className || ''}`.trim()
      }
      if (c.sorter === true && c.dataIndex) {
        out.sorter = (a, b) => {
          const x = a[c.dataIndex]
          const y = b[c.dataIndex]
          if (typeof x === 'number' && typeof y === 'number') return x - y
          return String(x ?? '').localeCompare(String(y ?? ''))
        }
      }
      const isAction =
        out.title === 'Actions' ||
        out.title === 'Available Actions' ||
        out.key === 'actions' ||
        out.dataIndex === 'actions'

      if (isAction) {
        out.align = out.align || 'left'
        out.className = out.className ? out.className + ' col-actions' : 'col-actions'
        if (c.width) out.width = c.width
        if (c.fixed) out.fixed = c.fixed
      } else if (c.fixed) {
        out.fixed = c.fixed
      }
      delete out.numeric
      return out
    })
    if (!serial) return built
    return [
      {
        title: 'S.No',
        key: 'serial',
        width: 62,
        align: 'center',
        className: 'col-sno',
        render: (_, __, i) => <span className="num dim">{i + 1}</span>,
      },
      ...built,
    ]
  }, [columns, serial])

  const hasToolbar = searchKeys.length > 0 || filters.length > 0 || showRange || toolbarExtra

  const toolbar = hasToolbar && (
    <FilterBar
      search={q}
      onSearch={searchKeys.length ? setQ : undefined}
      searchPlaceholder={searchPlaceholder}
      filters={filters}
      values={sel}
      onChange={(k, v) => setSel((p) => ({ ...p, [k]: v }))}
      showRange={showRange}
      range={range}
      onRangeChange={setRange}
      onClear={clear}
      extra={toolbarExtra}
    />
  )

  if (error) {
    return (
      <div className="tbl-card">
        {toolbar}
        <ErrorState description={error} onRetry={onRetry} />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="tbl-card">
        {toolbar}
        <TableSkeleton cols={Math.min(cols.length, 7)} />
      </div>
    )
  }

  const filteredEmpty = (data || []).length > 0 && rows.length === 0

  return (
    <div className="tbl-card tbl-comfy">
      {toolbar}
      <Table
        size={size}
        columns={cols}
        dataSource={rows}
        rowKey={rowKey}
        summary={summary}
        scroll={scrollX ? { x: scrollX } : { x: 'max-content' }}
        pagination={
          rows.length > pageSize
            ? { pageSize, showSizeChanger: false, size: 'small', showTotal: (t, r) => `${r[0]}–${r[1]} of ${t}` }
            : false
        }
        locale={{
          emptyText: filteredEmpty ? (
            <EmptyState
              compact
              title="No matching records"
              description="No row matches the current search or filters. Try clearing them."
            />
          ) : (
            <EmptyState
              compact
              icon={empty.icon}
              title={empty.title || 'Nothing here yet'}
              description={empty.description}
              action={empty.action}
            />
          ),
        }}
        {...rest}
      />
    </div>
  )
}
