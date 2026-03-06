export type ContentType = 'video' | 'photo' | 'audio' | 'update';
export type SubscriptionTier = 'free' | 'basic' | 'premium' | 'vip';

export interface Creator {
  id: string;
  name: string;
  username: string;
  avatar: string;
  coverImage: string;
  bio: string;
  tagline: string;
  location: string;
  verified: boolean;
  subscriberCount: number;
  postCount: number;
  tags: string[];
  tiers: Tier[];
  rating: number;
  responseTime: string;
  isOnline: boolean;
  callAvailable: boolean;
  nextCallSlot?: string;
  giftWishlist: WishlistItem[];
}

export interface Tier {
  id: string;
  name: string;
  price: number;
  description: string;
  perks: string[];
  color: string;
  popular?: boolean;
}

export interface Post {
  id: string;
  creatorId: string;
  creatorName: string;
  creatorAvatar: string;
  type: ContentType;
  title: string;
  description: string;
  thumbnail: string;
  mediaUrl?: string;
  likes: number;
  comments: number;
  isLiked: boolean;
  tier: SubscriptionTier;
  createdAt: string;
  duration?: string;
  isNew?: boolean;
  emoji?: string;
}

export interface WishlistItem {
  id: string;
  name: string;
  price: number;
  image: string;
  category: string;
}

export interface CallSlot {
  id: string;
  creatorId: string;
  date: string;
  time: string;
  duration: number;
  price: number;
  type: 'audio' | 'video';
  available: boolean;
}

export interface Gift {
  id: string;
  fromUser: string;
  toCreator: string;
  wishlistItemId: string;
  message: string;
  anonymous: boolean;
  sentAt: string;
  status: 'pending' | 'shipped' | 'delivered';
}

export interface Message {
  id: string;
  fromId: string;
  fromName: string;
  fromAvatar: string;
  preview: string;
  timestamp: string;
  unread: number;
  isCreator: boolean;
}
