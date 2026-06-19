import { Newspaper } from 'lucide-react';
import type { BlogPost } from '../types/chat';

const staticPosts: BlogPost[] = [
  {
    id: 'rail-first-europe',
    title: 'Rail-first Europe: building a slower, richer itinerary',
    content:
      'Start with cities connected by direct rail, then use the assistant to group hotels and activities near transit. It reduces transfer stress and gives each stop more texture.',
    userName: 'NovaPlan.ai',
    imageUrl: 'https://images.unsplash.com/photo-1474487548417-781cb71495f3?auto=format&fit=crop&q=80&w=1200',
  },
  {
    id: 'air-quality-travel',
    title: 'Using air quality data before booking outdoor tours',
    content:
      'AQI and PM2.5 data can change the best time for walking tours, cycling, and family activities. NovaPlan surfaces those signals on the user dashboard.',
    userName: 'NovaPlan.ai',
    imageUrl: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&q=80&w=1200',
  },
  {
    id: 'airport-context',
    title: 'Why nearest-airport context matters',
    content:
      'A good trip plan starts before the flight. Airport distance, wind, and local weather help decide arrival buffers, transfer options, and hotel neighborhoods.',
    userName: 'NovaPlan.ai',
    imageUrl: 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&q=80&w=1200',
  },
];

export default function TravelBlogPage() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-8 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="relative min-h-80">
          <img src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&q=80&w=1800" alt="" className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-white via-white/80 to-transparent" />
          <div className="relative max-w-2xl p-8">
            <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-600 text-white">
              <Newspaper className="h-5 w-5" />
            </div>
            <h1 className="text-4xl font-black text-slate-950">Travel Blog</h1>
            <p className="mt-3 text-slate-700">Practical notes for sustainable trips, climate-aware planning, and better traveler support.</p>
          </div>
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        {staticPosts.map((post) => (
          <article key={post.id} className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            {post.imageUrl && <img src={post.imageUrl} alt="" className="aspect-video w-full object-cover" />}
            <div className="p-6">
              <p className="text-xs font-bold uppercase tracking-widest text-emerald-700">{post.userName || 'NovaPlan.ai'}</p>
              <h2 className="mt-2 text-xl font-bold text-slate-950">{post.title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">{post.content}</p>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
