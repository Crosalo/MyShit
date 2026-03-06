import { X, Gift, Package, Shield, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import type { Creator, WishlistItem } from '../types';

interface GiftModalProps {
  creator: Creator;
  onClose: () => void;
}

export default function GiftModal({ creator, onClose }: GiftModalProps) {
  const [step, setStep] = useState<'list' | 'message' | 'confirm' | 'sent'>('list');
  const [selected, setSelected] = useState<WishlistItem | null>(null);
  const [message, setMessage] = useState('');
  const [anonymous, setAnonymous] = useState(false);

  const handleSelect = (item: WishlistItem) => {
    setSelected(item);
    setStep('message');
  };

  const handleSend = () => {
    setStep('sent');
  };

  if (step === 'sent') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div className="w-full max-w-sm glass rounded-3xl p-8 text-center">
          <div className="w-20 h-20 rounded-full gradient-brand flex items-center justify-center mx-auto mb-4 glow-purple">
            <Gift className="w-10 h-10 text-white" />
          </div>
          <h2 className="font-bold text-white text-xl mb-2">Geschenk unterwegs! 🎁</h2>
          <p className="text-gray-400 text-sm mb-4">
            Dein Geschenk an <span className="text-brand-400 font-semibold">{creator.name}</span> wurde aufgegeben.
          </p>

          <div className="bg-white/5 rounded-2xl p-4 mb-4 text-left space-y-3">
            <div className="flex items-center gap-3">
              <img src={selected!.image} alt={selected!.name} className="w-12 h-12 rounded-xl object-cover" />
              <div>
                <p className="text-white text-sm font-medium">{selected!.name}</p>
                <p className="text-brand-400 font-bold text-sm">{selected!.price}€</p>
              </div>
            </div>

            <div className="flex items-start gap-2 bg-green-500/10 border border-green-500/20 rounded-xl p-3">
              <Shield className="w-4 h-4 text-green-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-green-400 text-xs font-semibold">Adresse geschützt</p>
                <p className="text-gray-400 text-xs mt-0.5">
                  {creator.name} bekommt das Paket über unser anonymes Weiterleitungssystem.
                  Ihre Privatadresse bleibt zu 100% geheim.
                </p>
              </div>
            </div>

            {anonymous && (
              <p className="text-xs text-gray-500 text-center">Dein Name bleibt ebenfalls anonym</p>
            )}
          </div>

          <p className="text-gray-500 text-xs mb-4">
            {creator.name} kann das Geschenk in einem Video oder Post zeigen – wenn sie möchte!
          </p>

          <button onClick={onClose} className="w-full gradient-brand text-white font-semibold py-3 rounded-2xl">
            Danke!
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md glass rounded-3xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            {step !== 'list' && (
              <button
                onClick={() => setStep(step === 'message' ? 'list' : 'message')}
                className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white"
              >
                ←
              </button>
            )}
            <h2 className="font-bold text-white">
              {step === 'list' && `🎁 Wishlist von ${creator.name}`}
              {step === 'message' && 'Nachricht hinzufügen'}
              {step === 'confirm' && 'Bestätigen'}
            </h2>
          </div>
          <button onClick={onClose} className="w-8 h-8 bg-white/10 rounded-full flex items-center justify-center hover:bg-white/20 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step 1: Wishlist */}
        {step === 'list' && (
          <div className="p-4">
            <div className="flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-2xl p-3 mb-4">
              <Shield className="w-4 h-4 text-blue-400 shrink-0" />
              <p className="text-blue-300 text-xs">
                <strong>Anonym & sicher:</strong> {creator.name} erfährt niemals deine Adresse
                oder die Adresse wohin geliefert werden soll. Wir leiten alles anonym weiter.
              </p>
            </div>

            <div className="space-y-3">
              {creator.giftWishlist.map(item => (
                <button
                  key={item.id}
                  onClick={() => handleSelect(item)}
                  className="w-full flex items-center gap-4 p-3 glass rounded-2xl hover:bg-white/5 transition-colors text-left"
                >
                  <img src={item.image} alt={item.name} className="w-16 h-16 rounded-xl object-cover bg-gray-800 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium text-sm">{item.name}</p>
                    <p className="text-gray-400 text-xs mt-0.5">{item.category}</p>
                    <p className="text-brand-400 font-bold text-sm mt-1">{item.price}€</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
                </button>
              ))}
            </div>

            <div className="mt-4 flex items-center gap-2 text-xs text-gray-500">
              <Package className="w-3.5 h-3.5" />
              <span>Versand über unser anonymes Postfach-Netzwerk</span>
            </div>
          </div>
        )}

        {/* Step 2: Message */}
        {step === 'message' && selected && (
          <div className="p-4 space-y-4">
            {/* Selected item preview */}
            <div className="flex items-center gap-3 bg-white/5 rounded-2xl p-3">
              <img src={selected.image} alt={selected.name} className="w-12 h-12 rounded-xl object-cover" />
              <div>
                <p className="text-white text-sm font-medium">{selected.name}</p>
                <p className="text-brand-400 font-bold text-sm">{selected.price}€</p>
              </div>
            </div>

            {/* Message */}
            <div>
              <label className="text-white text-sm font-semibold block mb-2">
                Nachricht <span className="text-gray-500 font-normal">(optional)</span>
              </label>
              <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder={`Schreib ${creator.name} etwas Nettes...`}
                maxLength={200}
                rows={3}
                className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm placeholder-gray-500 resize-none focus:outline-none focus:border-brand-500/50 transition-colors"
              />
              <p className="text-gray-600 text-xs text-right mt-1">{message.length}/200</p>
            </div>

            {/* Anonymous toggle */}
            <div
              className="flex items-center justify-between p-3 glass rounded-2xl cursor-pointer"
              onClick={() => setAnonymous(!anonymous)}
            >
              <div>
                <p className="text-white text-sm font-medium">Anonym senden</p>
                <p className="text-gray-400 text-xs">Dein Name wird nicht angezeigt</p>
              </div>
              <div className={`w-11 h-6 rounded-full transition-all duration-200 ${anonymous ? 'gradient-brand' : 'bg-gray-700'}`}>
                <div className={`w-5 h-5 bg-white rounded-full mt-0.5 transition-all duration-200 shadow-sm ${anonymous ? 'ml-5.5' : 'ml-0.5'}`} style={{ marginLeft: anonymous ? '22px' : '2px' }} />
              </div>
            </div>

            <button
              onClick={() => setStep('confirm')}
              className="w-full gradient-brand text-white font-semibold py-3 rounded-2xl hover:opacity-90 transition-opacity"
            >
              Weiter zur Bestätigung
            </button>
          </div>
        )}

        {/* Step 3: Confirm */}
        {step === 'confirm' && selected && (
          <div className="p-4 space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Artikel</span>
                <span className="text-white">{selected.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Preis</span>
                <span className="text-white">{selected.price}€</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Versand (anonym)</span>
                <span className="text-white">4.99€</span>
              </div>
              <div className="border-t border-white/10 pt-2 flex justify-between text-sm font-bold">
                <span className="text-white">Gesamt</span>
                <span className="text-brand-400">{(selected.price + 4.99).toFixed(2)}€</span>
              </div>
            </div>

            {message && (
              <div className="bg-white/5 rounded-2xl p-3">
                <p className="text-gray-400 text-xs mb-1">Deine Nachricht:</p>
                <p className="text-white text-sm italic">„{message}"</p>
              </div>
            )}

            <div className="flex items-start gap-2 bg-green-500/10 border border-green-500/20 rounded-2xl p-3">
              <Shield className="w-4 h-4 text-green-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-green-400 text-xs font-semibold mb-0.5">Adress-Schutz aktiv</p>
                <p className="text-gray-400 text-xs">
                  Das Paket wird über unsere anonyme Paketweiterleitungs-Adresse verschickt.
                  {creator.name} sieht nur unsere Adresse, nie deine.
                </p>
              </div>
            </div>

            <button
              onClick={handleSend}
              className="w-full gradient-brand text-white font-semibold py-3 rounded-2xl hover:opacity-90 transition-opacity glow-purple"
            >
              Jetzt senden – {(selected.price + 4.99).toFixed(2)}€
            </button>
            <p className="text-center text-gray-500 text-xs">Sichere Zahlung · Käuferschutz inklusive</p>
          </div>
        )}
      </div>
    </div>
  );
}
