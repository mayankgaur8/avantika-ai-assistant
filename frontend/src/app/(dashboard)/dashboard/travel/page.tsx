"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { languageApi } from "@/lib/api";
import { usePreferences } from "@/lib/store";
import { LANGUAGES, SCENARIO_TYPES } from "@/lib/utils";
import { MapPin, AlertTriangle } from "lucide-react";

export default function TravelPage() {
  const { sourceLanguage, targetLanguage, setSourceLanguage, setTargetLanguage } = usePreferences();
  const [destinationCountry, setDestinationCountry] = useState("");
  const [scenarioType, setScenarioType] = useState(SCENARIO_TYPES[0].value);

  const mutation = useMutation({
    mutationFn: () =>
      languageApi.travelScenario({
        destination_country: destinationCountry,
        source_language: sourceLanguage,
        target_language: targetLanguage,
        scenario_type: scenarioType,
      }).then((r) => r.data),
    onSuccess: () => toast.success("Travel scenario ready!"),
    onError: (err: any) => toast.error(err.response?.data?.detail || "Failed. Check your plan."),
  });

  const data = mutation.data?.data;

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="section-title mb-2">Travel Scenarios</h1>
      <p className="text-gray-500 text-sm mb-8">Practice real conversations for your destination — airport, hotel, restaurant, emergencies.</p>

      <div className="card mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">My Language</label>
            <select value={sourceLanguage} onChange={(e) => setSourceLanguage(e.target.value)} className="input-field">
              {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Language There</label>
            <select value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)} className="input-field">
              {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Destination Country</label>
            <input value={destinationCountry} onChange={(e) => setDestinationCountry(e.target.value)}
              placeholder="Germany, Japan, UAE..." className="input-field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Scenario</label>
            <select value={scenarioType} onChange={(e) => setScenarioType(e.target.value)} className="input-field">
              {SCENARIO_TYPES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={() => mutation.mutate()}
          disabled={!destinationCountry.trim() || mutation.isPending}
          className="btn-primary"
        >
          {mutation.isPending ? "Preparing scenario..." : "Generate Travel Scenario"}
        </button>
      </div>

      {data && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <MapPin className="h-6 w-6 text-orange-500" />
            <div>
              <h2 className="text-xl font-bold text-gray-900">{data.scenario_description}</h2>
            </div>
          </div>

          {/* Essential Phrases */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Essential Phrases</h3>
            <div className="space-y-3">
              {data.essential_phrases?.map((p: any, i: number) => (
                <div key={i} className="border border-gray-100 rounded-lg p-3">
                  <p className="font-medium text-brand-700 text-sm">{p.phrase}</p>
                  <p className="text-gray-700 text-sm">{p.translation}</p>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-gray-500 italic text-xs">{p.pronunciation}</span>
                    <span className="text-gray-400 text-xs">{p.when_to_use}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Dialogue */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Role-Play Dialogue</h3>
            <div className="space-y-3">
              {data.dialogue?.map((line: any, i: number) => (
                <div key={i} className={`flex ${line.speaker === "traveler" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-sm rounded-xl px-4 py-2.5 ${line.speaker === "traveler" ? "bg-blue-100" : "bg-gray-100"}`}>
                    <p className="text-xs font-medium text-gray-500 capitalize mb-0.5">{line.speaker}</p>
                    <p className="text-sm text-gray-900 font-medium">{line.text}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{line.translation}</p>
                    {line.note && <p className="text-xs text-amber-600 mt-1 italic">{line.note}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Emergency phrase */}
          {data.emergency_phrase && (
            <div className="card bg-red-50 border-red-200">
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                <h3 className="font-semibold text-red-800 text-sm">Emergency Phrase</h3>
              </div>
              <p className="text-red-700 font-medium">{data.emergency_phrase}</p>
            </div>
          )}

          {/* Etiquette tips */}
          {data.etiquette_tips?.length > 0 && (
            <div className="card bg-green-50 border-green-200">
              <h3 className="font-semibold text-green-800 mb-3">Cultural Etiquette Tips</h3>
              <ul className="space-y-1">
                {data.etiquette_tips.map((tip: string, i: number) => (
                  <li key={i} className="text-sm text-green-700 flex items-start gap-1.5">
                    <span className="text-green-500 mt-0.5">•</span> {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Common mistakes */}
          {data.common_mistakes?.length > 0 && (
            <div className="card bg-amber-50 border-amber-200">
              <h3 className="font-semibold text-amber-800 mb-3">Common Mistakes to Avoid</h3>
              <ul className="space-y-1">
                {data.common_mistakes.map((m: string, i: number) => (
                  <li key={i} className="text-sm text-amber-700 flex items-start gap-1.5">
                    <span className="text-amber-500 mt-0.5">!</span> {m}
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
