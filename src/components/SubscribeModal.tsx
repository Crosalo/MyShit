import { X, Check, Sparkles } from 'lucide-react';
import type { Creator } from '../types';

interface SubscribeModalProps {
  creator: Creator;
  onClose: () => void;
  onSubscribe: (tierId: string) => void;
}

const tierColors: Record<string, string> = {
  gray:   'border-gray-600 bg-gray-800/50',
  purple: 'border-brand-500/50 bg-brand-500/10',
  pink:   'border-pink-500/50 bg-pink-500/10',
  amber:  'border-amber-500/50 bg-amber-500/10',
  orange: 'border-orange-500/50 bg-orange-500/10',
  red:    'border-red-500/50 bg-red-500/10',
  yellow: 'border-yellow-500/50 bg-yellow-500/10',
  teal:   'border-teal-500/50 bg-teal-500/10',
  indigo: 'border-indigo-500/50 bg-indigo-500/10',
  violet: 'border-violet-500/50 bg-violet-500/10',
};

const tierBadgeColors: Record<string, string> = {
  gray:   'bg-gray-700 text-gray-300',
  purple: 'bg-brand-500/20 text-brand-400',
  pink:   'bg-pink-500/20 text-pink-400',
  amber:  'bg-amber-500/20 text-amber-400',
  orange: 'bg-orange-500/20 text-orange-400',
  red:    'bg-red-500/20 text-red-400',
  yellow: 'bg-yellow-500/20 text-yellow-400',
  teal:   'bg-teal-500/20 text-teal-400',
  indigo: 'bg-indigo-500/20 text-indigo-400',
  violet: 'bg-violet-500/20 text-violet-400',
};

export default function SubscribeModal({ creator, onClose, onSubscribe }: SubscribeModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg glass rounded-3xl overflow-hidden animate-in slide-in-from-bottom-4">
        {/* Header */}
        <div className="relative h-24 overflow-hidden">
          <img src={creator.coverImage} alt="" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-gray-900 to-transparent" />
          <button
            onClick={onClose}
            className="absolute top-3 right-3 w-8 h-8 bg-black/40 rounded-full flex items-center justify-center hover:bg-black/60 transition-colors"
          >
            <X className="w-4 h-4 text-white" />
          </button>
          <div className="absolute bottom-3 left-4 flex items-center gap-3">
            <img src={creator.avatar} alt={creator.name} className="w-10 h-10 rounded-xl border-2 border-gray-900 bg-gray-800" />
            <div>
              <p className="font-bold text-white text-sm">{creator.name}</p>
              <p className="text-gray-400 text-xs">@{creator.username}</p>
            </div>
          </div>
        </div>

        <div className="p-4">
          <h2 className="font-bold text-white text-lg mb-1">Wähle dein Tier</h2>
          <p className="text-gray-400 text-sm mb-4">Unterstütze {creator.name} und bekomme exklusiven Content</p>

          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {creator.tiers.map(tier => (
              <div
                key={tier.id}
                className={`relative border rounded-2xl p-4 cursor-pointer transition-all duration-200 hover:scale-[1.01] ${tierColors[tier.color] ?? tierColors.gray}`}
                onClick={() => {
                  onSubscribe(tier.id);
                  onClose();
                }}
              >
                {tier.popular && (
                  <div className="absolute -top-2.5 left-4 flex items-center gap-1 gradient-brand text-white text-xs font-bold px-3 py-0.5 rounded-full">
                    <Sparkles className="w-3 h-3" />
                    Beliebt
                  </div>
                )}

                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${tierBadgeColors[tier.color] ?? tierBadgeColors.gray}`}>
                        {tier.name}
                      </span>
                    </div>
                    <p className="text-gray-400 text-xs">{tier.description}</p>
                  </div>
                  <div className="text-right shrink-0">
                    {tier.price === 0 ? (
                      <span className="font-bold text-white text-lg">Gratis</span>
                    ) : (
                      <>
                        <span className="font-bold text-white text-lg">{tier.price}€</span>
                        <span className="text-gray-500 text-xs">/Monat</span>
                      </>
                    )}
                  </div>
                </div>

                <ul className="space-y-1.5">
                  {tier.perks.map(perk => (
                    <li key={perk} className="flex items-start gap-2 text-xs text-gray-300">
                      <Check className="w-3.5 h-3.5 text-green-400 mt-0.5 shrink-0" />
                      {perk}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
