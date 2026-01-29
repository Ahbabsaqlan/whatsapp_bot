import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { WhatsAppService } from './whatsapp.service';
import { WhatsAppController } from './whatsapp.controller';
import { WhatsAppWebhookController } from './webhook.controller';

// ⚠️ IMPORTANT: When uncommenting imports below, follow these steps:
// 1. Uncomment BOTH the import statement AND the module in the imports array
// 2. Make sure the paths match your project structure
// 3. Remove the comment syntax (//) from both lines together
// 
// Example:
// import { NotificationsModule } from '../notifications/notifications.module';
// ...and in imports array below...
// NotificationsModule,

// Step 1: Uncomment these import statements if you need them
// import { NotificationsModule } from '../notifications/notifications.module';
// import { UsersModule } from '../users/users.module';

@Module({
  imports: [
    ConfigModule,
    // Step 2: Uncomment the corresponding modules here (match with Step 1)
    // NotificationsModule,
    // UsersModule,
  ],
  controllers: [WhatsAppController, WhatsAppWebhookController],
  providers: [WhatsAppService],
  exports: [WhatsAppService], // Export so other modules can use it
})
export class WhatsAppModule {}
