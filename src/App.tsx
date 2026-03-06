import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import Navbar from './components/Navbar';
import DiscoverPage from './pages/DiscoverPage';
import FeedPage from './pages/FeedPage';
import CreatorProfilePage from './pages/CreatorProfilePage';
import MessagesPage from './pages/MessagesPage';
import ProfilePage from './pages/ProfilePage';

export default function App() {
  const [subscribedCreators, setSubscribedCreators] = useState<string[]>(['c1', 'c4']);
  const [likedPosts, setLikedPosts] = useState<string[]>(['p2', 'p4']);

  const handleSubscribe = (creatorId: string) => {
    setSubscribedCreators(prev =>
      prev.includes(creatorId) ? prev.filter(id => id !== creatorId) : [...prev, creatorId]
    );
  };

  const handleLike = (postId: string) => {
    setLikedPosts(prev =>
      prev.includes(postId) ? prev.filter(id => id !== postId) : [...prev, postId]
    );
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950">
        <Navbar subscribedCount={subscribedCreators.length} />
        <main className="pb-24 md:pb-0">
          <Routes>
            <Route path="/" element={<Navigate to="/discover" replace />} />
            <Route
              path="/discover"
              element={
                <DiscoverPage
                  subscribedCreators={subscribedCreators}
                  onSubscribe={handleSubscribe}
                />
              }
            />
            <Route
              path="/feed"
              element={
                <FeedPage
                  subscribedCreators={subscribedCreators}
                  likedPosts={likedPosts}
                  onLike={handleLike}
                />
              }
            />
            <Route
              path="/creator/:id"
              element={
                <CreatorProfilePage
                  subscribedCreators={subscribedCreators}
                  onSubscribe={handleSubscribe}
                  likedPosts={likedPosts}
                  onLike={handleLike}
                />
              }
            />
            <Route path="/messages" element={<MessagesPage />} />
            <Route path="/profile" element={<ProfilePage subscribedCreators={subscribedCreators} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
