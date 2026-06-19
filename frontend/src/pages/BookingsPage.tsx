import { useEffect, useState } from 'react';
import { FileDown, RefreshCw } from 'lucide-react';
import UserPortalLayout from '../components/layout/UserPortalLayout';
import { getItineraries } from '../lib/api';
import { bookingFromItinerary, openBookingTicket } from '../lib/bookings';
import { useAuth } from '../hooks/useAuth';
import type { Itinerary } from '../types/chat';

export default function BookingsPage() {
  const { profile } = useAuth();
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadBookings = async () => {
    if (!profile?.userId) return;
    setLoading(true);
    setError('');
    try {
      setItineraries(await getItineraries(profile.userId));
    } catch (err) {
      setItineraries([]);
      setError(err instanceof Error ? err.message : 'Unable to load bookings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadBookings();
  }, [profile?.userId]);

  return (
    <UserPortalLayout>
      <section className="p-8">
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">Bookings</p>
            <h1 className="mt-2 text-4xl font-black">Saved itineraries</h1>
          </div>
          <button onClick={loadBookings} className="inline-flex w-fit items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:border-emerald-500 hover:text-emerald-800">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {error && <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
        {loading && <p className="mb-4 text-sm font-semibold text-emerald-700">Loading bookings...</p>}

        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-[980px] w-full border-collapse text-left text-sm">
            <thead className="bg-emerald-50 text-xs font-black uppercase tracking-widest text-emerald-900">
              <tr>
                <th className="border-b border-slate-200 px-4 py-3">Book Ref.</th>
                <th className="border-b border-slate-200 px-4 py-3">Origin</th>
                <th className="border-b border-slate-200 px-4 py-3">Destination</th>
                <th className="border-b border-slate-200 px-4 py-3">Travel Dates</th>
                <th className="border-b border-slate-200 px-4 py-3">Passengers</th>
                <th className="border-b border-slate-200 px-4 py-3">Mode</th>
                <th className="border-b border-slate-200 px-4 py-3">Carbon</th>
                <th className="border-b border-slate-200 px-4 py-3">Total Price</th>
                <th className="border-b border-slate-200 px-4 py-3 text-right">View / Download</th>
              </tr>
            </thead>
            <tbody>
              {itineraries.map((item) => {
                const booking = bookingFromItinerary(item);
                return (
                  <tr key={item.itnId} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-3 font-bold text-slate-950">{booking.ref}</td>
                    <td className="px-4 py-3 text-slate-700">{booking.origin}</td>
                    <td className="px-4 py-3 text-slate-700">{booking.destination}</td>
                    <td className="px-4 py-3 text-slate-700">{booking.travelDates}</td>
                    <td className="px-4 py-3 text-slate-700">{booking.passengers}</td>
                    <td className="px-4 py-3 text-slate-700">{booking.mode}</td>
                    <td className="px-4 py-3 text-slate-700">{booking.carbon}</td>
                    <td className="px-4 py-3 text-slate-700">{booking.totalPrice}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => openBookingTicket(booking)}
                        className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 px-3 py-2 text-xs font-bold text-emerald-800 transition hover:bg-emerald-50"
                      >
                        <FileDown className="h-4 w-4" />
                        View / Download
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!loading && !error && itineraries.length === 0 && (
            <div className="p-6 text-sm text-slate-600">
              No saved itineraries found yet. Confirmed trips will appear here once the backend saves them to the database.
            </div>
          )}
        </div>
      </section>
    </UserPortalLayout>
  );
}
