import React, { useState, useEffect } from 'react';
import { X, Volume2, AlertTriangle, TrendingUp, Calendar, MapPin, Droplets } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';

interface WaterMeter {
  id: string;
  name: string;
  coordinates: [number, number];
  status: 'normal' | 'warning' | 'alert';
  lastReading: number;
  predictedFailureRisk: number;
}

interface Alarm {
  id: string;
  meterId: string;
  meterName: string;
  type: 'high_consumption' | 'zero_consumption' | 'anomaly' | 'spike';
  severity: 'alert' | 'warning';
  title: string;
  description: string;
  data: {
    currentValue: number;
    meanValue: number;
    daysAffected: number;
    dates: string[];
    location?: string;
  };
  explanation: {
    whatIsHappening: string;
    whatCouldBeDone: string;
    whatUsuallyHappens: string;
  };
}

interface InsightsSheetProps {
  isOpen: boolean;
  onClose: () => void;
  meters: WaterMeter[];
}

// Generate mock location based on meter name/ID
const generateLocation = (meterName: string): string => {
  const districts = ['Eixample', 'Gràcia', 'Sant Martí', 'Les Corts', 'Ciutat Vella', 'Sants-Montjuïc'];
  const hash = meterName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return `${districts[hash % districts.length]}, Barcelona`;
};

// Generate mock alarms based on meters with alerts/warnings
const generateAlarms = (meters: WaterMeter[]): Alarm[] => {
  const alarms: Alarm[] = [];
  
  // Filter meters with alerts or warnings
  const problematicMeters = meters.filter(m => m.status === 'alert' || m.status === 'warning');
  
  // Create sample alarms - prioritize alert status meters
  problematicMeters.slice(0, 10).forEach((meter, index) => {
    const location = generateLocation(meter.name);
    
    if (index === 0) {
      // First alarm: The user's example - 2 days with 5000l while mean is 100
      alarms.push({
        id: `alarm-${meter.id}`,
        meterId: meter.id,
        meterName: meter.name,
        type: 'high_consumption',
        severity: 'alert',
        title: 'Unusually High Consumption Detected',
        description: 'Two consecutive days with extremely high consumption values',
        data: {
          currentValue: 5000,
          meanValue: 100,
          daysAffected: 2,
          dates: ['2024-01-15', '2024-01-16'],
          location
        },
        explanation: {
          whatIsHappening: `This water meter (${meter.name}) has recorded consumption of 5,000 liters on two consecutive days (January 15-16, 2024), which is 50 times higher than the monthly average of 100 liters. This represents a 4,900% increase from normal consumption patterns. Such a dramatic spike typically indicates either a significant water leak, meter malfunction, or unusual activity at the property.`,
          whatCouldBeDone: `1. **Immediate Inspection**: Dispatch a technician to the location within 24 hours to verify the meter readings and check for visible leaks.\n\n2. **Leak Detection**: Conduct a thorough inspection of the property's water system, including pipes, fixtures, and connections. Check for signs of water damage or unusual water flow.\n\n3. **Meter Verification**: Test the meter's accuracy by comparing readings with a calibrated device. If the meter is faulty, replace it immediately.\n\n4. **Property Contact**: Notify the property owner or tenant about the anomaly and request information about any recent activities that might explain the spike (e.g., filling a pool, construction work, etc.).\n\n5. **Continuous Monitoring**: Increase monitoring frequency for this meter to track if the pattern continues or resolves.`,
          whatUsuallyHappens: `In similar cases, approximately 60% of high consumption spikes are caused by water leaks (often in underground pipes or within building infrastructure). About 25% are due to meter malfunctions or reading errors. The remaining 15% are typically explained by legitimate but unusual activities such as pool filling, construction work, or industrial use. Most leaks are detected within 48 hours of the initial spike, and prompt action usually prevents significant water waste and property damage. Historical data shows that meters with this pattern that are addressed within 48 hours have a 90% resolution rate.`
        }
      });
    } else if (index === 1) {
      // Second alarm: Zero consumption
      alarms.push({
        id: `alarm-${meter.id}`,
        meterId: meter.id,
        meterName: meter.name,
        type: 'zero_consumption',
        severity: meter.status === 'alert' ? 'alert' : 'warning',
        title: 'Zero Consumption Pattern',
        description: 'Multiple consecutive days with zero consumption detected',
        data: {
          currentValue: 0,
          meanValue: 150,
          daysAffected: 5,
          dates: ['2024-01-12', '2024-01-13', '2024-01-14', '2024-01-15', '2024-01-16'],
          location
        },
        explanation: {
          whatIsHappening: `Meter ${meter.name} has recorded zero consumption for 5 consecutive days, which is unusual given its historical average of 150 liters per day. This pattern suggests either a meter malfunction, a closed main water valve, or the property being unoccupied.`,
          whatCouldBeDone: `1. Verify meter functionality and connectivity\n2. Check if the property is occupied\n3. Inspect the main water valve\n4. Review recent maintenance records`,
          whatUsuallyHappens: `Zero consumption patterns are typically caused by meter failures (40%), vacant properties (35%), or closed valves (25%). Most cases resolve within a week after intervention.`
        }
      });
    } else {
      // Other alarms: Various types
      const types: Alarm['type'][] = ['anomaly', 'spike', 'high_consumption'];
      const type = types[index % types.length];
      
      alarms.push({
        id: `alarm-${meter.id}`,
        meterId: meter.id,
        meterName: meter.name,
        type,
        severity: meter.status === 'alert' ? 'alert' : 'warning',
        title: type === 'anomaly' ? 'Consumption Anomaly Detected' : 'Consumption Spike',
        description: `Unusual consumption pattern detected for meter ${meter.name}`,
        data: {
          currentValue: meter.lastReading,
          meanValue: Math.round(meter.lastReading * 0.3),
          daysAffected: 1 + (index % 3),
          dates: ['2024-01-16'],
          location
        },
        explanation: {
          whatIsHappening: `Meter ${meter.name} is showing unusual consumption patterns that deviate significantly from its historical average. The current readings indicate potential issues that require investigation.`,
          whatCouldBeDone: `1. Review recent consumption data\n2. Schedule maintenance inspection\n3. Monitor for pattern continuation\n4. Check for external factors affecting consumption`,
          whatUsuallyHappens: `Similar anomalies are often resolved through regular maintenance or are attributed to temporary usage patterns. Early detection helps prevent more serious issues.`
        }
      });
    }
  });
  
  return alarms;
};

