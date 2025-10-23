import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { MeterPopup } from './MeterPopup';

interface WaterMeter {
  id: string;
  coordinates: [number, number]; // [lng, lat] for Mapbox
  status: 'normal' | 'warning' | 'alert';
  lastReading: number;
  predictedFailureRisk: number;
}

interface WaterMeterMapProps {
  onMeterSelect?: (meter: WaterMeter | null) => void;
  simulateAlert?: boolean;
}

// Barcelona bounds for meter generation
const BARCELONA_BOUNDS = {
  minLng: 2.05,
  maxLng: 2.25,
  minLat: 41.32,
  maxLat: 41.47,
};

// Generate mock water meters positioned across Barcelona
const generateMockMeters = (count: number): WaterMeter[] => {
  const meters: WaterMeter[] = [];
  
  for (let i = 0; i < count; i++) {
    // Position meters within Barcelona's geographical bounds
    const lng = BARCELONA_BOUNDS.minLng + Math.random() * (BARCELONA_BOUNDS.maxLng - BARCELONA_BOUNDS.minLng);
    const lat = BARCELONA_BOUNDS.minLat + Math.random() * (BARCELONA_BOUNDS.maxLat - BARCELONA_BOUNDS.minLat);
    const risk = Math.random() * 100;
    
    meters.push({
      id: `meter-${i}`,
      coordinates: [lng, lat],
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
  const map = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const [meters] = useState<WaterMeter[]>(generateMockMeters(800));
  const [hoveredMeter, setHoveredMeter] = useState<WaterMeter | null>(null);
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!mapContainer.current) return;

    // Initialize Mapbox
    mapboxgl.accessToken = 'pk.eyJ1IjoiamFuYWd1aTciLCJhIjoiY21oMzhpOXFsMTdqZTU5c2J0a2R6aXp4aSJ9.ryKFzFTxG2CidKGv6a162Q';
    
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [2.1734, 41.3851], // Barcelona coordinates
      zoom: 12,
      pitch: 0,
    });

    // Add navigation controls (zoom in/out)
    map.current.addControl(
      new mapboxgl.NavigationControl({
        visualizePitch: false,
      }),
      'top-right'
    );

    // Add water meter markers once map is loaded
    map.current.on('load', () => {
      meters.forEach((meter, index) => {
        const color = meter.status === 'alert' 
          ? 'hsl(0, 75%, 58%)' 
          : meter.status === 'warning'
          ? 'hsl(35, 95%, 60%)'
          : 'hsl(205, 85%, 45%)';

        // Create custom marker element
        const el = document.createElement('div');
        el.className = 'cursor-pointer transition-all duration-300 hover:z-50';
        el.style.width = '12px';
        el.style.height = '12px';
        el.style.animationDelay = `${index * 0.001}s`;
        
        const dot = document.createElement('div');
        dot.className = 'w-3 h-3 rounded-full border-2 border-white shadow-md animate-dot-appear hover:scale-150 transition-transform';
        dot.style.backgroundColor = color;

        // Add ripple effect for alerts
        if (simulateAlert && meter.status === 'alert') {
          const ripple = document.createElement('div');
          ripple.className = 'absolute inset-0 rounded-full border-2 animate-ripple';
          ripple.style.borderColor = color;
          ripple.style.width = '28px';
          ripple.style.height = '28px';
          ripple.style.top = '50%';
          ripple.style.left = '50%';
          ripple.style.transform = 'translate(-50%, -50%)';
          dot.appendChild(ripple);
        }

        el.appendChild(dot);

        // Add hover events
        el.addEventListener('mouseenter', (e) => {
          const rect = el.getBoundingClientRect();
          setHoverPosition({ 
            x: rect.left + rect.width / 2, 
            y: rect.top 
          });
          setHoveredMeter(meter);
        });

        el.addEventListener('mouseleave', () => {
          setHoveredMeter(null);
          setHoverPosition(null);
        });

        el.addEventListener('click', () => {
          onMeterSelect?.(meter);
        });

        // Create and add marker
        const marker = new mapboxgl.Marker({ element: el })
          .setLngLat(meter.coordinates)
          .addTo(map.current!);

        markersRef.current.push(marker);
      });
    });

    // Cleanup
    return () => {
      markersRef.current.forEach(marker => marker.remove());
      markersRef.current = [];
      map.current?.remove();
    };
  }, [meters, onMeterSelect, simulateAlert]);

  return (
    <div className="relative w-full h-full">
      <div 
        ref={mapContainer} 
        className="absolute inset-0 rounded-2xl overflow-hidden"
      />
      
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
