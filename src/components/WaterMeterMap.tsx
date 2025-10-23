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
  onMetersChange?: (meters: WaterMeter[]) => void;
}

// Barcelona land zones - approximating the city's actual shape, excluding water
const BARCELONA_LAND_ZONES = [
  // Central Barcelona (Eixample, Ciutat Vella)
  { minLng: 2.150, maxLng: 2.190, minLat: 41.375, maxLat: 41.405 },
  // Upper Barcelona (Gràcia, Sant Gervasi)
  { minLng: 2.135, maxLng: 2.175, minLat: 41.395, maxLat: 41.420 },
  // Eastern Barcelona (Sant Martí)
  { minLng: 2.180, maxLng: 2.220, minLat: 41.390, maxLat: 41.420 },
  // Western Barcelona (Les Corts, Sants)
  { minLng: 2.110, maxLng: 2.155, minLat: 41.370, maxLat: 41.395 },
  // Southern Barcelona (Sants-Montjuïc)
  { minLng: 2.140, maxLng: 2.180, minLat: 41.355, maxLat: 41.380 },
  // Northern Barcelona (Horta-Guinardó)
  { minLng: 2.150, maxLng: 2.190, minLat: 41.410, maxLat: 41.440 },
  // North-West (Sarrià-Sant Gervasi)
  { minLng: 2.105, maxLng: 2.145, minLat: 41.390, maxLat: 41.425 },
  // Far East (Sant Andreu, Nou Barris)
  { minLng: 2.165, maxLng: 2.200, minLat: 41.420, maxLat: 41.455 },
];

// Generate mock water meters positioned realistically across Barcelona's land areas
const generateMockMeters = (count: number): WaterMeter[] => {
  const meters: WaterMeter[] = [];
  
  for (let i = 0; i < count; i++) {
    // Randomly select a zone with weighted probability (central zones get more meters)
    const zoneWeights = [3, 2, 2, 2, 2, 1.5, 1.5, 1]; // Higher weight for central areas
    const totalWeight = zoneWeights.reduce((a, b) => a + b, 0);
    let random = Math.random() * totalWeight;
    let selectedZoneIndex = 0;
    
    for (let j = 0; j < zoneWeights.length; j++) {
      random -= zoneWeights[j];
      if (random <= 0) {
        selectedZoneIndex = j;
        break;
      }
    }
    
    const zone = BARCELONA_LAND_ZONES[selectedZoneIndex];
    
    // Position meters within the selected zone
    const lng = zone.minLng + Math.random() * (zone.maxLng - zone.minLng);
    const lat = zone.minLat + Math.random() * (zone.maxLat - zone.minLat);
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
  simulateAlert = false,
  onMetersChange
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const [meters] = useState<WaterMeter[]>(generateMockMeters(1800));
  const [hoveredMeter, setHoveredMeter] = useState<WaterMeter | null>(null);
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null);

  // Notify parent component when meters change
  useEffect(() => {
    onMetersChange?.(meters);
  }, [meters, onMetersChange]);

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
        el.style.width = '6px';
        el.style.height = '6px';
        el.style.animationDelay = `${index * 0.001}s`;
        
        const dot = document.createElement('div');
        dot.className = 'w-1.5 h-1.5 rounded-full border border-white shadow-sm animate-dot-appear hover:scale-[2.5] transition-transform';
        dot.style.backgroundColor = color;

        // Add ripple effect for alerts
        if (simulateAlert && meter.status === 'alert') {
          const ripple = document.createElement('div');
          ripple.className = 'absolute inset-0 rounded-full border animate-ripple';
          ripple.style.borderColor = color;
          ripple.style.width = '18px';
          ripple.style.height = '18px';
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
