import { Link } from 'react-router-dom';
import { Settings, Heart, Gift, Phone, Star, Crown, ChevronRight, Users, TrendingUp } from 'lucide-react';
import { CREATORS } from '../data/mockData';

interface ProfilePageProps {
  subscribedCreators: string[];
}

export default function ProfilePage({ subscribedCreators }: ProfilePageProps) {
  const myCreators = CREATORS.filter(c => subscribedCreators.includes(c.id));
  const totalMonthly = myCreators.reduce((sum, c) => {
    const lowestPaid = c.tiers.find(t => t.price > 0);
    return sum + (lowestPaid?.price ?? 0);
  }, 0);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Profile header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-black text-white">Mein Profil</h1>
        <button className="w-9 h-9 glass rounded-xl flex items-center justify-center hover:bg-white/10 transition-colors">
          <Settings className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* User card */}
      <div className="glass rounded-3xl p-5 mb-5">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 rounded-2xl gradient-brand flex items-center justify-center text-2xl font-black text-white">
            M
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Max Mustermann</h2>
            <p className="text-gray-400 text-sm">@maxmustermann</p>
            <div className="flex items-center gap-1 mt-1">
              <Crown className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-amber-400 text-xs font-semibold">Premium Fan</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Friends', value: subscribedCreators.length, icon: Users },
            { label: 'Likes', value: '47', icon: Heart },
            { label: 'Geschenke', value: '3', icon: Gift },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-white/5 rounded-2xl p-3 text-center">
              <Icon className="w-4 h-4 text-brand-400 mx-auto mb-1" />
              <p className="font-bold text-white text-lg">{value}</p>
              <p className="text-gray-500 text-xs">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Subscription summary */}
      <div className="glass rounded-3xl p-5 mb-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white">Meine Abonnements</h3>
          <span className="text-brand-400 text-sm font-semibold">{totalMonthly.toFixed(2)}€/Mo</span>
        </div>

        {myCreators.length === 0 ? (
          <div className="text-center py-6 text-gray-500">
            <p className="text-sm">Noch keine Abonnements</p>
            <Link to="/discover" className="text-brand-400 text-sm mt-1 inline-block">
              Creators entdecken →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {myCreators.map(creator => {
              const lowestPaid = creator.tiers.find(t => t.price > 0);
              return (
                <Link
                  key={creator.id}
                  to={`/creator/${creator.id}`}
                  className="flex items-center gap-3 hover:bg-white/5 rounded-2xl p-2 -mx-2 transition-colors"
                >
                  <div className="relative">
                    <img src={creator.avatar} alt={creator.name} className="w-10 h-10 rounded-xl bg-gray-800" />
                    {creator.isOnline && (
                      <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-950 online-dot" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white text-sm">{creator.name}</p>
                    <p className="text-gray-500 text-xs">{creator.tiers[1]?.name ?? 'Friend'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-brand-400 text-sm font-semibold">{lowestPaid?.price ?? 0}€</p>
                    <p className="text-gray-600 text-xs">pro Monat</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-600" />
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {/* Activity */}
      <div className="glass rounded-3xl p-5 mb-5">
        <h3 className="font-bold text-white mb-4">Aktivität</h3>
        <div className="space-y-3">
          {[
            { icon: Phone, text: 'Call mit Sophie Müller', sub: 'Gestern, 15:00 · 20 Min', color: 'text-green-400' },
            { icon: Gift, text: 'Soy Wax Kerzen Set verschickt', sub: 'vor 3 Tagen · Sophie Müller', color: 'text-pink-400' },
            { icon: Star, text: 'Best Friend Abo gestartet', sub: 'vor 1 Woche · Jonas Weber', color: 'text-amber-400' },
            { icon: TrendingUp, text: 'Feed Aktivität', sub: '47 Likes diese Woche', color: 'text-brand-400' },
          ].map(({ icon: Icon, text, sub, color }) => (
            <div key={text} className="flex items-center gap-3">
              <div className={`w-9 h-9 bg-white/5 rounded-xl flex items-center justify-center ${color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <p className="text-white text-sm font-medium">{text}</p>
                <p className="text-gray-500 text-xs">{sub}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Settings */}
      <div className="glass rounded-3xl overflow-hidden mb-8">
        {[
          { label: 'Zahlungsmethoden', icon: '💳' },
          { label: 'Benachrichtigungen', icon: '🔔' },
          { label: 'Datenschutz', icon: '🔒' },
          { label: 'Hilfe & Support', icon: '💬' },
          { label: 'Creator werden', icon: '✨' },
        ].map((item, i) => (
          <button
            key={item.label}
            className={`w-full flex items-center gap-3 px-5 py-4 hover:bg-white/5 transition-colors text-left ${
              i < 4 ? 'border-b border-white/5' : ''
            }`}
          >
            <span className="text-lg">{item.icon}</span>
            <span className="text-white text-sm font-medium flex-1">{item.label}</span>
            <ChevronRight className="w-4 h-4 text-gray-600" />
          </button>
        ))}
      </div>
    </div>
  );
}
