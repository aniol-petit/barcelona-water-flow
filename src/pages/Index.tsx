import React, { useState } from 'react';
import { WaterMeterMap } from '@/components/WaterMeterMap';
import { ControlPanel } from '@/components/ControlPanel';
import { ExplanationSheet } from '@/components/ExplanationSheet';
import { MapboxTokenInput } from '@/components/MapboxTokenInput';
import { Droplets } from 'lucide-react';

const Index = () => {
  const [explanationOpen, setExplanationOpen] = useState(false);
  const [explanationType, setExplanationType] = useState<'text' | 'voice'>('text');
  const [simulateAlert, setSimulateAlert] = useState(false);
  const [hasToken, setHasToken] = useState(false);

  const handleTextExplanation = () => {
    setExplanationType('text');
    setExplanationOpen(true);
  };

  const handleVoiceExplanation = () => {
    setExplanationType('voice');
    setExplanationOpen(true);
    // Simulate voice chime
    setTimeout(() => {
      console.log('🔊 Voice explanation starting...');
    }, 300);
  };

  const handleInfo = () => {
    setSimulateAlert(!simulateAlert);
  };

  return (
    <div className="relative min-h-screen w-full bg-background">
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-30 bg-gradient-to-b from-background/95 to-transparent backdrop-blur-sm">
        <div className="container mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-md">
                <Droplets className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">
                  Barcelona Water Intelligence
                </h1>
                <p className="text-sm text-muted-foreground">
                  Predictive meter failure monitoring
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="bg-card/80 backdrop-blur-sm border border-border rounded-xl px-4 py-2">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-primary" />
                    <span className="text-xs text-muted-foreground">Normal</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-accent" />
                    <span className="text-xs text-muted-foreground">Warning</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-destructive animate-glow-pulse" />
                    <span className="text-xs text-muted-foreground">Alert</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Map */}
      <div className="h-screen w-full p-6 pt-28">
        {!hasToken && (
          <div className="absolute top-32 left-1/2 -translate-x-1/2 z-40 max-w-xl w-full px-6">
            <MapboxTokenInput onTokenSave={() => setHasToken(true)} />
          </div>
        )}
        <WaterMeterMap
          simulateAlert={simulateAlert}
          onMeterSelect={(meter) => {
            if (meter) {
              console.log('Selected meter:', meter);
            }
          }}
        />
      </div>

      {/* Control Panel */}
      <ControlPanel
        onTextExplanation={handleTextExplanation}
        onVoiceExplanation={handleVoiceExplanation}
        onInfo={handleInfo}
      />

      {/* Explanation Sheet */}
      <ExplanationSheet
        isOpen={explanationOpen}
        onClose={() => setExplanationOpen(false)}
        type={explanationType}
      />
    </div>
  );
};

export default Index;
