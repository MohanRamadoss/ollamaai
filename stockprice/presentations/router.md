## Step-by-Step Plan

1. Create Language Detection component
2. Implement Model Router logic
3. Build core AgentGeneration component 
4. Handle code generation with fallbacks
5. Show progress and results

Here's the implementation:

```typescript


import { Language, LANGUAGE_CONFIGS } from '../../config/languages.config';

export class LanguageDetector {
  static detect(code: string): Language | null {
    // Simple detection based on file extensions and syntax patterns
    const patterns = {
      python: /\b(def|import|from|class)\b|\.py$/i,
      javascript: /\b(const|let|var|function)\b|\.js$/i,
      typescript: /\b(interface|type|export)\b|\.ts$/i,
      java: /\b(public|class|void|private)\b|\.java$/i,
      go: /\b(func|package|import)\b|\.go$/i,
      rust: /\b(fn|let|mut|impl)\b|\.rs$/i,
    };

    for (const [lang, pattern] of Object.entries(patterns)) {
      if (pattern.test(code)) {
        return lang as Language;
      }
    }
    return null;
  }
}
```

```typescript


import { Language } from '../../config/languages.config';
import { Model } from '../../types';

export class ModelRouter {
  static getModelForLanguage(language: Language): Model[] {
    // Route to specific models based on language
    const modelRoutes: Record<Language, Model[]> = {
      python: ['gemini-pro-code', 'codellama'],
      javascript: ['gemini-pro-code', 'deepseek-coder:33b'],
      typescript: ['gemini-pro-code', 'deepseek-coder:33b'],
      java: ['gemini-pro-code', 'codellama:13b'],
      go: ['gemini-pro-code', 'codellama'],
      rust: ['gemini-pro-code', 'codellama:13b']
    };

    return modelRoutes[language] || ['gemini-pro-code']; // Default fallback
  }
}
```

```tsx


import React, { useState, useEffect } from 'react';
import { LanguageDetector } from './components/AgentGeneration/LanguageDetector';
import { ModelRouter } from './components/AgentGeneration/ModelRouter';
import { GenerationProgress } from './components/CodeGeneration/GenerationProgress';
import { CodeOutput } from './components/CodeGeneration/CodeOutput';
import { generateCode } from './lib/api/generate';
import { Language, Model } from './types';
import { MODELS } from './config/constants';

export function AgentGeneration() {
  const [code, setCode] = useState<string>('');
  const [detectedLanguage, setDetectedLanguage] = useState<Language | null>(null);
  const [selectedModels, setSelectedModels] = useState<Model[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentModel, setCurrentModel] = useState<Model | null>(null);
  const [completedModels, setCompletedModels] = useState<Model[]>([]);
  const [results, setResults] = useState<Array<{code: string; model: Model}>>([]);
  const [error, setError] = useState<string | null>(null);

  // Detect language when code changes
  useEffect(() => {
    if (code) {
      const language = LanguageDetector.detect(code);
      setDetectedLanguage(language);
      if (language) {
        const models = ModelRouter.getModelForLanguage(language);
        setSelectedModels(models);
      }
    }
  }, [code]);

  const handleGenerate = async () => {
    if (!detectedLanguage || !code) return;
    
    setIsGenerating(true);
    setError(null);
    setResults([]);
    setCompletedModels([]);

    for (const model of selectedModels) {
      try {
        setCurrentModel(model);
        const result = await generateCode(code, detectedLanguage, model, 'intermediate');
        
        setResults(prev => [...prev, {
          code: result.code,
          model: model
        }]);
        setCompletedModels(prev => [...prev, model]);
      } catch (err) {
        console.error(`Error with model ${model}:`, err);
        setError(`Failed with ${model}. Trying next model...`);
      }
    }

    setIsGenerating(false);
    setCurrentModel(null);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto p-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">AI Code Generation</h1>
        
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Paste your code here..."
          className="w-full h-64 p-4 bg-gray-800 rounded-lg"
        />

        {detectedLanguage && (
          <div className="text-sm text-blue-400">
            Detected Language: {detectedLanguage}
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={!detectedLanguage || isGenerating}
          className="px-4 py-2 bg-blue-600 rounded-lg disabled:opacity-50"
        >
          {isGenerating ? 'Generating...' : 'Generate'}
        </button>
      </div>

      {isGenerating && (
        <GenerationProgress
          models={selectedModels}
          currentModel={currentModel}
          completedModels={completedModels}
        />
      )}

      {results.map((result, index) => (
        <CodeOutput
          key={index}
          code={result.code}
          language={detectedLanguage!}
          modelName={MODELS[result.model]}
        />
      ))}

      {error && (
        <div className="text-red-500 p-4 bg-red-900/20 rounded-lg">
          {error}
        </div>
      )}
    </div>
  );
}
```

