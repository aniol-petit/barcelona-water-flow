import React, { useState } from 'react';
import { X, MapPin, Droplets, AlertTriangle, CheckCircle2, Clock, Gauge, Search, TrendingUp } from 'lucide-react';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';

interface WaterMeter {
  id: string;
  coordinates: [number, number];
  status: 'normal' | 'warning' | 'alert';
  risk_percent: number; // Final combined risk (0-100)
  risk_percent_base?: number; // Base risk from anomaly + degradation (0-100)
  subcount_percent?: number; // Subcounting probability (0-100)
  cluster_id?: number;
  seccio_censal?: string;
  age?: number;
  canya?: number;
  last_month_consumption?: number;
  // Legacy fields for compatibility
  name?: string;
  lastReading?: number;
  predictedFailureRisk?: number;
  location?: string;
  lastMaintenance?: string;
  installationDate?: string;
}

interface DashboardProps {
  isOpen: boolean;
  onClose: () => void;
  meters: WaterMeter[];
}

// Mock data for demonstration
const generateMockMeterData = (meter: WaterMeter): WaterMeter => {
  const locations = [
    'Carrer de la Pau, 12',
    'Plaça de Catalunya, 8',
    'Avinguda Diagonal, 245',
    'Carrer de Balmes, 156',
    'Passeig de Gràcia, 78',
    'Carrer de Mallorca, 234',
    'Avinguda de Sarrià, 45',
    'Carrer de València, 189',
    'Plaça de Sant Jaume, 3',
    'Carrer de la Rambla, 67'
  ];

  // Use meter ID to ensure consistent data for the same meter
  // Create a hash from the meter ID for consistent location assignment
  const idHash = meter.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const locationIndex = idHash % locations.length;

  return {
    ...meter,
    location: locations[locationIndex],
    lastMaintenance: '12/15/2024',
    installationDate: '06/20/2022'
  };
};

