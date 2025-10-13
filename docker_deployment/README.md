# Analytics AI Platform

AI-powered analytics platform for data insights and visualization.

## Setup Instructions

### 1. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and add your actual API keys:
   ```bash
   nano .env
   ```

3. **Required**: Get your Google AI API key from [Google AI Studio](https://makersuite.google.com/app/apikey) and replace `your_gemini_api_key_here` in the `.env` file.

### 2. Running the Application

#### Option 1: Docker (Recommended)
```bash
# Start the application
./start.sh

# Stop the application
./stop.sh

# View logs
./logs.sh
```

#### Option 2: Manual Docker Commands
```bash
# Build and start services
docker-compose up --build -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google AI API key | Yes |
| `DATABASE_PATH` | Path to SQLite database | No (default: data/analytics_ai.db) |
| `JWT_SECRET` | Secret for JWT authentication | No (default: auto-generated) |
| `PROJECT_ID` | Google Cloud project ID | No (default: ai-analysis-v1) |
| `DEFAULT_BUCKET` | Default GCS bucket | No (default: ai-analysis-default-bucket) |
| `FRONTEND_URL` | Frontend URL for CORS | No (default: http://localhost:3000) |
| `PORT` | Backend port | No (default: 8000) |
| `NODE_ENV` | Environment mode | No (default: development) |

## Security Notes

- **Never commit `.env` files to version control**
- The `.env` file contains sensitive API keys
- Use different API keys for development and production
- Rotate API keys regularly

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your `GEMINI_API_KEY` in `.env` is valid
2. **Port Conflicts**: Ensure ports 3000 and 8000 are available
3. **Permission Issues**: Make sure Docker has permission to access your directories

### Logs
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs analytics-ai-backend
docker-compose logs analytics-ai-frontend
```
