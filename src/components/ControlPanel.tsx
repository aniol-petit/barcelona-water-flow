import React from 'react';
import { Lightbulb, BarChart3 } from 'lucide-react';
import { Button } from './ui/button';

interface ControlPanelProps {
  onInsights: () => void;
  onDashboard: () => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  onInsights,
  onDashboard
}) => {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 animate-fade-in">
      <div className="glass-effect rounded-3xl shadow-2xl px-8 py-5 border border-border/50">
        <div className="flex items-center gap-3">
          {/* Insights Button */}
          <Button
            onClick={onInsights}
            size="lg"
            className="h-12 px-6 bg-gradient-to-r from-primary to-primary-glow hover:from-primary-glow hover:to-primary text-primary-foreground shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/40 hover:scale-105 transition-all duration-300 rounded-xl font-semibold"
          >
            <Lightbulb className="w-4 h-4 mr-2" />
            Informació
          </Button>
          
          <div className="h-8 w-px bg-border/50" />
          
          {/* Dashboard Button */}
          <Button
            onClick={onDashboard}
            variant="outline"
            size="lg"
            className="h-12 px-5 border-2 border-primary/30 hover:border-primary/50 hover:bg-primary/5 text-primary hover:text-primary-glow hover:scale-105 transition-all duration-300 rounded-xl font-semibold"
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Tauler
          </Button>
        </div>
      </div>
    </div>
  );
};
