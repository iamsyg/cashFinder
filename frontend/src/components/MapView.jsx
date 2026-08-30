// frontend/src/components/MapView.jsx
import React from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'

// Fix default Leaflet icon assets
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Create custom colored circle SVG pins for Green, Yellow, Red probability levels
const createCustomPin = (colorHex, score) => {
  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="
        background-color: ${colorHex};
        width: 34px;
        height: 34px;
        border-radius: 50%;
        border: 3px solid #0f172a;
        box-shadow: 0 0 15px ${colorHex}80;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #0f172a;
        font-weight: 800;
        font-size: 11px;
        font-family: sans-serif;
      ">
        ${score}%
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -17],
  })
}

const BADGE_COLORS = {
  green: '#10b981',
  yellow: '#f59e0b',
  red: '#ef4444',
  gray: '#64748b'
}

export default function MapView({ cashPoints, userLocation, selectedPoint, onSelectPoint, onInitiateWithdraw }) {
  const center = [userLocation.lat, userLocation.lng]

  return (
    <div className="w-full h-[420px] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl relative z-0">
      <MapContainer center={center} zoom={14} scrollWheelZoom={true} className="w-full h-full">
        {/* Dark map tiles (CartoDB Dark Matter - No API Key Required) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* User Location Marker */}
        <Marker
          position={center}
          icon={L.divIcon({
            className: 'user-pin',
            html: `<div style="background-color: #3b82f6; width: 20px; height: 20px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 0 12px #3b82f6;"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10],
          })}
        >
          <Popup className="dark-popup">
            <div className="text-xs font-bold text-slate-800">Your Current Location</div>
          </Popup>
        </Marker>

        {/* Cash Point Markers */}
        {cashPoints.map((cp) => {
          const colorHex = BADGE_COLORS[cp.badge_color] || BADGE_COLORS.gray
          const customPin = createCustomPin(colorHex, cp.probability_score)

          return (
            <Marker
              key={cp.id}
              position={[cp.latitude, cp.longitude]}
              icon={customPin}
              eventHandlers={{
                click: () => onSelectPoint(cp),
              }}
            >
              <Popup className="dark-popup">
                <div className="p-1 min-w-[200px]">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-bold text-slate-900 text-sm">{cp.name}</span>
                    <span
                      style={{ backgroundColor: colorHex }}
                      className="px-2 py-0.5 rounded text-[10px] font-black text-slate-950"
                    >
                      {cp.probability_score}% {cp.confidence_level}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 mb-2">{cp.type} • {cp.distance_km} km away</p>
                  <p className="text-xs text-slate-700 font-semibold mb-3">
                    Available Float: ₹{cp.current_cash_balance.toLocaleString('en-IN')}
                  </p>

                  <button
                    onClick={() => onInitiateWithdraw(cp)}
                    className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all shadow"
                  >
                    Withdraw via UPI
                  </button>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}
