# Jira Webhook Receiver

A FastAPI application that receives and processes Jira webhooks to track customer complaints and ticket closures.

## 🎯 Purpose

This application automatically captures Jira tickets when they are closed, extracting customer and transaction information for downstream processing and analytics.

## ✨ Features

- ✅ Receives Jira webhooks in real-time
- ✅ Processes only tickets transitioned to "Close" status
- ✅ Prevents duplicate processing (idempotent)
- ✅ Extracts customer and transaction data from custom fields
- ✅ Stores ticket-customer mappings in PostgreSQL
- ✅ Structured logging with request ID tracking
- ✅ Docker support for easy deployment
- ✅ Health check endpoint for monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- MySQL 8.0+
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/Carylen/jira_webhook.git
cd jira-webhook-receiver

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application

uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### Docker Quick Start

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f app
```

## 📖 Documentation

- **[SETUP.md](./docs/SETUP.md)** - Detailed setup instructions
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - Application architecture and flow
- **[DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Production deployment guide
- **[API_REFERENCE.md](./docs/API_REFERENCE.md)** - API endpoint documentation

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│             │ webhook │                  │ persist │             │
│    Jira     ├────────>│  FastAPI App     ├────────>│ PostgreSQL  │
│             │         │                  │         │             │
└─────────────┘         └──────────────────┘         └─────────────┘
```

### Tech Stack

- **FastAPI** - Modern async web framework
- **SQLModel** - SQL database ORM with Pydantic integration
- **aiomysql** - Relational database
- **Uvicorn** - ASGI server
- **Docker** - Containerization

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

### Jira Custom Fields

Update `src/utils/constants.py` if your Jira uses different custom field IDs:

```python
CUSTOM_FIELD_TRANSACTION_ID = "customfield_11226"
CUSTOM_FIELD_CUSTOMER_PHONE = "customfield_11227"
# ... etc
```

## 📝 API Endpoints

### `POST /jira-webhook`

Receive and process Jira webhooks.

**Query Parameters:**
- `triggeredByUser` (optional) - User identifier

**Response:**
```json
{
  "status": "processed",
  "message": "Webhook processed successfully",
  "issueKey": "SDO-123",
  "projectKey": "SDO",
  "projectName": "Service Desk",
  "triggeredByUser": "John Doe",
  "savedAt": "2025-01-21T10:30:00"
}
```

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "jira-webhook-receiver",
  "version": "1.0.0"
}
```

## 🧪 Testing

Test the webhook endpoint:

```bash
curl -X POST http://localhost:8000/jira-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": 1706745600000,
    "webhookEvent": "jira:issue_updated",
    "user": {"displayName": "Test User"},
    "issue": {
      "key": "TEST-1",
      "fields": {"summary": "Test ticket"}
    },
    "changelog": {
      "items": [{"field": "status", "toString": "Close"}]
    }
  }'
```

## 📊 Database Schema

### `tb_r_ticket_customer_mapping`

Stores ticket-customer relationships:

| Field | Type | Description |
|-------|------|-------------|
| `mapping_id` | UUID | Primary key |
| `ticket_key` | String | Jira ticket key (unique) |
| `customer_id` | String | Customer identifier |
| `customer_phone` | String | Customer phone number |
| `transaction_id` | String | Transaction identifier |
| `ticket_summary` | Text | Issue summary |
| `ticket_url` | String | Full URL to ticket |
| `priority` | String | Ticket priority |
| `complaint_data` | JSON | Complete issue data |
| `close_notified` | Boolean | Notification status |
| `created_on` | Timestamp | Creation time |

## 🔍 Monitoring

### Logs

Application logs include request IDs for tracing:

```
2025-01-21 10:30:00 | a7b3c4d5 | Main | INFO | Processing webhook: issue_key=SDO-123
2025-01-21 10:30:01 | a7b3c4d5 | webhook_service | INFO | Successfully saved ticket
```

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check with Docker
docker-compose exec app curl http://localhost:8000/health
```

## 🐛 Troubleshooting

### Common Issues

1. **Database connection fails**
   - Verify `DATABASE_URL` in `.env`
   - Check PostgreSQL is running: `pg_isready`

2. **Webhooks not received**
   - Verify webhook URL in Jira settings
   - Check firewall/security group rules
   - Review Jira webhook delivery history

3. **Port already in use**
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

For more troubleshooting, see [SETUP.md](./docs/SETUP.md#troubleshooting).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Support

For issues or questions:
- Check the [documentation](./docs/)
- Enable DEBUG logging: `LOG_LEVEL=DEBUG`
- Review application logs
- Check Jira webhook delivery history

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Database ORM by [SQLModel](https://sqlmodel.tiangolo.com/)
- Inspired by webhook best practices