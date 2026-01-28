import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { WhatsAppService } from './whatsapp.service';
import { WhatsAppController } from './whatsapp.controller';
import { WhatsAppWebhookController } from './webhook.controller';

// Uncomment these imports when integrating with your AinSongjog modules
// import { NotificationsModule } from '../notifications/notifications.module';
// import { UsersModule } from '../users/users.module';

@Module({
  imports: [
    ConfigModule,
    // Uncomment these when ready to integrate
    // NotificationsModule,
    // UsersModule,
  ],
  controllers: [WhatsAppController, WhatsAppWebhookController],
  providers: [WhatsAppService],
  exports: [WhatsAppService], // Export so other modules can use it
})
export class WhatsAppModule {}