export const Dashboard: React.FC<DashboardProps> = ({ isOpen, onClose, meters }) => {
  const [selectedTab, setSelectedTab] = useState('normal');
  const [searchQuery, setSearchQuery] = useState('');
  const [displayLimit, setDisplayLimit] = useState(70);

  if (!isOpen) return null;

  // Generate mock data for all meters, ensuring name field exists
  const metersWithData = (meters && meters.length > 0) ? meters.map(meter => {
    const meterWithName = {
      ...meter,
      name: meter.name || `Comptador ${meter.id}`
    };
    return generateMockMeterData(meterWithName);
  }) : [];

  // Filter meters by status and search query
  const filterMeters = (meters: WaterMeter[]) => {
    if (!searchQuery.trim()) return meters;
    
    const query = searchQuery.toLowerCase();
    return meters.filter(meter => 
      meter.name?.toLowerCase().includes(query) ||
      meter.location?.toLowerCase().includes(query) ||
      meter.id.toLowerCase().includes(query)
    );
  };

  // Filter meters by status first, then by search query
  const normalMetersAll = filterMeters(metersWithData.filter(m => m.status === 'normal'));
  const warningMetersAll = filterMeters(metersWithData.filter(m => m.status === 'warning'));
  const alertMetersAll = filterMeters(metersWithData.filter(m => m.status === 'alert'));
  
  // Apply pagination - show only first N meters per tab
  const normalMeters = normalMetersAll.slice(0, displayLimit);
  const warningMeters = warningMetersAll.slice(0, displayLimit);
  const alertMeters = alertMetersAll.slice(0, displayLimit);
  
  // Check if there are more meters to load
  // If total > displayLimit, there are more to show
  const hasMoreNormal = normalMetersAll.length > displayLimit;
  const hasMoreWarning = warningMetersAll.length > displayLimit;
  const hasMoreAlert = alertMetersAll.length > displayLimit;
  
  // Handle load more
  const handleLoadMore = () => {
    setDisplayLimit(prev => prev + 70);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'alert':
        return <AlertTriangle className="w-4 h-4 text-destructive" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-accent" />;
      default:
        return <CheckCircle2 className="w-4 h-4 text-primary" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'alert':
        return <Badge variant="destructive">Alerta</Badge>;
      case 'warning':
        return <Badge variant="secondary" className="bg-accent text-accent-foreground">Avis</Badge>;
      default:
        return <Badge variant="default">Normal</Badge>;
    }
  };

  const MeterCard = ({ meter }: { meter: WaterMeter }) => (
    <Card className="hover:shadow-lg hover:border-primary/20 transition-all duration-300 bg-card/50 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getStatusIcon(meter.status)}
            <CardTitle className="text-sm font-medium">{meter.name}</CardTitle>
          </div>
          {getStatusBadge(meter.status)}
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <MapPin className="w-3 h-3" />
          <span className="truncate">{meter.location}</span>
        </div>
        
        <div className="space-y-2">
          {/* Risk Scores Section */}
          <div className="bg-muted/30 rounded-lg p-2 space-y-1.5 border border-border/50">
            <div className="text-xs font-semibold text-muted-foreground mb-1.5">Puntuacions de Risc</div>
            <div className="grid grid-cols-1 gap-1.5 text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <Gauge className="w-3 h-3 text-primary" />
                  <span className="text-muted-foreground">Risc Base:</span>
                </div>
                <span className="font-medium text-foreground">
                  {Math.round(meter.risk_percent_base ?? meter.risk_percent ?? meter.predictedFailureRisk ?? 0)}%
                </span>
              </div>
              {meter.subcount_percent !== undefined && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <TrendingUp className="w-3 h-3 text-accent" />
                    <span className="text-muted-foreground">Subcomptatge:</span>
                  </div>
                  <span className="font-medium text-foreground">
                    {Math.round(meter.subcount_percent)}%
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between pt-1 border-t border-border/50">
                <div className="flex items-center gap-1">
                  <Gauge className="w-3 h-3 text-destructive" />
                  <span className="text-muted-foreground font-semibold">Risc Final:</span>
                </div>
                <span className="font-bold text-foreground">
                  {Math.round(meter.risk_percent || meter.predictedFailureRisk || 0)}%
                </span>
              </div>
            </div>
          </div>
          
          {/* Other Metrics */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="flex items-center gap-1">
              <Droplets className="w-3 h-3 text-primary" />
              <span className="text-muted-foreground">Darrer Mes:</span>
              <span className="font-medium">
                {meter.last_month_consumption ? Math.round(meter.last_month_consumption).toLocaleString() : 'N/A'} L
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-muted-foreground" />
              <span className="text-muted-foreground">Edat:</span>
              <span className="font-medium">
                {meter.age ? meter.age.toFixed(1) : 'N/A'} anys
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Droplets className="w-3 h-3 text-muted-foreground" />
              <span className="text-muted-foreground">Canya:</span>
              <span className="font-medium">
                {meter.canya ? Math.round(meter.canya).toLocaleString() : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-background/60 backdrop-blur-sm z-50 animate-fade-in"
        onClick={onClose}
      />
      
      {/* Dashboard */}
      <div className="fixed inset-4 z-50 glass-effect rounded-3xl shadow-2xl animate-slide-up overflow-hidden">
        <div className="sticky top-0 glass-effect border-b border-border/50 px-6 py-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-3xl font-bold tracking-tight">
                <span className="text-gradient-primary">Comptadors</span>
              </h2>
              <p className="text-sm text-muted-foreground mt-1.5 font-medium">
                Monitorització de tots els comptadors d'aigua a Barcelona
              </p>
            </div>
            <Button
              onClick={onClose}
              variant="ghost"
              size="icon"
              className="hover:bg-muted/50"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
          
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              type="text"
              placeholder="Cerca per nom, localització, ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 w-full max-w-md"
            />
            {searchQuery && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0 hover:bg-muted/50"
              >
                <X className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>
        
        <div className="p-6 pb-20 h-[calc(100vh-8rem)] overflow-y-auto">
          <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6">
              <TabsTrigger value="normal" className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Normal ({normalMetersAll.length})
              </TabsTrigger>
              <TabsTrigger value="warning" className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Avis ({warningMetersAll.length})
              </TabsTrigger>
              <TabsTrigger value="alert" className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Alerta ({alertMetersAll.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="normal" className="space-y-4">
              {normalMeters.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>{searchQuery ? 'No s\'han trobat comptadors normals que coincideixin amb la cerca' : 'No hi ha comptadors normals per mostrar'}</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {normalMeters.map((meter) => (
                      <MeterCard key={meter.id} meter={meter} />
                    ))}
                  </div>
                  {hasMoreNormal ? (
                    <div className="w-full flex justify-center py-4">
                      <Button onClick={handleLoadMore} variant="outline" size="lg" className="px-8">
                        Carregar Més ({normalMetersAll.length - normalMeters.length} restants)
                      </Button>
                    </div>
                  ) : null}
                </>
              )}
            </TabsContent>

            <TabsContent value="warning" className="space-y-4">
              {warningMeters.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>{searchQuery ? 'No s\'han trobat comptadors amb avis que coincideixin amb la cerca' : 'No hi ha comptadors amb avis per mostrar'}</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {warningMeters.map((meter) => (
                      <MeterCard key={meter.id} meter={meter} />
                    ))}
                  </div>
                  {hasMoreWarning ? (
                    <div className="w-full flex justify-center py-4">
                      <Button onClick={handleLoadMore} variant="outline" size="lg" className="px-8">
                        Carregar Més ({warningMetersAll.length - warningMeters.length} restants)
                      </Button>
                    </div>
                  ) : null}
                </>
              )}
            </TabsContent>

            <TabsContent value="alert" className="space-y-4">
              {alertMeters.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>{searchQuery ? 'No s\'han trobat comptadors amb alerta que coincideixin amb la cerca' : 'No hi ha comptadors amb alerta per mostrar'}</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {alertMeters.map((meter) => (
                      <MeterCard key={meter.id} meter={meter} />
                    ))}
                  </div>
                  {hasMoreAlert ? (
                    <div className="w-full flex justify-center py-4">
                      <Button onClick={handleLoadMore} variant="outline" size="lg" className="px-8">
                        Carregar Més ({alertMetersAll.length - alertMeters.length} restants)
                      </Button>
                    </div>
                  ) : null}
                </>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </>
  );
};
