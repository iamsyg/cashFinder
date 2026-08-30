// frontend/src/components/AmountSelector.jsx
import React from 'react'
import { IndianRupee, Sliders } from 'lucide-react'

const QUICK_AMOUNTS = [500, 1000, 2000, 5000, 10000]

export default function AmountSelector({ selectedAmount, onAmountChange }) {
  return (
    <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800 rounded-2xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2 text-slate-300 font-medium text-sm">
          <Sliders className="w-4 h-4 text-emerald-400" />
          <span>How much cash do you need?</span>
        </div>
        <span className="text-xs text-slate-400">Live ML filtering applied</span>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        {QUICK_AMOUNTS.map((amt) => {
          const isSelected = selectedAmount === amt
          return (
            <button
              key={amt}
              onClick={() => onAmountChange(amt)}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center space-x-1 ${
                isSelected
                  ? 'bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/25 scale-105'
                  : 'bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/50'
              }`}
            >
              <IndianRupee className="w-3.5 h-3.5" />
              <span>{amt.toLocaleString('en-IN')}</span>
            </button>
          )
        })}

        {/* Custom Input */}
        <div className="relative flex-1 min-w-[120px]">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 text-xs">
            ₹
          </span>
          <input
            type="number"
            value={selectedAmount || ''}
            onChange={(e) => onAmountChange(Number(e.target.value) || 0)}
            placeholder="Custom"
            className="w-full pl-7 pr-3 py-2 bg-slate-800/80 border border-slate-700/50 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all"
          />
        </div>
      </div>
    </div>
  )
}
