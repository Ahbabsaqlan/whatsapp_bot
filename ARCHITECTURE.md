# System Architecture

## Overview

This document describes the architecture of the WhatsApp bot integration for lawyer directory applications.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Lawyer Directory Web App                     │
│                  (Your Flask/Django/Express App)                 │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Lawyer    │  │   Client    │  │    Chat     │            │
│  │  Dashboard  │  │ Management  │  │  Interface  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└────────────┬──────────────┬──────────────┬─────────────────────┘
             │              │              │
             │ REST API     │ REST API     │ REST API
             │ (API Key)    │ (API Key)    │ (API Key)
             ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WhatsApp Bot Server                         │
│                      (Flask on port 5001)                        │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    API Layer                                │ │
│  │  • Authentication (API Keys)                               │ │
│  │  • Request Validation                                       │ │
│  │  • Rate Limiting                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Business Logic Layer                          │ │
│  │  • Lawyer Management (lawyer_directory_integration.py)     │ │
│  │  • Client Management                                        │ │
│  │  • Message Routing (lawyer_api_routes.py)                  │ │
│  │  • Webhook Management                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Database Layer (SQLite)                      │ │
│  │  • Lawyers • Clients • Relationships                       │ │
│  │  • Conversations • Messages • Webhooks                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           WhatsApp Automation Layer                        │ │
│  │  • Selenium WebDriver (selenium_handler.py)                │ │
│  │  • Message Scraping                                         │ │
│  │  • Message Sending                                          │ │
│  │  • Profile Management                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Selenium WebDriver
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Chrome/Chromium Browser                       │
│                     (WhatsApp Web Client)                        │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ WhatsApp Protocol
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WhatsApp Servers                            │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
        Client's Phone
```

## Data Flow

### 1. Lawyer Sends Message to Client

```
Web App                Bot Server              Browser              WhatsApp
   │                       │                      │                    │
   │  POST /messages/send  │                      │                    │
   ├──────────────────────>│                      │                    │
   │  (API Key + Phone)    │                      │                    │
   │                       │  Open Browser        │                    │
   │                       ├─────────────────────>│                    │
   │                       │                      │                    │
   │                       │  Send Message        │                    │
   │                       ├─────────────────────>│                    │
   │                       │                      │  Send via WhatsApp │
   │                       │                      ├───────────────────>│
   │                       │                      │                    │
   │  202 Accepted         │                      │                    │
   │<──────────────────────┤                      │                    │
   │                       │                      │                    │
   │                       │  Scrape Sent Msg     │                    │
   │                       │<─────────────────────┤                    │
   │                       │                      │                    │
   │                       │  Save to DB          │                    │
   │                       │                      │                    │
```

### 2. Client Sends Message (Continuous Bot Mode)

```
WhatsApp              Browser              Bot Server            Web App
   │                     │                      │                    │
   │  New Message        │                      │                    │
   ├────────────────────>│                      │                    │
   │                     │                      │                    │
   │                     │  Sync Task (runs     │                    │
   │                     │  every 60s)          │                    │
   │                     │<─────────────────────┤                    │
   │                     │                      │                    │
   │                     │  Scrape Messages     │                    │
   │                     ├─────────────────────>│                    │
   │                     │                      │                    │
   │                     │                      │  Save to DB        │
   │                     │                      │                    │
   │                     │                      │  Get Webhooks      │
   │                     │                      │                    │
   │                     │                      │  POST to Webhook   │
   │                     │                      ├───────────────────>│
   │                     │                      │  (JSON payload)    │
   │                     │                      │                    │
   │                     │                      │  200 OK            │
   │                     │                      │<───────────────────┤
   │                     │                      │                    │
