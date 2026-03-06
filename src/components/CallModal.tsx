import { X, Phone, Video, Clock, Star, Calendar, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import type { Creator } from '../types';

interface CallModalProps {
  creator: Creator;
  onClose: () => void;
}

const TIME_SLOTS = [
  { time: '14:00', available: true },
  { time: '15:00', available: true },
  { time: '16:00', available: false },
  { time: '17:00', available: true },
  { time: '18:00', available: true },
  { time: '19:00', available: false },
  { time: '20:00', available: true },
];

const DURATIONS = [
  { min: 10, price: 9.99, label: '10 Minuten', popular: false },
  { min: 20, price: 17.99, label: '20 Minuten', popular: true },
  { min: 30, price: 24.99, label: '30 Minuten', popular: false },
];

export default function CallModal({ creator, onClose }: CallModalProps) {
  const [callType, setCallType] = useState<'audio' | 'video'>('audio');
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [selectedDuration, setSelectedDuration] = useState(DURATIONS[1]);
  const [booked, setBooked] = useState(false);

  const handleBook = () => {
    if (!selectedSlot) return;
    setBooked(true);
  };

  if (booked) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div className="w-full max-w-sm glass rounded-3xl p-8 text-center">
          <div className="w-16 h-16 rounded-full gradient-brand flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-white" />
          </div>
          <h2 className="font-bold text-white text-xl mb-2">Call gebucht! 🎉</h2>
          <p className="text-gray-400 text-sm mb-2">
            Dein {callType === 'video' ? 'Video' : 'Audio'} Call mit{' '}
            <span className="text-brand-400 font-semibold">{creator.name}</span>
          </p>
          <div className="bg-white/5 rounded-2xl p-4 mb-6 text-left space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Datum</span>
              <span className="text-white font-medium">Heute</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Uhrzeit</span>
              <span className="text-white font-medium">{selectedSlot} Uhr</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Dauer</span>
              <span className="text-white font-medium">{selectedDuration.label}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Preis</span>
              <span className="text-brand-400 font-bold">{selectedDuration.price}€</span>
            </div>
          </div>
          <p className="text-gray-500 text-xs mb-4">Du bekommst eine Erinnerung 15 Minuten vorher</p>
          <button onClick={onClose} className="w-full gradient-brand text-white font-semibold py-3 rounded-2xl">
            Super, danke!
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
          <div className="flex items-center gap-3">
            <img src={creator.avatar} alt={creator.name} className="w-10 h-10 rounded-xl bg-gray-800" />
            <div>
              <p className="font-bold text-white text-sm">{creator.name}</p>
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                {creator.rating} · Antw. in {creator.responseTime}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 bg-white/10 rounded-full flex items-center justify-center hover:bg-white/20 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Call type */}
          <div>
            <p className="text-white font-semibold text-sm mb-3">Call-Typ</p>
            <div className="grid grid-cols-2 gap-3">
              {(['audio', 'video'] as const).map(type => (
                <button
                  key={type}
                  onClick={() => setCallType(type)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all duration-200 ${
                    callType === type
                      ? 'border-brand-500 bg-brand-500/10 text-brand-400'
                      : 'border-white/10 text-gray-400 hover:border-white/20'
                  }`}
                >
                  {type === 'audio' ? <Phone className="w-6 h-6" /> : <Video className="w-6 h-6" />}
                  <span className="text-sm font-medium capitalize">{type === 'audio' ? 'Audio Call' : 'Video Call'}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Duration */}
          <div>
            <p className="text-white font-semibold text-sm mb-3">Dauer & Preis</p>
            <div className="space-y-2">
              {DURATIONS.map(d => (
                <button
                  key={d.min}
                  onClick={() => setSelectedDuration(d)}
                  className={`w-full flex items-center justify-between p-3 rounded-2xl border transition-all duration-200 ${
                    selectedDuration.min === d.min
                      ? 'border-brand-500 bg-brand-500/10'
                      : 'border-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="text-white text-sm font-medium">{d.label}</span>
                    {d.popular && (
                      <span className="text-[10px] gradient-brand text-white px-2 py-0.5 rounded-full font-bold">Beliebt</span>
                    )}
                  </div>
                  <span className={`font-bold text-sm ${selectedDuration.min === d.min ? 'text-brand-400' : 'text-gray-400'}`}>
                    {d.price}€
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Time slots */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-gray-400" />
              <p className="text-white font-semibold text-sm">Uhrzeit – Heute</p>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {TIME_SLOTS.map(slot => (
                <button
                  key={slot.time}
                  onClick={() => slot.available && setSelectedSlot(slot.time)}
                  disabled={!slot.available}
                  className={`py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                    !slot.available
                      ? 'bg-white/5 text-gray-600 cursor-not-allowed'
                      : selectedSlot === slot.time
                      ? 'gradient-brand text-white'
                      : 'bg-white/5 text-gray-300 hover:bg-white/10'
                  }`}
                >
                  {slot.time}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/10">
          <button
            onClick={handleBook}
            disabled={!selectedSlot}
            className={`w-full py-3 rounded-2xl font-bold text-sm transition-all duration-200 ${
              selectedSlot
                ? 'gradient-brand text-white hover:opacity-90 glow-purple'
                : 'bg-white/5 text-gray-600 cursor-not-allowed'
            }`}
          >
            {selectedSlot
              ? `${callType === 'video' ? 'Video' : 'Audio'} Call um ${selectedSlot} buchen – ${selectedDuration.price}€`
              : 'Wähle eine Uhrzeit'}
          </button>
          <p className="text-center text-gray-500 text-xs mt-2">Sichere Zahlung · Stornierung bis 2h vorher kostenlos</p>
        </div>
      </div>
    </div>
  );
}