This implementation:
- Automatically detects code language
- Routes to appropriate models (Gemini + Ollama models)
- Handles generation with fallbacks
- Shows real-time progress
- Displays results from multiple models
- Includes error handling

The component uses the existing configuration files and APIs while adding intelligent routing between different LLM providers.


## Step-by-Step Plan

1. Define OpenAI models and configurations
2. Update ModelRouter for language-specific model routing
3. Add OpenAI API integration
4. Implement fallback logic between providers

### 1. Update Model Types and Constants

```typescript


export type ModelProvider = 'openai' | 'gemini' ;

export type OpenAIModel = 
  | 'gpt-4-turbo-preview'
  | 'gpt-4'
  | 'gpt-3.5-turbo'
  | 'gpt-3.5-turbo-16k';

export type Model = OpenAIModel | GeminiModel;

export interface ModelConfig {
  provider: ModelProvider;
  capabilities: string[];
  contextLength: number;
  fallbacks: Model[];
}
```

### 2. Update Constants with OpenAI Models

```typescript


export const MODEL_CONFIGS: Record<Model, ModelConfig> = {
  'gpt-4-turbo-preview': {
    provider: 'openai',
    capabilities: ['code generation', 'code analysis'],
    contextLength: 128000,
    fallbacks: ['gpt-4', 'gpt-3.5-turbo-16k']
  },
  'gpt-4': {
    provider: 'openai',
    capabilities: ['code generation', 'code analysis'],
    contextLength: 8192,
    fallbacks: ['gpt-3.5-turbo-16k']
  },
  'gpt-3.5-turbo-16k': {
    provider: 'openai',
    capabilities: ['code generation'],
    contextLength: 16384,
    fallbacks: ['gemini-pro-code']
  },
  // 
}
```

### 3. Updated ModelRouter Implementation

```typescript


import { Language } from '../../types';
import { Model, ModelProvider } from '../../types';
import { MODEL_CONFIGS } from '../../config/constants';

export class ModelRouter {
  static getPreferredModels(language: Language): Model[] {
    const languageModelMap: Record<Language, Model[]> = {
      typescript: ['gpt-4-turbo-preview', 'gpt-4', 'gemini-pro-code'],
      javascript: ['gpt-4-turbo-preview', 'gpt-4', 'gemini-pro-code'],
      python: ['gpt-4-turbo-preview', 'gpt-3.5-turbo-16k', 'gemini-pro-code'],
      java: ['gpt-4-turbo-preview', 'gpt-4', 'gemini-pro-code'],
      rust: ['gpt-4-turbo-preview', 'gpt-4', 'gemini-pro-code'],
      go: ['gpt-4-turbo-preview', 'gpt-3.5-turbo-16k', 'gemini-pro-code']
    };

    return languageModelMap[language] || ['gpt-4-turbo-preview'];
  }

  static async getFallbackModel(failedModel: Model): Promise<Model | null> {
    const config = MODEL_CONFIGS[failedModel];
    if (!config?.fallbacks.length) return null;
    return config.fallbacks[0];
  }

  static getModelProvider(model: Model): ModelProvider {
    return MODEL_CONFIGS[model].provider;
  }
}
```

### 4. Environment Configuration

```typescript


export const ENV_CONFIG = {
  ...existingConfig,
  OPENAI_API_KEY: import.meta.env.VITE_OPENAI_API_KEY,
  OPENAI_API_URL: import.meta.env.VITE_OPENAI_API_URL || 'https://api.openai.com/v1',
}
```

This implementation:
- Prioritizes OpenAI models for code generation
- Provides fallbacks to other providers
- Supports language-specific model routing
- Maintains compatibility with existing Ollama/Gemini setup

Use this ModelRouter in your AgentGeneration component to automatically select and fallback between OpenAI and other models based on the detected programming language.