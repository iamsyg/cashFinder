// frontend/src/components/Navbar.jsx
import React from 'react'
import { Wallet, MapPin, Sparkles, RefreshCw } from 'lucide-react'

export default function Navbar({ onRefresh, isRefreshing }) {
  return (
    <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-500/10">
            <Wallet className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">
                cashFinder
              </span>
              <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> ML Live
              </span>
            </div>
            <p className="text-xs text-slate-400">Predictive Cash Availability & UPI Withdrawal</p>
          </div>
        </div>

        {/* Location Indicator & Refresh Button */}
        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 bg-slate-800/60 border border-slate-700/50 rounded-lg text-xs text-slate-300">
            <MapPin className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span>Koramangala, Bengaluru</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-slate-700/60 transition-all flex items-center justify-center disabled:opacity-50"
            title="Refresh Map & Scores"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>

      </div>
    </header>
  )
}
