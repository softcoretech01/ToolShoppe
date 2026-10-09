import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Drawer, Layout } from 'antd'
import { useApp } from '../store/AppContext.jsx'
import { dashboardCounts } from '../store/selectors.js'
import { DocLabelProvider } from './docLabel.jsx'
import Sidebar from './Sidebar.jsx'
import Topbar from './Topbar.jsx'

import Dashboard from '../pages/Dashboard.jsx'
import Login from '../pages/Login.jsx'
import EmailLog from '../pages/EmailLog.jsx'
import Customers from '../modules/masters/Customers.jsx'
import Suppliers from '../modules/masters/Suppliers.jsx'
import Items from '../modules/masters/Items.jsx'
import CustomerRequest from '../modules/sales/CustomerRequest.jsx'
import CustomerRequestView from '../modules/sales/CustomerRequestView.jsx'
import Quotation from '../modules/sales/Quotation.jsx'
import QuotationView from '../modules/sales/QuotationView.jsx'
import CustomerPO from '../modules/sales/CustomerPO.jsx'
import CustomerPOView from '../modules/sales/CustomerPOView.jsx'
import Outward from '../modules/sales/Outward.jsx'
import OutwardView from '../modules/sales/OutwardView.jsx'
import SalesInvoice from '../modules/sales/SalesInvoice.jsx'
import SalesInvoiceView from '../modules/sales/SalesInvoiceView.jsx'
import PurchaseRequest from '../modules/purchase/Request.jsx'
import PurchaseRequestView from '../modules/purchase/RequestView.jsx'
import VendorQuotation from '../modules/purchase/VendorQuotation.jsx'
import VendorQuotationForm from '../modules/purchase/VendorQuotationForm.jsx'
import Comparison from '../modules/purchase/Comparison.jsx'
import ComparisonView from '../modules/purchase/ComparisonView.jsx'
import PurchaseOrder from '../modules/purchase/PurchaseOrder.jsx'
import PurchaseOrderView from '../modules/purchase/PurchaseOrderView.jsx'
import GRN from '../modules/purchase/GRN.jsx'
import GRNView from '../modules/purchase/GRNView.jsx'
import Inward from '../modules/purchase/Inward.jsx'
import InwardView from '../modules/purchase/InwardView.jsx'
import PurchaseInvoice from '../modules/purchase/PurchaseInvoice.jsx'
import PurchaseInvoiceView from '../modules/purchase/PurchaseInvoiceView.jsx'
import Inventory from '../modules/inventory/Inventory.jsx'

const { Sider, Content } = Layout
const MOBILE = 1024

export default function App() {
  const { state, isAuth } = useApp()
  const loc = useLocation()
  const counts = useMemo(() => dashboardCounts(state), [state])

  const [collapsed, setCollapsed] = useState(false)
  const [mobile, setMobile] = useState(() => (typeof window !== 'undefined' ? window.innerWidth < MOBILE : false))
  const [drawer, setDrawer] = useState(false)
  const [docLabel, setDocLabel] = useState(null)

  useEffect(() => {
    const onResize = () => setMobile(window.innerWidth < MOBILE)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Every route change starts at the top of the page.
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [loc.pathname])

  const setLabel = useCallback((l) => setDocLabel(l), [])
  const toggle = () => (mobile ? setDrawer((d) => !d) : setCollapsed((c) => !c))

  const sidebar = (
    <Sidebar
      collapsed={!mobile && collapsed}
      counts={counts}
      onNavigate={mobile ? () => setDrawer(false) : undefined}
    />
  )

  if (!isAuth) {
    return <Login />
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {!mobile && (
        <Sider
          width={252}
          collapsedWidth={72}
          collapsed={collapsed}
          trigger={null}
          style={{ position: 'sticky', top: 0, height: '100vh', overflow: 'hidden' }}
        >
          {sidebar}
        </Sider>
      )}

      {mobile && (
        <Drawer
          placement="left"
          open={drawer}
          onClose={() => setDrawer(false)}
          width={264}
          closeIcon={null}
          styles={{ header: { display: 'none' }, body: { padding: 0, background: 'var(--c-sidebar)' } }}
        >
          {sidebar}
        </Drawer>
      )}

      <Layout style={{ minWidth: 0, background: 'var(--c-page)' }}>
        <Topbar collapsed={mobile ? true : collapsed} onToggle={toggle} docLabel={docLabel} />
        <Content>
          <DocLabelProvider setLabel={setLabel}>
            <div className="page">
              <Routes>
                <Route path="/" element={<Dashboard />} />

                <Route path="/masters/customers" element={<Customers />} />
                <Route path="/masters/suppliers" element={<Suppliers />} />
                <Route path="/masters/items" element={<Items />} />

                <Route path="/sales/customer-request" element={<CustomerRequest />} />
                <Route path="/sales/customer-request/:id" element={<CustomerRequestView />} />
                <Route path="/sales/quotation" element={<Quotation />} />
                <Route path="/sales/quotation/:id" element={<QuotationView />} />
                <Route path="/sales/customer-po" element={<CustomerPO />} />
                <Route path="/sales/customer-po/:id" element={<CustomerPOView />} />
                <Route path="/sales/outward" element={<Outward />} />
                <Route path="/sales/outward/:id" element={<OutwardView />} />
                <Route path="/sales/invoice" element={<SalesInvoice />} />
                <Route path="/sales/invoice/:id" element={<SalesInvoiceView />} />

                <Route path="/purchase/request" element={<PurchaseRequest />} />
                <Route path="/purchase/request/:id" element={<PurchaseRequestView />} />
                <Route path="/purchase/vendor-quotation" element={<VendorQuotation />} />
                <Route path="/purchase/vendor-quotation/new" element={<VendorQuotationForm />} />
                <Route path="/purchase/vendor-quotation/:id" element={<VendorQuotationForm />} />
                <Route path="/purchase/quotation-comparison" element={<Comparison />} />
                <Route path="/purchase/quotation-comparison/:id" element={<ComparisonView />} />
                <Route path="/purchase/purchase-order" element={<PurchaseOrder />} />
                <Route path="/purchase/purchase-order/:id" element={<PurchaseOrderView />} />
                <Route path="/purchase/grn" element={<GRN />} />
                <Route path="/purchase/grn/:id" element={<GRNView />} />
                <Route path="/purchase/inward" element={<Inward />} />
                <Route path="/purchase/inward/:id" element={<InwardView />} />
                <Route path="/purchase/invoice" element={<PurchaseInvoice />} />
                <Route path="/purchase/invoice/:id" element={<PurchaseInvoiceView />} />

                <Route path="/inventory" element={<Inventory />} />
                <Route path="/email-log" element={<EmailLog />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </DocLabelProvider>

          <footer className="app-footer no-print">
            <span>ToolShoppe ERP — Back-to-Back Trading System</span>
            <span>Stock exists only between a supplier delivery and the customer shipment of the same order.</span>
          </footer>
        </Content>
      </Layout>
    </Layout>
  )
}
