import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import type { GeoJSON } from 'geojson';

interface WaterMeter {
  id: string;
  coordinates: [number, number];
  status: 'normal' | 'warning' | 'alert';
  risk_percent: number; // Final combined risk (0-100)
  risk_percent_base?: number; // Base risk from anomaly + degradation (0-100)
  subcount_percent?: number; // Subcounting probability (0-100)
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
              risk_percent_base: props?.risk_percent_base,
              subcount_percent: props?.subcount_percent,
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

        // Remove existing meter layers first (must remove layers before source)
        ['normal', 'warning', 'alert'].forEach(status => {
          const layerId = `${status}-meters`;
          if (map.current!.getLayer(layerId)) {
            map.current!.removeLayer(layerId);
          }
        });
        
        // Remove existing meter source if it exists
        if (map.current.getSource('water-meters')) {
          map.current.removeSource('water-meters');
        }
        
        // Add meters source
        map.current.addSource('water-meters', {
          type: 'geojson',
          data: metersGeoJSON,
        });

        // Add meter layers by status
        ['normal', 'warning', 'alert'].forEach(status => {
          const layerId = `${status}-meters`;
          
          const color = status === 'normal' ? '#00a8ff' : status === 'warning' ? '#ffb800' : '#e74c3c';
          const radius = status === 'normal' ? 2 : status === 'warning' ? 2.5 : 3; // Smaller dots
          const opacity = filterStatus[status as keyof typeof filterStatus] ?
            (status === 'normal' ? 0.8 : status === 'warning' ? 0.85 : 0.9) : 0;

          try {
            map.current!.addLayer({
              id: layerId,
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

        // Remove existing section layers first (must remove layers before source)
        if (map.current.getLayer('census-sections-border')) {
          map.current.removeLayer('census-sections-border');
        }
        if (map.current.getLayer('census-sections')) {
          map.current.removeLayer('census-sections');
        }
        
        // Remove existing section source if it exists
        if (map.current.getSource('census-sections')) {
          map.current.removeSource('census-sections');
        }
        
        // Add sections source
        map.current.addSource('census-sections', {
          type: 'geojson',
          data: sectionsGeoJSON,
        });

        // Add sections layer (hidden - we only want borders)
        map.current.addLayer({
          id: 'census-sections',
          type: 'fill',
          source: 'census-sections',
          paint: {
            'fill-opacity': 0,  // No fill color, only borders will be visible
          },
        });

        // Add sections border (always visible to show section frontiers)
        map.current.addLayer({
          id: 'census-sections-border',
          type: 'line',
          source: 'census-sections',
          paint: {
            'line-color': '#333333',
            'line-width': 0.5,
            'line-opacity': 0.6,
          },
        });

        // Set initial visibility
        // Section borders are always visible
        map.current.setLayoutProperty('census-sections-border', 'visibility', 'visible');
        
        // Section fill is hidden (only borders visible)
        map.current.setLayoutProperty('census-sections', 'visibility', 'visible');

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
              
              const subcountRisk = props?.subcount_percent;
              const finalRisk = risk;
              
              meterPopup
                .setLngLat(e.lngLat)
                .setHTML(`
                  <div class="p-2 min-w-[200px]">
                    <div class="font-semibold text-sm mb-2">Comptador ${props?.id || 'Desconegut'}</div>
                    <div class="space-y-1 text-xs border-t border-gray-200 pt-1">
                      <div class="flex justify-between pt-1">
                        <span class="text-gray-700 font-semibold">Risc Final:</span>
                        <span class="font-bold">${finalRisk.toFixed(1)}%</span>
                      </div>
                      ${subcountRisk !== undefined && subcountRisk !== null ? `
                      <div class="flex justify-between">
                        <span class="text-gray-600">Puntuació de Subcomptatge:</span>
                        <span class="font-medium">${Number(subcountRisk).toFixed(1)}%</span>
                      </div>
                      ` : ''}
                    </div>
                    <div class="text-xs text-gray-500 mt-2 pt-1 border-t border-gray-100">
                      ${props?.nom_barri ? `Secció: ${props.nom_barri}` : (props?.seccio_censal ? `Secció: ${props.seccio_censal}` : '')}
                    </div>
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
                risk_percent_base: props?.risk_percent_base,
                subcount_percent: props?.subcount_percent,
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

        // No popup for census sections (user requested to remove it)

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
          const opacity = filterStatus[status as keyof typeof filterStatus] ?
            (status === 'normal' ? 0.8 : status === 'warning' ? 0.85 : 0.9) : 0;
          map.current.setPaintProperty(layerId, 'circle-opacity', opacity);
        }
      });

      // Section fill remains hidden (only borders visible)
      if (map.current.getLayer('census-sections')) {
        map.current.setPaintProperty('census-sections', 'fill-opacity', 0);
      }
      // Section borders are always visible
      if (map.current.getLayer('census-sections-border')) {
        map.current.setLayoutProperty('census-sections-border', 'visibility', 'visible');
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
      

      {/* Loading indicator */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-sm z-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Carregant dades del mapa...</p>
          </div>
        </div>
      )}

      {/* Legend */}
      {!loading && (
        <div className="absolute bottom-4 right-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4">
          <div className="mb-3">
            <div className="text-sm font-semibold mb-2">Nivells de Risc dels Comptadors</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#00a8ff]"></div>
                <span>Normal (&lt;50%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#ffb800]"></div>
                <span>Avis (50-80%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#e74c3c]"></div>
                <span>Alerta (≥80%)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="absolute inset-0 pointer-events-none bg-gradient-to-b from-transparent via-transparent to-background/5" />
    </div>
  );
};