```

### 3. Web App Retrieves Conversation

```
Web App                Bot Server              Database
   │                       │                      │
   │  GET /conversations/  │                      │
   │  +1234567890          │                      │
   ├──────────────────────>│                      │
   │  (API Key)            │                      │
   │                       │  Query Messages      │
   │                       ├─────────────────────>│
   │                       │                      │
   │                       │  Messages Data       │
   │                       │<─────────────────────┤
   │                       │                      │
   │  200 OK + Messages    │                      │
   │<──────────────────────┤                      │
   │  (JSON)               │                      │
```

## Database Schema

```
┌─────────────────────┐
│      Lawyers        │
├─────────────────────┤
│ id (PK)             │
│ name                │
│ email (UNIQUE)      │
│ phone_number (UQ)   │
│ whatsapp_name       │
│ api_key (UNIQUE)    │──┐
│ profile_path        │  │
│ is_active           │  │
│ created             │  │
│ updated             │  │
└─────────────────────┘  │
          │              │
          │ 1:N          │
          ▼              │
┌─────────────────────┐  │
│LawyerClientRel      │  │
├─────────────────────┤  │
│ id (PK)             │  │
│ lawyer_id (FK) ─────┼──┘
│ client_id (FK) ─────┼──┐
│ conversation_id (FK)│  │
│ status              │  │
│ created             │  │
│ updated             │  │
└─────────────────────┘  │
          │              │
          │              │
          ▼              │
┌─────────────────────┐  │
│      Clients        │  │
├─────────────────────┤  │
│ id (PK)             │◄─┘
│ name                │
│ phone_number (UQ)   │
│ email               │
│ created             │
│ updated             │
└─────────────────────┘
          │
          │ 1:1
          ▼
┌─────────────────────┐
│   Conversations     │
├─────────────────────┤
│ id (PK)             │──┐
│ title               │  │
│ phone_number (UQ)   │  │
│ created             │  │
│ updated             │  │
│ context_summary     │  │
│ size                │  │
└─────────────────────┘  │
          │              │
          │ 1:N          │
          ▼              │
┌─────────────────────┐  │
│     Messages        │  │
├─────────────────────┤  │
│ id (PK)             │  │
│ conversation_id (FK)┼──┘
│ role                │
│ sender_name         │
│ content             │
│ message_index       │
│ sending_date        │
│ stored_date         │
│ meta_text (UNIQUE)  │
│ attachment_filename │
└─────────────────────┘

┌─────────────────────┐
│     Webhooks        │
├─────────────────────┤
│ id (PK)             │
│ lawyer_id (FK)      │──┐
│ url                 │  │
│ event_type          │  │
│ is_active           │  │
│ created             │  │
└─────────────────────┘  │
          │              │
          │ 1:N          │
          ▼              │
