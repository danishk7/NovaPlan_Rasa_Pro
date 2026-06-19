interface Props {
  onSelect: (value: string) => void;
}

const suggestions = ['Book a flight', 'Find hotels', 'Plan a 3 day trip', 'Carbon footprint'];

export default function QuickReplies({ onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-white px-4 py-3">
      {suggestions.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onSelect(item)}
          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-700 transition hover:border-emerald-500 hover:text-emerald-800"
        >
          {item}
        </button>
      ))}
    </div>
  );
}
