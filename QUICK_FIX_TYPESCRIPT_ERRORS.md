# Quick Fix - TypeScript Errors

## 🔴 Error 1: appointments.service.ts - Missing 'findOne'

**File:** `src/appointments/appointments.service.ts`

### Add to imports:
```typescript
import { WhatsAppService } from '../whatsapp/whatsapp.service';
```

### Add to constructor:
```typescript
constructor(
  @InjectRepository(Appointment)
  private appointmentsRepository: Repository<Appointment>,
  private whatsappService: WhatsAppService, // ← ADD THIS
) {}
```

### Replace the method with:
```typescript
async sendAppointmentReminder(appointmentId: string) {
  const appointment = await this.appointmentsRepository.findOne({
    where: { id: appointmentId },
    relations: ['lawyer', 'lawyer.lawyerProfile', 'client', 'client.clientProfile'],
  });
  
  if (!appointment) {
    throw new Error(`Appointment not found`);
  }
  
  // ⚠️ IMPORTANT: Check your Appointment entity for actual field names!
  // Common variations: scheduledDate, appointmentDate, startTime, etc.
  // Update the template string below to match YOUR entity fields
  
  await this.whatsappService.sendMessage(
    appointment.lawyer.email,
    {
      clientPhoneNumber: appointment.client.clientProfile.mobileNumber,
      text: `Reminder: You have an appointment scheduled. Please check your appointment details.`,
      // Example with actual fields (customize based on your entity):
      // text: `Reminder: Appointment on ${appointment.scheduledDate} at ${appointment.startTime}`,
    },
  );
}
```

---

## 🔴 Error 2: users.service.ts - Missing 'findAllLawyers'

**File:** `src/users/users.service.ts`

### Add to imports:
```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import { WhatsAppService } from '../whatsapp/whatsapp.service';
import { UserRole } from '../common/enums/role.enum';
```

### Update class declaration:
```typescript
@Injectable()
export class UsersService implements OnModuleInit { // ← ADD OnModuleInit
```

### Add to constructor:
```typescript
constructor(
  @InjectRepository(User)
  private usersRepository: Repository<User>,
  private whatsappService: WhatsAppService, // ← ADD THIS
) {}
```

### Add these methods:
```typescript
async findAllLawyers(): Promise<User[]> {
  return this.usersRepository.find({
    where: { role: UserRole.LAWYER },
    relations: ['lawyerProfile'],
  });
}

async onModuleInit() {
  const lawyers = await this.findAllLawyers();
  for (const lawyer of lawyers) {
    if (lawyer.lawyerProfile?.whatsappApiKey) {
      this.whatsappService.registerLawyerApiKey(
        lawyer.email,
        lawyer.lawyerProfile.whatsappApiKey,
      );
    }
  }
  console.log(`✅ Registered API keys for ${lawyers.filter(l => l.lawyerProfile?.whatsappApiKey).length} lawyers`);
}
```

---

## 📦 Module Updates

### File: `src/appointments/appointments.module.ts`

```typescript
import { WhatsAppModule } from '../whatsapp/whatsapp.module'; // ADD

@Module({
  imports: [
    TypeOrmModule.forFeature([Appointment]),
    WhatsAppModule, // ← ADD THIS
  ],
  // ...
})
```

### File: `src/users/users.module.ts`

```typescript
import { WhatsAppModule } from '../whatsapp/whatsapp.module'; // ADD

@Module({
  imports: [
    TypeOrmModule.forFeature([User, LawyerProfile, ClientProfile]),
    WhatsAppModule, // ← ADD THIS
  ],
  // ...
})
```

---

## ✅ Checklist

- [ ] Add WhatsAppService import to appointments.service.ts
- [ ] Inject WhatsAppService in AppointmentsService constructor
- [ ] Update sendAppointmentReminder to use repository.findOne
- [ ] Import WhatsAppModule in appointments.module.ts
- [ ] Add WhatsAppService import to users.service.ts
- [ ] Add OnModuleInit to UsersService class declaration
- [ ] Inject WhatsAppService in UsersService constructor
- [ ] Add findAllLawyers() method to UsersService
- [ ] Add onModuleInit() method to UsersService
- [ ] Import WhatsAppModule in users.module.ts
- [ ] Run `npm run build` to check for errors
- [ ] Run `npm run start:dev` to test

---

## 🏃 Quick Test

After changes, run:
```bash
npm run build
npm run start:dev
```

You should see:
```
✅ Registered API keys for X lawyers
```

---

## 🔧 Troubleshooting

### Error: Property 'date' or 'time' does not exist on type 'Appointment'

**Problem:** The example code uses generic field names that might not match your entity.

**Solution:** Check your actual Appointment entity fields:

1. Open `src/appointments/entities/appointment.entity.ts`
2. Look for the date/time field names (e.g., `scheduledDate`, `appointmentDate`, `startTime`, `endTime`)
3. Update the message template in your service:

```typescript
// Example if your entity has 'scheduledDate' and 'startTime':
text: `Reminder: Appointment on ${appointment.scheduledDate} at ${appointment.startTime}`,

// Or use a generic message without field references:
text: `Reminder: You have an upcoming appointment. Please check your schedule.`,
```

**Common field name variations:**
- Date: `date`, `scheduledDate`, `appointmentDate`, `scheduledAt`
- Time: `time`, `startTime`, `appointmentTime`, `timeSlot`

---

See `AINSONGJOG_TYPESCRIPT_FIXES.md` for detailed explanations.
