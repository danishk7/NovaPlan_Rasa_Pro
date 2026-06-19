import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bot, CalendarCheck, LayoutDashboard, LogOut } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

interface Props {
  children: ReactNode;
}

const navItems = [
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Planner', path: '/planner', icon: Bot },
  { label: 'Bookings', path: '/bookings', icon: CalendarCheck },
];

export default function UserPortalLayout({ children }: Props) {
  const { logout } = useAuth();
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-950">
      <aside className="flex w-72 shrink-0 flex-col border-r border-slate-200 bg-white p-5">
        <div className="mb-8">
          <p className="text-xl font-black">NovaPlan.ai</p>
          <p className="text-xs text-slate-500">Traveler workspace</p>
        </div>
        <nav className="space-y-2">
          {navItems.map(({ label, path, icon: Icon }) => {
            const active = location.pathname === path;
            return (
              <Link key={path} to={path} className={tabClass(active)}>
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <button onClick={logout} className="mt-auto flex w-full items-center gap-3 rounded-lg border border-slate-200 px-4 py-3 text-left text-sm font-bold text-slate-600 hover:border-emerald-300 hover:text-emerald-800">
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}

function tabClass(active: boolean) {
  return `flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-bold transition ${
    active ? 'bg-emerald-50 text-emerald-900' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
  }`;
}
