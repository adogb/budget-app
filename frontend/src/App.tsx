import { Navigate, NavLink, Route, Routes } from 'react-router'
import TransactionsPage from './pages/TransactionsPage.tsx'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center gap-8 px-4 py-3">
          <span className="text-lg font-semibold">Budget</span>
          <nav>
            <NavLink
              to="/transactions"
              className={({ isActive }) =>
                isActive ? 'font-medium text-blue-700' : 'text-gray-600 hover:text-gray-900'
              }
            >
              Transactions
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/transactions" replace />} />
          <Route path="/transactions" element={<TransactionsPage />} />
        </Routes>
      </main>
    </div>
  )
}
