# Plan: Enhanced Stack with Redis and Database Integration

1. Add Database Layer
2. Add Redis Caching
3. Update API Layer
4. Add Data Persistence

## Implementation Steps

### 1. Docker Compose Update

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    
  api:
    build: ./api
    ports: ["4000:4000"]
    depends_on: ["redis", "postgres"]
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/aicodecraft
      - REDIS_URL=redis://redis:6379
      
  redis:
    image: redis:alpine
    ports: ["6379:6379"]
    volumes: ["redis_data:/data"]
    
  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=aicodecraft
    volumes: ["postgres_data:/var/lib/postgresql/data"]

volumes:
  redis_data:
  postgres_data:
```

### 2. Database Schema

```sql
CREATE TABLE code_generations (
  id SERIAL PRIMARY KEY,
  prompt TEXT NOT NULL,
  language VARCHAR(50) NOT NULL,
  model VARCHAR(50) NOT NULL,
  generated_code TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  user_id UUID REFERENCES users(id)
);

CREATE TABLE code_conversions (
  id SERIAL PRIMARY KEY,
  source_code TEXT NOT NULL,
  from_language VARCHAR(50) NOT NULL,
  to_language VARCHAR(50) NOT NULL,
  converted_code TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  user_id UUID REFERENCES users(id)
);

CREATE INDEX idx_code_generations_user ON code_generations(user_id);
CREATE INDEX idx_code_conversions_user ON code_conversions(user_id);
```

### 3. Redis Cache Service

```typescript
import { Redis } from 'ioredis';

export class RedisCache {
  private client: Redis;
  
  constructor() {
    this.client = new Redis(process.env.REDIS_URL);
  }

  async get(key: string): Promise<string | null> {
    return this.client.get(key);
  }

  async set(key: string, value: string, ttl?: number): Promise<void> {
    if (ttl) {
      await this.client.setex(key, ttl, value);
    } else {
      await this.client.set(key, value);
    }
  }

  async invalidate(key: string): Promise<void> {
    await this.client.del(key);
  }
}
```

### 4. Database Service

```typescript
import { Pool } from 'pg';
import { z } from 'zod';

export class Database {
  private pool: Pool;

  constructor() {
    this.pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });
  }

  async saveGeneration(data: CodeGenerationInput): Promise<void> {
    const query = `
      INSERT INTO code_generations 
      (prompt, language, model, generated_code, user_id)
      VALUES ($1, $2, $3, $4, $5)
    `;
    await this.pool.query(query, [
      data.prompt,
      data.language,
      data.model,
      data.generatedCode,
      data.userId
    ]);
  }

  async getGenerationHistory(userId: string): Promise<CodeGeneration[]> {
    const query = `
      SELECT * FROM code_generations 
      WHERE user_id = $1 
      ORDER BY created_at DESC 
      LIMIT 50
    `;
    const result = await this.pool.query(query, [userId]);
    return result.rows;
  }
}
```

### 5. API Integration

```typescript
import { RedisCache } from '../cache/redis';
import { Database } from '../db/postgres';

export class GenerationService {
  private cache: RedisCache;
  private db: Database;

  constructor() {
    this.cache = new RedisCache();
    this.db = new Database();
  }

  async generateCode(params: GenerateParams): Promise<string> {
    const cacheKey = this.getCacheKey(params);
    
    // Check cache first
    const cached = await this.cache.get(cacheKey);
    if (cached) return cached;

    // Generate if not cached
    const result = await this.callAIService(params);
    
    // Save to cache and database
    await Promise.all([
      this.cache.set(cacheKey, result, 3600),
      this.db.saveGeneration({
        ...params,
        generatedCode: result
      })
    ]);

    return result;
  }
}
```

### 6. Install Dependencies

```bash
# Install backend dependencies
npm install ioredis pg @types/pg

# Install migrations tool
npm install -g prisma

# Initialize database
prisma migrate dev
```

This enhanced stack provides:
- Redis caching for AI responses
- PostgreSQL for data persistence
- Generation history
- User management
- Performance optimization