// frontend/src/components/TelemetryModal.jsx
import React, { useState } from 'react'
import { X, CheckCircle, AlertTriangle, XCircle, Send } from 'lucide-react'

export default function TelemetryModal({ cashPoint, onClose, onSubmitPing }) {
  const [status, setStatus] = useState('GOT_CASH')
  const [note, setNote] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!cashPoint) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    await onSubmitPing({
      cash_point_id: cashPoint.id,
      status,
      note
    })
    setIsSubmitting(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-full transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-white mb-1">Report Cash Status</h2>
          <p className="text-xs text-slate-400">Help update real-time ML predictions for {cashPoint.name}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Status Selection Buttons */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300">What happened?</label>
            
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={() => setStatus('GOT_CASH')}
                className={`p-3 rounded-xl border text-left flex items-center justify-between transition-all ${
                  status === 'GOT_CASH'
                    ? 'bg-emerald-500/10 border-emerald-500 text-emerald-400 font-bold'
                    : 'bg-slate-800/60 border-slate-700/60 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <span className="text-sm">Successfully Got Cash</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setStatus('OUT_OF_CASH')}
                className={`p-3 rounded-xl border text-left flex items-center justify-between transition-all ${
                  status === 'OUT_OF_CASH'
                    ? 'bg-amber-500/10 border-amber-500 text-amber-400 font-bold'
                    : 'bg-slate-800/60 border-slate-700/60 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5 text-amber-400" />
                  <span className="text-sm">Out of Cash / Empty</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setStatus('MACHINE_BROKEN')}
                className={`p-3 rounded-xl border text-left flex items-center justify-between transition-all ${
                  status === 'MACHINE_BROKEN'
                    ? 'bg-rose-500/10 border-rose-500 text-rose-400 font-bold'
                    : 'bg-slate-800/60 border-slate-700/60 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <XCircle className="w-5 h-5 text-rose-400" />
                  <span className="text-sm">Machine / Shutter Hardware Error</span>
                </div>
              </button>
            </div>
          </div>

          {/* Optional Note */}
          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">Optional Details</label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g., Only Rs. 500 notes available"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl text-sm flex items-center justify-center space-x-2 shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            <span>{isSubmitting ? 'Submitting...' : 'Submit Live Report'}</span>
          </button>
        </form>

      </div>
    </div>
  )
}
