import React, { useEffect, useRef, useState } from 'react';
import { MeterPopup } from './MeterPopup';
import barcelonaMap from '@/assets/barcelona-map.jpg';

interface WaterMeter {
  id: string;
  coordinates: [number, number]; // Now [x%, y%] for positioning
  status: 'normal' | 'warning' | 'alert';
  lastReading: number;
  predictedFailureRisk: number;
}

interface WaterMeterMapProps {
  onMeterSelect?: (meter: WaterMeter | null) => void;
  simulateAlert?: boolean;
}

// Generate mock water meters positioned across the map
const generateMockMeters = (count: number): WaterMeter[] => {
  const meters: WaterMeter[] = [];
  
  for (let i = 0; i < count; i++) {
    // Position meters across the map area (percentage-based for static image)
    const x = 10 + Math.random() * 80; // 10-90% from left
    const y = 10 + Math.random() * 80; // 10-90% from top
    const risk = Math.random() * 100;
    
    meters.push({
      id: `meter-${i}`,
      coordinates: [x, y], // Now using percentage positions
      status: risk > 80 ? 'alert' : risk > 50 ? 'warning' : 'normal',
      lastReading: Math.floor(1000 + Math.random() * 9000),
      predictedFailureRisk: risk,
    });
  }
  
  return meters;
};

export const WaterMeterMap: React.FC<WaterMeterMapProps> = ({ 
  onMeterSelect,
  simulateAlert = false 
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const [meters] = useState<WaterMeter[]>(generateMockMeters(800));
  const [hoveredMeter, setHoveredMeter] = useState<WaterMeter | null>(null);
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null);

  return (
    <div className="relative w-full h-full">
      {/* Static Map Background */}
      <div className="absolute inset-0 rounded-2xl overflow-hidden bg-gradient-to-br from-ocean-light to-background">
        <img 
          src={barcelonaMap} 
          alt="Barcelona Map" 
          className="w-full h-full object-cover opacity-90"
        />
        {/* Subtle overlay for depth */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background/10" />
      </div>
      
      {/* Interactive Water Meters */}
      <div className="absolute inset-0">
        {meters.map((meter, index) => {
          const color = meter.status === 'alert' 
            ? 'hsl(0, 75%, 58%)' 
            : meter.status === 'warning'
            ? 'hsl(35, 95%, 60%)'
            : 'hsl(205, 85%, 45%)';

          return (
            <div
              key={meter.id}
              className="absolute cursor-pointer transition-all duration-300 hover:z-50"
              style={{
                left: `${meter.coordinates[0]}%`,
                top: `${meter.coordinates[1]}%`,
                animationDelay: `${index * 0.001}s`,
              }}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                setHoverPosition({ 
                  x: rect.left + rect.width / 2, 
                  y: rect.top 
                });
                setHoveredMeter(meter);
              }}
              onMouseLeave={() => {
                setHoveredMeter(null);
                setHoverPosition(null);
              }}
              onClick={() => onMeterSelect?.(meter)}
            >
              <div
                className="w-3 h-3 rounded-full border-2 border-white shadow-md animate-dot-appear hover:scale-150 transition-transform"
                style={{ backgroundColor: color }}
              >
                {/* Ripple effect for alerts */}
                {simulateAlert && meter.status === 'alert' && (
                  <div
                    className="absolute inset-0 rounded-full border-2 animate-ripple"
                    style={{ 
                      borderColor: color,
                      width: '28px',
                      height: '28px',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)'
                    }}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Hover Popup */}
      {hoveredMeter && hoverPosition && (
        <MeterPopup 
          meter={hoveredMeter} 
          position={hoverPosition}
        />
      )}
    </div>
  );
};
