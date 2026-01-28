import { Controller, Post, Body, Headers, UnauthorizedException, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

/**
 * Webhook controller for receiving WhatsApp messages from the bot
 * POST /webhooks/whatsapp
 * 
 * This endpoint receives notifications when:
 * - A client sends a message to a lawyer
 * - A lawyer sends a message (confirmation)
 * 
 * To use this controller, you need to:
 * 1. Make sure it's publicly accessible (use ngrok for local development)
 * 2. Register the webhook URL with the WhatsApp bot for each lawyer
 * 3. Set WHATSAPP_WEBHOOK_SECRET in your .env file
 */
@Controller('webhooks/whatsapp')
export class WhatsAppWebhookController {
  private readonly logger = new Logger(WhatsAppWebhookController.name);
  private readonly webhookSecret: string;

  constructor(
    private configService: ConfigService,
    // Inject your services here:
    // private notificationsService: NotificationsService,
    // private usersService: UsersService,
  ) {
    this.webhookSecret = this.configService.get<string>('WHATSAPP_WEBHOOK_SECRET', '');
  }

  /**
   * Receive webhook notifications from WhatsApp bot
   * 
   * Expected payload format:
   * {
   *   event_type: 'message_received' | 'message_sent',
   *   data: {
   *     client_phone_number: string,
   *     message: string,
   *     timestamp: string
   *   },
   *   lawyer_id: number
   * }
   */
  @Post()
  async handleWebhook(
    @Headers('x-webhook-secret') webhookSecret: string,
    @Body() payload: any,
  ) {
    // Verify webhook secret for security
    if (this.webhookSecret && webhookSecret !== this.webhookSecret) {
      this.logger.warn('Invalid webhook secret received');
      throw new UnauthorizedException('Invalid webhook secret');
    }

    this.logger.log(`Received webhook: ${payload.event_type}`);
    this.logger.debug(`Webhook payload: ${JSON.stringify(payload)}`);

    try {
      const { event_type, data, lawyer_id } = payload;

      if (event_type === 'message_received') {
        // Handle incoming WhatsApp message from client
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
   * Handle incoming WhatsApp message from client to lawyer
   */
  private async handleIncomingMessage(data: any, lawyerId: number) {
    const { client_phone_number, message, timestamp } = data;

    this.logger.log(
      `Incoming message from ${client_phone_number} to lawyer ${lawyerId}: ${message}`,
    );

    // TODO: Implement your business logic here
    // Examples:
    
    // 1. Find the lawyer user by WhatsApp lawyer ID
    // const lawyer = await this.usersService.findByWhatsAppLawyerId(lawyerId);
    
    // 2. Find or create the client by phone number
    // const client = await this.usersService.findOrCreateByPhone(client_phone_number);
    
    // 3. Create a notification for the lawyer
    // await this.notificationsService.create({
    //   userId: lawyer.id,
    //   type: 'whatsapp_message',
    //   title: 'New WhatsApp Message',
    //   message: `New message from ${client_phone_number}: ${message}`,
    //   data: { 
    //     phone: client_phone_number, 
    //     message, 
    //     timestamp 
    //   },
    // });
    
    // 4. Store the message in your database
    // await this.messagesService.create({
    //   lawyerId: lawyer.id,
    //   clientPhone: client_phone_number,
    //   content: message,
    //   direction: 'incoming',
    //   timestamp: new Date(timestamp),
    // });
    
    // 5. Send push notification to lawyer's mobile app
    // await this.pushService.sendToUser(lawyer.id, {
    //   title: 'New WhatsApp Message',
    //   body: message,
    // });
    
    // 6. Send email notification if lawyer is offline
    // if (!lawyer.isOnline) {
    //   await this.emailService.sendLawyerMessageNotification(lawyer, message);
    // }
    
    // 7. Update case or appointment if message relates to one
    // await this.casesService.addMessageToCase(caseId, message);
  }

  /**
   * Handle sent message confirmation from lawyer to client
   */
  private async handleSentMessage(data: any, lawyerId: number) {
    const { client_phone_number, message, timestamp } = data;

    this.logger.log(
      `Message sent to ${client_phone_number} from lawyer ${lawyerId}`,
    );

    // TODO: Implement your business logic here
    // Examples:
    
    // 1. Update message status in your database
    // await this.messagesService.updateStatus(messageId, 'sent');
    
    // 2. Track sent messages for analytics
    // await this.analyticsService.trackMessageSent(lawyerId, client_phone_number);
    
    // 3. Update conversation metadata
    // await this.conversationsService.updateLastMessage(lawyerId, client_phone_number, message);
  }
}
