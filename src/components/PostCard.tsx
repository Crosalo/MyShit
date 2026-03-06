import { Heart, MessageCircle, Play, Volume2, Image, FileText, Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { de } from 'date-fns/locale';
import type { Post } from '../types';

interface PostCardProps {
  post: Post;
  isLiked: boolean;
  onLike: (id: string) => void;
  isSubscribed?: boolean;
}

const typeIcons = {
  video: Play,
  audio: Volume2,
  photo: Image,
  update: FileText,
};

const typeLabels = {
  video: 'Video',
  audio: 'Audio',
  photo: 'Fotos',
  update: 'Update',
};

export default function PostCard({ post, isLiked, onLike, isSubscribed = true }: PostCardProps) {
  const navigate = useNavigate();
  const Icon = typeIcons[post.type];
  const isLocked = !isSubscribed && post.tier !== 'free';

  const timeAgo = formatDistanceToNow(new Date(post.createdAt), {
    addSuffix: true,
    locale: de,
  });

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 pb-3">
        <img
          src={post.creatorAvatar}
          alt={post.creatorName}
          className="w-10 h-10 rounded-xl bg-gray-800 cursor-pointer"
          onClick={() => navigate(`/creator/${post.creatorId}`)}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="font-semibold text-white text-sm cursor-pointer hover:text-brand-400 transition-colors"
              onClick={() => navigate(`/creator/${post.creatorId}`)}
            >
              {post.creatorName}
            </span>
            {post.isNew && (
              <span className="text-[10px] font-bold bg-brand-500/20 text-brand-400 px-1.5 py-0.5 rounded-full">
                NEU
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Icon className="w-3 h-3" />
              {typeLabels[post.type]}
            </span>
            <span>·</span>
            <span>{timeAgo}</span>
          </div>
        </div>
        <span className="text-lg">{post.emoji}</span>
      </div>

      {/* Media */}
      <div className="relative mx-4 rounded-xl overflow-hidden bg-gray-800 aspect-video mb-3">
        <img
          src={post.thumbnail}
          alt={post.title}
          className={`w-full h-full object-cover ${isLocked ? 'blur-md scale-110' : ''}`}
        />

        {/* Play overlay for videos */}
        {!isLocked && post.type === 'video' && (
          <div className="absolute inset-0 flex items-center justify-center">
            <button className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white/30 transition-colors">
              <Play className="w-5 h-5 text-white fill-white ml-0.5" />
            </button>
          </div>
        )}

        {/* Duration badge */}
        {!isLocked && post.duration && (
          <span className="absolute bottom-2 right-2 text-xs bg-black/60 text-white px-2 py-0.5 rounded-md font-medium">
            {post.duration}
          </span>
        )}

        {/* Lock overlay */}
        {isLocked && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <Lock className="w-8 h-8 text-white/70" />
            <p className="text-white/70 text-sm font-medium">Abonnement erforderlich</p>
            <button
              className="gradient-brand text-white text-xs px-4 py-1.5 rounded-full font-semibold"
              onClick={() => navigate(`/creator/${post.creatorId}`)}
            >
              Jetzt abonnieren
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="px-4 pb-3">
        <h3 className="font-semibold text-white text-sm mb-1">{post.title}</h3>
        {!isLocked && (
          <p className="text-gray-400 text-sm leading-relaxed line-clamp-2">{post.description}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4 px-4 pb-4">
        <button
          onClick={() => onLike(post.id)}
          className={`flex items-center gap-1.5 text-sm transition-all duration-200 ${
            isLiked ? 'text-red-400' : 'text-gray-500 hover:text-red-400'
          }`}
        >
          <Heart className={`w-4 h-4 ${isLiked ? 'fill-red-400' : ''}`} />
          <span className="font-medium">{(post.likes + (isLiked ? 1 : 0)).toLocaleString('de-DE')}</span>
        </button>

        <button className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-white transition-colors">
          <MessageCircle className="w-4 h-4" />
          <span className="font-medium">{post.comments}</span>
        </button>
      </div>
    </div>
  );
}
