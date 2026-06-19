import { Mic } from 'lucide-react';

interface Props {
  onVoice: () => void;
  listening: boolean;
}

export default function VoiceInput({ onVoice, listening }: Props) {
  return (
    <button
      type="button"
      onClick={onVoice}
      aria-label={listening ? 'Listening' : 'Start voice input'}
      className={`inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border transition ${
        listening
          ? 'border-emerald-300 bg-emerald-400/20 text-emerald-200'
          : 'border-white/10 bg-white/[0.04] text-slate-200 hover:border-emerald-400'
      }`}
    >
      <Mic className="h-5 w-5" />
    </button>
  );
}
