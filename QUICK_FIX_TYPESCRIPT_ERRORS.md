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
  
  await this.whatsappService.sendMessage(
    appointment.lawyer.email,
    {
      clientPhoneNumber: appointment.client.clientProfile.mobileNumber,
      text: `Reminder: Appointment on ${appointment.date} at ${appointment.time}`,
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

See `AINSONGJOG_TYPESCRIPT_FIXES.md` for detailed explanations.
