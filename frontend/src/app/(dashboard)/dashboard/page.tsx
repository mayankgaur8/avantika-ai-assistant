"use client";

import { useQuery } from "@tanstack/react-query";
import { languageApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";
import { BookOpen, Globe, MapPin, Briefcase, TrendingUp, Zap } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuthStore();

  const { data: progress } = useQuery({
    queryKey: ["progress"],
    queryFn: () => languageApi.progress().then((r) => r.data),
  });

  const quickActions = [
    { href: "/dashboard/translate", label: "Quick Translate", icon: Globe, color: "bg-blue-500" },
    { href: "/dashboard/learn", label: "Start a Lesson", icon: BookOpen, color: "bg-purple-500" },
    { href: "/dashboard/travel", label: "Travel Scenario", icon: MapPin, color: "bg-orange-500" },
    { href: "/dashboard/coach", label: "Job Coaching", icon: Briefcase, color: "bg-green-500" },
  ];

  return (
    <div className="p-8">
      {/* Welcome */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.name?.split(" ")[0]}!
        </h1>
        <p className="text-gray-500 mt-1">What would you like to practice today?</p>
      </div>

      {/* Stats */}
      {progress && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Lessons Completed" value={progress.lessons_completed} icon={BookOpen} />
          <StatCard label="Total Lessons" value={progress.lessons_total} icon={TrendingUp} />
          <StatCard label="Translations" value={progress.translations_total} icon={Globe} />
          <StatCard label="Coaching Sessions" value={progress.coaching_sessions_total} icon={Briefcase} />
        </div>
      )}

      {/* Usage bar */}
      {progress && (
        <div className="card mb-8">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-brand-500" />
              <span className="font-semibold text-gray-900 text-sm">Monthly Usage</span>
            </div>
            <Link href="/pricing" className="text-xs text-brand-600 hover:underline font-medium">
              Upgrade Plan
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex-1 bg-gray-100 rounded-full h-2">
              <div
                className="bg-brand-500 h-2 rounded-full transition-all"
                style={{ width: `${Math.min((progress.monthly_requests_used / 20) * 100, 100)}%` }}
              />
            </div>
            <span className="text-sm text-gray-600 whitespace-nowrap">
              {progress.monthly_requests_used} / 20 requests
            </span>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Link
              key={action.href}
              href={action.href}
              className="card hover:shadow-md transition-all hover:-translate-y-0.5 cursor-pointer"
            >
              <div className={`${action.color} w-10 h-10 rounded-lg flex items-center justify-center mb-3`}>
                <Icon className="h-5 w-5 text-white" />
              </div>
              <p className="font-semibold text-gray-900 text-sm">{action.label}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon }: { label: string; value: number; icon: any }) {
  return (
    <div className="card">
      <Icon className="h-5 w-5 text-brand-500 mb-2" />
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}
