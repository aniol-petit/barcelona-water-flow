import React, { useState } from 'react';
import { X, MapPin, Droplets, AlertTriangle, CheckCircle2, Clock, Gauge, Search } from 'lucide-react';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';

interface WaterMeter {
  id: string;
  coordinates: [number, number];
  status: 'normal' | 'warning' | 'alert';
  lastReading: number;
  predictedFailureRisk: number;
  name?: string;
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

  const names = [
    'Meter Alpha-001',
    'Meter Beta-002', 
    'Meter Gamma-003',
    'Meter Delta-004',
    'Meter Epsilon-005',
    'Meter Zeta-006',
    'Meter Eta-007',
    'Meter Theta-008',
    'Meter Iota-009',
    'Meter Kappa-010'
  ];

  // Use meter ID to ensure consistent data for the same meter
  const nameIndex = parseInt(meter.id.split('-')[1]) % names.length;
  const locationIndex = parseInt(meter.id.split('-')[1]) % locations.length;

  return {
    ...meter,
    name: names[nameIndex],
    location: locations[locationIndex],
    lastMaintenance: '12/15/2024',
    installationDate: '06/20/2022'
  };
};

export const Dashboard: React.FC<DashboardProps> = ({ isOpen, onClose, meters }) => {
  const [selectedTab, setSelectedTab] = useState('normal');
  const [searchQuery, setSearchQuery] = useState('');

  if (!isOpen) return null;

  // Generate mock data for all meters
  const metersWithData = meters.length > 0 ? meters.map(generateMockMeterData) : [];

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
  const normalMeters = filterMeters(metersWithData.filter(m => m.status === 'normal'));
  const warningMeters = filterMeters(metersWithData.filter(m => m.status === 'warning'));
  const alertMeters = filterMeters(metersWithData.filter(m => m.status === 'alert'));

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
        return <Badge variant="destructive">Alert</Badge>;
      case 'warning':
        return <Badge variant="secondary" className="bg-accent text-accent-foreground">Warning</Badge>;
      default:
        return <Badge variant="default">Normal</Badge>;
    }
  };

  const MeterCard = ({ meter }: { meter: WaterMeter }) => (
    <Card className="hover:shadow-md transition-shadow">
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
        
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="flex items-center gap-1">
            <Droplets className="w-3 h-3 text-primary" />
            <span className="text-muted-foreground">Reading:</span>
            <span className="font-medium">{meter.lastReading.toLocaleString()} L</span>
          </div>
          <div className="flex items-center gap-1">
            <Gauge className="w-3 h-3 text-accent" />
            <span className="text-muted-foreground">Risk:</span>
            <span className="font-medium">{Math.round(meter.predictedFailureRisk)}%</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-muted-foreground" />
            <span className="text-muted-foreground">Last Maint:</span>
            <span className="font-medium">{meter.lastMaintenance}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-muted-foreground" />
            <span className="text-muted-foreground">Installed:</span>
            <span className="font-medium">{meter.installationDate}</span>
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
      <div className="fixed inset-4 z-50 bg-card border border-border rounded-2xl shadow-2xl animate-slide-up overflow-hidden">
        <div className="sticky top-0 bg-card/95 backdrop-blur-md border-b border-border px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-foreground">Water Meter Dashboard</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Monitor all water meters across Barcelona
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
              placeholder="Search by meter name, location, or ID..."
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
        
        <div className="p-6 h-[calc(100vh-8rem)] overflow-y-auto">
          <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6">
              <TabsTrigger value="normal" className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Normal ({normalMeters.length})
              </TabsTrigger>
              <TabsTrigger value="warning" className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Warning ({warningMeters.length})
              </TabsTrigger>
              <TabsTrigger value="alert" className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Alert ({alertMeters.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="normal" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {normalMeters.map((meter) => (
                  <MeterCard key={meter.id} meter={meter} />
                ))}
              </div>
              {normalMeters.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>{searchQuery ? 'No normal meters found matching your search' : 'No normal meters to display'}</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="warning" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {warningMeters.map((meter) => (
                  <MeterCard key={meter.id} meter={meter} />
                ))}
              </div>
              {warningMeters.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>{searchQuery ? 'No warning meters found matching your search' : 'No warning meters to display'}</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="alert" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {alertMeters.map((meter) => (
                  <MeterCard key={meter.id} meter={meter} />
                ))}
              </div>
              {alertMeters.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>{searchQuery ? 'No alert meters found matching your search' : 'No alert meters to display'}</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </>
  );
};
