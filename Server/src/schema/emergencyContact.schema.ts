import { z } from "zod";
// import { loginSchema } from "@server/schema/login.schema.ts";

export const emergencyContactSchema = z.object({
  emergencyContact: z.string().min(1, "Emergency contact is required"),
});

export type EmergencyContactInput = z.infer<typeof emergencyContactSchema>;
