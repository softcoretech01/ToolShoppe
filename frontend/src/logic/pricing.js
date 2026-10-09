export const round2 = (n) => Math.round((Number(n) || 0) * 100) / 100

/** Default customer price = supplier rate x (1 + markup%). */
export const defaultCustomerPrice = (supplierRate, markupPct) =>
  round2((Number(supplierRate) || 0) * (1 + (Number(markupPct) || 0) / 100))

/** Margin % = (price - cost) / price. */
export const marginPct = (customerPrice, supplierRate) => {
  const p = Number(customerPrice) || 0
  if (!p) return 0
  return round2(((p - (Number(supplierRate) || 0)) / p) * 100)
}

export const money = (n) =>
  (Number(n) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const inr = (n) => `₹ ${money(n)}`

export const sum = (arr, fn) => arr.reduce((a, x) => a + (Number(fn(x)) || 0), 0)

export const amountInWords = (amount) => {
  const n = Math.floor(Math.abs(Number(amount) || 0))
  if (n === 0) return 'INR Zero Only'

  const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
    'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
  const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

  const numToWords = (num) => {
    let str = ''
    if (num >= 100) {
      str += ones[Math.floor(num / 100)] + ' Hundred '
      num %= 100
    }
    if (num >= 20) {
      str += tens[Math.floor(num / 10)] + ' '
      num %= 10
    }
    if (num > 0) {
      str += ones[num] + ' '
    }
    return str.trim()
  }

  let words = ''
  const crore = Math.floor(n / 10000000)
  let rem = n % 10000000
  const lakh = Math.floor(rem / 100000)
  rem = rem % 100000
  const thousand = Math.floor(rem / 1000)
  rem = rem % 1000
  const hundredAndBelow = rem

  if (crore) words += numToWords(crore) + ' Crore '
  if (lakh) words += numToWords(lakh) + ' Lakh '
  if (thousand) words += numToWords(thousand) + ' Thousand '
  if (hundredAndBelow) words += numToWords(hundredAndBelow) + ' '

  const paise = Math.round(((Number(amount) || 0) - n) * 100)
  let result = 'INR ' + words.trim()
  if (paise > 0) {
    result += ' and ' + numToWords(paise) + ' Paise'
  }
  return result + ' Only'
}
