# AinSongjog Integration Guide

Complete guide for integrating the WhatsApp Bot with your AinSongjog lawyer directory application.

## Overview

This guide provides step-by-step instructions to integrate WhatsApp messaging functionality into your AinSongjog platform (https://github.com/Ahbabsaqlan/AinSongjog), enabling lawyers and clients to communicate via WhatsApp.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AinSongjog Platform                       │
│          (NestJS Backend + Next.js Frontend)                 │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Lawyers    │  │   Clients    │  │ Appointments │     │
│  │   (Users)    │  │   (Users)    │  │    Cases     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────┬──────────────────────────────────────────────┘
             │
             │ HTTP REST API
             │ (API Keys per Lawyer)
             ▼
┌─────────────────────────────────────────────────────────────┐
│              WhatsApp Bot Server (Python/Flask)              │
│                                                               │
│  • Multi-user support (one account per lawyer)              │
│  • Message sending/receiving                                 │
│  • Conversation history                                      │
│  • Webhook notifications                                     │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
         WhatsApp Web
```

## Prerequisites

- Node.js 20+ (for AinSongjog)
- Python 3.7+ (for WhatsApp Bot)
- Google Chrome browser
- Both applications running (AinSongjog backend and WhatsApp bot server)

## Part 1: Setup WhatsApp Bot

### 1.1 Install WhatsApp Bot

```bash
# Clone the WhatsApp bot repository (if not already done)
git clone https://github.com/Ahbabsaqlan/whatsapp_bot.git
cd whatsapp_bot

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Initialize Database

```bash
# Initialize the lawyer directory database
python setup_lawyer_directory.py
```

Follow the prompts to create lawyer accounts for each lawyer in your AinSongjog system. You'll need:
- Lawyer's full name
- Email (should match AinSongjog user email)
- Phone number (WhatsApp number)
- WhatsApp display name

**Important**: Save the API key generated for each lawyer - you'll need it for AinSongjog integration.

### 1.3 Start WhatsApp Bot Server

```bash
# Start the bot server
python run_server.py
```

The server will start on `http://localhost:5001`

## Part 2: Integrate with AinSongjog Backend

### 2.1 Create WhatsApp Module in NestJS

Create a new module in your AinSongjog backend:

```bash
cd AinSongjog/BackEnd
nest generate module whatsapp
nest generate service whatsapp
nest generate controller whatsapp
```

### 2.2 Install Required Dependencies

```bash
npm install axios
```

### 2.3 Configure Environment Variables

Add to your `AinSongjog/BackEnd/.env`:

```env
# WhatsApp Bot Configuration
WHATSAPP_BOT_URL=http://localhost:5001
WHATSAPP_BOT_ENABLED=true

# Webhook configuration (for receiving messages from WhatsApp bot)
WHATSAPP_WEBHOOK_SECRET=your-secure-webhook-secret-here
```

### 2.4 Create WhatsApp Service

Create `src/whatsapp/whatsapp.service.ts`:

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios, { AxiosInstance } from 'axios';

export interface SendMessageDto {
  clientPhoneNumber: string;
  text?: string;
  filePath?: string;
}

export interface LawyerWhatsAppConfig {
  apiKey: string;
  lawyerEmail: string;
}

@Injectable()
export class WhatsAppService {
  private readonly logger = new Logger(WhatsAppService.name);
  private readonly botUrl: string;
  private readonly enabled: boolean;
  private axiosInstance: AxiosInstance;

  // Store lawyer API keys (in production, store in database)
  private lawyerApiKeys: Map<string, string> = new Map();

  constructor(private configService: ConfigService) {
    this.botUrl = this.configService.get<string>('WHATSAPP_BOT_URL', 'http://localhost:5001');
    this.enabled = this.configService.get<boolean>('WHATSAPP_BOT_ENABLED', true);
    
    this.axiosInstance = axios.create({
      baseURL: `${this.botUrl}/api/lawyer`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Register a lawyer's WhatsApp API key
   * Call this after lawyer signs up or when loading lawyer data
   */
  registerLawyerApiKey(lawyerEmail: string, apiKey: string): void {
    this.lawyerApiKeys.set(lawyerEmail, apiKey);
    this.logger.log(`Registered WhatsApp API key for lawyer: ${lawyerEmail}`);
  }

  /**
   * Get API key for a lawyer
   */
  private getLawyerApiKey(lawyerEmail: string): string | undefined {
    return this.lawyerApiKeys.get(lawyerEmail);
  }

  /**
   * Send a WhatsApp message from a lawyer to a client
   */
  async sendMessage(
    lawyerEmail: string,
    dto: SendMessageDto,
  ): Promise<{ success: boolean; message: string }> {
    if (!this.enabled) {
      this.logger.warn('WhatsApp integration is disabled');
      return { success: false, message: 'WhatsApp integration is disabled' };
    }

    const apiKey = this.getLawyerApiKey(lawyerEmail);
    if (!apiKey) {
      this.logger.error(`No API key found for lawyer: ${lawyerEmail}`);
      return { success: false, message: 'Lawyer not configured for WhatsApp' };
    }

    try {
      const response = await this.axiosInstance.post(
        '/messages/send',
        {
          client_phone_number: dto.clientPhoneNumber,
          text: dto.text,
          file_path: dto.filePath,
        },
        {
          headers: {
            'X-API-Key': apiKey,
          },
        },
      );

      this.logger.log(
        `Message sent to ${dto.clientPhoneNumber} from ${lawyerEmail}`,
      );
      return { success: true, message: 'Message sent successfully' };
    } catch (error) {
      this.logger.error(
        `Failed to send WhatsApp message: ${error.message}`,
        error.stack,
      );
      return { success: false, message: 'Failed to send message' };
    }
  }

  /**
   * Get conversation history between a lawyer and client
   */
  async getConversationHistory(
    lawyerEmail: string,
    clientPhoneNumber: string,
    count: number = 50,
  ): Promise<any> {
    if (!this.enabled) {
      return { messages: [] };
    }

    const apiKey = this.getLawyerApiKey(lawyerEmail);
    if (!apiKey) {
      this.logger.error(`No API key found for lawyer: ${lawyerEmail}`);
      return { messages: [] };
    }

    try {
      const response = await this.axiosInstance.get(
        `/conversations/${clientPhoneNumber}`,
        {
          params: { count },
          headers: {
            'X-API-Key': apiKey,
          },
        },
      );

      return response.data;
    } catch (error) {
      this.logger.error(
        `Failed to get conversation history: ${error.message}`,
        error.stack,
      );
      return { messages: [] };
    }
  }

  /**
   * Get all clients for a lawyer
   */
  async getLawyerClients(lawyerEmail: string): Promise<any[]> {
    if (!this.enabled) {
      return [];
    }

    const apiKey = this.getLawyerApiKey(lawyerEmail);
    if (!apiKey) {
      return [];
    }

    try {
      const response = await this.axiosInstance.get('/clients', {
        headers: {
          'X-API-Key': apiKey,
        },
      });

      return response.data.clients || [];
    } catch (error) {
      this.logger.error(`Failed to get lawyer clients: ${error.message}`);
      return [];
    }
  }

  /**
   * Add a client to a lawyer's WhatsApp contact list
   */
  async addClient(
    lawyerEmail: string,
    clientName: string,
    clientPhoneNumber: string,
    clientEmail?: string,
  ): Promise<{ success: boolean; clientId?: number }> {
    if (!this.enabled) {
      return { success: false };
    }

    const apiKey = this.getLawyerApiKey(lawyerEmail);
    if (!apiKey) {
      return { success: false };
    }

    try {
      const response = await this.axiosInstance.post(
        '/clients',
        {
          name: clientName,
          phone_number: clientPhoneNumber,
          email: clientEmail,
        },
        {
          headers: {
            'X-API-Key': apiKey,
          },
        },
      );

      return {
        success: true,
        clientId: response.data.client_id,
      };
    } catch (error) {
      this.logger.error(`Failed to add client: ${error.message}`);
      return { success: false };
    }
  }

  /**
   * Register a webhook for receiving WhatsApp messages
   */
  async registerWebhook(
    lawyerEmail: string,
    webhookUrl: string,
    eventType: string = 'message_received',
  ): Promise<{ success: boolean }> {
    if (!this.enabled) {
      return { success: false };
    }

    const apiKey = this.getLawyerApiKey(lawyerEmail);
    if (!apiKey) {
      return { success: false };
    }

    try {
      await this.axiosInstance.post(
        '/webhooks',
        {
          url: webhookUrl,
          event_type: eventType,
        },
        {
          headers: {
            'X-API-Key': apiKey,
          },
        },
      );

      this.logger.log(`Webhook registered for ${lawyerEmail}: ${webhookUrl}`);
      return { success: true };
    } catch (error) {
      this.logger.error(`Failed to register webhook: ${error.message}`);
      return { success: false };
    }
  }
}
```

### 2.5 Create WhatsApp Controller

Create `src/whatsapp/whatsapp.controller.ts`:

```typescript
import { Controller, Post, Get, Body, Param, Query, UseGuards, Request } from '@nestjs/common';
import { WhatsAppService } from './whatsapp.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RolesGuard } from '../auth/guards/roles.guard';
import { Roles } from '../auth/decorators/roles.decorator';
import { UserRole } from '../common/enums/role.enum';

@Controller('whatsapp')
@UseGuards(JwtAuthGuard, RolesGuard)
export class WhatsAppController {
  constructor(private readonly whatsappService: WhatsAppService) {}

  /**
   * Send a message to a client (Lawyer only)
   */
  @Post('send')
  @Roles(UserRole.LAWYER)
  async sendMessage(@Request() req, @Body() body: any) {
    const lawyerEmail = req.user.email;
    
    return this.whatsappService.sendMessage(lawyerEmail, {
      clientPhoneNumber: body.clientPhoneNumber,
      text: body.text,
      filePath: body.filePath,
    });
  }

  /**
   * Get conversation history with a client (Lawyer only)
   */
  @Get('conversations/:phoneNumber')
  @Roles(UserRole.LAWYER)
  async getConversation(
    @Request() req,
    @Param('phoneNumber') phoneNumber: string,
    @Query('count') count?: number,
  ) {
    const lawyerEmail = req.user.email;
    return this.whatsappService.getConversationHistory(
      lawyerEmail,
      phoneNumber,
      count || 50,
    );
  }

  /**
   * Get all WhatsApp clients for the lawyer
   */
  @Get('clients')
  @Roles(UserRole.LAWYER)
  async getClients(@Request() req) {
    const lawyerEmail = req.user.email;
    return this.whatsappService.getLawyerClients(lawyerEmail);
  }

  /**
   * Add a client to WhatsApp contacts (Lawyer only)
   */
  @Post('clients')
  @Roles(UserRole.LAWYER)
  async addClient(@Request() req, @Body() body: any) {
    const lawyerEmail = req.user.email;
    return this.whatsappService.addClient(
      lawyerEmail,
      body.name,
      body.phoneNumber,
      body.email,
    );
  }
}
```

### 2.6 Create Webhook Receiver

Create `src/whatsapp/webhook.controller.ts`:

```typescript
import { Controller, Post, Body, Headers, UnauthorizedException, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NotificationsService } from '../notifications/notifications.service';
import { UsersService } from '../users/users.service';

@Controller('webhooks/whatsapp')
export class WhatsAppWebhookController {
  private readonly logger = new Logger(WhatsAppWebhookController.name);
  private readonly webhookSecret: string;

  constructor(
    private configService: ConfigService,
    private notificationsService: NotificationsService,
    private usersService: UsersService,
  ) {
    this.webhookSecret = this.configService.get<string>('WHATSAPP_WEBHOOK_SECRET', '');
  }

  /**
   * Receive webhook notifications from WhatsApp bot
   */
  @Post()
  async handleWebhook(
    @Headers('x-webhook-secret') webhookSecret: string,
    @Body() payload: any,
  ) {
    // Verify webhook secret
    if (this.webhookSecret && webhookSecret !== this.webhookSecret) {
      this.logger.warn('Invalid webhook secret');
      throw new UnauthorizedException('Invalid webhook secret');
    }

    this.logger.log(`Received webhook: ${payload.event_type}`);

    try {
      const { event_type, data, lawyer_id } = payload;

      if (event_type === 'message_received') {
        // Handle incoming WhatsApp message
        await this.handleIncomingMessage(data, lawyer_id);
      } else if (event_type === 'message_sent') {
        // Handle sent message confirmation
        await this.handleSentMessage(data, lawyer_id);
      }

      return { status: 'ok' };
    } catch (error) {
      this.logger.error(`Webhook processing error: ${error.message}`, error.stack);
      return { status: 'error', message: error.message };
    }
  }

  /**
   * Handle incoming WhatsApp message from client
   */
  private async handleIncomingMessage(data: any, lawyerId: number) {
    const { client_phone_number, message, timestamp } = data;

    this.logger.log(
      `Incoming message from ${client_phone_number} to lawyer ${lawyerId}`,
    );

    // Find the lawyer user
    // const lawyer = await this.usersService.findByWhatsAppLawyerId(lawyerId);
    
    // Create a notification for the lawyer
    // await this.notificationsService.create({
    //   userId: lawyer.id,
    //   type: 'whatsapp_message',
    //   title: 'New WhatsApp Message',
    //   message: `New message from ${client_phone_number}: ${message}`,
    //   data: { phone: client_phone_number, message, timestamp },
    // });

    // You can also:
    // 1. Store the message in your database
    // 2. Send push notification to lawyer's mobile app
    // 3. Send email notification
    // 4. Update case/appointment records
  }

  /**
   * Handle sent message confirmation
   */
  private async handleSentMessage(data: any, lawyerId: number) {
    const { client_phone_number, message, timestamp } = data;

    this.logger.log(
      `Message sent to ${client_phone_number} from lawyer ${lawyerId}`,
    );

    // Update message status in your database
    // Track sent messages for analytics
  }
}
```

### 2.7 Update WhatsApp Module

Update `src/whatsapp/whatsapp.module.ts`:

```typescript
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { WhatsAppService } from './whatsapp.service';
import { WhatsAppController } from './whatsapp.controller';
import { WhatsAppWebhookController } from './webhook.controller';
import { NotificationsModule } from '../notifications/notifications.module';
import { UsersModule } from '../users/users.module';

@Module({
  imports: [ConfigModule, NotificationsModule, UsersModule],
  controllers: [WhatsAppController, WhatsAppWebhookController],
  providers: [WhatsAppService],
  exports: [WhatsAppService],
})
export class WhatsAppModule {}
```

### 2.8 Register Module in AppModule

Update `src/app.module.ts`:

```typescript
import { WhatsAppModule } from './whatsapp/whatsapp.module';

@Module({
  imports: [
    // ... other imports
    WhatsAppModule,
  ],
  // ...
})
export class AppModule {}
```

## Part 3: Store Lawyer API Keys

You need to store the WhatsApp bot API keys for each lawyer. Here are two approaches:

### Option 1: Add to LawyerProfile Entity

Add a field to `src/users/entities/lawyer-profile.entity.ts`:

```typescript
@Column({ nullable: true, select: false })
whatsappApiKey: string; // Store securely, don't return in regular queries
```

Then update your users service to register API keys on startup or when lawyer logs in:

```typescript
// In users.service.ts
constructor(
  // ... other dependencies
  private whatsappService: WhatsAppService,
) {}

async onModuleInit() {
  // Load all lawyers and register their API keys
  const lawyers = await this.findAllLawyers();
  for (const lawyer of lawyers) {
    if (lawyer.lawyerProfile?.whatsappApiKey) {
      this.whatsappService.registerLawyerApiKey(
        lawyer.email,
        lawyer.lawyerProfile.whatsappApiKey,
      );
    }
  }
}
```

### Option 2: Separate WhatsApp Configuration Table

Create a new entity for WhatsApp configuration:

```typescript
// src/whatsapp/entities/whatsapp-config.entity.ts
import { Entity, PrimaryGeneratedColumn, Column, OneToOne, JoinColumn } from 'typeorm';
import { User } from '../../users/entities/user.entity';

@Entity('whatsapp_configs')
export class WhatsAppConfig {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ select: false }) // Don't expose API key in regular queries
  apiKey: string;

  @Column({ nullable: true })
  whatsappNumber: string;

  @Column({ default: true })
  enabled: boolean;

  @OneToOne(() => User)
  @JoinColumn()
  user: User;

  @Column({ type: 'timestamp', default: () => 'CURRENT_TIMESTAMP' })
  createdAt: Date;
}
```

## Part 4: Frontend Integration (Next.js)

### 4.1 Create WhatsApp Chat Component

Create `frontend/components/WhatsAppChat.tsx`:

```typescript
'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sending_date: string;
}

interface WhatsAppChatProps {
  clientPhone: string;
  clientName: string;
}

export default function WhatsAppChat({ clientPhone, clientName }: WhatsAppChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMessages();
  }, [clientPhone]);

  const loadMessages = async () => {
    try {
      const response = await axios.get(
        `/api/whatsapp/conversations/${clientPhone}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;

    setLoading(true);
    try {
      await axios.post(
        '/api/whatsapp/send',
        {
          clientPhoneNumber: clientPhone,
          text: newMessage,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      setNewMessage('');
      
      // Reload messages after a delay to show the sent message
      setTimeout(loadMessages, 2000);
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full border rounded-lg">
      <div className="bg-green-600 text-white p-4 rounded-t-lg">
        <h3 className="font-semibold">WhatsApp Chat with {clientName}</h3>
        <p className="text-sm">{clientPhone}</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'assistant' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs px-4 py-2 rounded-lg ${
                msg.role === 'assistant'
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 text-gray-800'
              }`}
            >
              <p>{msg.content}</p>
              <span className="text-xs opacity-75">
                {new Date(msg.sending_date).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type a message..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !newMessage.trim()}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

### 4.2 Create API Route Proxy (Next.js)

Create `frontend/app/api/whatsapp/[...path]/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3001';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const token = request.headers.get('authorization');

  try {
    const response = await fetch(`${BACKEND_URL}/whatsapp/${path}?${request.nextUrl.searchParams}`, {
      headers: {
        'Authorization': token || '',
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch' }, { status: 500 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const token = request.headers.get('authorization');
  const body = await request.json();

  try {
    const response = await fetch(`${BACKEND_URL}/whatsapp/${path}`, {
      method: 'POST',
      headers: {
        'Authorization': token || '',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to send' }, { status: 500 });
  }
}
```

## Part 5: Common Use Cases

### Use Case 1: Appointment Reminders

```typescript
// In appointments.service.ts
async sendAppointmentReminder(appointmentId: string) {
  const appointment = await this.findOne(appointmentId);
  
  // Send WhatsApp reminder to client
  await this.whatsappService.sendMessage(
    appointment.lawyer.email,
    {
      clientPhoneNumber: appointment.client.clientProfile.mobileNumber,
      text: `Reminder: You have an appointment with ${appointment.lawyer.firstName} ${appointment.lawyer.lastName} on ${appointment.date} at ${appointment.time}. Location: ${appointment.location}`,
    },
  );
}
```

### Use Case 2: Case Updates

```typescript
// In cases.service.ts
async notifyClientAboutCaseUpdate(caseId: string, updateMessage: string) {
  const case = await this.findOne(caseId);
  
  await this.whatsappService.sendMessage(
    case.lawyer.email,
    {
      clientPhoneNumber: case.client.clientProfile.mobileNumber,
      text: `Case Update (${case.title}): ${updateMessage}`,
    },
  );
}
```

### Use Case 3: Client Onboarding

```typescript
// In users.service.ts
async sendWelcomeMessage(clientId: string, lawyerEmail: string) {
  const client = await this.findOne(clientId);
  
  await this.whatsappService.sendMessage(
    lawyerEmail,
    {
      clientPhoneNumber: client.clientProfile.mobileNumber,
      text: `Welcome to AinSongjog! I'm your lawyer, and I'm here to assist you with your legal matters. Feel free to message me anytime on WhatsApp.`,
    },
  );
}
```

## Part 6: Deployment

### 6.1 Deploy WhatsApp Bot

```bash
# On your server
git clone https://github.com/Ahbabsaqlan/whatsapp_bot.git
cd whatsapp_bot
pip install -r requirements.txt

# Setup lawyer accounts
python setup_lawyer_directory.py

# Run with systemd or supervisor
# Example systemd service file:
sudo nano /etc/systemd/system/whatsapp-bot.service
```

```ini
[Unit]
Description=WhatsApp Bot Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/whatsapp_bot
ExecStart=/usr/bin/python3 run_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable whatsapp-bot
sudo systemctl start whatsapp-bot
```

### 6.2 Configure Nginx Reverse Proxy

```nginx
# Add to your Nginx config
location /whatsapp-bot {
    proxy_pass http://localhost:5001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 6.3 Update AinSongjog Environment

Update your production `.env`:

```env
WHATSAPP_BOT_URL=https://yourdomain.com/whatsapp-bot
WHATSAPP_BOT_ENABLED=true
WHATSAPP_WEBHOOK_SECRET=your-production-secret
```

## Part 7: Testing

### 7.1 Test Lawyer Account Setup

```bash
# From WhatsApp bot directory
python -c "
import lawyer_directory_integration as ldi
lawyers = ldi.get_lawyer_by_id(1)
print(f'Lawyer: {lawyers}')
"
```

### 7.2 Test Message Sending

```bash
# From AinSongjog backend
curl -X POST http://localhost:3001/whatsapp/send \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientPhoneNumber": "+1234567890",
    "text": "Test message from AinSongjog"
  }'
```

### 7.3 Test Webhook

```bash
# Simulate webhook from WhatsApp bot
curl -X POST http://localhost:3001/webhooks/whatsapp \
  -H "X-Webhook-Secret: your-webhook-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "message_received",
    "data": {
      "client_phone_number": "+1234567890",
      "message": "Hello, I need legal help",
      "timestamp": "2026-01-28T10:00:00"
    },
    "lawyer_id": 1
  }'
