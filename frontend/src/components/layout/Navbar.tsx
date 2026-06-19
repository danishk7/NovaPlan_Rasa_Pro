import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Bot, LogOut, Shield, User } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export default function Navbar() {
  const { profile, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 shadow-sm backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-white">
            <Bot className="h-5 w-5" />
          </span>
          <span className="text-lg font-black tracking-tight text-slate-950">NovaPlan.ai</span>
        </Link>

        <nav className="hidden items-center gap-2 md:flex">
          <NavLink to="/" className={({ isActive }) => navClass(isActive)}>
            Home
          </NavLink>
          {!profile && (
            <>
              <NavLink to="/about" className={({ isActive }) => navClass(isActive)}>
                About
              </NavLink>
              <NavLink to="/travel-blog" className={({ isActive }) => navClass(isActive)}>
                Travel Blog
              </NavLink>
              <NavLink to="/contact" className={({ isActive }) => navClass(isActive)}>
                Contact
              </NavLink>
            </>
          )}
          {profile?.role === 'user' && (
            <>
              <NavLink to="/dashboard" className={({ isActive }) => navClass(isActive)}>
                Dashboard
              </NavLink>
              <NavLink to="/chat" className={({ isActive }) => navClass(isActive)}>
                Assistant
              </NavLink>
            </>
          )}
          {profile?.role === 'admin' && (
            <NavLink to="/admin" className={({ isActive }) => navClass(isActive)}>
              Admin
            </NavLink>
          )}
          {profile?.role === 'support' && (
            <NavLink to="/support" className={({ isActive }) => navClass(isActive)}>
              Support
            </NavLink>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {profile ? (
            <>
              <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 sm:flex">
                {profile.role === 'admin' ? <Shield className="h-4 w-4 text-emerald-700" /> : <User className="h-4 w-4 text-emerald-700" />}
                {profile.name}
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-emerald-300 hover:text-emerald-800"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 transition hover:text-emerald-800">
                User Login
              </Link>
              <Link to="/admin/login" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-emerald-700">
                Staff Login
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function navClass(isActive: boolean) {
  return `rounded-lg px-3 py-2 text-sm font-semibold transition ${
    isActive ? 'bg-emerald-50 text-emerald-800' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
  }`;
}
