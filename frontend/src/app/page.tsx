import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-brand-50 to-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold text-brand-600">Avantika</span>
          <span className="text-sm text-gray-500 font-medium">Global Language AI</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/pricing" className="text-sm text-gray-600 hover:text-brand-600 font-medium">Pricing</Link>
          <Link href="/login" className="btn-secondary text-sm py-2 px-4">Sign In</Link>
          <Link href="/register" className="btn-primary text-sm py-2 px-4">Get Started Free</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 py-24 text-center">
        <div className="badge badge-blue mb-6 py-1 px-4 text-sm">
          AI-Powered Language Learning & Translation
        </div>
        <h1 className="text-5xl font-extrabold text-gray-900 leading-tight mb-6">
          Learn Any Language.<br />
          <span className="text-brand-500">Travel Confidently.</span><br />
          Communicate Professionally.
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-10">
          From Hindi to German, Japan to Dubai — Avantika prepares you for every conversation.
          Real-time translation, travel scenarios, job coaching, and structured lessons.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link href="/register" className="btn-primary text-base py-3 px-8">
            Start for Free
          </Link>
          <Link href="/demo" className="btn-secondary text-base py-3 px-8">
            See a Demo
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="card hover:shadow-md transition-shadow">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
              <p className="text-sm text-gray-600">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Use cases */}
      <section className="bg-gray-900 text-white py-20 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Built for Real Life</h2>
          <p className="text-gray-400 mb-12">Every scenario you actually face as a traveler, learner, or professional.</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {USE_CASES.map((u) => (
              <div key={u} className="bg-gray-800 rounded-lg px-5 py-4 text-sm text-gray-300 font-medium">
                {u}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">Start Learning Today</h2>
        <p className="text-gray-500 mb-8">Free plan available. No credit card required.</p>
        <Link href="/register" className="btn-primary text-base py-3 px-10">
          Create Free Account
        </Link>
      </section>
    </main>
  );
}

const FEATURES = [
  {
    icon: "🌍",
    title: "Real-Time Translation",
    description: "Instant, context-aware translation with pronunciation guides and cultural notes.",
  },
  {
    icon: "📚",
    title: "Structured Learning",
    description: "Personalized lessons for beginner to advanced — vocabulary, grammar, dialogue.",
  },
  {
    icon: "✈️",
    title: "Travel Scenarios",
    description: "Airport, hotel, restaurant, emergency — practice real conversations before you land.",
  },
  {
    icon: "💼",
    title: "Job Coaching",
    description: "Interview prep, email writing, presentation skills in any language for your field.",
  },
];

const USE_CASES = [
  "Airport arrival in Germany",
  "Hindi speaker learning French",
  "IT job interview in English",
  "Tokyo restaurant conversation",
  "Dubai business meeting etiquette",
  "Emergency phrases in Japan",
  "Hotel check-in in Spanish",
  "Team email in German",
  "Shopping in South Korea",
];