```

## Troubleshooting

### Issue: "No API key found for lawyer"

**Solution**: Ensure you've registered the lawyer's API key:
```typescript
await this.whatsappService.registerLawyerApiKey(
  'lawyer@example.com',
  'api-key-from-setup'
);
```

### Issue: Webhook not receiving messages

**Solution**: 
1. Check that webhook URL is publicly accessible
2. Verify webhook secret matches
3. Check WhatsApp bot logs: `tail -f /path/to/whatsapp_bot/logs`

### Issue: WhatsApp Web QR code not scanning

**Solution**: 
1. Make sure Chrome is installed on the server
2. For headless servers, use X virtual framebuffer (Xvfb)
3. Check that WhatsApp Web is not blocked in your region

## Security Considerations

1. **API Keys**: Store WhatsApp API keys encrypted in database
2. **Webhook Secret**: Use strong, random secrets for webhook validation
3. **Rate Limiting**: Implement rate limiting on message sending endpoints
4. **Input Validation**: Validate phone numbers and message content
5. **HTTPS**: Always use HTTPS in production
6. **Audit Logs**: Log all WhatsApp interactions for compliance

## Support

- **WhatsApp Bot Documentation**: See [LAWYER_DIRECTORY_INTEGRATION.md](LAWYER_DIRECTORY_INTEGRATION.md)
- **Security Guide**: See [SECURITY.md](SECURITY.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: [GitHub Issues](https://github.com/Ahbabsaqlan/whatsapp_bot/issues)

## Next Steps

1. ✅ Set up WhatsApp bot server
2. ✅ Create lawyer accounts in WhatsApp bot
3. ✅ Implement WhatsApp module in AinSongjog backend
4. ✅ Add WhatsApp chat component to frontend
5. ✅ Configure webhooks for real-time notifications
6. ✅ Test end-to-end flow
7. ✅ Deploy to production

Congratulations! Your AinSongjog platform now has WhatsApp integration! 🎉
