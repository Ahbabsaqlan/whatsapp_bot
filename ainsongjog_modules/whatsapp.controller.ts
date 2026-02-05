import { Controller, Post, Get, Body, Param, Query, UseGuards, Request } from '@nestjs/common';
import { WhatsAppService } from './whatsapp.service';
// import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
// import { RolesGuard } from '../auth/guards/roles.guard';
// import { Roles } from '../auth/decorators/roles.decorator';
// import { UserRole } from '../common/enums/role.enum';

@Controller('whatsapp')
// Uncomment these guards when integrating with your auth system
// @UseGuards(JwtAuthGuard, RolesGuard)
export class WhatsAppController {
  constructor(private readonly whatsappService: WhatsAppService) {}

  /**
   * Send a message to a client (Lawyer only)
   * POST /whatsapp/send
   * 
   * Body: {
   *   clientPhoneNumber: string,
   *   text: string,
   *   filePath?: string
   * }
   */
  @Post('send')
  // @Roles(UserRole.LAWYER)
  async sendMessage(@Request() req, @Body() body: any) {
    // Extract lawyer email from authenticated user
    const lawyerEmail = req.user?.email || body.lawyerEmail;
    
    return this.whatsappService.sendMessage(lawyerEmail, {
      clientPhoneNumber: body.clientPhoneNumber,
      text: body.text,
      filePath: body.filePath,
    });
  }

  /**
   * Get conversation history with a client (Lawyer only)
   * GET /whatsapp/conversations/:phoneNumber?count=50
   */
  @Get('conversations/:phoneNumber')
  // @Roles(UserRole.LAWYER)
  async getConversation(
    @Request() req,
    @Param('phoneNumber') phoneNumber: string,
    @Query('count') count?: number,
  ) {
    const lawyerEmail = req.user?.email;
    return this.whatsappService.getConversationHistory(
      lawyerEmail,
      phoneNumber,
      count || 50,
    );
  }

  /**
   * Get all WhatsApp clients for the lawyer
   * GET /whatsapp/clients
   */
  @Get('clients')
  // @Roles(UserRole.LAWYER)
  async getClients(@Request() req) {
    const lawyerEmail = req.user?.email;
    return this.whatsappService.getLawyerClients(lawyerEmail);
  }

  /**
   * Add a client to WhatsApp contacts (Lawyer only)
   * POST /whatsapp/clients
   * 
   * Body: {
   *   name: string,
   *   phoneNumber: string,
   *   email?: string
   * }
   */
  @Post('clients')
  // @Roles(UserRole.LAWYER)
  async addClient(@Request() req, @Body() body: any) {
    const lawyerEmail = req.user?.email;
    return this.whatsappService.addClient(
      lawyerEmail,
      body.name,
      body.phoneNumber,
      body.email,
    );
  }

  /**
   * Register webhook for receiving WhatsApp messages
   * POST /whatsapp/webhook
   * 
   * Body: {
   *   url: string,
   *   eventType?: string
   * }
   */
  @Post('webhook')
  // @Roles(UserRole.LAWYER)
  async registerWebhook(@Request() req, @Body() body: any) {
    const lawyerEmail = req.user?.email;
    return this.whatsappService.registerWebhook(
      lawyerEmail,
      body.url,
      body.eventType || 'message_received',
    );
  }
}
