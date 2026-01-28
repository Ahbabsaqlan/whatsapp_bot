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
