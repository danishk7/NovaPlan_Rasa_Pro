import { ExternalLink } from 'lucide-react';
import { CONFIG } from '../../config/config';

export default function SurveyFeedback() {
  const openSurvey = () => {
    window.open(CONFIG.USER_ACCEPTANCE_SURVEY_URL, '_blank', 'noopener,noreferrer');
  };

  return (
    <section className="mt-3 rounded-lg border border-emerald-200 bg-white p-4 text-xs">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-black text-emerald-900">{'\u2B50'} Help Us Improve NovaPlan.ai</p>
          <p className="mt-1 leading-5 text-slate-600">
            Thank you for using NovaPlan.ai. We would appreciate your feedback through a short 1-minute survey.
          </p>
        </div>
        <button
          type="button"
          onClick={openSurvey}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 font-bold text-white transition hover:bg-emerald-700"
        >
          Provide Feedback
          <ExternalLink size={14} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}
