// frontend/src/components/MerchantPanel.jsx
import React, { useState } from 'react'
import { Store, PlusCircle, RotateCcw, IndianRupee } from 'lucide-react'

export default function MerchantPanel({ cashPoints, onRefill, onDeposit }) {
  const [selectedPointId, setSelectedPointId] = useState(cashPoints[0]?.id || '')
  const [amount, setAmount] = useState('')
  const [actionType, setActionType] = useState('deposit') // 'deposit' or 'refill'
  const [isSubmitting, setIsSubmitting] = useState(false)

  const selectedCp = cashPoints.find(cp => cp.id === Number(selectedPointId))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!amount || !selectedPointId) return
    setIsSubmitting(true)

    if (actionType === 'deposit') {
      await onDeposit(Number(selectedPointId), Number(amount))
    } else {
      await onRefill(Number(selectedPointId), Number(amount))
    }

    setAmount('')
    setIsSubmitting(false)
  }

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-3xl p-5 shadow-2xl">
      <div className="flex items-center space-x-2 text-slate-200 font-bold text-base mb-1">
        <Store className="w-5 h-5 text-purple-400" />
        <span>Merchant Float Management</span>
      </div>
      <p className="text-xs text-slate-400 mb-4">Top up cash float or deposit customer cash</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Select Cash Point */}
        <div>
          <label className="text-xs font-medium text-slate-300 block mb-1">Select Cash Point</label>
          <select
            value={selectedPointId}
            onChange={(e) => setSelectedPointId(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white focus:outline-none focus:border-purple-500"
          >
            {cashPoints.map(cp => (
              <option key={cp.id} value={cp.id}>
                {cp.name} (₹{cp.current_cash_balance.toLocaleString('en-IN')} available)
              </option>
            ))}
          </select>
        </div>

        {/* Action Type Tabs */}
        <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => setActionType('deposit')}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1 transition-all ${
              actionType === 'deposit'
                ? 'bg-purple-500 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Add Float</span>
          </button>

          <button
            type="button"
            onClick={() => setActionType('refill')}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1 transition-all ${
              actionType === 'refill'
                ? 'bg-purple-500 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Float</span>
          </button>
        </div>

        {/* Amount Input */}
        <div>
          <label className="text-xs font-medium text-slate-300 block mb-1">
            {actionType === 'deposit' ? 'Amount to Add (INR)' : 'Set New Exact Balance (INR)'}
          </label>
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 text-xs">
              ₹
            </span>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="e.g. 5000"
              className="w-full pl-7 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>
        </div>

        {/* Current Info */}
        {selectedCp && (
          <div className="text-[11px] text-slate-400 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80 flex items-center justify-between">
            <span>Capacity Limit: ₹{selectedCp.standard_float_limit.toLocaleString('en-IN')}</span>
            <span className="text-purple-400 font-semibold">Available: ₹{selectedCp.current_cash_balance.toLocaleString('en-IN')}</span>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isSubmitting || !amount}
          className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-xl text-xs flex items-center justify-center space-x-2 shadow-lg shadow-purple-500/20 transition-all disabled:opacity-50"
        >
          <IndianRupee className="w-4 h-4" />
          <span>{isSubmitting ? 'Updating...' : (actionType === 'deposit' ? 'Deposit Cash Float' : 'Reset Exact Balance')}</span>
        </button>
      </form>
    </div>
  )
}
