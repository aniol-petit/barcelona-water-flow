import React, { useState, useEffect } from 'react';
import { Key, Check } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';

interface MapboxTokenInputProps {
  onTokenSave: (token: string) => void;
}

export const MapboxTokenInput: React.FC<MapboxTokenInputProps> = ({ onTokenSave }) => {
  const [token, setToken] = useState('');
  const [savedToken, setSavedToken] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('mapbox_token');
    if (stored) {
      setSavedToken(stored);
      onTokenSave(stored);
    }
  }, [onTokenSave]);

  const handleSave = () => {
    if (token.trim()) {
      localStorage.setItem('mapbox_token', token.trim());
      setSavedToken(token.trim());
      onTokenSave(token.trim());
      setToken('');
    }
  };

  if (savedToken) {
    return (
      <div className="bg-primary/10 border border-primary/20 rounded-xl p-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
          <Check className="w-5 h-5 text-primary" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-foreground">Mapbox token configured</p>
          <p className="text-xs text-muted-foreground">Map should now load correctly</p>
        </div>
        <Button
          onClick={() => {
            localStorage.removeItem('mapbox_token');
            setSavedToken(null);
            window.location.reload();
          }}
          variant="outline"
          size="sm"
        >
          Change Token
        </Button>
      </div>
    );
  }

  return (
    <div className="bg-accent/10 border border-accent/20 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center">
          <Key className="w-5 h-5 text-accent" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">Mapbox Token Required</p>
          <p className="text-xs text-muted-foreground">
            Get your free public token from{' '}
            <a 
              href="https://mapbox.com" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              mapbox.com
            </a>
          </p>
        </div>
      </div>
      
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder="pk.eyJ1Ijo..."
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="flex-1"
        />
        <Button onClick={handleSave} disabled={!token.trim()}>
          Save Token
        </Button>
      </div>
    </div>
  );
};
