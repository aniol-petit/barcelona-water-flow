import React, { useState } from 'react';
import { WaterMeterMap } from '@/components/WaterMeterMap';
import { ControlPanel } from '@/components/ControlPanel';
import { InsightsSheet } from '@/components/InsightsSheet';
import { Dashboard } from '@/components/Dashboard';
import { Droplets, Activity, TrendingUp, Shield } from 'lucide-react';

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
}

const Index = () => {
  const [insightsOpen, setInsightsOpen] = useState(false);
  const [simulateAlert, setSimulateAlert] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [selectedMeter, setSelectedMeter] = useState<WaterMeter | null>(null);
  const [allMeters, setAllMeters] = useState<WaterMeter[]>([]);
  const [filterStatus, setFilterStatus] = useState<{normal: boolean, warning: boolean, alert: boolean}>({
    normal: true,
    warning: true,
    alert: true
  });

  const handleInsights = () => {
    setInsightsOpen(true);
  };

  const handleDashboard = () => {
    setDashboardOpen(true);
  };

  const handleMeterSelect = (meter: WaterMeter | null) => {
    setSelectedMeter(meter);
    if (meter) {
      console.log('Selected meter:', meter);
    }
  };

  const handleMetersChange = (meters: WaterMeter[]) => {
    setAllMeters(meters);
  };

  // Calculate stats for the header
  const stats = {
    total: allMeters.length,
    normal: allMeters.filter(m => m.status === 'normal').length,
    warning: allMeters.filter(m => m.status === 'warning').length,
    alert: allMeters.filter(m => m.status === 'alert').length,
    avgRisk: allMeters.length > 0 
      ? (allMeters.reduce((sum, m) => sum + (m.risk_percent || m.predictedFailureRisk || 0), 0) / allMeters.length).toFixed(1)
      : '0'
  };

  return (
    <div className="relative min-h-screen w-full bg-gradient-to-br from-background via-background to-primary/5 overflow-hidden">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(200,90%,50%,0.03),transparent_50%)]" />
      
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-30 glass-effect border-b border-border/50 shadow-medium">
        <div className="container mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            {/* Logo & Branding */}
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="w-12 h-12 rounded-2xl gradient-primary flex items-center justify-center shadow-glow-primary">
                  <Droplets className="w-6 h-6 text-primary-foreground" strokeWidth={2.5} />
                </div>
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-accent rounded-full shadow-glow-accent animate-gentle-pulse" />
              </div>
                             <div>
                 <p className="text-sm text-muted-foreground font-medium">
                   FlowGuard
                 </p>
               </div>
            </div>
            
            {/* Stats Cards */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                {/* Total Meters */}
                <div className="glass-effect rounded-xl px-4 py-2.5 border border-border/50">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-primary" />
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Total</p>
                      <p className="text-lg font-bold text-foreground">{stats.total}</p>
                    </div>
                  </div>
                </div>

                {/* Normal Status */}
                <button
                  onClick={() => setFilterStatus({...filterStatus, normal: !filterStatus.normal})}
                  className={`glass-effect rounded-xl px-4 py-2.5 border transition-all duration-300 ${
                    filterStatus.normal 
                      ? 'border-primary/30 hover:border-primary/50 bg-primary/5' 
                      : 'border-border/30 hover:border-border/50 opacity-40'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-primary shadow-glow-primary" />
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Normal</p>
                      <p className="text-lg font-bold text-primary">{stats.normal}</p>
                    </div>
                  </div>
                </button>

                {/* Warning Status */}
                <button
                  onClick={() => setFilterStatus({...filterStatus, warning: !filterStatus.warning})}
                  className={`glass-effect rounded-xl px-4 py-2.5 border transition-all duration-300 ${
                    filterStatus.warning 
                      ? 'border-accent/30 hover:border-accent/50 bg-accent/5' 
                      : 'border-border/30 hover:border-border/50 opacity-40'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-accent" />
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Avis</p>
                      <p className="text-lg font-bold text-accent">{stats.warning}</p>
                    </div>
                  </div>
                </button>

                {/* Alert Status */}
                <button
                  onClick={() => setFilterStatus({...filterStatus, alert: !filterStatus.alert})}
                  className={`glass-effect rounded-xl px-4 py-2.5 border transition-all duration-300 ${
                    filterStatus.alert 
                      ? 'border-destructive/30 hover:border-destructive/50 bg-destructive/5' 
                      : 'border-border/30 hover:border-border/50 opacity-40'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-destructive" />
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Alerta</p>
                      <p className="text-lg font-bold text-destructive">{stats.alert}</p>
                    </div>
                  </div>
                </button>

                {/* Average Risk */}
                <div className="glass-effect rounded-xl px-4 py-2.5 border border-border/50 hover:border-primary/30 transition-all duration-300">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Risc Mitjà</p>
                      <p className="text-lg font-bold text-foreground">{stats.avgRisk}%</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Map Container */}
      <div className="h-screen w-full p-6 pt-32">
        <div className="h-full w-full rounded-3xl overflow-hidden shadow-2xl border border-border/50 bg-card/50 backdrop-blur-sm">
          <WaterMeterMap
            onMeterSelect={handleMeterSelect}
            onMetersChange={handleMetersChange}
            filterStatus={filterStatus}
          />
        </div>
      </div>

      {/* Control Panel */}
      <ControlPanel
        onInsights={handleInsights}
        onDashboard={handleDashboard}
      />

      {/* Insights Sheet */}
      <InsightsSheet
        isOpen={insightsOpen}
        onClose={() => setInsightsOpen(false)}
        meters={allMeters}
      />

      {/* Dashboard */}
      <Dashboard
        isOpen={dashboardOpen}
        onClose={() => setDashboardOpen(false)}
        meters={allMeters}
      />
    </div>
  );
};

export default Index;
