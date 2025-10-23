import React from 'react';
import { MessageSquare, Volume2, Info, BarChart3 } from 'lucide-react';
import { Button } from './ui/button';

interface ControlPanelProps {
  onTextExplanation: () => void;
  onVoiceExplanation: () => void;
  onInfo: () => void;
  onDashboard: () => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  onTextExplanation,
  onVoiceExplanation,
  onInfo,
  onDashboard
}) => {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
      <div className="bg-card/95 backdrop-blur-md border border-border rounded-2xl shadow-lg px-6 py-4 animate-fade-in">
        <div className="flex items-center gap-4">
          <Button
            onClick={onInfo}
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground hover:bg-muted/50"
          >
            <Info className="w-4 h-4 mr-2" />
            About
          </Button>
          
          <div className="h-6 w-px bg-border" />
          
          <Button
            onClick={onTextExplanation}
            className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-md animate-gentle-pulse"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Text Explanation
          </Button>
          
          <Button
            onClick={onVoiceExplanation}
            variant="secondary"
            className="bg-secondary hover:bg-secondary/80 text-secondary-foreground animate-gentle-pulse"
            style={{ animationDelay: '0.5s' }}
          >
            <Volume2 className="w-4 h-4 mr-2" />
            Voice Explanation
          </Button>
          
          <div className="h-6 w-px bg-border" />
          
          <Button
            onClick={onDashboard}
            variant="outline"
            className="border-primary/20 hover:bg-primary/5 text-primary animate-gentle-pulse"
            style={{ animationDelay: '1s' }}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
};
