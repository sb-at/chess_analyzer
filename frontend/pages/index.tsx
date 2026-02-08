import { useState } from 'react'
import Head from 'next/head'
import AuthModal from '@/components/AuthModal'

export default function Home() {
  const [showAuthModal, setShowAuthModal] = useState(false)

  return (
    <>
      <Head>
        <title>ChessMirror - See Your Chess Blind Spots Clearly</title>
        <meta name="description" content="Analyze patterns across hundreds of your games to reveal habits, blind spots, and recurring mistakes." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
        {/* Navigation */}
        <nav className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <div className="flex justify-between items-center">
              <div className="text-2xl font-bold text-blue-600">ChessMirror</div>
              <button
                onClick={() => setShowAuthModal(true)}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
              >
                Sign In
              </button>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-20">
          <div className="container mx-auto px-4">
            <div className="max-w-3xl mx-auto text-center">
              <h1 className="text-5xl font-bold mb-6">
                See Your Chess Blind Spots Clearly
              </h1>
              <p className="text-xl mb-8 text-blue-100">
                Analyze patterns across hundreds of your games to reveal habits,
                blind spots, and recurring mistakes. Get personalized insights
                that actually improve your game.
              </p>
              <button
                onClick={() => setShowAuthModal(true)}
                className="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition shadow-lg"
              >
                Start Free Analysis
              </button>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <FeatureCard
                number="1"
                title="Connect Your Account"
                description="Link your Chess.com or Lichess account in seconds. We'll automatically import your games."
              />
              <FeatureCard
                number="2"
                title="Analyze Patterns"
                description="Our engine analyzes hundreds of games to identify recurring patterns, mistakes, and blind spots."
              />
              <FeatureCard
                number="3"
                title="Get Better"
                description="Receive personalized recommendations and track your improvement over time."
              />
            </div>
          </div>
        </section>

        {/* Sample Insights Section */}
        <section className="py-16 bg-white">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center mb-12">Sample Insights</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <InsightCard
                title="Missed Tactics"
                description="You miss forks in 23% of tactical positions"
                severity={0.8}
                color="red"
              />
              <InsightCard
                title="Time Pressure"
                description="Accuracy drops 15% when under 60 seconds"
                severity={0.6}
                color="yellow"
              />
              <InsightCard
                title="Opening Choice"
                description="Your Caro-Kann has a 35% win rate"
                severity={0.4}
                color="blue"
              />
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="bg-blue-600 text-white py-16">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl font-bold mb-4">Ready to See Your Blind Spots?</h2>
            <p className="text-xl mb-8 text-blue-100">
              Join thousands of players improving their game with ChessMirror
            </p>
            <button
              onClick={() => setShowAuthModal(true)}
              className="bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-gray-100 transition shadow-lg"
            >
              Get Started Free
            </button>
          </div>
        </section>

        {/* Footer */}
        <footer className="bg-gray-900 text-gray-400 py-8">
          <div className="container mx-auto px-4 text-center">
            <p>&copy; 2024 ChessMirror. All rights reserved.</p>
          </div>
        </footer>

        {/* Auth Modal */}
        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
        />
      </main>
    </>
  )
}

function FeatureCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
        {number}
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}

function InsightCard({ title, description, severity, color }: { title: string; description: string; severity: number; color: string }) {
  const colorClasses = {
    red: 'bg-red-100 border-red-500',
    yellow: 'bg-yellow-100 border-yellow-500',
    blue: 'bg-blue-100 border-blue-500'
  }

  const badgeClasses = {
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
    blue: 'bg-blue-500'
  }

  const severityLabel = severity > 0.7 ? 'High' : severity > 0.4 ? 'Medium' : 'Low'

  return (
    <div className={`border-2 rounded-lg p-6 ${colorClasses[color as keyof typeof colorClasses]}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">{title}</h3>
        <span className={`${badgeClasses[color as keyof typeof badgeClasses]} text-white px-3 py-1 rounded-full text-xs font-semibold`}>
          {severityLabel}
        </span>
      </div>
      <p className="text-gray-700">{description}</p>
    </div>
  )
}
