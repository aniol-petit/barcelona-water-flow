import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { MeterPopup } from './MeterPopup';

interface WaterMeter {
  id: string;
  coordinates: [number, number];
  status: 'normal' | 'warning' | 'alert';
  lastReading: number;
  predictedFailureRisk: number;
}

interface WaterMeterMapProps {
  onMeterSelect?: (meter: WaterMeter | null) => void;
  simulateAlert?: boolean;
}

// Generate mock water meters across Barcelona
const generateMockMeters = (count: number): WaterMeter[] => {
  const meters: WaterMeter[] = [];
  // Barcelona bounds: ~41.32-41.47 lat, 2.05-2.23 lng
  const minLat = 41.32, maxLat = 41.47;
  const minLng = 2.05, maxLng = 2.23;
  
  for (let i = 0; i < count; i++) {
    const lat = minLat + Math.random() * (maxLat - minLat);
    const lng = minLng + Math.random() * (maxLng - minLng);
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
  const [meters] = useState<WaterMeter[]>(generateMockMeters(800));
  const [hoveredMeter, setHoveredMeter] = useState<WaterMeter | null>(null);
  const [hoverPosition, setHoverPosition] = useState<{ x: number; y: number } | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Initialize map centered on Barcelona
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [2.1734, 41.3851], // Barcelona center
      zoom: 12,
      pitch: 0,
      accessToken: 'pk.eyJ1IjoibG92YWJsZS1kZW1vIiwiYSI6ImNtNWZuZXRsZzA4ZmIya3M4anYxbTdpOGgifQ.JVBdYIu3LKepe_vBdLsb3g',
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    // Custom style on load
    map.current.on('style.load', () => {
      if (!map.current) return;
      
      // Customize map appearance
      map.current.setPaintProperty('water', 'fill-color', 'hsl(200, 70%, 90%)');
    });

    // Cleanup
    return () => {
      markersRef.current.forEach(marker => marker.remove());
      map.current?.remove();
    };
  }, []);

  // Add meter markers
  useEffect(() => {
    if (!map.current) return;

    // Clear existing markers
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    meters.forEach((meter, index) => {
      const el = document.createElement('div');
      el.className = 'water-meter-marker';
      
      // Color based on status
      const color = meter.status === 'alert' 
        ? 'hsl(0, 75%, 58%)' 
        : meter.status === 'warning'
        ? 'hsl(35, 95%, 60%)'
        : 'hsl(205, 85%, 45%)';
      
      el.style.cssText = `
        width: 12px;
        height: 12px;
        background-color: ${color};
        border-radius: 50%;
        border: 2px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        opacity: 0;
        animation: dot-appear 0.6s ease-out forwards;
        animation-delay: ${index * 0.001}s;
      `;

      // Hover effects
      el.addEventListener('mouseenter', (e) => {
        el.style.transform = 'scale(1.5)';
        el.style.boxShadow = `0 0 20px ${color}, 0 4px 12px rgba(0,0,0,0.2)`;
        el.style.zIndex = '1000';
        
        const rect = el.getBoundingClientRect();
        setHoverPosition({ x: rect.left + rect.width / 2, y: rect.top });
        setHoveredMeter(meter);
      });

      el.addEventListener('mouseleave', () => {
        el.style.transform = 'scale(1)';
        el.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
        el.style.zIndex = 'auto';
        
        setHoveredMeter(null);
        setHoverPosition(null);
      });

      el.addEventListener('click', () => {
        onMeterSelect?.(meter);
      });

      // Simulate alert animation
      if (simulateAlert && meter.status === 'alert') {
        const ripple = document.createElement('div');
        ripple.style.cssText = `
          position: absolute;
          top: -8px;
          left: -8px;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          border: 2px solid ${color};
          animation: ripple 1s ease-out infinite;
          pointer-events: none;
        `;
        el.appendChild(ripple);
      }

      const marker = new mapboxgl.Marker(el)
        .setLngLat(meter.coordinates)
        .addTo(map.current!);

      markersRef.current.push(marker);
    });
  }, [meters, onMeterSelect, simulateAlert]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="absolute inset-0 rounded-2xl overflow-hidden" />
      
      {hoveredMeter && hoverPosition && (
        <MeterPopup 
          meter={hoveredMeter} 
          position={hoverPosition}
        />
      )}
    </div>
  );
};
