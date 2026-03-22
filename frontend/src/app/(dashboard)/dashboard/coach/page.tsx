"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { languageApi } from "@/lib/api";
import { usePreferences } from "@/lib/store";
import { LANGUAGES, COACHING_TYPES, JOB_FIELDS } from "@/lib/utils";
import { Briefcase, Star } from "lucide-react";

export default function CoachPage() {
  const { sourceLanguage, targetLanguage, setSourceLanguage, setTargetLanguage } = usePreferences();
  const [jobField, setJobField] = useState(JOB_FIELDS[0]);
  const [coachingType, setCoachingType] = useState(COACHING_TYPES[0].value);
  const [userDraft, setUserDraft] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      languageApi.coach({
        job_field: jobField,
        coaching_type: coachingType,
        source_language: sourceLanguage,
        target_language: targetLanguage,
        user_draft: userDraft || undefined,
      }).then((r) => r.data),
    onSuccess: () => toast.success("Coaching ready!"),
    onError: (err: any) => toast.error(err.response?.data?.detail || "Coaching failed. Check your plan."),
  });

  const data = mutation.data?.data;

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="section-title mb-2">Professional Coaching</h1>
      <p className="text-gray-500 text-sm mb-8">Job interviews, emails, presentations — coached in your target language for your industry.</p>

      <div className="card mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">My Language</label>
            <select value={sourceLanguage} onChange={(e) => setSourceLanguage(e.target.value)} className="input-field">
              {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Target Language</label>
            <select value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)} className="input-field">
              {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Job Field</label>
            <select value={jobField} onChange={(e) => setJobField(e.target.value)} className="input-field">
              {JOB_FIELDS.map((f) => <option key={f}>{f}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Coaching Type</label>
            <select value={coachingType} onChange={(e) => setCoachingType(e.target.value)} className="input-field">
              {COACHING_TYPES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
        </div>
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-600 mb-1">Your Draft (optional — paste an email, answer, etc.)</label>
          <textarea value={userDraft} onChange={(e) => setUserDraft(e.target.value)}
            placeholder="Paste your draft text here for feedback..."
            className="input-field h-24 resize-none" />
        </div>
        <button onClick={() => mutation.mutate()} disabled={mutation.isPending} className="btn-primary">
          {mutation.isPending ? "Coaching you..." : "Get Coaching"}
        </button>
      </div>

      {data && (
        <div className="space-y-6">
          {/* Analysis */}
          {(data.analysis?.strengths?.length > 0 || data.analysis?.improvements?.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="card bg-green-50 border-green-200">
                <h3 className="font-semibold text-green-800 mb-3 text-sm">Strengths</h3>
                <ul className="space-y-1">
                  {data.analysis.strengths?.map((s: string, i: number) => (
                    <li key={i} className="text-sm text-green-700 flex items-start gap-1.5">
                      <Star className="h-3.5 w-3.5 mt-0.5 text-green-500 flex-shrink-0" /> {s}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="card bg-orange-50 border-orange-200">
                <h3 className="font-semibold text-orange-800 mb-3 text-sm">Areas to Improve</h3>
                <ul className="space-y-1">
                  {data.analysis.improvements?.map((s: string, i: number) => (
                    <li key={i} className="text-sm text-orange-700 flex items-start gap-1.5">
                      <span className="text-orange-400 mt-0.5">→</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Improved version */}
          {data.improved_version && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-3">Improved Version</h3>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap font-mono">
                {data.improved_version}
              </div>
            </div>
          )}

          {/* Interview Q&A */}
          {data.interview_qa?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">Interview Q&A</h3>
              <div className="space-y-4">
                {data.interview_qa.map((qa: any, i: number) => (
                  <div key={i} className="border border-gray-100 rounded-lg p-4">
                    <p className="font-medium text-gray-900 text-sm mb-2">Q: {qa.question}</p>
                    <p className="text-gray-700 text-sm mb-2">{qa.ideal_answer}</p>
                    <p className="text-xs text-brand-600 italic">{qa.tips}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Professional vocabulary */}
          {data.professional_vocabulary?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">Professional Vocabulary for {jobField}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.professional_vocabulary.map((v: any, i: number) => (
                  <div key={i} className="bg-gray-50 rounded-lg p-3">
                    <span className="font-medium text-brand-700 text-sm">{v.term}</span>
                    <p className="text-xs text-gray-600 mt-0.5">{v.meaning}</p>
                    <p className="text-xs text-gray-500 italic mt-0.5">{v.example}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Confidence tips */}
          {data.confidence_tips?.length > 0 && (
            <div className="card bg-brand-50 border-brand-100">
              <h3 className="font-semibold text-brand-800 mb-3">Confidence Tips</h3>
              <ul className="space-y-1.5">
                {data.confidence_tips.map((tip: string, i: number) => (
                  <li key={i} className="text-sm text-brand-700 flex items-start gap-1.5">
                    <Briefcase className="h-3.5 w-3.5 mt-0.5 text-brand-500 flex-shrink-0" /> {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
