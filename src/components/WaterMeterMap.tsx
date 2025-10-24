import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

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
  const [meters] = useState<WaterMeter[]>(generateMockMeters(5000));

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

    // Add water meter data as a GeoJSON source
    map.current.on('load', () => {
      const geojsonData = {
        type: 'FeatureCollection',
        features: meters.map(meter => ({
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: meter.coordinates
          },
          properties: {
            id: meter.id,
            status: meter.status,
            lastReading: meter.lastReading,
            predictedFailureRisk: meter.predictedFailureRisk
          }
        }))
      };

      // Add the source
      map.current!.addSource('water-meters', {
        type: 'geojson',
        data: geojsonData
      });

      // Add normal meters layer
      map.current!.addLayer({
        id: 'normal-meters',
        type: 'circle',
        source: 'water-meters',
        filter: ['==', ['get', 'status'], 'normal'],
        paint: {
          'circle-radius': 2,
          'circle-color': 'hsl(205, 85%, 45%)',
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff'
        }
      });

      // Add warning meters layer
      map.current!.addLayer({
        id: 'warning-meters',
        type: 'circle',
        source: 'water-meters',
        filter: ['==', ['get', 'status'], 'warning'],
        paint: {
          'circle-radius': 2,
          'circle-color': 'hsl(35, 95%, 60%)',
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff'
        }
      });

      // Add alert meters layer
      map.current!.addLayer({
        id: 'alert-meters',
        type: 'circle',
        source: 'water-meters',
        filter: ['==', ['get', 'status'], 'alert'],
        paint: {
          'circle-radius': 2,
          'circle-color': 'hsl(0, 75%, 58%)',
          'circle-stroke-width': 1,
          'circle-stroke-color': '#ffffff'
        }
      });

      // Add hover popup
      const popup = new mapboxgl.Popup({
        closeButton: false,
        closeOnClick: false
      });

      // Add hover effect and popup
      ['normal-meters', 'warning-meters', 'alert-meters'].forEach(layerId => {
        map.current!.on('mouseenter', layerId, (e) => {
          map.current!.getCanvas().style.cursor = 'pointer';
          
          const feature = e.features?.[0];
          if (feature) {
            const meter = meters.find(m => m.id === feature.properties.id);
            if (meter) {
              popup.setLngLat(e.lngLat)
                .setHTML(`
                  <div class="p-2">
                    <div class="font-semibold text-sm">${meter.name || `Meter ${meter.id}`}</div>
                    <div class="text-xs text-gray-600">Risk: ${Math.round(meter.predictedFailureRisk)}%</div>
                    <div class="text-xs text-gray-600">Reading: ${meter.lastReading.toLocaleString()} L</div>
                  </div>
                `)
                .addTo(map.current!);
            }
          }
        });

        map.current!.on('mouseleave', layerId, () => {
          map.current!.getCanvas().style.cursor = '';
          popup.remove();
        });
      });

      // Add click handler
      map.current!.on('click', ['normal-meters', 'warning-meters', 'alert-meters'], (e) => {
        const feature = e.features?.[0];
        if (feature) {
          const meter = meters.find(m => m.id === feature.properties.id);
          if (meter) {
            onMeterSelect?.(meter);
          }
        }
      });
    });

    // Cleanup
    return () => {
      if (map.current) {
        // Remove layers and sources
        if (map.current.getLayer('normal-meters')) map.current.removeLayer('normal-meters');
        if (map.current.getLayer('warning-meters')) map.current.removeLayer('warning-meters');
        if (map.current.getLayer('alert-meters')) map.current.removeLayer('alert-meters');
        if (map.current.getSource('water-meters')) map.current.removeSource('water-meters');
        map.current.remove();
      }
    };
  }, [meters, onMeterSelect, simulateAlert]);

  return (
    <div className="relative w-full h-full">
      <div 
        ref={mapContainer} 
        className="absolute inset-0 rounded-2xl overflow-hidden"
      />
    </div>
  );
};
