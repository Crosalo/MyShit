import { Link } from 'react-router-dom';
import { LayoutGrid, Sparkles } from 'lucide-react';
import PostCard from '../components/PostCard';
import { POSTS, CREATORS } from '../data/mockData';

interface FeedPageProps {
  subscribedCreators: string[];
  likedPosts: string[];
  onLike: (id: string) => void;
}

export default function FeedPage({ subscribedCreators, likedPosts, onLike }: FeedPageProps) {
  const feedPosts = POSTS.filter(p => subscribedCreators.includes(p.creatorId));
  const allPosts = POSTS;

  const subscribedCreatorData = CREATORS.filter(c => subscribedCreators.includes(c.id));

  if (subscribedCreators.length === 0) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center">
        <div className="w-20 h-20 gradient-brand rounded-3xl flex items-center justify-center mx-auto mb-4">
          <LayoutGrid className="w-10 h-10 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Dein Feed ist leer</h2>
        <p className="text-gray-400 mb-6">Abonniere Creators um ihren Content hier zu sehen</p>
        <Link to="/discover" className="inline-flex items-center gap-2 gradient-brand text-white font-semibold px-6 py-3 rounded-2xl hover:opacity-90 transition-opacity">
          <Sparkles className="w-4 h-4" />
          Creators entdecken
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Stories row */}
      <div className="mb-6">
        <h2 className="font-bold text-white text-base mb-3">Heute aktiv</h2>
        <div className="flex gap-3 overflow-x-auto pb-2">
          {subscribedCreatorData.map(creator => (
            <Link
              key={creator.id}
              to={`/creator/${creator.id}`}
              className="flex flex-col items-center gap-1.5 shrink-0"
            >
              <div className={`relative p-0.5 rounded-2xl ${creator.isOnline ? 'gradient-brand' : 'bg-gray-700'}`}>
                <img
                  src={creator.avatar}
                  alt={creator.name}
                  className="w-14 h-14 rounded-[14px] bg-gray-800 block"
                />
                {creator.isOnline && (
                  <span className="absolute bottom-0.5 right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-gray-950 online-dot" />
                )}
              </div>
              <span className="text-[11px] text-gray-400 font-medium max-w-[56px] truncate text-center">
                {creator.name.split(' ')[0]}
              </span>
            </Link>
          ))}
        </div>
      </div>

      {/* New content alert */}
      {feedPosts.some(p => p.isNew) && (
        <div className="flex items-center gap-2 bg-brand-500/10 border border-brand-500/20 rounded-2xl px-4 py-3 mb-5">
          <Sparkles className="w-4 h-4 text-brand-400" />
          <span className="text-brand-400 text-sm font-medium">
            {feedPosts.filter(p => p.isNew).length} neue Posts von deinen Friends
          </span>
        </div>
      )}

      {/* Posts */}
      <div className="space-y-5">
        {feedPosts.map(post => (
          <PostCard
            key={post.id}
            post={post}
            isLiked={likedPosts.includes(post.id)}
            onLike={onLike}
            isSubscribed={true}
          />
        ))}
      </div>

      {/* Discover more */}
      {allPosts.filter(p => !subscribedCreators.includes(p.creatorId)).length > 0 && (
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-gray-500 text-xs font-medium">Das könnte dir gefallen</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>
          <div className="space-y-5">
            {allPosts
              .filter(p => !subscribedCreators.includes(p.creatorId))
              .slice(0, 3)
              .map(post => (
                <PostCard
                  key={post.id}
                  post={post}
                  isLiked={likedPosts.includes(post.id)}
                  onLike={onLike}
                  isSubscribed={false}
                />
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
