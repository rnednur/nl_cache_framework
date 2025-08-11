# 🚀 ThinkForge Demo Package

**The Complete Natural Language Cache Framework & Recipe Hub**

This package contains everything needed to demonstrate ThinkForge's capabilities as both a natural language processing cache and an intelligent recipe automation hub.

## 📦 What's Included

- **Complete ThinkForge System**: Backend API, Frontend UI, Database
- **Pre-loaded Demo Data**: Sample tools, APIs, recipes, and usage logs
- **Docker Environment**: One-command deployment with all dependencies
- **Data Export/Import**: Easily transfer data between installations
- **Comprehensive Documentation**: Setup guides and feature walkthroughs

## ⚡ Quick Start (30 seconds)

```bash
# 1. Extract and enter directory
cd thinkforge-demo/

# 2. Run the demo deployment script
./scripts/demo_deploy.sh

# 3. Open browser to http://localhost:3001
```

That's it! The script handles everything: Docker setup, database initialization, data seeding, and service startup.

## 🎯 Key Demo Features

### 🧠 Natural Language Processing
- **Real Similarity Search**: Uses sentence transformers for semantic matching
- **Confidence Scoring**: AI-powered quality assessment for tool mappings
- **Context Awareness**: Understands step types and dependencies

### 🔧 Tool Hub & Discovery
- **Multi-type Support**: MCP tools, AI agents, functions, APIs
- **Catalog Organization**: Type, subtype, and name-based filtering
- **Health Monitoring**: Track tool status and reliability

### 📋 Recipe Intelligence
- **Natural Language Input**: Describe workflows in plain English
- **Automatic Tool Mapping**: AI finds and maps appropriate tools
- **Dependency Detection**: Smart workflow step ordering
- **Complexity Analysis**: Time estimation and difficulty scoring

### 📊 Analytics & Insights
- **Usage Tracking**: Query patterns and success rates
- **Tool Popularity**: Most-used tools and recipes
- **Performance Metrics**: Confidence scores and optimization opportunities

## 🎬 Demo Scenarios

### Scenario 1: Create a Smart Recipe
1. Navigate to **Recipes → Create Recipe**
2. Switch to **Natural Language** tab
3. Enter: *"Process customer orders by extracting from database, validating payment info, updating inventory, and sending confirmation email"*
4. Click **Analyze Recipe**
5. Watch AI analyze steps and suggest tools with confidence scores
6. Review and accept the generated workflow

### Scenario 2: Explore Tool Ecosystem
1. Go to **Tools → Tool Hub**
2. Filter by catalog types (database, API, function, agent)
3. Click on tools to see capabilities and health status
4. Test tool functionality with sample inputs

### Scenario 3: Analyze Usage Patterns
1. Visit **Usage Logs**
2. Review query success rates and patterns
3. Identify most popular tools and recipes
4. Analyze confidence score distributions

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │   PostgreSQL DB │
│   (Port 3001)   │◄──►│   (Port 8000)    │◄──►│   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        │              ┌─────────────────┐                │
        └──────────────►│  ThinkForge Core │◄──────────────┘
                       │  • NLP Engine    │
                       │  • Recipe Parser │
                       │  • Tool Mapper   │
                       │  • Confidence AI │
                       └─────────────────┘
```

## 📁 Project Structure

```
thinkforge-demo/
├── 🚀 scripts/demo_deploy.sh     # One-click deployment
├── 📋 docker-compose.demo.yml    # Demo environment setup
├── 🗄️ demo_data_export/          # Exportable demo data
├── 🎨 frontend/                  # React UI application
├── ⚙️ backend/                   # FastAPI server
├── 🧠 thinkforge/                # Core NLP framework
├── 📊 dbscripts/                 # Database utilities
└── 📖 docs/                      # Documentation
```

## 🛠️ Manual Setup (Advanced)

If you prefer manual control:

```bash
# 1. Start with Docker Compose
docker-compose -f docker-compose.demo.yml up -d

