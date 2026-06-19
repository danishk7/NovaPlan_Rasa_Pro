import { Leaf, Plane, ShieldCheck } from 'lucide-react';
import type { ReactNode } from 'react';

export default function AboutPage() {
  return (
    <PublicShell eyebrow="About NovaPlan.ai" title="AI travel planning with sustainability built in.">
      <div className="grid gap-4 md:grid-cols-3">
        <Info icon={Plane} title="Smarter journeys" text="Plan flights, stays, and daily itineraries through the Rasa-powered assistant." />
        <Info icon={Leaf} title="Lower impact choices" text="Surface weather, air quality, and carbon-aware decisions while planning." />
        <Info icon={ShieldCheck} title="Real accounts" text="User, support, and admin access are backed by the Neon API rather than deprecated frontend-only state." />
      </div>
    </PublicShell>
  );
}

function PublicShell({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) {
  return (
    <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">{eyebrow}</p>
      <h1 className="mt-3 max-w-3xl text-4xl font-black text-slate-950 sm:text-5xl">{title}</h1>
      <div className="mt-8">{children}</div>
    </main>
  );
}

function Info({ icon: Icon, title, text }: { icon: typeof Plane; title: string; text: string }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <Icon className="mb-4 h-7 w-7 text-emerald-700" />
      <h2 className="text-lg font-bold text-slate-950">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
    </article>
  );
}
