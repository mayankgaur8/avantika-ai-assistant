"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { languageApi } from "@/lib/api";
import { usePreferences } from "@/lib/store";
import { LANGUAGES, LEVELS } from "@/lib/utils";
import { BookOpen, CheckCircle } from "lucide-react";

export default function LearnPage() {
  const { sourceLanguage, targetLanguage, userLevel, setSourceLanguage, setTargetLanguage, setUserLevel } = usePreferences();
  const [topic, setTopic] = useState("");
  const [sessionNumber, setSessionNumber] = useState(1);

  const mutation = useMutation({
    mutationFn: () =>
      languageApi.learn({
        source_language: sourceLanguage,
        target_language: targetLanguage,
        user_level: userLevel,
        lesson_topic: topic,
        session_number: sessionNumber,
      }).then((r) => r.data),
    onSuccess: () => toast.success("Lesson generated!"),
    onError: (err: any) => toast.error(err.response?.data?.detail?.message || "Lesson generation failed"),
  });

  const lesson = mutation.data?.data;

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="section-title mb-2">Language Lessons</h1>
      <p className="text-gray-500 text-sm mb-8">AI-generated personalized lessons with vocabulary, grammar, dialogue, and exercises.</p>

      {/* Controls */}
      <div className="card mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">My Language</label>
            <select value={sourceLanguage} onChange={(e) => setSourceLanguage(e.target.value)} className="input-field">
              {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Learning</label>
            <select value={targetLanguage} onChange={(e) => setTargetLanguage(e.target.value)} className="input-field">
              {LANGUAGES.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Level</label>
            <select value={userLevel} onChange={(e) => setUserLevel(e.target.value)} className="input-field">
              {LEVELS.map((l) => <option key={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Session #</label>
            <input type="number" min={1} value={sessionNumber} onChange={(e) => setSessionNumber(+e.target.value)}
              className="input-field" />
          </div>
        </div>
        <div className="mb-4">
          <label className="block text-xs font-medium text-gray-600 mb-1">Lesson Topic</label>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Greetings, Numbers, Food, Travel vocabulary..."
            className="input-field"
          />
        </div>
        <button
          onClick={() => mutation.mutate()}
          disabled={!topic.trim() || mutation.isPending}
          className="btn-primary"
        >
          {mutation.isPending ? "Generating lesson..." : "Generate Lesson"}
        </button>
      </div>

      {/* Lesson output */}
      {lesson && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <BookOpen className="h-6 w-6 text-brand-500" />
            <div>
              <h2 className="text-xl font-bold text-gray-900">{lesson.lesson_title}</h2>
              <p className="text-sm text-gray-500">~{lesson.estimated_duration_minutes} minutes</p>
            </div>
          </div>

          {/* Objectives */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-3">Learning Objectives</h3>
            <ul className="space-y-1.5">
              {lesson.objectives?.map((obj: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                  {obj}
                </li>
              ))}
            </ul>
          </div>

          {/* Vocabulary */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Vocabulary</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase border-b border-gray-200">
                    <th className="text-left pb-2 font-medium">Word</th>
                    <th className="text-left pb-2 font-medium">Translation</th>
                    <th className="text-left pb-2 font-medium">Pronunciation</th>
                    <th className="text-left pb-2 font-medium">Example</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {lesson.vocabulary?.map((v: any, i: number) => (
                    <tr key={i}>
                      <td className="py-2.5 font-medium text-brand-700">{v.word}</td>
                      <td className="py-2.5 text-gray-700">{v.translation}</td>
                      <td className="py-2.5 text-gray-500 italic">{v.pronunciation}</td>
                      <td className="py-2.5 text-gray-600">{v.example}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Grammar */}
          {lesson.grammar && (
            <div className="card bg-brand-50 border-brand-100">
              <h3 className="font-semibold text-brand-800 mb-2">Grammar Focus</h3>
              <p className="font-medium text-brand-900 text-sm">{lesson.grammar.rule}</p>
              <p className="text-brand-700 text-sm mt-1">{lesson.grammar.explanation}</p>
              <ul className="mt-3 space-y-1">
                {lesson.grammar.examples?.map((ex: string, i: number) => (
                  <li key={i} className="text-sm text-brand-800 pl-3 border-l-2 border-brand-300">{ex}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Dialogue */}
          {lesson.dialogue?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">Dialogue Practice</h3>
              <div className="space-y-3">
                {lesson.dialogue.map((line: any, i: number) => (
                  <div key={i} className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}>
                    <div className={`max-w-sm rounded-xl px-4 py-2.5 ${i % 2 === 0 ? "bg-gray-100" : "bg-brand-100"}`}>
                      <p className="text-xs font-medium text-gray-500 mb-0.5">{line.speaker}</p>
                      <p className="text-sm text-gray-900 font-medium">{line.text}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{line.translation}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Exercises */}
          {lesson.exercises?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-4">Practice Exercises</h3>
              <div className="space-y-4">
                {lesson.exercises.map((ex: any, i: number) => (
                  <div key={i} className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm font-medium text-gray-900 mb-3">
                      {i + 1}. {ex.question}
                    </p>
                    {ex.options?.map((opt: string, j: number) => (
                      <label key={j} className="flex items-center gap-2 text-sm text-gray-700 mb-1.5 cursor-pointer">
                        <input type="radio" name={`q${i}`} value={opt} className="text-brand-500" />
                        {opt}
                      </label>
                    ))}
                    <details className="mt-2">
                      <summary className="text-xs text-brand-600 cursor-pointer font-medium">Show answer</summary>
                      <p className="text-xs text-green-700 mt-1 font-medium">{ex.answer}</p>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Cultural tip */}
          {lesson.cultural_tip && (
            <div className="card bg-amber-50 border-amber-200">
              <h3 className="font-semibold text-amber-800 mb-1">Cultural Tip</h3>
              <p className="text-sm text-amber-700">{lesson.cultural_tip}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
