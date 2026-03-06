import { useState } from 'react';
import { Search, Sparkles, TrendingUp, Users, Flame } from 'lucide-react';
import CreatorCard from '../components/CreatorCard';
import { CREATORS } from '../data/mockData';

interface DiscoverPageProps {
  subscribedCreators: string[];
  onSubscribe: (id: string) => void;
}

const CATEGORIES = ['Alle', 'Lifestyle', 'Food', 'Musik', 'Wellness', 'Reisen', 'Chat'];

export default function DiscoverPage({ subscribedCreators, onSubscribe }: DiscoverPageProps) {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('Alle');

  const filtered = CREATORS.filter(c => {
    const matchesSearch = search === '' ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.username.toLowerCase().includes(search.toLowerCase()) ||
      c.tags.some(t => t.toLowerCase().includes(search.toLowerCase()));

    const matchesCategory = activeCategory === 'Alle' ||
      c.tags.some(t => t.toLowerCase().includes(activeCategory.toLowerCase()));

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl gradient-brand p-8 mb-8">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-white/80" />
            <span className="text-white/80 text-sm font-medium">Echte Verbindungen</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-white mb-2">
            Deine Freunde,<br />dein Content
          </h1>
          <p className="text-white/80 text-base md:text-lg max-w-md">
            Tägliche Updates, persönliche Calls und echte Nähe –
            ganz ohne unangemessenen Content.
          </p>
        </div>
        {/* Decorative circles */}
        <div className="absolute -right-16 -top-16 w-64 h-64 rounded-full bg-white/10" />
        <div className="absolute -right-8 -bottom-20 w-48 h-48 rounded-full bg-white/5" />
      </div>

      {/* Search */}
      <div className="relative mb-5">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Suche nach Namen, Tags..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-2xl pl-11 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-brand-500/50 transition-colors"
        />
      </div>

      {/* Categories */}
      <div className="flex gap-2 overflow-x-auto pb-3 mb-6 scrollbar-hide">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all duration-200 ${
              activeCategory === cat
                ? 'gradient-brand text-white'
                : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        {[
          { icon: Users, value: '12.4K', label: 'Aktive Creators' },
          { icon: TrendingUp, value: '98K', label: 'Abonnements' },
          { icon: Flame, value: '4.8★', label: 'Ø Bewertung' },
        ].map(({ icon: Icon, value, label }) => (
          <div key={label} className="glass rounded-2xl p-4 text-center">
            <Icon className="w-5 h-5 text-brand-400 mx-auto mb-1" />
            <p className="font-bold text-white text-lg">{value}</p>
            <p className="text-gray-500 text-xs">{label}</p>
          </div>
        ))}
      </div>

      {/* Section title */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-white text-lg">
          {activeCategory === 'Alle' ? 'Alle Creators' : activeCategory}
          <span className="text-gray-500 font-normal text-sm ml-2">({filtered.length})</span>
        </h2>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Search className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Keine Creators gefunden</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map(creator => (
            <CreatorCard
              key={creator.id}
              creator={creator}
              isSubscribed={subscribedCreators.includes(creator.id)}
              onSubscribe={onSubscribe}
            />
          ))}
        </div>
      )}
    </div>
  );
}
