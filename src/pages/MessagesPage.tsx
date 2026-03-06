import { MessageCircle, Search } from 'lucide-react';
import { useState } from 'react';
import { MESSAGES } from '../data/mockData';

const MOCK_CHAT = [
  { id: 1, from: 'creator', text: 'Hey! Danke für dein Geschenk, die Kerzen riechen wunderschön! 🕯️', time: '10:30' },
  { id: 2, from: 'me', text: 'So froh dass du sie magst! Du hast sofort an Vanille gedacht 😊', time: '10:32' },
  { id: 3, from: 'creator', text: 'Haha ja, wie hast du das gewusst? 😂 Ich zeig sie morgen im Video!', time: '10:33' },
  { id: 4, from: 'me', text: 'Ich freue mich schon so drauf! 🙌', time: '10:34' },
  { id: 5, from: 'creator', text: 'Danke für dein Geschenk, die Kerzen riechen so wunderschön 🕯️', time: '10:34' },
];

export default function MessagesPage() {
  const [activeChat, setActiveChat] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState('');

  const activeMessage = MESSAGES.find(m => m.id === activeChat);

  if (activeChat && activeMessage) {
    return (
      <div className="max-w-2xl mx-auto flex flex-col h-[calc(100vh-120px)]">
        {/* Chat header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10 glass sticky top-16">
          <button onClick={() => setActiveChat(null)} className="text-gray-400 hover:text-white text-sm">
            ← Zurück
          </button>
          <img src={activeMessage.fromAvatar} alt="" className="w-9 h-9 rounded-xl bg-gray-800" />
          <div>
            <p className="font-semibold text-white text-sm">{activeMessage.fromName}</p>
            <p className="text-xs text-green-400">Online</p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {MOCK_CHAT.map(msg => (
            <div key={msg.id} className={`flex ${msg.from === 'me' ? 'justify-end' : 'justify-start'}`}>
              {msg.from === 'creator' && (
                <img src={activeMessage.fromAvatar} alt="" className="w-7 h-7 rounded-lg bg-gray-800 mr-2 mt-1 shrink-0" />
              )}
              <div
                className={`max-w-[70%] px-4 py-2.5 rounded-2xl text-sm ${
                  msg.from === 'me'
                    ? 'gradient-brand text-white rounded-br-sm'
                    : 'bg-white/10 text-white rounded-bl-sm'
                }`}
              >
                {msg.text}
                <div className={`text-[10px] mt-1 ${msg.from === 'me' ? 'text-white/60' : 'text-gray-500'}`}>
                  {msg.time}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-white/10">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Nachricht schreiben..."
              value={newMessage}
              onChange={e => setNewMessage(e.target.value)}
              className="flex-1 bg-white/5 border border-white/10 rounded-2xl px-4 py-2.5 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-brand-500/50 transition-colors"
            />
            <button
              className={`px-4 py-2.5 rounded-2xl font-medium text-sm transition-all duration-200 ${
                newMessage.trim() ? 'gradient-brand text-white' : 'bg-white/5 text-gray-600'
              }`}
              onClick={() => setNewMessage('')}
            >
              Senden
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-black text-white mb-5">Nachrichten</h1>

      {/* Search */}
      <div className="relative mb-5">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder="Chats durchsuchen..."
          className="w-full bg-white/5 border border-white/10 rounded-2xl pl-11 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-brand-500/50 transition-colors"
        />
      </div>

      {MESSAGES.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Noch keine Nachrichten</p>
          <p className="text-sm mt-1">Abonniere Creators um mit ihnen zu chatten</p>
        </div>
      ) : (
        <div className="space-y-2">
          {MESSAGES.map(msg => (
            <button
              key={msg.id}
              onClick={() => setActiveChat(msg.id)}
              className="w-full flex items-center gap-3 p-4 glass rounded-2xl hover:bg-white/5 transition-colors text-left"
            >
              <div className="relative shrink-0">
                <img src={msg.fromAvatar} alt="" className="w-12 h-12 rounded-2xl bg-gray-800" />
                {msg.isCreator && (
                  <span className="absolute -bottom-1 -right-1 w-4 h-4 gradient-brand rounded-full flex items-center justify-center">
                    <span className="text-white text-[8px] font-bold">★</span>
                  </span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="font-semibold text-white text-sm">{msg.fromName}</span>
                  <span className="text-gray-500 text-xs">{msg.timestamp}</span>
                </div>
                <p className="text-gray-400 text-sm truncate">{msg.preview}</p>
              </div>
              {msg.unread > 0 && (
                <div className="w-5 h-5 gradient-brand rounded-full flex items-center justify-center shrink-0">
                  <span className="text-white text-[10px] font-bold">{msg.unread}</span>
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
