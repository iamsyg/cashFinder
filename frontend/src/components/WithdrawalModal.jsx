// frontend/src/components/WithdrawalModal.jsx
import React from 'react'
import { X, QrCode, ExternalLink, CheckCircle, ShieldCheck, IndianRupee } from 'lucide-react'

export default function WithdrawalModal({ withdrawalData, onClose }) {
  if (!withdrawalData) return null

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl relative animate-in fade-in zoom-in duration-200">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-full transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-3 shadow-lg shadow-emerald-500/10">
            <QrCode className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white mb-1">Initiate UPI Cash Withdrawal</h2>
          <p className="text-xs text-slate-400">{withdrawalData.cash_point_name}</p>
        </div>

        {/* Withdrawal Details */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 mb-6 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Withdrawal Amount</span>
            <span className="text-emerald-400 font-bold text-base flex items-center">
              <IndianRupee className="w-4 h-4" />
              {withdrawalData.amount_requested.toLocaleString('en-IN')}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Transaction Ref</span>
            <span className="font-mono text-slate-300">{withdrawalData.upi_ref}</span>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Status</span>
            <span className="flex items-center space-x-1 text-emerald-400 font-semibold">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>{withdrawalData.status}</span>
            </span>
          </div>
        </div>

        {/* QR Code Payload Display */}
        <div className="bg-white p-4 rounded-2xl flex flex-col items-center justify-center mb-6 shadow-xl border border-slate-700">
          {withdrawalData.qr_code_base64 ? (
            <img
              src={withdrawalData.qr_code_base64}
              alt="UPI Withdrawal QR Code"
              className="w-48 h-48 object-contain"
            />
          ) : (
            <div className="w-48 h-48 bg-slate-200 rounded flex items-center justify-center text-slate-500 text-xs">
              Generating QR Code...
            </div>
          )}
          <p className="text-[11px] text-slate-600 font-medium mt-2 text-center">
            Scan with GPay, PhonePe, or Paytm on desktop
          </p>
        </div>

        {/* 1-Tap Deep-Link Button for Mobile */}
        <div className="space-y-3">
          <a
            href={withdrawalData.upi_intent_uri}
            className="w-full py-3 px-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl text-sm flex items-center justify-center space-x-2 shadow-lg shadow-emerald-500/25 transition-all"
          >
            <span>Open UPI App on Mobile</span>
            <ExternalLink className="w-4 h-4" />
          </a>

          <div className="flex items-center justify-center space-x-1 text-[11px] text-slate-500">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>NPCI Standard Cardless Cash Intent Protocol</span>
          </div>
        </div>

      </div>
    </div>
  )
}
