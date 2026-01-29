# URGENT FIX: Appointment Entity Field Errors

## Your Current Error

```
error TS2339: Property 'date' does not exist on type 'Appointment'.
error TS2339: Property 'time' does not exist on type 'Appointment'.
```

## Quick Fix (Choose One Option)

### ✅ Option 1: Use Generic Message (FASTEST - No Entity Changes Needed)

In `src/appointments/appointments.service.ts`, update the message to:

```typescript
await this.whatsappService.sendMessage(
  appointment.lawyer.email,
  {
    clientPhoneNumber: appointment.client.clientProfile.mobileNumber,
    text: `Reminder: You have an upcoming appointment. Please check your schedule.`,
  },
);
```

**This will work immediately!** No need to check entity fields.

---

### 🔧 Option 2: Customize Based on Your Entity Fields

**Step 1:** Check your Appointment entity fields

```bash
cat src/appointments/entities/appointment.entity.ts
```

Look for date/time field names. They might be:
- `scheduledDate`, `appointmentDate`, `date`, `scheduledAt`
- `startTime`, `endTime`, `time`, `timeSlot`

**Step 2:** Update your message using the actual field names

```typescript
await this.whatsappService.sendMessage(
  appointment.lawyer.email,
  {
    clientPhoneNumber: appointment.client.clientProfile.mobileNumber,
    // Replace 'scheduledDate' and 'startTime' with your actual field names:
    text: `Reminder: Appointment on ${appointment.scheduledDate} at ${appointment.startTime}`,
  },
);
```

---

## Common Field Name Patterns

| What You Need | Possible Field Names |
|---------------|---------------------|
| Date | `scheduledDate`, `appointmentDate`, `date`, `scheduledAt` |
| Time | `startTime`, `endTime`, `time`, `timeSlot` |
| Location | `location`, `address`, `venue` |

---

## Test Your Fix

```bash
npm run build
npm run start:dev
```

Should compile without errors!

---

## More Examples

### If your entity has `scheduledAt` (DateTime field):

```typescript
text: `Reminder: Appointment scheduled for ${new Date(appointment.scheduledAt).toLocaleString()}`,
```

### If your entity has separate date and time fields:

```typescript
text: `Reminder: Appointment on ${appointment.appointmentDate} at ${appointment.appointmentTime}`,
```

### If you want to keep it simple:

```typescript
text: `Reminder: You have an upcoming appointment with ${appointment.lawyer.firstName} ${appointment.lawyer.lastName}.`,
```

---

## Still Getting Errors?

1. **Check entity file:** Open `src/appointments/entities/appointment.entity.ts`
2. **Look for `@Column()` decorators** - these show available fields
3. **Use console.log temporarily:**
   ```typescript
   console.log('Available fields:', Object.keys(appointment));
   ```
4. **See full guide:** Check `AINSONGJOG_TYPESCRIPT_FIXES.md` for detailed help

---

## Summary

✅ **Quickest fix:** Use generic message (Option 1)  
🔧 **Best fix:** Check your entity and use actual field names (Option 2)  
📖 **Need help:** See `AINSONGJOG_TYPESCRIPT_FIXES.md` for complete guide
