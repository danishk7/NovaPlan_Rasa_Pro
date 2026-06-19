import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { ReactElement } from 'react';
import ErrorBoundary from './components/shared/ErrorBoundary';
import Navbar from './components/layout/Navbar';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import AdminPage from './pages/AdminPage';
import AboutPage from './pages/AboutPage';
import AuthPage from './pages/AuthPage';
import BookingsPage from './pages/BookingsPage';
import ChatPage from './pages/ChatPage';
import ContactPage from './pages/ContactPage';
import Dashboard from './pages/Dashboard';
import HomePage from './pages/HomePage';
import SupportPage from './pages/SupportPage';
import TravelBlogPage from './pages/TravelBlogPage';

function ProtectedRoute({ children }: { children: ReactElement }) {
  const { profile } = useAuth();

  if (!profile) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AppNavbar() {
  const { profile } = useAuth();
  const location = useLocation();

  const portalRoute = ['/dashboard', '/planner', '/bookings', '/admin', '/support'].some((path) => location.pathname.startsWith(path));
  if (profile && portalRoute) {
    return null;
  }

  return <Navbar />;
}

function AdminRoute({ children }: { children: ReactElement }) {
  const { profile } = useAuth();

  if (!profile) {
    return <Navigate to="/admin/login" replace />;
  }

  if (profile.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function SupportRoute({ children }: { children: ReactElement }) {
  const { profile } = useAuth();

  if (!profile) {
    return <Navigate to="/admin/login" replace />;
  }

  if (profile.role !== 'support') {
    return <Navigate to={profile.role === 'admin' ? '/admin' : '/dashboard'} replace />;
  }

  return children;
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-slate-50 text-slate-900">
            <AppNavbar />
            <main>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/about" element={<AboutPage />} />
                <Route path="/travel-blog" element={<TravelBlogPage />} />
                <Route path="/blogs" element={<TravelBlogPage />} />
                <Route path="/contact" element={<ContactPage />} />
                <Route path="/login" element={<AuthPage mode="login" />} />
                <Route path="/register" element={<AuthPage mode="register" />} />
                <Route path="/admin/login" element={<AuthPage mode="admin" />} />
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/planner"
                  element={
                    <ProtectedRoute>
                      <ChatPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/bookings"
                  element={
                    <ProtectedRoute>
                      <BookingsPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="/chat" element={<Navigate to="/planner" replace />} />
                <Route
                  path="/admin"
                  element={
                    <AdminRoute>
                      <AdminPage />
                    </AdminRoute>
                  }
                />
                <Route
                  path="/support"
                  element={
                    <SupportRoute>
                      <SupportPage />
                    </SupportRoute>
                  }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
