import React, { useState, useEffect } from 'react';
import { X, Volume2, AlertTriangle, TrendingUp, Calendar, MapPin, Droplets } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';

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
    age?: number;
    canya?: number;
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

// Generate mock alarms based on top 20 riskiest meters
const generateAlarms = (meters: WaterMeter[]): Alarm[] => {
  const alarms: Alarm[] = [];
  
  // Sort by risk_percent (highest first) and take top 20
  const topRiskyMeters = [...meters]
    .sort((a, b) => (b.risk_percent || 0) - (a.risk_percent || 0))
    .slice(0, 20);
  
  // Create alarms for top 20 riskiest meters
  topRiskyMeters.forEach((meter, index) => {
    const meterName = meter.name || `Comptador ${meter.id}`;
    const location = generateLocation(meterName);
    const risk = meter.risk_percent || meter.predictedFailureRisk || 0;
    
    if (index === 0) {
      // First alarm: The user's example - 2 days with 5000l while mean is 100
      alarms.push({
        id: `alarm-${meter.id}`,
        meterId: meter.id,
        meterName: meterName,
        type: 'high_consumption',
        severity: risk >= 80 ? 'alert' : 'warning',
        title: `Risc Alt de Fallada Detectat (${risk.toFixed(1)}%)`,
        description: `El comptador té una puntuació de risc de fallada del ${risk.toFixed(1)}%, indicant possible subcomptatge o degradació`,
        data: {
          currentValue: meter.last_month_consumption ? Math.round(meter.last_month_consumption) : 0,
          meanValue: meter.canya && meter.age ? Math.round(meter.canya / meter.age) : 0,
          daysAffected: 2,
          dates: ['2024-01-15', '2024-01-16'],
          location,
          age: meter.age,
          canya: meter.canya
        },
        explanation: {
          whatIsHappening: `Aquest comptador d'aigua (${meterName}, ID: ${meter.id}) ha estat identificat com d'alt risc amb una puntuació de probabilitat de fallada del ${risk.toFixed(1)}%. La puntuació de risc combina el comportament anòmal dins del clúster i els factors de degradació a nivell de clúster. Això indica que el comptador mostra patrons de consum atípics dins del seu clúster comportamental i està ubicat en una àrea d'alta degradació, suggerint possible comportament de subcompte o degradació del comptador.`,
          whatCouldBeDone: `1. **Inspecció Immediata**: Enviar un tècnic a la ubicació en un termini de 24 hores per verificar les lectures del comptador i comprovar si hi ha fuites visibles.\n\n2. **Detecció de Fuites**: Realitzar una inspecció exhaustiva del sistema d'aigua de la propietat, incloent canonades, accessoris i connexions. Comprovar signes de danys per aigua o flux d'aigua inusual.\n\n3. **Verificació del Comptador**: Provar la precisió del comptador comparant les lectures amb un dispositiu calibrat. Si el comptador està defectuós, substituir-lo immediatament.\n\n4. **Contacte amb la Propietat**: Notificar al propietari o llogater sobre l'anomalia i sol·licitar informació sobre qualsevol activitat recent que pugui explicar el pic (per exemple, omplir una piscina, obres de construcció, etc.).\n\n5. **Monitorització Contínua**: Augmentar la freqüència de monitorització d'aquest comptador per fer un seguiment de si el patró continua o es resol.`,
          whatUsuallyHappens: `En casos similars, aproximadament el 60% dels pics de consum alt són causats per fuites d'aigua (sovint en canonades subterrànies o dins de la infraestructura de l'edifici). Al voltant del 25% es deuen a malfuncionaments del comptador o errors de lectura. El 15% restant normalment s'explica per activitats legítimes però inusuals com omplir una piscina, obres de construcció o ús industrial. La majoria de fuites es detecten en un termini de 48 hores des del pic inicial, i l'acció ràpida normalment evita un desaprofitament significatiu d'aigua i danys a la propietat. Les dades històriques mostren que els comptadors amb aquest patró que s'aborden en un termini de 48 hores tenen una taxa de resolució del 90%.`
        }
      });
    } else if (index === 1) {
      // Second alarm: Zero consumption
      alarms.push({
        id: `alarm-${meter.id}`,
        meterId: meter.id,
        meterName: meterName,
        type: 'zero_consumption',
        severity: risk >= 80 ? 'alert' : 'warning',
        title: 'Patró de Consum Zero',
        description: 'S\'han detectat múltiples dies consecutius amb consum zero',
        data: {
          currentValue: meter.last_month_consumption ? Math.round(meter.last_month_consumption) : 0,
          meanValue: meter.canya && meter.age ? Math.round(meter.canya / meter.age) : 0,
          daysAffected: 5,
          dates: ['2024-01-12', '2024-01-13', '2024-01-14', '2024-01-15', '2024-01-16'],
          location,
          age: meter.age,
          canya: meter.canya
        },
        explanation: {
          whatIsHappening: `El comptador ${meterName} (ID: ${meter.id}) ha estat marcat amb una puntuació de risc de fallada del ${risk.toFixed(1)}%. El comptador mostra patrons de comportament anòmals en comparació amb altres comptadors del seu clúster, combinat amb la ubicació en una àrea amb nivells mitjans de degradació més alts. Això suggereix possibles problemes amb la precisió del comptador o comportament de subcompte.`,
          whatCouldBeDone: `1. Verificar la funcionalitat i connectivitat del comptador\n2. Comprovar si la propietat està ocupada\n3. Inspeccionar la vàlvula principal d'aigua\n4. Revisar els registres de manteniment recents`,
          whatUsuallyHappens: `Els patrons de consum zero normalment són causats per fallades del comptador (40%), propietats buides (35%) o vàlvules tancades (25%). La majoria dels casos es resolen en una setmana després de la intervenció.`
        }
      });
    } else {
      // Other alarms: Various types
      const types: Alarm['type'][] = ['anomaly', 'spike', 'high_consumption'];
      const type = types[index % types.length];
      
      alarms.push({
        id: `alarm-${meter.id}`,
        meterId: meter.id,
        meterName: meterName,
        type,
        severity: risk >= 80 ? 'alert' : 'warning',
        title: `Alerta de Risc de Fallada (${risk.toFixed(1)}%)`,
        description: `S'ha detectat un risc alt de fallada per al comptador ${meterName}`,
        data: {
          currentValue: meter.last_month_consumption ? Math.round(meter.last_month_consumption) : 0,
          meanValue: meter.canya && meter.age ? Math.round(meter.canya / meter.age) : 0,
          daysAffected: 1 + (index % 3),
          dates: ['2024-01-16'],
          location,
          age: meter.age,
          canya: meter.canya
        },
        explanation: {
          whatIsHappening: `El comptador ${meterName} (ID: ${meter.id}) té una puntuació de risc de fallada del ${risk.toFixed(1)}%, indicant que mostra patrons comportamentals atípics dins del seu clúster. L'avaluació del risc combina la detecció d'anomalies (desviació comportamental) i els factors de degradació del clúster (edat i consum acumulat). Això suggereix possibles problemes de subcompte o degradació del comptador.`,
          whatCouldBeDone: `1. Revisar les dades de consum recents\n2. Programar una inspecció de manteniment\n3. Monitoritzar la continuació del patró\n4. Comprovar factors externs que afectin el consum`,
          whatUsuallyHappens: `Les anomalies similars sovint es resolen mitjançant manteniment regular o s'atribueixen a patrons d'ús temporals. La detecció primerenca ajuda a prevenir problemes més greus.`
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
      const synthInstance = window.speechSynthesis;
      // Load voices if they haven't loaded yet
      if (synthInstance.getVoices().length === 0) {
        synthInstance.addEventListener('voiceschanged', () => {
          setSynth(synthInstance);
        });
      } else {
        setSynth(synthInstance);
      }
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
      Accions recomanades: ${selectedAlarm.explanation.whatCouldBeDone.replace(/\n\n/g, '. ').replace(/\d+\.\s+\*\*/g, '').replace(/\*\*/g, '')}
      Què sol passar: ${selectedAlarm.explanation.whatUsuallyHappens}
    `;

    const utterance = new SpeechSynthesisUtterance(text);
    // Try to find a Catalan voice, otherwise fall back to available voices
    const voices = synth.getVoices();
    const catalanVoice = voices.find(voice => 
      voice.lang.toLowerCase().startsWith('ca') || 
      voice.name.toLowerCase().includes('catalan') ||
      voice.name.toLowerCase().includes('català')
    );
    if (catalanVoice) {
      utterance.voice = catalanVoice;
      utterance.lang = catalanVoice.lang;
    } else {
      utterance.lang = 'ca';
    }
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
              Informació i Alarmes
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Els 20 comptadors amb major risc amb explicacions detallades
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
                Els {Math.min(alarms.length, 20)} Comptadors amb Major Risc
              </h3>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-2">
                {alarms.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    No hi ha alarmes actives
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
                        <span>{alarm.data.daysAffected} {alarm.data.daysAffected > 1 ? 'dies' : 'dia'}</span>
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
                      <div className="grid grid-cols-4 gap-4 mt-4">
                        <div className="bg-background/50 rounded-lg p-3 border border-border">
                          <div className="flex items-center gap-2 mb-1">
                            <Droplets className="w-4 h-4 text-primary" />
                            <span className="text-xs text-muted-foreground">Darrer Mes</span>
                          </div>
                          <p className="text-lg font-bold text-foreground">
                            {selectedAlarm.data.currentValue.toLocaleString()} L
                          </p>
                        </div>
                        <div className="bg-background/50 rounded-lg p-3 border border-border">
                          <div className="flex items-center gap-2 mb-1">
                            <TrendingUp className="w-4 h-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">Mitjana Anual</span>
                          </div>
                          <p className="text-lg font-bold text-foreground">
                            {selectedAlarm.data.meanValue.toLocaleString()} L
                          </p>
                        </div>
                        <div className="bg-background/50 rounded-lg p-3 border border-border">
                          <div className="flex items-center gap-2 mb-1">
                            <Calendar className="w-4 h-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">Edat</span>
                          </div>
                          <p className="text-lg font-bold text-foreground">
                            {selectedAlarm.data.age ? selectedAlarm.data.age.toFixed(1) : 'N/A'} anys
                          </p>
                        </div>
                        <div className="bg-background/50 rounded-lg p-3 border border-border">
                          <div className="flex items-center gap-2 mb-1">
                            <Droplets className="w-4 h-4 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">Canya</span>
                          </div>
                          <p className="text-lg font-bold text-foreground">
                            {selectedAlarm.data.canya ? Math.round(selectedAlarm.data.canya).toLocaleString() : 'N/A'}
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
                        Què Està Passant
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
                        Què Es Pot Fer
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
                        Què Sol Passar
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
                      <p className="text-sm font-medium text-foreground">Explicació de Veu</p>
                      <p className="text-xs text-muted-foreground">
                        {isPlayingVoice ? 'Reproduint...' : 'Feu clic per escoltar l\'explicació'}
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={handlePlayVoice}
                    size="lg"
                    className="bg-gradient-to-r from-accent to-[hsl(35,100%,72%)] hover:from-[hsl(35,100%,70%)] hover:to-accent text-accent-foreground"
                  >
                    <Volume2 className="w-4 h-4 mr-2" />
                    {isPlayingVoice ? 'Aturar' : 'Reproduir Veu'}
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center p-6">
                <div className="text-center text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Seleccioneu una alarma de la llista per veure els detalls</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Disclaimer */}
        <div className="border-t border-border px-6 py-3 bg-muted/50 flex-shrink-0">
          <p className="text-xs text-muted-foreground text-center">
            Aquesta anàlisi s'ha generat utilitzant models predictius impulsats per intel·ligència artificial. Sempre verifiqueu els resultats amb una inspecció in situ abans de prendre mesures.
          </p>
        </div>
      </div>
    </>
  );
};

