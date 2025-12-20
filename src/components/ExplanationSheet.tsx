import React from 'react';
import { X, Droplets, TrendingUp, AlertTriangle, CheckCircle2, Wrench, Clock, MapPin } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

interface WaterMeter {
  id: string;
  coordinates: [number, number];
  status: 'normal' | 'warning' | 'alert';
  lastReading: number;
  predictedFailureRisk: number;
  risk_percent?: number;
  risk_percent_base?: number;
  subcount_percent?: number;
  name?: string;
  location?: string;
}

interface ExplanationSheetProps {
  isOpen: boolean;
  onClose: () => void;
  type: 'text' | 'voice';
  selectedMeter?: WaterMeter | null;
}

export const ExplanationSheet: React.FC<ExplanationSheetProps> = ({ 
  isOpen, 
  onClose,
  type,
  selectedMeter
}) => {
  if (!isOpen) return null;

  // Generate mock failure explanation based on meter status
  const generateFailureExplanation = (meter: WaterMeter | null) => {
    if (!meter) {
      return {
        title: "No Meter Selected",
        description: "Please select a water meter from the map to view its failure analysis.",
        issues: [],
        actions: [],
        urgency: "info"
      };
    }

    const risk = meter.risk_percent ?? meter.predictedFailureRisk;
    const issues = [];
    const actions = [];

    if (meter.status === 'alert') {
      issues.push(
        "Abnormal water flow patterns detected",
        "Internal mechanism showing signs of wear",
        "Temperature fluctuations affecting accuracy",
        "Potential leak in the meter housing"
      );
      actions.push(
        "Immediate on-site inspection required",
        "Replace meter within 24-48 hours",
        "Check surrounding pipe connections",
        "Notify residents of temporary service interruption"
      );
    } else if (meter.status === 'warning') {
      issues.push(
        "Gradual decrease in measurement accuracy",
        "Minor internal component degradation",
        "Slight temperature sensitivity detected"
      );
      actions.push(
        "Schedule maintenance within 1-2 weeks",
        "Monitor readings more frequently",
        "Prepare replacement meter for installation",
        "Document current readings for comparison"
      );
    } else {
      issues.push(
        "All systems operating within normal parameters",
        "No significant anomalies detected",
        "Regular maintenance schedule adequate"
      );
      actions.push(
        "Continue regular monitoring",
        "Maintain current maintenance schedule",
        "No immediate action required"
      );
    }

    return {
      title: `${meter.name || `Meter ${meter.id}`} - Failure Analysis`,
      description: `Risk Assessment: ${Math.round(risk)}% failure probability`,
      issues,
      actions,
      urgency: meter.status
    };
  };

  const explanation = generateFailureExplanation(selectedMeter);

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
              {type === 'text' ? 'Meter Failure Analysis' : 'Voice Analysis'}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Technical assessment and recommended actions
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
                <p className="text-sm font-medium text-foreground">Voice analysis ready</p>
                <p className="text-xs text-muted-foreground">Click play to hear the technical assessment</p>
              </div>
              <Button size="sm" className="ml-auto">
                Play Audio
              </Button>
            </div>
          )}

          {/* Meter Info */}
          {selectedMeter && (
            <div className="bg-muted/30 rounded-xl p-4 border border-border">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-foreground">{explanation.title}</h3>
                <Badge 
                  variant={explanation.urgency === 'alert' ? 'destructive' : 
                          explanation.urgency === 'warning' ? 'secondary' : 'default'}
                  className={explanation.urgency === 'warning' ? 'bg-accent text-accent-foreground' : ''}
                >
                  {explanation.urgency.toUpperCase()}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">{explanation.description}</p>
              
              {/* Risk Scores Breakdown */}
              <div className="grid grid-cols-3 gap-2 mb-3 p-2 bg-background/50 rounded-lg border border-border/50">
                <div className="text-center">
                  <div className="text-xs text-muted-foreground mb-1">Base Risk</div>
                  <div className="text-sm font-semibold text-foreground">
                    {Math.round(selectedMeter.risk_percent_base ?? selectedMeter.predictedFailureRisk ?? 0)}%
                  </div>
                </div>
                {selectedMeter.subcount_percent !== undefined && (
                  <div className="text-center">
                    <div className="text-xs text-muted-foreground mb-1">Subcounting</div>
                    <div className="text-sm font-semibold text-foreground">
                      {Math.round(selectedMeter.subcount_percent)}%
                    </div>
                  </div>
                )}
                <div className="text-center border-l border-border/50 pl-2">
                  <div className="text-xs text-muted-foreground mb-1">Final Risk</div>
                  <div className="text-sm font-bold text-foreground">
                    {Math.round(selectedMeter.risk_percent ?? selectedMeter.predictedFailureRisk ?? 0)}%
                  </div>
                </div>
              </div>
              
              {selectedMeter.location && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <MapPin className="w-4 h-4" />
                  <span>{selectedMeter.location}</span>
                </div>
              )}
            </div>
          )}
          
          {/* Issues Detected */}
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-destructive/10 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-destructive" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Issues Detected</h3>
                <div className="space-y-2">
                  {explanation.issues.map((issue, index) => (
                    <div key={index} className="flex items-start gap-2 text-sm">
                      <div className="w-1.5 h-1.5 rounded-full bg-destructive mt-2 flex-shrink-0" />
                      <span className="text-muted-foreground">{issue}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            {/* Recommended Actions */}
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <Wrench className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Recommended Actions</h3>
                <div className="space-y-2">
                  {explanation.actions.map((action, index) => (
                    <div key={index} className="flex items-start gap-2 text-sm">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                      <span className="text-muted-foreground">{action}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Priority Timeline */}
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
                <Clock className="w-5 h-5 text-accent" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground mb-2">Priority Timeline</h3>
                <div className="text-sm text-muted-foreground">
                  {explanation.urgency === 'alert' ? (
                    <p>🚨 <strong>URGENT:</strong> Immediate action required within 24-48 hours to prevent service disruption.</p>
                  ) : explanation.urgency === 'warning' ? (
                    <p>⚠️ <strong>HIGH:</strong> Schedule maintenance within 1-2 weeks to prevent escalation.</p>
                  ) : (
                    <p>✅ <strong>NORMAL:</strong> Continue regular monitoring and maintenance schedule.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-muted/50 rounded-xl p-4 border border-border">
            <p className="text-xs text-muted-foreground text-center">
              This analysis is generated using AI-powered predictive models. 
              Always verify findings with on-site inspection before taking action.
            </p>
          </div>
        </div>
      </div>
    </>
  );
};
