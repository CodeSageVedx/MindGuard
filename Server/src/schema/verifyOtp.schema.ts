import { z } from "zod";
import { loginSchema } from "@server/schema/login.schema.ts";

export const verifyOtpSchema = loginSchema.extend({
  otp: z.string().length(6, "OTP must be 6 digits"),
});

export type VerifyOtpInput = z.infer<typeof verifyOtpSchema>;
