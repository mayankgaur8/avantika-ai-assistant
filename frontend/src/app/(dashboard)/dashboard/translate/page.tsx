"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { languageApi } from "@/lib/api";
import { usePreferences } from "@/lib/store";
import { LANGUAGES } from "@/lib/utils";
import { ArrowLeftRight, Copy, Volume2 } from "lucide-react";

export default function TranslatePage() {
  const { sourceLanguage, targetLanguage, setSourceLanguage, setTargetLanguage } = usePreferences();
  const [inputText, setInputText] = useState("");
  const [contextTone, setContextTone] = useState("neutral");
  const [formality, setFormality] = useState("neutral");

  const mutation = useMutation({
    mutationFn: () =>
      languageApi.translate({
        input_text: inputText,
        source_language: sourceLanguage,
        target_language: targetLanguage,
        context_tone: contextTone,
        formality_level: formality,
      }).then((r) => r.data),
    onError: (err: any) => {
      toast.error(err.response?.data?.detail?.message || "Translation failed");
    },
  });

  const result = mutation.data?.data;

  const handleSwap = () => {
    setSourceLanguage(targetLanguage);
    setTargetLanguage(sourceLanguage);
  };

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="section-title mb-2">Real-Time Translation</h1>
      <p className="text-gray-500 text-sm mb-8">Context-aware translation with pronunciation and cultural notes.</p>

      {/* Language selector */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={sourceLanguage}
          onChange={(e) => setSourceLanguage(e.target.value)}
          className="input-field max-w-[180px]"
        >
          {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
        </select>

        <button onClick={handleSwap} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
          <ArrowLeftRight className="h-5 w-5 text-gray-500" />
        </button>

        <select
          value={targetLanguage}
          onChange={(e) => setTargetLanguage(e.target.value)}
          className="input-field max-w-[180px]"
        >
          {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
        </select>

        <select value={formality} onChange={(e) => setFormality(e.target.value)} className="input-field max-w-[150px]">
          <option value="formal">Formal</option>
          <option value="neutral">Neutral</option>
          <option value="casual">Casual</option>
        </select>
      </div>

      {/* Input area */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600">
            {sourceLanguage}
          </div>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={`Type text in ${sourceLanguage}...`}
            className="w-full p-4 text-sm text-gray-900 resize-none focus:outline-none h-36"
          />
        </div>

        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600 flex items-center justify-between">
            <span>{targetLanguage}</span>
            {result?.primary_translation && (
              <button
                onClick={() => { navigator.clipboard.writeText(result.primary_translation); toast.success("Copied!"); }}
                className="p-1 hover:bg-gray-200 rounded"
              >
                <Copy className="h-3.5 w-3.5 text-gray-500" />
              </button>
            )}
          </div>
          <div className="p-4 h-36 text-sm text-gray-900">
            {mutation.isPending && <span className="text-gray-400 animate-pulse">Translating...</span>}
            {result?.primary_translation && <p>{result.primary_translation}</p>}
          </div>
        </div>
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={!inputText.trim() || mutation.isPending}
        className="btn-primary mb-8"
      >
        {mutation.isPending ? "Translating..." : "Translate"}
      </button>

      {/* Rich result */}
      {result && (
        <div className="space-y-6">
          {/* Pronunciation */}
          {result.pronunciation && (
            <div className="card">
              <div className="flex items-center gap-2 mb-2">
                <Volume2 className="h-4 w-4 text-brand-500" />
                <h3 className="font-semibold text-gray-900 text-sm">Pronunciation</h3>
              </div>
              <p className="text-gray-700 italic">{result.pronunciation}</p>
            </div>
          )}

          {/* Alternatives */}
          {result.alternatives?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 text-sm mb-3">Alternative Phrasings</h3>
              <ul className="space-y-1">
                {result.alternatives.map((alt: string, i: number) => (
                  <li key={i} className="text-sm text-gray-700 pl-3 border-l-2 border-brand-200">{alt}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Vocabulary */}
          {result.vocabulary?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 text-sm mb-3">Key Vocabulary</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {result.vocabulary.map((v: any, i: number) => (
                  <div key={i} className="bg-gray-50 rounded-lg p-3">
                    <span className="font-medium text-brand-700 text-sm">{v.word}</span>
                    <span className="text-gray-500 text-xs ml-2">({v.part_of_speech})</span>
                    <p className="text-sm text-gray-700 mt-0.5">{v.meaning}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cultural note */}
          {result.cultural_note && (
            <div className="card bg-amber-50 border-amber-200">
              <h3 className="font-semibold text-amber-800 text-sm mb-1">Cultural Note</h3>
              <p className="text-sm text-amber-700">{result.cultural_note}</p>
            </div>
          )}

          {/* Usage warning */}
          {result.usage_warning && (
            <div className="card bg-red-50 border-red-200">
              <h3 className="font-semibold text-red-800 text-sm mb-1">Usage Warning</h3>
              <p className="text-sm text-red-700">{result.usage_warning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
