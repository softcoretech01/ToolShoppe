import { round2, sum } from './pricing.js'

/** Stock is tracked per item + CR, never as free stock. */
export function available(ledger, itemId, crId) {
  const rows = (ledger || []).filter(
    (r) => String(r.itemId) === String(itemId) && String(r.crId) === String(crId)
  )
  const inQty = sum(rows.filter((r) => r.type === 'IN'), (r) => Number(r.qty) || 0)
  const outQty = sum(rows.filter((r) => r.type === 'OUT'), (r) => Number(r.qty) || 0)
  return round2(inQty - outQty)
}

export function crHasStock(ledger, crId) {
  const rows = (ledger || []).filter((r) => String(r.crId) === String(crId))
  const items = [...new Set(rows.map((r) => r.itemId))]
  return items.some((i) => available(ledger, i, crId) > 0)
}

export function stockSummary(ledger, items) {
  const byItem = {}
  ledger.forEach((r) => {
    const b = (byItem[r.itemId] = byItem[r.itemId] || { itemId: r.itemId, qtyIn: 0, qtyOut: 0, inValue: 0 })
    if (r.type === 'IN') {
      b.qtyIn += Number(r.qty) || 0
      b.inValue += Number(r.value) || 0
    } else {
      b.qtyOut += Number(r.qty) || 0
    }
  })
  return Object.values(byItem).map((b) => {
    const item = items.find((i) => i.id === b.itemId)
    const onHand = round2(b.qtyIn - b.qtyOut)
    const avgCost = b.qtyIn ? round2(b.inValue / b.qtyIn) : 0
    return {
      key: b.itemId,
      itemId: b.itemId,
      itemName: item?.name || '—',
      itemCode: item?.code || '—',
      unit: item?.unit || '',
      qtyIn: round2(b.qtyIn),
      qtyOut: round2(b.qtyOut),
      onHand,
      avgCost,
      stockValue: round2(onHand * avgCost),
    }
  })
}

/** purchaseValue = IN qty x supplier rate; salesValue = OUT qty x customer price. */
export function crMargin(ledger, crId) {
  const rows = ledger.filter((r) => r.crId === crId)
  const purchaseValue = round2(sum(rows.filter((r) => r.type === 'IN'), (r) => r.value))
  const salesValue = round2(sum(rows.filter((r) => r.type === 'OUT'), (r) => r.value))
  const margin = round2(salesValue - purchaseValue)
  return {
    purchaseValue,
    salesValue,
    margin,
    marginPct: salesValue ? round2((margin / salesValue) * 100) : 0,
  }
}
