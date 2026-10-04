import { Navigate, NavLink, Route, Routes } from 'react-router'
import AccountsPage from './pages/AccountsPage.tsx'
import LinkBankPage from './pages/LinkBankPage.tsx'
import LinkCallbackPage from './pages/LinkCallbackPage.tsx'
import TransactionsPage from './pages/TransactionsPage.tsx'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center gap-8 px-4 py-3">
          <span className="text-lg font-semibold">Budget</span>
          <nav className="flex gap-6">
            <NavItem to="/transactions">Transactions</NavItem>
            <NavItem to="/accounts">Accounts</NavItem>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/transactions" replace />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/link" element={<LinkBankPage />} />
          <Route path="/link/callback" element={<LinkCallbackPage />} />
        </Routes>
      </main>
    </div>
  )
}

function NavItem({ to, children }: { to: string; children: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        isActive ? 'font-medium text-blue-700' : 'text-gray-600 hover:text-gray-900'
      }
    >
      {children}
    </NavLink>
  )
}
