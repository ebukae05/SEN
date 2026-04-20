'use client'

import { cn } from '@/lib/utils'
import {
  Home,
  Plane,
  Activity,
  Bot,
  Wrench,
  Settings,
  Radio,
} from 'lucide-react'

type View = 'home' | 'fleet' | 'engine' | 'agents' | 'recommendations' | 'settings'

interface SenSidebarProps {
  currentView: View
  onViewChange: (view: View) => void
}

const navItems: { id: View; label: string; icon: React.ElementType }[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'fleet', label: 'Fleet Overview', icon: Plane },
  { id: 'engine', label: 'Engine Detail', icon: Activity },
  { id: 'agents', label: 'Agent Activity', icon: Bot },
  { id: 'recommendations', label: 'Recommendations', icon: Wrench },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export function SenSidebar({ currentView, onViewChange }: SenSidebarProps) {
  return (
    <aside className="w-64 h-screen bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center glow-navy">
              <span className="text-primary-foreground font-bold text-lg">S</span>
            </div>
            <div className="absolute inset-0 rounded-lg bg-gradient-to-br from-primary/50 to-accent/50 blur-md -z-10 animate-pulse-glow" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-foreground tracking-wide">SEN</h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Sensor Engine Network</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = currentView === item.id
            
            return (
              <li key={item.id}>
                <button
                  onClick={() => onViewChange(item.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-sidebar-accent text-primary glow-navy'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-foreground'
                  )}
                >
                  <Icon className={cn('w-5 h-5', isActive && 'text-primary')} />
                  {item.label}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Status indicator */}
      <div className="p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="relative flex items-center justify-center">
            <Radio className="w-4 h-4 text-primary" />
            <span className="absolute w-2 h-2 rounded-full bg-primary animate-ping" />
            <span className="absolute w-2 h-2 rounded-full bg-primary" />
          </div>
          <span>Live telemetry connected</span>
        </div>
      </div>
    </aside>
  )
}
