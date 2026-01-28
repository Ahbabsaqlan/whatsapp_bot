# AinSongjog WhatsApp Integration Modules

Ready-to-use NestJS modules for integrating WhatsApp Bot with your AinSongjog application.

## Files Included

- `whatsapp.service.ts` - Core service for WhatsApp operations
- `whatsapp.controller.ts` - REST API endpoints for lawyers
- `webhook.controller.ts` - Webhook receiver for incoming messages
- `whatsapp.module.ts` - NestJS module configuration

## Installation Steps

### 1. Copy Files to Your AinSongjog Backend

```bash
# From your AinSongjog/BackEnd directory
cd src
mkdir whatsapp
cd whatsapp

# Copy all files from this directory to src/whatsapp/
# Or manually create each file with the content provided
```

### 2. Install Dependencies

```bash
npm install axios
```

### 3. Configure Environment Variables

Add to your `.env` file:

```env
# WhatsApp Bot Configuration
WHATSAPP_BOT_URL=http://localhost:5001
WHATSAPP_BOT_ENABLED=true
WHATSAPP_WEBHOOK_SECRET=your-secure-random-secret-here
```

### 4. Register the Module

In `src/app.module.ts`, add:

```typescript
import { WhatsAppModule } from './whatsapp/whatsapp.module';

@Module({
  imports: [
    // ... your existing imports
    WhatsAppModule,
  ],
  // ...
})
export class AppModule {}
```

### 5. Store Lawyer API Keys

Choose one of these approaches:

#### Option A: Add to LawyerProfile Entity

Add a field in `src/users/entities/lawyer-profile.entity.ts`:

```typescript
@Column({ nullable: true, select: false }) // Don't expose in regular queries
whatsappApiKey: string;
```

Then register API keys when lawyers log in or on app startup:

```typescript
// In src/users/users.service.ts
import { WhatsAppService } from '../whatsapp/whatsapp.service';

@Injectable()
export class UsersService {
  constructor(
    // ... other dependencies
    private whatsappService: WhatsAppService,
  ) {}

  async onModuleInit() {
    // Load all lawyers and register their WhatsApp API keys
    const lawyers = await this.userRepository.find({
      where: { role: UserRole.LAWYER },
      relations: ['lawyerProfile'],
    });

    for (const lawyer of lawyers) {
      if (lawyer.lawyerProfile?.whatsappApiKey) {
        this.whatsappService.registerLawyerApiKey(
          lawyer.email,
          lawyer.lawyerProfile.whatsappApiKey,
        );
      }
    }
  }
}
```

#### Option B: Create Separate WhatsApp Config Entity

Create a new entity (optional, more secure):

```typescript
// src/whatsapp/entities/whatsapp-config.entity.ts
import { Entity, PrimaryGeneratedColumn, Column, OneToOne, JoinColumn } from 'typeorm';
import { User } from '../../users/entities/user.entity';

@Entity('whatsapp_configs')
export class WhatsAppConfig {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ select: false }) // Never expose in queries
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

### 6. Enable Authentication Guards

Uncomment the guard decorators in `whatsapp.controller.ts`:

```typescript
@UseGuards(JwtAuthGuard, RolesGuard)
// and
@Roles(UserRole.LAWYER)
```

Update the imports at the top:

```typescript
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RolesGuard } from '../auth/guards/roles.guard';
import { Roles } from '../auth/decorators/roles.decorator';
import { UserRole } from '../common/enums/role.enum';
```

### 7. Implement Webhook Business Logic

In `webhook.controller.ts`, uncomment and implement the TODO sections:

```typescript
constructor(
  private configService: ConfigService,
  private notificationsService: NotificationsService, // Add your service
  private usersService: UsersService, // Add your service
) {
  // ...
}
```

Then implement the business logic in `handleIncomingMessage()`:

```typescript
private async handleIncomingMessage(data: any, lawyerId: number) {
  // 1. Find lawyer
  const lawyer = await this.usersService.findOne({ 
    where: { /* find by lawyerId */ } 
  });
  
  // 2. Create notification
  await this.notificationsService.create({
    userId: lawyer.id,
    type: 'whatsapp_message',
    title: 'New WhatsApp Message',
    message: `${data.message}`,
  });
}
```

## API Endpoints

Once installed, your AinSongjog backend will have these new endpoints:

### Send Message
```http
POST /whatsapp/send
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "clientPhoneNumber": "+8801712345678",
  "text": "Hello from AinSongjog!"
}
```

### Get Conversation History
```http
GET /whatsapp/conversations/+8801712345678?count=50
Authorization: Bearer <jwt_token>
```

### Get WhatsApp Clients
```http
GET /whatsapp/clients
Authorization: Bearer <jwt_token>
```

### Add Client
```http
POST /whatsapp/clients
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "John Doe",
  "phoneNumber": "+8801712345678",
  "email": "john@example.com"
}
```

### Webhook Receiver
```http
POST /webhooks/whatsapp
X-Webhook-Secret: <your-webhook-secret>
Content-Type: application/json