┌─────────────────────┐  │
│   WebhookQueue      │  │
├─────────────────────┤  │
│ id (PK)             │  │
│ webhook_id (FK) ────┼──┘
│ payload (JSON)      │
│ attempts            │
│ status              │
│ created             │
│ last_attempt        │
└─────────────────────┘
```

## Component Responsibilities

### lawyer_directory_integration.py
- Database schema initialization
- Lawyer account management
- Client management
- Relationship mapping
- Webhook registration
- API key generation

### lawyer_api_routes.py
- REST API endpoints
- Authentication middleware
- Request validation
- Message sending coordination
- Webhook triggering
- Response formatting

### selenium_handler.py
- Browser automation
- WhatsApp Web interaction
- Message scraping
- Message sending
- Profile management
- Element location and interaction

### database_manager.py
- Database connections
- Conversation management
- Message storage
- Query helpers
- Data normalization

### run_server.py
- Flask app initialization
- Blueprint registration
- Server startup
- Configuration loading

## Security Layers

```
┌─────────────────────────────────────────────┐
│          Network Layer                       │
│  • HTTPS/SSL (Production)                   │
│  • Firewall rules                           │
│  • DDoS protection                          │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         Application Layer                    │
│  • Rate limiting                            │
│  • Input validation                         │
│  • Output sanitization                      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│        Authentication Layer                  │
│  • API key validation                       │
│  • Session management                       │
│  • Token expiration                         │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         Authorization Layer                  │
│  • Resource ownership check                 │
│  • Role-based access                        │
│  • Data isolation                           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│            Data Layer                        │
│  • Parameterized queries                    │
│  • Data encryption (optional)               │
│  • Audit logging                            │
└─────────────────────────────────────────────┘
```

## Deployment Topologies

### Single Server (Development/Small Scale)
```
┌──────────────────────────────────┐
│         Single Server            │
│                                  │
│  ┌────────────────────────────┐ │
│  │   Web App (Port 3000)      │ │
│  └────────────────────────────┘ │
│                                  │
│  ┌────────────────────────────┐ │
│  │   Bot Server (Port 5001)   │ │
│  └────────────────────────────┘ │
│                                  │
│  ┌────────────────────────────┐ │
│  │   SQLite Database          │ │
│  └────────────────────────────┘ │
│                                  │
│  ┌────────────────────────────┐ │
│  │   Chrome Browser           │ │
│  └────────────────────────────┘ │
└──────────────────────────────────┘
```

### Production (Multi-Server)
```
┌─────────────────┐
│  Load Balancer  │
│   (HTTPS/SSL)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌─────────┐
│ Web App │ │ Web App │
│ Server  │ │ Server  │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │ API
           ▼
    ┌──────────────┐
    │  Bot Server  │
    │  (Behind FW) │
    └──────┬───────┘
           │
      ┌────┴────┐
      │         │
      ▼         ▼
┌──────────┐ ┌─────────┐
│PostgreSQL│ │ Chrome  │
│ Database │ │ Browser │
└──────────┘ └─────────┘
```

## Scalability Considerations

### Horizontal Scaling
- Multiple bot server instances with message queue (Redis/RabbitMQ)
- Load balancer distributes API requests
- Shared database (PostgreSQL instead of SQLite)
- Session affinity for browser automation

### Vertical Scaling
- Increase server resources (CPU/RAM)
- Optimize database queries
- Cache frequently accessed data
- Batch webhook notifications

### Performance Optimization
- Connection pooling for database
- Async webhook delivery
- Message queue for send operations
- CDN for static assets
- Redis for session storage

## Monitoring & Observability

```
┌─────────────────────────────────────────┐
│           Monitoring Stack              │
├─────────────────────────────────────────┤
│  • Application Logs (Logging)          │
│  • Metrics (Response time, errors)     │
│  • Traces (Request flow)               │
│  • Alerts (Failures, thresholds)       │
│  • Dashboards (Visual monitoring)      │
└─────────────────────────────────────────┘
```

Key metrics to monitor:
- API response times
- Message send success rate
- Webhook delivery rate
- Database query performance
- Browser session stability
- Active lawyer connections
- Message queue depth

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | Flask 2.3.2 |
| Database | SQLite (dev), PostgreSQL (prod) |
| Browser Automation | Selenium 4.15.2 |
| WebDriver | ChromeDriver (auto-managed) |
| HTTP Client | Requests 2.31.0 |
| Session Management | Flask-Session (optional) |
| Authentication | Custom API Key |
| Data Validation | Built-in + Custom |

## External Dependencies

- **Google Chrome/Chromium**: Required for browser automation
- **WhatsApp Web**: Must be accessible and functional
- **Internet Connection**: Required for WhatsApp communication
- **Phone with WhatsApp**: Required for initial QR code scanning

## Future Enhancements

1. **Message Queue Integration**: Redis/RabbitMQ for better scalability
2. **Database Migration**: PostgreSQL for production
3. **Real-time Updates**: WebSocket support for instant updates
4. **File Attachments**: Enhanced file upload/download support
5. **Message Templates**: Pre-configured message templates
6. **Analytics Dashboard**: Usage statistics and insights
7. **Multi-language Support**: i18n for international use
8. **Mobile App**: Native mobile app for lawyers
9. **AI Integration**: Smart replies and chatbot support
10. **Backup & Recovery**: Automated backup system
