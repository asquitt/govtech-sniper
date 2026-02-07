"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Mic, MicOff, Volume2, VolumeX } from "lucide-react";
import { useSpeechRecognition, useSpeechSynthesis } from "@/hooks/use-speech";

interface VoiceControlsProps {
  onTranscript: (text: string) => void;
  lastAssistantMessage?: string;
}

export function VoiceControls({
  onTranscript,
  lastAssistantMessage,
}: VoiceControlsProps) {
  const {
    transcript,
    isListening,
    isSupported: micSupported,
    start,
    stop,
    error: micError,
  } = useSpeechRecognition();
  const {
    speak,
    cancel,
    isSpeaking,
    isSupported: speakerSupported,
  } = useSpeechSynthesis();

  const [autoSpeak, setAutoSpeak] = React.useState(false);

  // When recognition finishes, pass transcript to parent
  React.useEffect(() => {
    if (!isListening && transcript) {
      onTranscript(transcript);
    }
  }, [isListening, transcript, onTranscript]);

  // Auto-speak new assistant messages
  React.useEffect(() => {
    if (autoSpeak && lastAssistantMessage) {
      speak(lastAssistantMessage);
    }
  }, [lastAssistantMessage, autoSpeak, speak]);

  if (!micSupported && !speakerSupported) return null;

  return (
    <div className="flex items-center gap-2">
      {/* Mic button */}
      {micSupported && (
        <Button
          variant={isListening ? "default" : "outline"}
          size="sm"
          onClick={isListening ? stop : start}
          className="relative"
        >
          {isListening ? (
            <>
              <MicOff className="w-4 h-4 mr-1" />
              Stop
              <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-destructive animate-pulse" />
            </>
          ) : (
            <>
              <Mic className="w-4 h-4 mr-1" />
              Voice
            </>
          )}
        </Button>
      )}

      {/* Speaker toggle */}
      {speakerSupported && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            if (isSpeaking) {
              cancel();
            } else {
              setAutoSpeak(!autoSpeak);
            }
          }}
        >
          {isSpeaking ? (
            <>
              <VolumeX className="w-4 h-4 mr-1" />
              Stop
            </>
          ) : autoSpeak ? (
            <>
              <Volume2 className="w-4 h-4 mr-1" />
              Auto
            </>
          ) : (
            <>
              <Volume2 className="w-4 h-4 mr-1" />
              Sound
            </>
          )}
        </Button>
      )}

      {/* Status indicators */}
      {isListening && (
        <Badge variant="destructive" className="text-[10px] animate-pulse">
          Listening...
        </Badge>
      )}
      {isSpeaking && (
        <Badge variant="secondary" className="text-[10px]">
          Speaking...
        </Badge>
      )}
      {micError && (
        <span className="text-xs text-destructive">{micError}</span>
      )}
    </div>
  );
}