{
  "event_type": "message_received",
  "data": {
    "client_phone_number": "+8801712345678",
    "message": "Hello, I need legal help",
    "timestamp": "2026-01-28T10:00:00"
  },
  "lawyer_id": 1
}
```

## Usage Examples

### Send Appointment Reminder

```typescript
// In appointments.service.ts
async sendReminder(appointmentId: string) {
  const appointment = await this.findOne(appointmentId);
  
  await this.whatsappService.sendMessage(
    appointment.lawyer.email,
    {
      clientPhoneNumber: appointment.client.clientProfile.mobileNumber,
      text: `Reminder: Appointment on ${appointment.date} at ${appointment.time}`,
    },
  );
}
```

### Send Case Update

```typescript
// In cases.service.ts
async notifyClient(caseId: string, update: string) {
  const case = await this.findOne(caseId);
  
  await this.whatsappService.sendMessage(
    case.lawyer.email,
    {
      clientPhoneNumber: case.client.clientProfile.mobileNumber,
      text: `Case Update (${case.title}): ${update}`,
    },
  );
}
```

### Welcome New Client

```typescript
// In users.service.ts
async welcomeClient(clientId: string, lawyerEmail: string) {
  const client = await this.findOne(clientId);
  
  await this.whatsappService.sendMessage(
    lawyerEmail,
    {
      clientPhoneNumber: client.clientProfile.mobileNumber,
      text: 'Welcome to AinSongjog! I am your lawyer. Feel free to message me anytime.',
    },
  );
}
```

## Testing

### Test Message Sending

```bash
curl -X POST http://localhost:3001/whatsapp/send \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientPhoneNumber": "+8801712345678",
    "text": "Test message"
  }'
```

### Test Webhook

```bash
curl -X POST http://localhost:3001/webhooks/whatsapp \
  -H "X-Webhook-Secret: your-webhook-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "message_received",
    "data": {
      "client_phone_number": "+8801712345678",
      "message": "Hello",
      "timestamp": "2026-01-28T10:00:00"
    },
    "lawyer_id": 1
  }'
```

## Troubleshooting

### "No API key found for lawyer"

Make sure you've called `registerLawyerApiKey()` for each lawyer:

```typescript
this.whatsappService.registerLawyerApiKey(
  'lawyer@example.com',
  'the-api-key-from-whatsapp-bot-setup'
);
```

### Webhook not working

1. Check that the webhook URL is publicly accessible
2. Verify the webhook secret matches
3. Check WhatsApp bot logs for errors
4. Make sure the URL is registered with the WhatsApp bot

### TypeScript errors

Make sure you have axios installed:
```bash
npm install axios
npm install --save-dev @types/node
```

## Next Steps

1. ✅ Copy all module files to `src/whatsapp/`
2. ✅ Install axios dependency
3. ✅ Add environment variables
4. ✅ Register module in app.module.ts
5. ✅ Add WhatsApp API key field to LawyerProfile
6. ✅ Implement webhook business logic
7. ✅ Enable authentication guards
8. ✅ Test the integration

## Support

For detailed integration guide, see [AINSONGJOG_INTEGRATION.md](../AINSONGJOG_INTEGRATION.md)

For WhatsApp bot documentation, see:
- [Lawyer Directory Integration](../LAWYER_DIRECTORY_INTEGRATION.md)
- [Security Guide](../SECURITY.md)
- [Architecture](../ARCHITECTURE.md)