export const InsightsSheet: React.FC<InsightsSheetProps> = ({ 
  isOpen, 
  onClose,
  meters
}) => {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [selectedAlarm, setSelectedAlarm] = useState<Alarm | null>(null);
  const [isPlayingVoice, setIsPlayingVoice] = useState(false);
  const [synth, setSynth] = useState<SpeechSynthesis | null>(null);

  // Initialize speech synthesis once
  useEffect(() => {
    if ('speechSynthesis' in window) {
      setSynth(window.speechSynthesis);
    }
  }, []);

  // Generate alarms when meters change or sheet opens
  useEffect(() => {
    if (isOpen && meters.length > 0) {
      const generatedAlarms = generateAlarms(meters);
      setAlarms(generatedAlarms);
      // Auto-select first alarm if available
      if (generatedAlarms.length > 0) {
        setSelectedAlarm(prev => {
          // Keep current selection if it still exists in the new list
          if (prev && generatedAlarms.find(a => a.id === prev.id)) {
            return prev;
          }
          return generatedAlarms[0];
        });
      } else {
        setSelectedAlarm(null);
      }
    } else if (!isOpen) {
      // Reset state when closed
      setSelectedAlarm(null);
      setAlarms([]);
    }
  }, [isOpen, meters]);

  const handlePlayVoice = () => {
    if (!selectedAlarm || !synth) return;

    if (isPlayingVoice) {
      synth.cancel();
      setIsPlayingVoice(false);
      return;
    }

    const text = `
      ${selectedAlarm.title}. 
      ${selectedAlarm.explanation.whatIsHappening}
      Recommended actions: ${selectedAlarm.explanation.whatCouldBeDone.replace(/\n\n/g, '. ').replace(/\d+\.\s+\*\*/g, '').replace(/\*\*/g, '')}
      What usually happens: ${selectedAlarm.explanation.whatUsuallyHappens}
    `;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 0.9;
    utterance.pitch = 1;
    utterance.volume = 1;

    utterance.onend = () => {
      setIsPlayingVoice(false);
    };

    utterance.onerror = () => {
      setIsPlayingVoice(false);
    };

    synth.speak(utterance);
    setIsPlayingVoice(true);
  };

  useEffect(() => {
    // Cleanup: cancel speech when component unmounts or closes
    return () => {
      if (synth) {
        synth.cancel();
        setIsPlayingVoice(false);
      }
    };
  }, [synth]);

  // Stop speech when sheet closes
  useEffect(() => {
    if (!isOpen && synth && isPlayingVoice) {
      synth.cancel();
      setIsPlayingVoice(false);
    }
  }, [isOpen, synth, isPlayingVoice]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-background/60 backdrop-blur-sm z-50 animate-fade-in"
        onClick={onClose}
      />
      
      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t border-border rounded-t-3xl shadow-2xl max-h-[85vh] overflow-hidden animate-slide-up flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-card/95 backdrop-blur-md border-b border-border px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              Insights & Alarms
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Active alarms and detailed explanations
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
        
        {/* Content Area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Sidebar - Alarm List */}
          <div className="w-80 border-r border-border bg-muted/20 flex flex-col">
            <div className="px-4 py-3 border-b border-border">
              <h3 className="text-sm font-semibold text-foreground">
                Active Alarms ({alarms.length})
              </h3>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-2">
                {alarms.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    No active alarms
                  </div>
                ) : (
                  alarms.map((alarm) => (
                    <button
                      key={alarm.id}
                      onClick={() => setSelectedAlarm(alarm)}
                      className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
                        selectedAlarm?.id === alarm.id
                          ? 'bg-primary/10 border-primary/50 shadow-sm'
                          : 'bg-card border-border hover:bg-muted/50 hover:border-primary/30'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <Badge 
                          variant={alarm.severity === 'alert' ? 'destructive' : 'secondary'}
                          className="text-xs"
                        >
                          {alarm.severity.toUpperCase()}
                        </Badge>
                        <AlertTriangle 
                          className={`w-4 h-4 flex-shrink-0 ${
                            alarm.severity === 'alert' ? 'text-destructive' : 'text-accent'
                          }`}
                        />
                      </div>
                      <h4 className="font-semibold text-sm text-foreground mb-1 line-clamp-1">
                        {alarm.meterName}
                      </h4>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {alarm.title}
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                        <Calendar className="w-3 h-3" />
                        <span>{alarm.data.daysAffected} day{alarm.data.daysAffected > 1 ? 's' : ''}</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>

          {/* Right Content - Detailed Explanation */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {selectedAlarm ? (
              <>
                <ScrollArea className="flex-1">
                  <div className="p-6 space-y-6">
                    {/* Alarm Header */}
                    <div className="bg-muted/30 rounded-xl p-4 border border-border">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            selectedAlarm.severity === 'alert' 
                              ? 'bg-destructive/10' 
                              : 'bg-accent/10'
                          }`}>
                            <AlertTriangle 
                              className={`w-5 h-5 ${
                                selectedAlarm.severity === 'alert' 
                                  ? 'text-destructive' 
                                  : 'text-accent'
                              }`}
                            />
                          </div>
                          <div>
                            <h3 className="font-semibold text-foreground">{selectedAlarm.title}</h3>
                            <p className="text-sm text-muted-foreground">{selectedAlarm.meterName}</p>
                          </div>
                        </div>
                        <Badge 
                          variant={selectedAlarm.severity === 'alert' ? 'destructive' : 'secondary'}
                        >
                          {selectedAlarm.severity.toUpperCase()}
                        </Badge>
                      </div>
                      
                      {/* Data Summary */}
                      <div className="grid grid-cols-3 gap-4 mt-4">
                        <div className="bg-background/50 rounded-lg p-3 border border-border">
                          <div className="flex items-center gap-2 mb-1">
                            <Droplets className="w-4 h-4 text-primary" />
                            <span className="text-xs text-muted-foreground">Current</span>
                          </div>
                          <p className="text-lg font-bold text-foreground">
                            {selectedAlarm.data.currentValue.toLocaleString()} L
                          </p>
                        </div>
                        <div className="bg-background/50 rounded-lg p-3 border border-border">
                          <div className="flex items-center gap-2 mb-1">
                            <TrendingUp className="w-4 h-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">Monthly Mean</span>
                          </div>
                          <p className="text-lg font-bold text-foreground">
                            {selectedAlarm.data.meanValue.toLocaleString()} L
                          </p>
                        </div>
                        <div className="bg-background/50 rounded-lg p-3 border border-border">
                          <div className="flex items-center gap-2 mb-1">
                            <Calendar className="w-4 h-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">Days Affected</span>
                          </div>
                          <p className="text-lg font-bold text-foreground">
                            {selectedAlarm.data.daysAffected}
                          </p>
                        </div>
                      </div>

                      {selectedAlarm.data.location && (
                        <div className="flex items-center gap-2 mt-3 text-sm text-muted-foreground">
                          <MapPin className="w-4 h-4" />
                          <span>{selectedAlarm.data.location}</span>
                        </div>
                      )}
                    </div>

                    {/* What is Happening */}
                    <div className="space-y-3">
                      <h4 className="font-semibold text-foreground flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-primary" />
                        What is Happening
                      </h4>
                      <div className="bg-muted/20 rounded-lg p-4 border border-border">
                        <p className="text-sm text-muted-foreground whitespace-pre-line">
                          {selectedAlarm.explanation.whatIsHappening}
                        </p>
                      </div>
                    </div>

                    {/* What Could Be Done */}
                    <div className="space-y-3">
                      <h4 className="font-semibold text-foreground flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-accent" />
                        What Could Be Done
                      </h4>
                      <div className="bg-muted/20 rounded-lg p-4 border border-border">
                        <p className="text-sm text-muted-foreground whitespace-pre-line">
                          {selectedAlarm.explanation.whatCouldBeDone}
                        </p>
                      </div>
                    </div>

                    {/* What Usually Happens */}
                    <div className="space-y-3">
                      <h4 className="font-semibold text-foreground flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-primary/70" />
                        What Usually Happens
                      </h4>
                      <div className="bg-muted/20 rounded-lg p-4 border border-border">
                        <p className="text-sm text-muted-foreground whitespace-pre-line">
                          {selectedAlarm.explanation.whatUsuallyHappens}
                        </p>
                      </div>
                    </div>
                  </div>
                </ScrollArea>

                {/* Voice Playback Footer */}
                <div className="border-t border-border px-6 py-4 bg-muted/10 flex items-center justify-between flex-shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center">
                      <Volume2 className="w-5 h-5 text-accent" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">Voice Explanation</p>
                      <p className="text-xs text-muted-foreground">
                        {isPlayingVoice ? 'Playing...' : 'Click to hear the explanation'}
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={handlePlayVoice}
                    size="lg"
                    className="bg-gradient-to-r from-accent to-[hsl(35,100%,72%)] hover:from-[hsl(35,100%,70%)] hover:to-accent text-accent-foreground"
                  >
                    <Volume2 className="w-4 h-4 mr-2" />
                    {isPlayingVoice ? 'Stop' : 'Play Voice'}
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center p-6">
                <div className="text-center text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Select an alarm from the list to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Disclaimer */}
        <div className="border-t border-border px-6 py-3 bg-muted/50 flex-shrink-0">
          <p className="text-xs text-muted-foreground text-center">
            This analysis is generated using AI-powered predictive models. Always verify findings with on-site inspection before taking action.
          </p>
        </div>
      </div>
    </>
  );
};

