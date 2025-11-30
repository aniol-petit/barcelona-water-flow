import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { GeoJSON } from 'geojson';

interface WaterMeter {
  id: string;
  coordinates: [number, number];
  status: 'normal' | 'warning' | 'alert';
  risk_percent: number;
  cluster_id: number;
  seccio_censal?: string;
  age?: number;
  canya?: number;
  last_month_consumption?: number;
}

interface CensusSection {
  seccio_censal: string;
  meter_count: number;
  avg_risk: number;
  min_risk: number;
  max_risk: number;
}

interface WaterMeterMapProps {
  onMeterSelect?: (meter: WaterMeter | null) => void;
  onMetersChange?: (meters: WaterMeter[]) => void;
  filterStatus?: {normal: boolean, warning: boolean, alert: boolean};
  viewMode?: 'meters' | 'sections' | 'both';
}

type ViewMode = 'meters' | 'sections' | 'both';

export const WaterMeterMap: React.FC<WaterMeterMapProps> = ({ 
  onMeterSelect,
  onMetersChange,
  filterStatus = {normal: true, warning: true, alert: true},
  viewMode: initialViewMode = 'meters'
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const mapInitialized = useRef(false);
  const [meters, setMeters] = useState<WaterMeter[]>([]);
  const [sections, setSections] = useState<CensusSection[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>(initialViewMode);
  const [loading, setLoading] = useState(true);

  // Load GeoJSON data for stats only (map will load its own data)
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load meters for stats/parent component
        const metersResponse = await fetch('/data/water_meters.geojson');
        if (!metersResponse.ok) {
          throw new Error(`Failed to load meters: ${metersResponse.statusText}`);
        }
        const metersData: GeoJSON.FeatureCollection = await metersResponse.json();
        
        const loadedMeters: WaterMeter[] = metersData.features
          .filter(f => f.geometry.type === 'Point')
          .map(f => {
            const props = f.properties;
            const coords = f.geometry.coordinates as [number, number];
            const risk = props?.risk_percent || 0;
            
            return {
              id: props?.id || '',
              coordinates: coords,
              status: risk >= 80 ? 'alert' : risk >= 50 ? 'warning' : 'normal',
              risk_percent: risk,
              cluster_id: props?.cluster_id || 0,
              seccio_censal: props?.seccio_censal,
              age: props?.age,
              canya: props?.canya,
              last_month_consumption: props?.last_month_consumption,
            };
          });
        
        setMeters(loadedMeters);
        onMetersChange?.(loadedMeters);
        console.log(`Loaded ${loadedMeters.length} meters`);

        // Load sections for stats
        const sectionsResponse = await fetch('/data/census_sections.geojson');
        if (!sectionsResponse.ok) {
          throw new Error(`Failed to load sections: ${sectionsResponse.statusText}`);
        }
        const sectionsData: GeoJSON.FeatureCollection = await sectionsResponse.json();
        
        const loadedSections: CensusSection[] = sectionsData.features
          .filter(f => f.geometry.type === 'Polygon')
          .map(f => ({
            seccio_censal: f.properties?.seccio_censal || '',
            meter_count: f.properties?.meter_count || 0,
            avg_risk: f.properties?.avg_risk || 0,
            min_risk: f.properties?.min_risk || 0,
            max_risk: f.properties?.max_risk || 0,
          }));
        
        setSections(loadedSections);
        console.log(`Loaded ${loadedSections.length} census sections`);
        setLoading(false);
      } catch (error) {
        console.error('Error loading map data:', error);
        setLoading(false);
      }
    };

    loadData();
  }, [onMetersChange]);


  // Initialize map ONLY ONCE
  useEffect(() => {
    if (!mapContainer.current || mapInitialized.current) return;
    
    mapboxgl.accessToken = 'pk.eyJ1IjoiamFuYWd1aTciLCJhIjoiY21oMzhpOXFsMTdqZTU5c2J0a2R6aXp4aSJ9.ryKFzFTxG2CidKGv6a162Q';
    
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [2.1734, 41.3851],
      zoom: 12,
      pitch: 0,
    });

    map.current.addControl(
      new mapboxgl.NavigationControl({
        visualizePitch: false,
      }),
      'top-right'
    );

    map.current.on('load', async () => {
      mapInitialized.current = true;
      if (!map.current) return;

      try {
        console.log('Map loaded, fetching GeoJSON data...');
        
        // Load meters GeoJSON
        const metersResponse = await fetch('/data/water_meters.geojson');
        if (!metersResponse.ok) {
          throw new Error(`Failed to fetch meters: ${metersResponse.statusText}`);
        }
        const metersGeoJSON: GeoJSON.FeatureCollection = await metersResponse.json();
        console.log(`Loaded ${metersGeoJSON.features.length} meter features`);

        // Add meters source
        map.current.addSource('water-meters', {
          type: 'geojson',
          data: metersGeoJSON,
        });

        // Add meter layers by status
        ['normal', 'warning', 'alert'].forEach(status => {
          const color = status === 'normal' ? '#00a8ff' : status === 'warning' ? '#ffb800' : '#e74c3c';
          const radius = status === 'normal' ? 3 : status === 'warning' ? 4 : 5; // Made larger for visibility
          const opacity = filterStatus[status as keyof typeof filterStatus] && viewMode !== 'sections' ?
            (status === 'normal' ? 0.8 : status === 'warning' ? 0.85 : 0.9) : 0;

          try {
            map.current!.addLayer({
              id: `${status}-meters`,
              type: 'circle',
              source: 'water-meters',
              filter: ['==', ['get', 'status'], status],
              paint: {
                'circle-radius': [
                  'interpolate',
                  ['linear'],
                  ['zoom'],
                  10, radius,
                  15, radius * 2,
                ],
                'circle-color': color,
                'circle-stroke-width': status === 'alert' ? 1.5 : 1,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': opacity,
              },
            });
            console.log(`Added ${status}-meters layer`);
          } catch (err) {
            console.error(`Error adding ${status}-meters layer:`, err);
          }
        });

        // Load sections GeoJSON
        const sectionsResponse = await fetch('/data/census_sections.geojson');
        if (!sectionsResponse.ok) {
          throw new Error(`Failed to fetch sections: ${sectionsResponse.statusText}`);
        }
        const sectionsGeoJSON: GeoJSON.FeatureCollection = await sectionsResponse.json();
        console.log(`Loaded ${sectionsGeoJSON.features.length} section features`);

        // Add sections source
        map.current.addSource('census-sections', {
          type: 'geojson',
          data: sectionsGeoJSON,
        });

        // Add sections layer with risk-based coloring
        map.current.addLayer({
          id: 'census-sections',
          type: 'fill',
          source: 'census-sections',
          paint: {
            'fill-color': [
              'interpolate',
              ['linear'],
              ['get', 'avg_risk'],
              0, '#10b981',    // green (low risk)
              25, '#3b82f6',   // blue
              50, '#f59e0b',   // orange
              75, '#ef4444',   // red (high risk)
              100, '#991b1b',  // dark red (very high risk)
            ],
            'fill-opacity': 0.6,
            'fill-outline-color': '#ffffff',
          },
        });

        // Add sections border
        map.current.addLayer({
          id: 'census-sections-border',
          type: 'line',
          source: 'census-sections',
          paint: {
            'line-color': '#ffffff',
            'line-width': 1,
            'line-opacity': 0.8,
          },
        });

        // Set initial visibility
        if (viewMode === 'sections') {
          map.current.setLayoutProperty('census-sections', 'visibility', 'visible');
          map.current.setLayoutProperty('census-sections-border', 'visibility', 'visible');
        } else if (viewMode === 'meters') {
          map.current.setLayoutProperty('census-sections', 'visibility', 'none');
          map.current.setLayoutProperty('census-sections-border', 'visibility', 'none');
        }

        // Popup for meters
        const meterPopup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
        });

        ['normal-meters', 'warning-meters', 'alert-meters'].forEach(layerId => {
          map.current!.on('mouseenter', layerId, (e) => {
            map.current!.getCanvas().style.cursor = 'pointer';
            
            const feature = e.features?.[0];
            if (feature) {
              const props = feature.properties;
              const risk = props?.risk_percent || 0;
              
              meterPopup
                .setLngLat(e.lngLat)
                .setHTML(`
                  <div class="p-2">
                    <div class="font-semibold text-sm">Meter ${props?.id || 'Unknown'}</div>
                    <div class="text-xs text-gray-600">Risk: ${risk.toFixed(1)}%</div>
                    <div class="text-xs text-gray-600">Cluster: ${props?.cluster_id || 'N/A'}</div>
                    ${props?.seccio_censal ? `<div class="text-xs text-gray-600">Section: ${props.seccio_censal}</div>` : ''}
                  </div>
                `)
                .addTo(map.current!);
            }
          });

          map.current!.on('mouseleave', layerId, () => {
            map.current!.getCanvas().style.cursor = '';
            meterPopup.remove();
          });

          map.current!.on('click', layerId, (e) => {
            const feature = e.features?.[0];
            if (feature) {
              const props = feature.properties;
              const coords = (feature.geometry as GeoJSON.Point).coordinates as [number, number];
              const risk = props?.risk_percent || 0;
              
              const meter: WaterMeter = {
                id: props?.id || '',
                coordinates: coords,
                status: risk >= 80 ? 'alert' : risk >= 50 ? 'warning' : 'normal',
                risk_percent: risk,
                cluster_id: props?.cluster_id || 0,
                seccio_censal: props?.seccio_censal,
                age: props?.age,
                canya: props?.canya,
                last_month_consumption: props?.last_month_consumption,
              };
              
              onMeterSelect?.(meter);
            }
          });
        });

        // Popup for sections
        const sectionPopup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
        });

        map.current.on('mouseenter', 'census-sections', (e) => {
          map.current!.getCanvas().style.cursor = 'pointer';
          
          const feature = e.features?.[0];
          if (feature) {
            const props = feature.properties;
            
            sectionPopup
              .setLngLat(e.lngLat)
              .setHTML(`
                <div class="p-2">
                  <div class="font-semibold text-sm">Census Section ${props?.seccio_censal || 'Unknown'}</div>
                  <div class="text-xs text-gray-600">Meters: ${props?.meter_count || 0}</div>
                  <div class="text-xs text-gray-600">Avg Risk: ${(props?.avg_risk || 0).toFixed(1)}%</div>
                  <div class="text-xs text-gray-600">Range: ${(props?.min_risk || 0).toFixed(1)}% - ${(props?.max_risk || 0).toFixed(1)}%</div>
                </div>
              `)
              .addTo(map.current!);
          }
        });

        map.current.on('mouseleave', 'census-sections', () => {
          map.current!.getCanvas().style.cursor = '';
          sectionPopup.remove();
        });

      } catch (error) {
        console.error('Error loading map layers:', error);
        // Show error to user
        if (map.current) {
          const errorMsg = error instanceof Error ? error.message : 'Unknown error';
          new mapboxgl.Popup()
            .setLngLat([2.1734, 41.3851])
            .setHTML(`<div class="p-3 text-red-600"><strong>Error:</strong> ${errorMsg}</div>`)
            .addTo(map.current);
        }
      }
    });

    return () => {
      if (map.current && mapInitialized.current) {
        map.current.remove();
        mapInitialized.current = false;
      }
    };
  }, []); // Empty deps - only initialize once

  // Update layers when filterStatus or viewMode changes
  useEffect(() => {
    if (!map.current || !mapInitialized.current) return;

    try {
      // Update meter layer opacity
      ['normal', 'warning', 'alert'].forEach(status => {
        const layerId = `${status}-meters`;
        if (map.current?.getLayer(layerId)) {
          const opacity = filterStatus[status as keyof typeof filterStatus] && viewMode !== 'sections' ?
            (status === 'normal' ? 0.8 : status === 'warning' ? 0.85 : 0.9) : 0;
          map.current.setPaintProperty(layerId, 'circle-opacity', opacity);
        }
      });

      // Update section layer visibility
      if (map.current.getLayer('census-sections')) {
        map.current.setLayoutProperty(
          'census-sections',
          'visibility',
          (viewMode === 'sections' || viewMode === 'both') ? 'visible' : 'none'
        );
      }
      if (map.current.getLayer('census-sections-border')) {
        map.current.setLayoutProperty(
          'census-sections-border',
          'visibility',
          (viewMode === 'sections' || viewMode === 'both') ? 'visible' : 'none'
        );
      }
    } catch (error) {
      console.debug('Layer update error:', error);
    }
  }, [filterStatus, viewMode]);

  return (
    <div className="relative w-full h-full">
      <div 
        ref={mapContainer} 
        className="absolute inset-0 overflow-hidden"
      />
      
      {/* View mode toggle */}
      <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-2 flex gap-2">
        <button
          onClick={() => setViewMode('meters')}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            viewMode === 'meters' 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Meters
        </button>
        <button
          onClick={() => setViewMode('sections')}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            viewMode === 'sections' 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Sections
        </button>
        <button
          onClick={() => setViewMode('both')}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            viewMode === 'both' 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Both
        </button>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-sm z-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading map data...</p>
          </div>
        </div>
      )}

      {/* Legend */}
      {!loading && (
        <div className="absolute bottom-4 right-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4">
          {viewMode !== 'sections' && (
            <div className="mb-3">
              <div className="text-sm font-semibold mb-2">Meter Risk Levels</div>
              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#00a8ff]"></div>
                  <span>Normal (&lt;50%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#ffb800]"></div>
                  <span>Warning (50-80%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#e74c3c]"></div>
                  <span>Alert (≥80%)</span>
                </div>
              </div>
            </div>
          )}
          {viewMode !== 'meters' && (
            <div>
              <div className="text-sm font-semibold mb-2">Section Average Risk</div>
              <div className="flex items-center gap-2 h-4">
                <div className="text-xs text-green-600">Low</div>
                <div className="flex-1 h-2 bg-gradient-to-r from-green-500 via-blue-500 via-yellow-500 to-red-700 rounded"></div>
                <div className="text-xs text-red-700">High</div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="absolute inset-0 pointer-events-none bg-gradient-to-b from-transparent via-transparent to-background/5" />
    </div>
  );
};
