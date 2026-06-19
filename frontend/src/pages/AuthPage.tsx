import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { LockKeyhole, UserPlus } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

interface Props {
  mode: 'login' | 'register' | 'admin';
}

export default function AuthPage({ mode }: Props) {
  const isRegister = mode === 'register';
  const isAdmin = mode === 'admin';
  const { profile, login, register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState(isAdmin ? 'admin@novaplan.ai' : '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (profile) {
    return <Navigate to={profile.role === 'admin' ? '/admin' : profile.role === 'support' ? '/support' : '/dashboard'} replace />;
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = isRegister ? await register(name, email, password) : await login(email, password);

      if (isAdmin && user.role !== 'admin' && user.role !== 'support') {
        setError('This account is not authorized for the admin portal.');
        return;
      }

      navigate(user.role === 'admin' ? '/admin' : user.role === 'support' ? '/support' : '/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-7xl items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <section className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-600 text-white">
            {isRegister ? <UserPlus className="h-5 w-5" /> : <LockKeyhole className="h-5 w-5" />}
          </div>
          <h1 className="text-2xl font-black text-slate-950">
            {isRegister ? 'Create your account' : isAdmin ? 'Staff login' : 'User login'}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {isAdmin ? 'Sign in with an admin or support account from the deployed auth backend.' : 'Use your NovaPlan backend account.'}
          </p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          {isRegister && (
            <label className="block">
              <span className="text-sm font-semibold text-slate-700">Name</span>
              <input value={name} onChange={(event) => setName(event.target.value)} required className={fieldClass} />
            </label>
          )}
          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Email, name, or user ID</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} required className={fieldClass} />
          </label>
          <label className="block">
            <span className="text-sm font-semibold text-slate-700">Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required className={fieldClass} />
          </label>

          {error && <p className="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</p>}

          <button disabled={loading} className="w-full rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:opacity-60">
            {loading ? 'Please wait...' : isRegister ? 'Register' : 'Login'}
          </button>
        </form>

        {!isAdmin && (
          <p className="mt-5 text-center text-sm text-slate-600">
            {isRegister ? 'Already have an account?' : 'Need an account?'}{' '}
            <Link to={isRegister ? '/login' : '/register'} className="font-bold text-emerald-700">
              {isRegister ? 'Login' : 'Register'}
            </Link>
          </p>
        )}
      </section>
    </div>
  );
}

const fieldClass = 'mt-2 w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none focus:border-emerald-500';
