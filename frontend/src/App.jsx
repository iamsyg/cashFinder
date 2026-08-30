// frontend/src/App.jsx
import React, { useState, useEffect } from 'react'
import axios from 'axios'

import Navbar from './components/Navbar'
import AmountSelector from './components/AmountSelector'
import MapView from './components/MapView'
import CashPointCard from './components/CashPointCard'
import WithdrawalModal from './components/WithdrawalModal'
import TelemetryModal from './components/TelemetryModal'
import MerchantPanel from './components/MerchantPanel'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// Default Koramangala, Bangalore GPS coordinates
const DEFAULT_USER_LOCATION = { lat: 12.9352, lng: 77.6245 }

export default function App() {
  const [selectedAmount, setSelectedAmount] = useState(2000)
  const [cashPoints, setCashPoints] = useState([])
  const [selectedPoint, setSelectedPoint] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Modals
  const [withdrawalData, setWithdrawalData] = useState(null)
  const [reportingPoint, setReportingPoint] = useState(null)

  // Fetch nearby cash points for Bangalore location from FastAPI backend
  const fetchCashPoints = async (amount = selectedAmount, isManual = false) => {
    if (isManual) setIsRefreshing(true)
    else setIsLoading(true)

    try {
      const response = await axios.get(`${API_BASE_URL}/cashpoints`, {
        params: {
          lat: DEFAULT_USER_LOCATION.lat,
          lng: DEFAULT_USER_LOCATION.lng,
          radius_km: 10.0,
          amount: amount
        }
      })
      const data = response.data || []
      setCashPoints(data)
      if (data.length > 0) {
        setSelectedPoint(prev => prev || data[0])
      }
    } catch (err) {
      console.error('Error fetching cash points:', err)
      setCashPoints([])
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchCashPoints(selectedAmount)
  }, [selectedAmount])

  // Initiate Withdrawal API Call
  const handleInitiateWithdrawal = async (cashPoint) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/upi/withdraw`, {
        cash_point_id: cashPoint.id,
        amount: selectedAmount
      })
      setWithdrawalData(response.data)
      // Refresh list to show updated balance
      fetchCashPoints(selectedAmount, true)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to initiate withdrawal')
    }
  }

  // Submit Telemetry Ping API Call
  const handleSubmitPing = async (pingPayload) => {
    try {
      await axios.post(`${API_BASE_URL}/telemetry`, pingPayload)
      // Refresh list to trigger immediate ML score recalculation
      fetchCashPoints(selectedAmount, true)
    } catch (err) {
      alert('Failed to submit report')
    }
  }

  // Refill Float API Call
  const handleRefillFloat = async (cashPointId, newBalance) => {
    try {
      await axios.post(`${API_BASE_URL}/cashpoints/${cashPointId}/refill`, {
        new_balance: newBalance
      })
      fetchCashPoints(selectedAmount, true)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to refill cash float')
    }
  }

  // Deposit Float API Call
  const handleDepositFloat = async (cashPointId, depositAmount) => {
    try {
      await axios.post(`${API_BASE_URL}/cashpoints/${cashPointId}/deposit`, {
        cash_point_id: cashPointId,
        amount: depositAmount
      })
      fetchCashPoints(selectedAmount, true)
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to deposit cash float')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-slate-950">
      
      {/* Top Navbar */}
      <Navbar
        onRefresh={() => fetchCashPoints(selectedAmount, true)}
        isRefreshing={isRefreshing}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Amount Filter Controls */}
        <AmountSelector
          selectedAmount={selectedAmount}
          onAmountChange={(amt) => setSelectedAmount(amt)}
        />

        {/* Map & List Grid Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Interactive Leaflet Map (7 cols on large screens) */}
          <div className="lg:col-span-7 sticky top-20">
            <MapView
              cashPoints={cashPoints}
              userLocation={DEFAULT_USER_LOCATION}
              selectedPoint={selectedPoint}
              onSelectPoint={(cp) => setSelectedPoint(cp)}
              onInitiateWithdraw={handleInitiateWithdrawal}
            />
          </div>

          {/* Cash Points List & Merchant Panel (5 cols on large screens) */}
          <div className="lg:col-span-5 space-y-4">
            
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>Nearby Cash Points</span>
                <span className="px-2 py-0.5 text-xs bg-slate-800 text-slate-300 border border-slate-700 rounded-full font-medium">
                  {cashPoints.length} Fulfillable
                </span>
              </h2>
            </div>

            {isLoading ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center text-slate-400 text-sm animate-pulse">
                Running ML Cash Availability Model...
              </div>
            ) : cashPoints.length === 0 ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center text-slate-400 text-sm">
                No nearby cash points have ₹{selectedAmount.toLocaleString('en-IN')} available.
              </div>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {cashPoints.map((cp) => (
                  <CashPointCard
                    key={cp.id}
                    cashPoint={cp}
                    isSelected={selectedPoint?.id === cp.id}
                    onSelect={() => setSelectedPoint(cp)}
                    onWithdraw={handleInitiateWithdrawal}
                    onReport={(targetCp) => setReportingPoint(targetCp)}
                  />
                ))}
              </div>
            )}

            {/* Merchant Control Drawer */}
            <MerchantPanel
              cashPoints={cashPoints}
              onRefill={handleRefillFloat}
              onDeposit={handleDepositFloat}
            />

          </div>

        </div>

      </main>

      {/* Modals */}
      {withdrawalData && (
        <WithdrawalModal
          withdrawalData={withdrawalData}
          onClose={() => setWithdrawalData(null)}
        />
      )}

      {reportingPoint && (
        <TelemetryModal
          cashPoint={reportingPoint}
          onClose={() => setReportingPoint(null)}
          onSubmitPing={handleSubmitPing}
        />
      )}

    </div>
  )
}
