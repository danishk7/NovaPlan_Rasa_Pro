import { useState, type FormEvent } from 'react';
import { Mail } from 'lucide-react';
import { sendContact } from '../lib/api';

const topics = ['Trip Planning', 'Refund', 'Support', 'Partnership', 'Technical Issues'];

export default function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', topic: topics[0], message: '' });
  const [status, setStatus] = useState('');

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus('Sending...');
    try {
      await sendContact(form);
      setStatus('Thanks. Your message has been sent.');
      setForm({ name: '', email: '', topic: topics[0], message: '' });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to send message.');
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-600 text-white">
        <Mail className="h-5 w-5" />
      </div>
      <h1 className="text-4xl font-black text-slate-950">Contact NovaPlan.ai</h1>
      <p className="mt-3 text-slate-600">Send travel, support, or partnership questions to the backend contact queue.</p>
      <form onSubmit={submit} className="mt-8 space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Name" required className={fieldClass} />
        <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email" type="email" required className={fieldClass} />
        <select value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} className={fieldClass}>
          {topics.map((topic) => (
            <option key={topic} value={topic}>
              {topic}
            </option>
          ))}
        </select>
        <textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Message" required rows={5} className={fieldClass} />
        {status && <p className="text-sm text-emerald-700">{status}</p>}
        <button className="rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-white hover:bg-emerald-700">Send Message</button>
      </form>
    </main>
  );
}

const fieldClass = 'w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none placeholder:text-slate-400 focus:border-emerald-500';
