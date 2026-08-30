// frontend/src/components/CashPointCard.jsx
import React, { useState } from 'react'
import { Building2, Store, MapPin, IndianRupee, QrCode, MessageSquarePlus, ChevronDown, ChevronUp, Sparkles, ShieldCheck } from 'lucide-react'

const BADGE_STYLES = {
  green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-emerald-500/10',
  yellow: 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-amber-500/10',
  red: 'bg-rose-500/10 text-rose-400 border-rose-500/20 shadow-rose-500/10',
  gray: 'bg-slate-500/10 text-slate-400 border-slate-500/20'
}

export default function CashPointCard({ cashPoint, isSelected, onSelect, onWithdraw, onReport }) {
  const [showReasons, setShowReasons] = useState(false)

  const isATM = cashPoint.type === 'ATM'
  const badgeStyle = BADGE_STYLES[cashPoint.badge_color] || BADGE_STYLES.gray

  return (
    <div
      onClick={onSelect}
      className={`bg-slate-900/80 backdrop-blur-md border rounded-2xl p-4 transition-all duration-200 cursor-pointer ${
        isSelected
          ? 'border-emerald-500/60 ring-1 ring-emerald-500/40 shadow-xl shadow-emerald-500/5'
          : 'border-slate-800 hover:border-slate-700/80'
      }`}
    >
      {/* Header Info */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start space-x-3">
          <div className={`p-2.5 rounded-xl border ${isATM ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-purple-500/10 border-purple-500/20 text-purple-400'}`}>
            {isATM ? <Building2 className="w-5 h-5" /> : <Store className="w-5 h-5" />}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-slate-100 text-base">{cashPoint.name}</h3>
              <span className={`px-2 py-0.5 text-[10px] font-semibold border rounded-md uppercase ${isATM ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-purple-500/10 text-purple-400 border-purple-500/20'}`}>
                {cashPoint.type}
              </span>
            </div>
            <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1">
              <span className="flex items-center space-x-1">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                <span>{cashPoint.distance_km} km away</span>
              </span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <IndianRupee className="w-3.5 h-3.5 text-emerald-400" />
                <span>₹{cashPoint.current_cash_balance.toLocaleString('en-IN')} available</span>
              </span>
            </div>
          </div>
        </div>

        {/* Live ML Probability Badge */}
        <div className={`flex flex-col items-end px-3 py-1.5 border rounded-xl shadow-lg ${badgeStyle}`}>
          <div className="flex items-center space-x-1 font-black text-lg">
            <span>{cashPoint.probability_score}%</span>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider">
            {cashPoint.confidence_level}
          </span>
        </div>
      </div>

      {/* Expandable Reasons List */}
      <div className="mb-3">
        <button
          onClick={(e) => {
            e.stopPropagation()
            setShowReasons(!showReasons)
          }}
          className="flex items-center space-x-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <Sparkles className="w-3 h-3 text-emerald-400" />
          <span>ML Confidence Breakdown</span>
          {showReasons ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>

        {showReasons && (
          <div className="mt-2 p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1.5 text-xs text-slate-300">
            {cashPoint.reasons && cashPoint.reasons.map((reason, idx) => (
              <div key={idx} className="flex items-start space-x-2">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                <span>{reason}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center space-x-2 pt-2 border-t border-slate-800/60">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onWithdraw(cashPoint)
          }}
          className="flex-1 py-2 px-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl text-xs flex items-center justify-center space-x-1.5 shadow-lg shadow-emerald-500/20 transition-all active:scale-[0.98]"
        >
          <QrCode className="w-4 h-4" />
          <span>Withdraw Cash via UPI</span>
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation()
            onReport(cashPoint)
          }}
          className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 rounded-xl text-xs font-semibold flex items-center space-x-1 transition-all"
          title="Submit Live Ping"
        >
          <MessageSquarePlus className="w-4 h-4 text-emerald-400" />
          <span className="hidden sm:inline">Report</span>
        </button>
      </div>
    </div>
  )
}
