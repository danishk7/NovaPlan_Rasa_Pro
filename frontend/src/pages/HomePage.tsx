import { Link } from 'react-router-dom';
import { ArrowRight, Bot, Leaf, LockKeyhole, Plane, Shield, SunMedium } from 'lucide-react';

const features = [
  { title: 'Rasa travel assistant', text: 'Plan flights, hotels, activities, and carbon-aware routes through the deployed assistant.', icon: Bot },
  { title: 'Climate-aware dashboard', text: 'See weather, air quality, wind, and nearest airport context for the traveler location.', icon: SunMedium },
  { title: 'Human support handoff', text: 'Switch from AI planning to a real support queue whenever the user needs help.', icon: Shield },
];

const destinations = [
  {
    city: 'Lisbon',
    image: 'https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&q=80&w=900',
    text: 'Rail-friendly coastal escapes with walkable neighborhoods.',
  },
  {
    city: 'Kyoto',
    image: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&q=80&w=900',
    text: 'Culture-rich planning with seasonal weather awareness.',
  },
  {
    city: 'Vancouver',
    image: 'https://images.unsplash.com/photo-1505820013142-f86a3439c5b2?auto=format&fit=crop&q=80&w=900',
    text: 'Nature, clean transit, and flexible airport planning.',
  },
];

export default function HomePage() {
  return (
    <div>
      <section className="relative min-h-[calc(100vh-73px)] overflow-hidden">
        <img
          src="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&q=80&w=2200"
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-white via-white/85 to-white/20" />
        <div className="relative mx-auto flex min-h-[calc(100vh-73px)] max-w-7xl items-center px-4 py-12 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-4 py-2 text-sm font-semibold text-emerald-800 shadow-sm backdrop-blur">
              <Plane className="h-4 w-4" />
              Sustainable AI-Smart travel partner
            </div>
            <h1 className="text-5xl font-black tracking-tight text-slate-950 sm:text-7xl">Travel sustained, AI Powered.</h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-700">
              NovaPlan.ai your AI powered travelling platform which is climate-aware. Smart platform for smarter people.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-4 md:grid-cols-3">
          {features.map((feature) => (
            <article key={feature.title} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <feature.icon className="mb-4 h-7 w-7 text-emerald-700" />
              <h2 className="text-lg font-bold text-slate-950">{feature.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-14 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">Featured planning ideas</p>
            <h2 className="mt-2 text-3xl font-black text-slate-950">Trips with context, not guesswork.</h2>
          </div>
          <Link to="/travel-blog" className="hidden text-sm font-bold text-emerald-700 hover:text-emerald-900 sm:block">
            Read blog
          </Link>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {destinations.map((destination) => (
            <article key={destination.city} className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
              <img src={destination.image} alt="" className="aspect-[4/3] w-full object-cover" />
              <div className="p-5">
                <h3 className="text-xl font-black text-slate-950">{destination.city}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{destination.text}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
