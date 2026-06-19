import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CloudSun, Gauge, MapPin, Plane, Save, User, Wind } from 'lucide-react';
import UserPortalLayout from '../components/layout/UserPortalLayout';
import { updateProfile } from '../lib/api';
import { getClimateSnapshot, type ClimateSnapshot } from '../lib/climate';
import { useAuth } from '../hooks/useAuth';

const packages = [
  {
    title: 'Lisbon Low-Impact Escape',
    price: 'EUR 1,240',
    image: 'https://images.unsplash.com/photo-1500375592092-40eb2168fd21?auto=format&fit=crop&q=80&w=900',
    text: 'Walkable districts, rail day trips, and boutique eco stays.',
  },
  {
    title: 'Kyoto Culture Route',
    price: 'EUR 1,880',
    image: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&q=80&w=900',
    text: 'Temple mornings, seasonal gardens, and slower neighborhood planning.',
  },
  {
    title: 'Vancouver Nature Week',
    price: 'EUR 1,560',
    image: 'https://images.unsplash.com/photo-1505820013142-f86a3439c5b2?auto=format&fit=crop&q=80&w=900',
    text: 'Transit-friendly city base with mountain and coastal excursions.',
  },
];

export default function Dashboard() {
  const { profile, updateProfile: updateLocalProfile } = useAuth();
  const [location, setLocation] = useState(profile?.location || 'Berlin');
  const [profileForm, setProfileForm] = useState({
    name: profile?.name || '',
    bio: profile?.bio || '',
    location: profile?.location || 'Berlin',
    loyaltyTier: profile?.loyaltyTier || '',
  });
  const [snapshot, setSnapshot] = useState<ClimateSnapshot | null>(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    void loadClimate(location);
  }, []);

  const loadClimate = async (value: string) => {
    setStatus('Loading climate data...');
    try {
      const next = await getClimateSnapshot(value);
      setSnapshot(next);
      setStatus('');
      if (profile?.userId && value !== profile.location) {
        updateProfile(profile.userId, { location: value }).catch(() => undefined);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to load climate data');
    }
  };

  const saveProfile = async () => {
    if (!profile?.userId) return;
    setStatus('Saving profile...');
    try {
      await updateProfile(profile.userId, profileForm);
      updateLocalProfile(profileForm);
      setLocation(profileForm.location);
      await loadClimate(profileForm.location);
      setStatus('Profile saved.');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to save profile');
    }
  };

  return (
    <UserPortalLayout>
      <div className="p-8">
        <section className="grid gap-6 xl:grid-cols-[1fr_360px]">
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">Traveler Dashboard</p>
            <h1 className="mt-3 text-4xl font-black text-slate-950">Welcome Back "{profile?.name || 'Traveler'}"</h1>
            <p className="mt-3 max-w-2xl text-slate-600"><b>NovaPlan.ai your sustainable travel partner.</b></p>
            <p className="mt-3 max-w-2xl text-slate-600"><i>Important Note: For all the travellers kindly review  your travel conditions, nearest airport, and suggested packages before continuing to the planner.</i></p>
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Metric icon={MapPin} label="Location" value={snapshot?.location || location} />
              <Metric icon={CloudSun} label="Weather" value={snapshot ? `${snapshot.temperature} C` : 'Loading'} />
              <Metric icon={Gauge} label="Air Quality" value={snapshot?.airQualityIndex ? `AQI ${snapshot.airQualityIndex}` : 'Pending'} />
              <Metric icon={Wind} label="Wind" value={snapshot ? `${snapshot.windSpeed} km/h` : 'Loading'} />
            </div>

            <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-5">
              <div className="flex items-center gap-3">
                <Plane className="h-6 w-6 text-emerald-700" />
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Nearest airport estimate</p>
                  <h2 className="text-2xl font-black text-slate-950">{snapshot ? `${snapshot.airport.code} - ${snapshot.airport.name}` : 'Loading airport'}</h2>
                </div>
              </div>
              {snapshot && (
                <p className="mt-4 text-sm leading-6 text-slate-600">
                  {snapshot.airport.city} is approximately {snapshot.airport.distanceKm} km from the selected customer location. PM2.5 is {snapshot.particulateMatter ?? 'not available'} ug/m3.
                </p>
              )}
            </div>
          </div>

          <aside className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center gap-3">
              <User className="h-6 w-6 text-emerald-700" />
              <div>
                <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">Profile</p>
                <h2 className="text-xl font-black text-slate-950">My Profile</h2>
              </div>
            </div>
            <div className="space-y-3">
              <input value={profileForm.name} onChange={(event) => setProfileForm({ ...profileForm, name: event.target.value })} placeholder="Name" className={fieldClass} />
              <input value={profile?.email || ''} disabled className={`${fieldClass} opacity-60`} />
              <input value={profileForm.location} onChange={(event) => setProfileForm({ ...profileForm, location: event.target.value })} placeholder="Location" className={fieldClass} />
              <input value={profileForm.loyaltyTier} disabled onChange={(event) => setProfileForm({ ...profileForm, loyaltyTier: event.target.value })} placeholder="Loyalty tier" className={fieldClass} />
              <textarea value={profileForm.bio} onChange={(event) => setProfileForm({ ...profileForm, bio: event.target.value })} placeholder="Bio" rows={4} className={fieldClass} />
              <button onClick={saveProfile} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-white hover:bg-emerald-700">
                <Save className="h-4 w-4" />
                Save Profile
              </button>
              {status && <p className="mt-4 text-sm font-semibold text-emerald-700">{status}</p>}
            </div>
          </aside>
        </section>

        <section className="mt-6">
          <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
            <div>
              <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">Explore</p>
              <h2 className="text-3xl font-black text-slate-950">Offers and travel packages</h2>
            </div>
            <Link to="/planner" className="w-fit rounded-lg border border-emerald-200 px-4 py-2 text-sm font-bold text-emerald-800 hover:bg-emerald-50">
              Open Planner
            </Link>
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            {packages.map((item) => (
              <article key={item.title} className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
                <img src={item.image} alt="" className="aspect-[4/3] w-full object-cover" />
                <div className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <h3 className="text-lg font-black">{item.title}</h3>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-800">{item.price}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{item.text}</p>
                  <Link to="/planner" className="mt-4 inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700">
                    Plan This
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </UserPortalLayout>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof MapPin; label: string; value: string }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <Icon className="mb-3 h-5 w-5 text-emerald-700" />
      <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-black text-slate-950">{value}</p>
    </article>
  );
}

const fieldClass = 'w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none placeholder:text-slate-400 focus:border-emerald-500';
