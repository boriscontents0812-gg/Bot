import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import ThoughtLine from './ThoughtLine';

let _updater = null;

function ThoughtLineWrapper({ initialProps = {} }) {
  const [props, setProps] = useState({
    working: false,
    label: 'Ready — waiting for action…',
    doneLabel: 'Idle — waiting for your next action.',
    glyph: 'sparkle',
    glyphColor: '#ff4088',
    color: 'inherit',
    fontSize: 14,
    breathPeriod: 1.6,
    breathDepth: 0.45,
    settleDuration: 350,
    settleBlur: 2,
    collapsible: true,
    collapseOnSettle: false,
    showTimer: true,
    steps: [],
    ...initialProps
  });

  useEffect(() => {
    _updater = (newProps) => {
      setProps(prev => ({
        ...prev,
        ...newProps,
        steps: newProps.steps !== undefined ? newProps.steps : prev.steps
      }));
    };
  }, []);

  return <ThoughtLine {...props} />;
}

export function initThoughtLine(containerId, initialProps = {}) {
  const container = document.getElementById(containerId);
  if (!container) return null;
  const root = createRoot(container);
  root.render(<ThoughtLineWrapper initialProps={initialProps} />);

  const api = {
    set(newProps) {
      if (_updater) _updater(newProps);
    },
    setWorking(working, label, steps = [], doneLabel = '') {
      if (_updater) {
        _updater({
          working,
          label: label || (working ? 'Processing…' : 'Done'),
          doneLabel: doneLabel || label || 'Done',
          steps: steps,
          glyphColor: '#ff4088'
        });
      }
    },
    addStep(step) {
      if (_updater) {
        _updater({
          steps: (prevSteps => [...(prevSteps || []), step])
        });
      }
    },
    updateFromStatus(msg) {
      if (!msg) {
        this.setWorking(false, '', [], 'Idle — waiting for your next action.');
        return;
      }
      const text = String(msg).trim();

      // Error status
      if (text.toLowerCase().startsWith('error') || text.toLowerCase().includes('connection lost')) {
        if (_updater) {
          _updater({
            working: false,
            doneLabel: text,
            glyphColor: '#ef4444',
            glyph: 'sparkle',
            steps: []
          });
        }
        return;
      }

      // Done / Settled status
      if (text.startsWith('✅') || text.startsWith('Loaded') || text.startsWith('Project') || text.toLowerCase().startsWith('idle')) {
        if (_updater) {
          _updater({
            working: false,
            doneLabel: text,
            glyphColor: '#ff4088',
            glyph: 'sparkle'
          });
        }
        return;
      }

      // Audio generation
      if (text.toLowerCase().includes('audio')) {
        let activeStep = 'Synthesizing voice clips with ElevenLabs';
        if (text.includes('/') || text.includes(':')) {
          activeStep = text;
        }
        if (_updater) {
          _updater({
            working: true,
            label: 'Generating audio…',
            glyphColor: '#ff4088',
            steps: [
              'Parsing conversation script',
              activeStep,
              'Merging audio timeline & normalizing audio'
            ]
          });
        }
        return;
      }

      // Video generation
      if (text.toLowerCase().includes('video') || text.toLowerCase().includes('building') || text.toLowerCase().includes('encoding')) {
        let activeStep = text.replace(/^Building video\s*—\s*/i, '');
        if (!activeStep) activeStep = 'Rendering video frames & layout';
        if (_updater) {
          _updater({
            working: true,
            label: 'Building video…',
            glyphColor: '#ff4088',
            steps: [
              'Preparing video frames & bubble layout',
              'Compositing audio timeline & gameplay track',
              activeStep,
              'Finalizing MP4 video export'
            ]
          });
        }
        return;
      }

      // Generic active message
      if (_updater) {
        _updater({
          working: true,
          label: text,
          glyphColor: '#ff4088',
          steps: [text]
        });
      }
    }
  };

  window.thoughtLine = api;
  return api;
}

if (typeof window !== 'undefined') {
  window.initThoughtLine = initThoughtLine;
}
