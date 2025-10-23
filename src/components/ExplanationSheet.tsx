import React from 'react';
import { X, Droplets, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Button } from './ui/button';

interface ExplanationSheetProps {
  isOpen: boolean;
  onClose: () => void;
  type: 'text' | 'voice';
}

export const ExplanationSheet: React.FC<ExplanationSheetProps> = ({ 
  isOpen, 
  onClose,
  type 
}) => {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-background/60 backdrop-blur-sm z-50 animate-fade-in"
        onClick={onClose}
      />
      
      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t border-border rounded-t-3xl shadow-2xl max-h-[80vh] overflow-y-auto animate-slide-up">
        <div className="sticky top-0 bg-card/95 backdrop-blur-md border-b border-border px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              {type === 'text' ? 'Prediction Explanation' : 'Voice Explanation'}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Understanding water meter failure predictions
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
        
        <div className="px-6 py-6 space-y-6">
          {type === 'voice' && (
            <div className="bg-accent/10 border border-accent/20 rounded-xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center animate-glow-pulse">
                <Droplets className="w-5 h-5 text-accent" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Voice playback ready</p>
                <p className="text-xs text-muted-foreground">Click play to hear the explanation</p>
              </div>
              <Button size="sm" className="ml-auto">
                Play Audio
              </Button>
            </div>
          )}
          
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Predictive Model</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Our AI analyzes historical usage patterns, environmental factors, and maintenance records 
                  to predict potential meter failures before they occur. The model uses machine learning 
                  to identify subtle anomalies that indicate degradation.
                </p>
              </div>
            </div>
            
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-accent" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Risk Levels</h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-3">
                  Each meter is assigned a risk score based on multiple factors:
                </p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-3 h-3 rounded-full bg-destructive" />
                    <span className="font-medium text-destructive">High Risk (80-100%)</span>
                    <span className="text-muted-foreground">- Immediate attention needed</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-3 h-3 rounded-full bg-accent" />
                    <span className="font-medium text-accent">Medium Risk (50-80%)</span>
                    <span className="text-muted-foreground">- Monitor closely</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-3 h-3 rounded-full bg-primary" />
                    <span className="font-medium text-primary">Low Risk (0-50%)</span>
                    <span className="text-muted-foreground">- Normal operation</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <CheckCircle2 className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Proactive Maintenance</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  By identifying at-risk meters early, maintenance teams can schedule preventive 
                  interventions, reducing unexpected failures and service disruptions. This approach 
                  saves costs and improves water infrastructure reliability across Barcelona.
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-muted/50 rounded-xl p-4 border border-border">
            <p className="text-xs text-muted-foreground text-center">
              This is a mockup demonstration of the water meter failure prediction system. 
              Data shown is simulated for visualization purposes.
            </p>
          </div>
        </div>
      </div>
    </>
  );
};
