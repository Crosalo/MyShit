import { useParams, Link } from 'react-router-dom';
import { useState } from 'react';
import {
  ArrowLeft, Star, MapPin, Users, CheckCircle2,
  Phone, Gift, MessageCircle, Share2, Grid3x3,
  Play, Volume2, Image, FileText, Wifi, Bell
} from 'lucide-react';
import PostCard from '../components/PostCard';
import SubscribeModal from '../components/SubscribeModal';
import CallModal from '../components/CallModal';
import GiftModal from '../components/GiftModal';
import { CREATORS, POSTS } from '../data/mockData';

interface CreatorProfilePageProps {
  subscribedCreators: string[];
  onSubscribe: (id: string) => void;
  likedPosts: string[];
  onLike: (id: string) => void;
}

const CONTENT_FILTERS = [
  { key: 'all', label: 'Alle', icon: Grid3x3 },
  { key: 'video', label: 'Videos', icon: Play },
  { key: 'audio', label: 'Audio', icon: Volume2 },
  { key: 'photo', label: 'Fotos', icon: Image },
  { key: 'update', label: 'Updates', icon: FileText },
];

export default function CreatorProfilePage({
  subscribedCreators,
  onSubscribe,
  likedPosts,
  onLike,
}: CreatorProfilePageProps) {
  const { id } = useParams<{ id: string }>();
  const [showSubscribe, setShowSubscribe] = useState(false);
  const [showCall, setShowCall] = useState(false);
  const [showGift, setShowGift] = useState(false);
  const [contentFilter, setContentFilter] = useState('all');

  const creator = CREATORS.find(c => c.id === id);
  if (!creator) {
    return (
      <div className="text-center py-20 text-gray-500">
        <p>Creator nicht gefunden</p>
        <Link to="/discover" className="text-brand-400 mt-2 inline-block">Zurück zur Übersicht</Link>
      </div>
    );
  }

  const isSubscribed = subscribedCreators.includes(creator.id);
  const creatorPosts = POSTS.filter(p =>
    p.creatorId === creator.id &&
    (contentFilter === 'all' || p.type === contentFilter)
  );

  return (
    <div className="max-w-2xl mx-auto">
      {/* Cover */}
      <div className="relative h-52 overflow-hidden">
        <img src={creator.coverImage} alt="" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/20 to-transparent" />

        <Link
          to="/discover"
          className="absolute top-4 left-4 w-9 h-9 bg-black/40 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-black/60 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 text-white" />
        </Link>

        <button className="absolute top-4 right-4 w-9 h-9 bg-black/40 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-black/60 transition-colors">
          <Share2 className="w-4 h-4 text-white" />
        </button>
      </div>

      {/* Profile info */}
      <div className="px-4 -mt-16 relative z-10">
        <div className="flex items-end justify-between mb-4">
          <div className="relative">
            <img
              src={creator.avatar}
              alt={creator.name}
              className="w-20 h-20 rounded-2xl border-4 border-gray-950 bg-gray-800"
            />
            {creator.isOnline && (
              <span className="absolute bottom-1 right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-gray-950 online-dot" />
            )}
            {creator.verified && (
              <CheckCircle2 className="absolute -top-2 -right-2 w-6 h-6 text-brand-400 fill-brand-400 bg-gray-950 rounded-full" />
            )}
          </div>

          <div className="flex gap-2">
            {creator.callAvailable && (
              <button
                onClick={() => setShowCall(true)}
                className="flex items-center gap-1.5 bg-green-500/20 border border-green-500/30 text-green-400 px-3 py-2 rounded-xl text-sm font-medium hover:bg-green-500/30 transition-colors"
              >
                <Phone className="w-4 h-4" />
                Call
              </button>
            )}
            <button
              onClick={() => setShowGift(true)}
              className="flex items-center gap-1.5 bg-pink-500/20 border border-pink-500/30 text-pink-400 px-3 py-2 rounded-xl text-sm font-medium hover:bg-pink-500/30 transition-colors"
            >
              <Gift className="w-4 h-4" />
              Gift
            </button>
          </div>
        </div>

        {/* Name & bio */}
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-0.5">
            <h1 className="text-2xl font-black text-white">{creator.name}</h1>
          </div>
          <p className="text-gray-400 text-sm mb-1">@{creator.username}</p>
          <p className="text-gray-300 text-sm leading-relaxed">{creator.bio}</p>
        </div>

        {/* Meta */}
        <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-4">
          <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {creator.location}</span>
          <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {creator.subscriberCount.toLocaleString('de-DE')} Abonnenten</span>
          <span className="flex items-center gap-1"><Star className="w-3 h-3 fill-yellow-400 text-yellow-400" /> {creator.rating}</span>
          <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3" /> Antw. {creator.responseTime}</span>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mb-5">
          {creator.tags.map(tag => (
            <span key={tag} className="text-xs bg-white/5 text-gray-400 px-3 py-1 rounded-full border border-white/5">
              {tag}
            </span>
          ))}
        </div>

        {/* Call availability banner */}
        {creator.callAvailable && creator.nextCallSlot && (
          <div
            onClick={() => setShowCall(true)}
            className="flex items-center gap-3 bg-green-500/10 border border-green-500/20 rounded-2xl px-4 py-3 mb-5 cursor-pointer hover:bg-green-500/15 transition-colors"
          >
            <div className="w-8 h-8 bg-green-500/20 rounded-xl flex items-center justify-center">
              <Wifi className="w-4 h-4 text-green-400" />
            </div>
            <div>
              <p className="text-green-400 font-semibold text-sm">Calls verfügbar</p>
              <p className="text-gray-400 text-xs">Nächster freier Slot: {creator.nextCallSlot}</p>
            </div>
            <div className="ml-auto">
              <span className="text-green-400 text-xs font-medium">Buchen →</span>
            </div>
          </div>
        )}

        {/* Subscribe CTA */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => setShowSubscribe(true)}
            className={`flex-1 py-3 rounded-2xl font-bold text-sm transition-all duration-200 ${
              isSubscribed
                ? 'bg-white/10 text-white hover:bg-white/15'
                : 'gradient-brand text-white hover:opacity-90 glow-purple'
            }`}
          >
            {isSubscribed ? '✓ Abonniert' : 'Abonnieren'}
          </button>
          <button className="w-12 h-12 bg-white/5 border border-white/10 rounded-2xl flex items-center justify-center hover:bg-white/10 transition-colors">
            <Bell className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Tiers preview */}
        {!isSubscribed && (
          <div className="mb-6">
            <h3 className="font-bold text-white text-sm mb-3">Tiers</h3>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {creator.tiers.filter(t => t.price > 0).map(tier => (
                <button
                  key={tier.id}
                  onClick={() => setShowSubscribe(true)}
                  className="shrink-0 glass rounded-2xl p-3 text-left min-w-[140px] hover:bg-white/5 transition-colors"
                >
                  <p className="font-bold text-white text-sm">{tier.name}</p>
                  <p className="text-brand-400 font-bold text-base">{tier.price}€<span className="text-gray-500 text-xs font-normal">/Mo</span></p>
                  <p className="text-gray-500 text-xs mt-1">{tier.perks[0]}</p>
                  {tier.popular && <span className="text-[10px] text-brand-400 font-bold">★ Beliebt</span>}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Content filter */}
      <div className="sticky top-16 z-20 bg-gray-950/80 backdrop-blur-md border-b border-white/5 px-4 py-3">
        <div className="flex gap-2 overflow-x-auto">
          {CONTENT_FILTERS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setContentFilter(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all duration-200 ${
                contentFilter === key
                  ? 'gradient-brand text-white'
                  : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
              }`}
            >
              <Icon className="w-3 h-3" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Posts */}
      <div className="px-4 py-5 space-y-4">
        {creatorPosts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p>Noch keine Posts in dieser Kategorie</p>
          </div>
        ) : (
          creatorPosts.map(post => (
            <PostCard
              key={post.id}
              post={post}
              isLiked={likedPosts.includes(post.id)}
              onLike={onLike}
              isSubscribed={isSubscribed}
            />
          ))
        )}
      </div>

      {/* Modals */}
      {showSubscribe && (
        <SubscribeModal
          creator={creator}
          onClose={() => setShowSubscribe(false)}
          onSubscribe={() => {
            onSubscribe(creator.id);
            setShowSubscribe(false);
          }}
        />
      )}
      {showCall && <CallModal creator={creator} onClose={() => setShowCall(false)} />}
      {showGift && <GiftModal creator={creator} onClose={() => setShowGift(false)} />}
    </div>
  );
}
