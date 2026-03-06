import { NavLink } from 'react-router-dom';
import { Compass, LayoutGrid, MessageCircle, User, Heart } from 'lucide-react';

interface NavbarProps {
  subscribedCount: number;
}

export default function Navbar({ subscribedCount }: NavbarProps) {
  const navItems = [
    { to: '/discover', label: 'Entdecken', icon: Compass },
    { to: '/feed', label: 'Feed', icon: LayoutGrid },
    { to: '/messages', label: 'Nachrichten', icon: MessageCircle },
    { to: '/profile', label: 'Profil', icon: User },
  ];

  return (
    <>
      {/* Desktop top nav */}
      <nav className="hidden md:flex fixed top-0 left-0 right-0 z-50 glass border-b border-white/10 px-6 py-3 items-center justify-between">
        <div className="flex items-center gap-2">
          <Heart className="w-6 h-6 text-brand-400 fill-brand-400" />
          <span className="text-xl font-bold gradient-text">Only Friends</span>
        </div>

        <div className="flex items-center gap-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-brand-500/20 text-brand-400'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            <span className="text-brand-400 font-semibold">{subscribedCount}</span> Friends
          </span>
          <div className="w-8 h-8 rounded-full gradient-brand flex items-center justify-center text-sm font-bold">
            M
          </div>
        </div>
      </nav>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 glass border-t border-white/10 px-2 py-2">
        <div className="flex items-center justify-around">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-col items-center gap-1 px-4 py-1 rounded-xl transition-all duration-200 ${
                  isActive ? 'text-brand-400' : 'text-gray-500'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Desktop spacer */}
      <div className="hidden md:block h-16" />
    </>
  );
}
