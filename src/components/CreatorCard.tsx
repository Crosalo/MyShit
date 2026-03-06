import { useNavigate } from 'react-router-dom';
import { Star, MapPin, Clock, Users, CheckCircle2, Wifi } from 'lucide-react';
import type { Creator } from '../types';

interface CreatorCardProps {
  creator: Creator;
  isSubscribed: boolean;
  onSubscribe: (id: string) => void;
}

export default function CreatorCard({ creator, isSubscribed, onSubscribe }: CreatorCardProps) {
  const navigate = useNavigate();
  const lowestPaid = creator.tiers.find(t => t.price > 0);

  return (
    <div
      className="glass rounded-2xl overflow-hidden card-hover cursor-pointer group"
      onClick={() => navigate(`/creator/${creator.id}`)}
    >
      {/* Cover */}
      <div className="relative h-32 overflow-hidden">
        <img
          src={creator.coverImage}
          alt="cover"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-900/80 to-transparent" />

        {creator.isOnline && (
          <div className="absolute top-3 right-3 flex items-center gap-1 bg-green-500/20 border border-green-500/40 rounded-full px-2 py-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 online-dot" />
            <span className="text-green-400 text-xs font-medium">Online</span>
          </div>
        )}
      </div>

      {/* Avatar */}
      <div className="px-4 pb-4">
        <div className="flex items-end justify-between -mt-8 mb-3">
          <div className="relative">
            <img
              src={creator.avatar}
              alt={creator.name}
              className="w-16 h-16 rounded-2xl border-2 border-gray-900 bg-gray-800"
            />
            {creator.verified && (
              <CheckCircle2 className="absolute -bottom-1 -right-1 w-5 h-5 text-brand-400 fill-brand-400 bg-gray-900 rounded-full" />
            )}
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onSubscribe(creator.id);
            }}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-all duration-200 ${
              isSubscribed
                ? 'bg-white/10 text-white hover:bg-red-500/20 hover:text-red-400'
                : 'gradient-brand text-white hover:opacity-90 glow-purple'
            }`}
          >
            {isSubscribed ? 'Abonniert ✓' : `Ab ${lowestPaid?.price ?? 0}€/Mo`}
          </button>
        </div>

        <div className="mb-2">
          <h3 className="font-bold text-white text-base leading-tight">{creator.name}</h3>
          <p className="text-gray-400 text-sm">@{creator.username}</p>
        </div>

        <p className="text-gray-300 text-sm leading-relaxed mb-3 line-clamp-2">{creator.tagline}</p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-3">
          {creator.tags.slice(0, 3).map(tag => (
            <span key={tag} className="text-xs bg-white/5 text-gray-400 px-2 py-0.5 rounded-full">
              {tag}
            </span>
          ))}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {creator.subscriberCount.toLocaleString('de-DE')}
          </span>
          <span className="flex items-center gap-1">
            <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
            {creator.rating}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {creator.responseTime}
          </span>
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {creator.location}
          </span>
        </div>

        {/* Call availability */}
        {creator.callAvailable && creator.nextCallSlot && (
          <div className="mt-3 flex items-center gap-2 bg-green-500/10 border border-green-500/20 rounded-xl px-3 py-2">
            <Wifi className="w-3.5 h-3.5 text-green-400" />
            <span className="text-green-400 text-xs font-medium">
              Nächster Call: {creator.nextCallSlot}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
