import React, { useState } from 'react'
import { Input, Button, Checkbox, Select } from 'antd'
import { 
  Wrench, User, Lock, Eye, EyeOff, 
  TrendingUp, Package, Handshake, ShieldCheck, 
  Users, ShoppingCart, Archive
} from 'lucide-react'
import { useApp } from '../store/AppContext.jsx'

export default function Login() {
  const { login } = useApp()
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const [error, setError] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const success = await login(user, pass)
    if (!success) {
      setError(true)
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', width: '100%', fontFamily: 'Inter, sans-serif' }}>
      
      {/* LEFT PANE - Branding & Features */}
      <div style={{
        flex: 1,
        position: 'relative',
        background: 'url(/bg-industrial.jpg) center/cover no-repeat',
        display: 'flex',
        flexDirection: 'column',
        padding: '60px',
        color: 'white',
        overflow: 'hidden'
      }}>
        {/* Dark Navy Overlay */}
        <div style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'linear-gradient(135deg, rgba(8, 25, 60, 0.9) 0%, rgba(13, 31, 70, 0.95) 100%)',
          zIndex: 1
        }} />

        <div style={{ position: 'relative', zIndex: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
          
          {/* Logo Area */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 80 }}>
            <div style={{ 
              background: 'white', color: '#1E3A8A', 
              width: 56, height: 56, borderRadius: 14, 
              display: 'flex', alignItems: 'center', justifyContent: 'center' 
            }}>
              <Wrench size={30} strokeWidth={2.5} />
            </div>
            <div>
              <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1 }}>Toolsphoppe</div>
              <div style={{ fontSize: 14, color: '#93C5FD', marginTop: 4, letterSpacing: '0.02em' }}>
                Sales &bull; Purchase &bull; Inventory
              </div>
            </div>
          </div>

          {/* Hero Text */}
          <div style={{ maxWidth: 460 }}>
            <h1 style={{ fontSize: 40, fontWeight: 700, lineHeight: 1.1, margin: '0 0 16px 0', color: 'white' }}>
              Smart Tools.<br />Stronger Business.
            </h1>
            <p style={{ fontSize: 16, color: '#BFDBFE', lineHeight: 1.6, margin: '0 0 48px 0' }}>
              Manage your back-to-back trading, inventory, sales and purchase seamlessly in one powerful platform.
            </p>
          </div>

          {/* Features List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 32, flex: 1, justifyContent: 'center', maxWidth: 500 }}>
            <Feature 
              icon={<TrendingUp size={20} />} 
              color="#6366F1" // Indigo
              title="End-to-End Management"
              desc="From request to invoice, manage the complete workflow."
            />
            <Feature 
              icon={<Package size={20} />} 
              color="#0284C7" // Light Blue
              title="Real-time Inventory"
              desc="Track stock in real time and never miss a delivery."
            />
            <Feature 
              icon={<Handshake size={20} />} 
              color="#10B981" // Emerald Green
              title="Stronger Relationships"
              desc="Build better relationships with customers and suppliers."
            />
            <Feature 
              icon={<ShieldCheck size={20} />} 
              color="#F59E0B" // Amber
              title="Secure & Reliable"
              desc="Your data is protected with enterprise grade security."
            />
          </div>
        </div>
      </div>


      {/* RIGHT PANE - Login Form */}
      <div style={{
        flex: 1,
        background: '#F8FAFC',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflowY: 'auto'
      }}>
        
        {/* Center Card Container */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
          <div style={{
            background: 'white',
            borderRadius: 24,
            padding: '32px 32px',
            width: '100%',
            maxWidth: 520,
            boxShadow: '0 10px 40px -10px rgba(0,0,0,0.08)'
          }}>
            
            {/* Header */}
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{ 
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                background: '#EEF2FF', color: '#4F46E5',
                width: 56, height: 56, borderRadius: '50%',
                marginBottom: 16
              }}>
                <Wrench size={26} strokeWidth={2} />
              </div>
              <h2 style={{ fontSize: 22, fontWeight: 700, margin: '0 0 4px 0', color: '#0F172A' }}>Welcome Back!</h2>
              <div style={{ color: '#64748B', fontSize: 14 }}>Sign in to continue to Toolsphoppe ERP</div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 14, fontWeight: 600, color: '#1E293B', marginBottom: 8 }}>Username</label>
                <Input 
                  size="large"
                  prefix={<User size={18} color="#94A3B8" style={{ marginRight: 8 }} />}
                  placeholder="Enter your username" 
                  value={user} 
                  onChange={e => { setUser(e.target.value); setError(false) }} 
                  style={{ height: 40, borderRadius: 8 }}
                />
              </div>

              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <label style={{ fontSize: 14, fontWeight: 600, color: '#1E293B' }}>Password</label>
                  <a href="#" style={{ fontSize: 14, color: '#4F46E5', fontWeight: 500, textDecoration: 'none' }}>Forgot password?</a>
                </div>
                <Input.Password 
                  size="large"
                  prefix={<Lock size={18} color="#94A3B8" style={{ marginRight: 8 }} />}
                  placeholder="Enter your password" 
                  value={pass} 
                  onChange={e => { setPass(e.target.value); setError(false) }} 
                  style={{ height: 40, borderRadius: 8 }}
                  iconRender={(visible) => (visible ? <Eye size={18} color="#94A3B8" /> : <EyeOff size={18} color="#94A3B8" />)}
                />
                
                {error && (
                  <div style={{ color: '#EF4444', fontSize: 13, marginTop: 8 }}>
                    Invalid username or password. (Hint: admin / admin)
                  </div>
                )}
              </div>

              <div style={{ marginBottom: 20 }}>
                <Checkbox style={{ color: '#475569', fontSize: 14, fontWeight: 500 }}>Remember me</Checkbox>
              </div>

              <Button type="primary" htmlType="submit" style={{ 
                width: '100%', height: 40, borderRadius: 8, fontSize: 16, fontWeight: 600,
                background: '#4F46E5', borderColor: '#4F46E5'
              }}>
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  &rarr; Sign In
                </span>
              </Button>
            </form>

            <div style={{ display: 'flex', alignItems: 'center', margin: '24px 0', color: '#94A3B8' }}>
              <div style={{ flex: 1, height: 1, background: '#E2E8F0' }}></div>
              <div style={{ padding: '0 16px', fontSize: 14 }}>or continue with</div>
              <div style={{ flex: 1, height: 1, background: '#E2E8F0' }}></div>
            </div>

            {/* Portals */}
            <div style={{ display: 'flex', gap: 16 }}>
              <PortalBtn onClick={() => login('admin', 'admin')} icon={<Users size={20} />} color="#4F46E5" title="Sales Portal" subtitle="Sales Team Login" />
              <PortalBtn onClick={() => login('admin', 'admin')} icon={<ShoppingCart size={20} />} color="#10B981" title="Purchase Portal" subtitle="Purchase Team Login" />
              <PortalBtn onClick={() => login('admin', 'admin')} icon={<Archive size={20} />} color="#F59E0B" title="Inventory Portal" subtitle="Inventory Team Login" />
            </div>

          </div>
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', padding: '16px 24px', color: '#64748B', fontSize: 13, fontWeight: 500 }}>
          &copy; {new Date().getFullYear()} Toolsphoppe. All rights reserved.
        </div>

      </div>
    </div>
  )
}

function Feature({ icon, color, title, desc }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
      <div style={{ 
        background: color, color: 'white', 
        width: 44, height: 44, borderRadius: 12, 
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.5 }}>{desc}</div>
      </div>
    </div>
  )
}

function PortalBtn({ icon, color, title, subtitle, onClick }) {
  return (
    <button 
      type="button"
      onClick={onClick}
      style={{ 
      flex: 1, 
      background: 'white', border: '1px solid #E2E8F0', borderRadius: 12, 
      padding: '12px 8px', 
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
      cursor: 'pointer', transition: 'all 0.2s'
    }}
    onMouseEnter={(e) => { e.currentTarget.style.borderColor = color; e.currentTarget.style.boxShadow = `0 4px 12px ${color}1A` }}
    onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#E2E8F0'; e.currentTarget.style.boxShadow = 'none' }}
    >
      <div style={{ 
        background: color, color: 'white', 
        width: 40, height: 40, borderRadius: 20, 
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        {icon}
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#1E293B' }}>{title}</div>
        <div style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{subtitle}</div>
      </div>
    </button>
  )
}
