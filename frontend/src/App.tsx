import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Navigate, RouterProvider, useLocation, useRouteError } from 'react-router'
import { Toaster } from 'sonner'
import { AuthProvider, useAuth } from './lib/auth'
import { AppDataProvider } from './lib/appData'
import { AppShell } from './components/layout/AppShell'
import { Button, Spinner } from './components/ui/primitives'
import { BrandedLoader, BrandMark } from './components/brand/Brand'
import LandingPage from './pages/Landing'
import { LoginPage, RegisterPage } from './pages/Auth'
import NotFoundPage from './pages/NotFound'

const DashboardPage = lazy(() => import('./pages/Dashboard'))
const TransactionsPage = lazy(() => import('./pages/Transactions'))
const ExpenseEditorPage = lazy(() => import('./pages/ExpenseEditor'))
const BudgetsPage = lazy(() => import('./pages/Budgets'))
const AnalyticsPage = lazy(() => import('./pages/Analytics'))
const InsightsPage = lazy(() => import('./pages/Insights'))
const AnomaliesPage = lazy(() => import('./pages/Anomalies'))
const ReceiptsPage = lazy(() => import('./pages/Receipts'))
const SimulatorPage = lazy(() => import('./pages/Simulator'))
const GoalsPage = lazy(() => import('./pages/Goals'))
const AssistantPage = lazy(() => import('./pages/Assistant'))
const ProfilePage = lazy(() => import('./pages/Profile'))
const SettingsPage = lazy(() => import('./pages/Settings'))

function BackendUnavailable() {
  const { retry } = useAuth()
  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <div className="edge-highlight max-w-md rounded-2xl border border-border bg-surface p-7 text-center">
        <BrandMark className="mx-auto mb-4 h-10 w-10" />
        <h1 className="text-lg font-semibold">FinSight is temporarily unavailable</h1>
        <p className="mt-2 text-sm text-muted">The application server could not be reached. If you are running locally, start the backend
          (<code className="rounded bg-surface-2 px-1">uvicorn app.main:create_app --factory</code>) and try again.</p>
        <Button className="mt-4" onClick={retry}>Try again</Button>
      </div>
    </div>
  )
}

/** Frontend route guard. The backend independently rejects unauthenticated API calls. */
function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <BrandedLoader label="Checking your session" />
  if (status === 'unavailable') return <BackendUnavailable />
  if (status !== 'authenticated') return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return (
    <AppDataProvider>
      <AppShell />
    </AppDataProvider>
  )
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'loading') return <BrandedLoader label="Loading" />
  if (status === 'authenticated') return <Navigate to="/app" replace />
  return <>{children}</>
}

function RouteError() {
  const error = useRouteError()
  console.error(error)
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="edge-highlight max-w-md rounded-2xl border border-border bg-surface p-7 text-center">
        <BrandMark className="mx-auto mb-4 h-10 w-10" />
        <h1 className="text-lg font-semibold">Something went wrong on this page</h1>
        <p className="mt-2 text-sm text-muted">Your data is safe. Reload the page or go back to the dashboard.</p>
        <div className="mt-4 flex justify-center gap-2">
          <Button variant="outline" onClick={() => window.location.reload()}>Reload</Button>
          <Button onClick={() => window.location.assign('/app')}>Dashboard</Button>
        </div>
      </div>
    </div>
  )
}

const page = (el: ReactNode) => <Suspense fallback={<Spinner />}>{el}</Suspense>

const router = createBrowserRouter([
  { path: '/', element: <LandingPage />, errorElement: <RouteError /> },
  { path: '/login', element: <GuestOnly><LoginPage /></GuestOnly> },
  { path: '/register', element: <GuestOnly><RegisterPage /></GuestOnly> },
  {
    path: '/app',
    element: <RequireAuth />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: page(<DashboardPage />) },
      { path: 'transactions', element: page(<TransactionsPage />) },
      { path: 'transactions/new', element: page(<ExpenseEditorPage />) },
      { path: 'transactions/:id/edit', element: page(<ExpenseEditorPage />) },
      { path: 'budgets', element: page(<BudgetsPage />) },
      { path: 'analytics', element: page(<AnalyticsPage />) },
      { path: 'insights', element: page(<InsightsPage />) },
      { path: 'anomalies', element: page(<AnomaliesPage />) },
      { path: 'receipts', element: page(<ReceiptsPage />) },
      { path: 'simulator', element: page(<SimulatorPage />) },
      { path: 'goals', element: page(<GoalsPage />) },
      { path: 'assistant', element: page(<AssistantPage />) },
      { path: 'profile', element: page(<ProfilePage />) },
      { path: 'settings', element: page(<SettingsPage />) },
      { path: '*', element: <NotFoundPage inApp /> },
    ],
  },
  // Insight action links use short paths (e.g. /transactions?category=food); map them into the app.
  { path: '/transactions', element: <RedirectIntoApp /> },
  { path: '/budgets', element: <RedirectIntoApp /> },
  { path: '/goals', element: <RedirectIntoApp /> },
  { path: '/simulator', element: <RedirectIntoApp /> },
  { path: '*', element: <NotFoundPage /> },
])

function RedirectIntoApp() {
  const location = useLocation()
  return <Navigate to={`/app${location.pathname}${location.search}`} replace />
}

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
      <Toaster position="top-right" richColors closeButton toastOptions={{ duration: 4500 }} />
    </AuthProvider>
  )
}
