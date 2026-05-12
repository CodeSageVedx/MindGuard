import { z } from "zod";
import { parsePhoneNumberFromString } from "libphonenumber-js";

export const loginSchema = z.object({
  phoneNumber: z
    .preprocess((val) => {
      if (val == null) return val;
      return String(val).trim();
    }, z.string())
    .transform((raw) => {
      // Try parsing as India number if user gave 10 digits or local format
      const parsed =
        parsePhoneNumberFromString(raw, "IN") ||
        parsePhoneNumberFromString(raw); // handles +91... too

      if (!parsed || !parsed.isValid() || parsed.country !== "IN") {
        throw new Error("Invalid Indian mobile number.");
      }
      return parsed.number; // E.164 like +919876543210
    }),
});

export type LoginInput = z.infer<typeof loginSchema>;