# 2. Wait for services (2-3 minutes)
docker-compose -f docker-compose.demo.yml logs -f

# 3. Access when you see "ThinkForge Demo Ready!"
# Frontend: http://localhost:3001
# Backend:  http://localhost:8000
```

## 📤 Exporting Demo Data

To export your demo data for sharing:

```bash
# Export current database to portable format
python scripts/export_demo_data.py

# Creates: demo_data_export/
# ├── cache_entries.json
# ├── usage_logs.json
# └── demo_metadata.json
```

## 📥 Importing Demo Data

To import demo data into a new installation:

```bash
# Import from exported data
python scripts/import_demo_data.py demo_data_export/

# Optional: Skip embedding regeneration for faster import
python scripts/import_demo_data.py demo_data_export/ --no-embeddings
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Database Configuration
POSTGRES_DB=thinkforge_demo
POSTGRES_USER=thinkforge
POSTGRES_PASSWORD=demo_password_2024

# AI Model Configuration
DEFAULT_MODEL_NAME=sentence-transformers/all-mpnet-base-v2
SIMILARITY_THRESHOLD=0.75

# Demo Settings
DEMO_MODE=true
AUTO_SEED_DATA=true
```

### Port Configuration
- **Frontend**: 3001 (configurable in docker-compose.demo.yml)
- **Backend**: 8000 (configurable in docker-compose.demo.yml)
- **Database**: 5432 (configurable in docker-compose.demo.yml)

## 📊 Demo Data Overview

### Pre-loaded Tools (7 items)
- PostgreSQL Database Connector
- JSON Data Transformer
- REST API Client
- Data Validation AI Agent
- Email Notification Service
- Weather API Integration
- Slack Messaging API

### Sample Recipes (2 workflows)
- Customer Data Processing Pipeline
- User Onboarding Automation

### Usage Analytics
- 30+ sample queries with realistic patterns
- Success rate distributions
- Tool usage statistics

## 🧪 Testing the System

### Natural Language Queries to Try
```
"Get customer data from the database"
"Transform JSON to CSV format"
"Send notification email to admin"
"Validate data completeness"
"Create user account via API"
"Process payment information"
```

### Recipe Creation Examples
```
"Build a user registration workflow with validation and email confirmation"
"Create a data backup process with compression and cloud upload"
"Set up automated report generation with database queries and email delivery"
```

## 🛟 Troubleshooting

### Common Issues

**Services won't start**
```bash
# Check port availability
lsof -i :3001 :8000 :5432

# View detailed logs
docker-compose -f docker-compose.demo.yml logs
```

**Database connection errors**
```bash
# Restart PostgreSQL
docker-compose -f docker-compose.demo.yml restart postgres

# Check database health
docker-compose -f docker-compose.demo.yml exec postgres pg_isready
```

**Frontend/Backend connection issues**  
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check environment variables
docker-compose -f docker-compose.demo.yml exec frontend env | grep API
```

### Reset Demo Environment
```bash
# Complete reset
docker-compose -f docker-compose.demo.yml down -v
./scripts/demo_deploy.sh
```

## 🔒 Security Notes

This is a **demo environment** with simplified security:
- Default passwords are used
- Demo mode bypasses some security checks
- Not intended for production use
- All data is sample/synthetic

## 🚀 Production Deployment

For production deployment:
1. Use `docker-compose.yml` instead of `docker-compose.demo.yml`
2. Set secure passwords and API keys
3. Configure SSL/TLS certificates
4. Set up proper monitoring and logging
5. Review security configurations

## 📞 Support & Feedback

- **Issues**: Report problems with the demo setup
- **Features**: Suggest improvements or new capabilities
- **Documentation**: Request clarification or additional guides
- **Performance**: Share insights about demo performance

## 📜 License

This demo package includes the complete ThinkForge system under its original license terms.

---

**🎉 Enjoy exploring ThinkForge!** 

The demo showcases real AI-powered natural language processing, intelligent tool mapping, and automated recipe generation. All processing is done locally with no external API dependencies required.