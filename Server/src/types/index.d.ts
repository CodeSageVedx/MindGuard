import type { User } from "@server/models/user.model.ts";

declare global {
  namespace Express {
    interface Request {
      user?: User;
    }
  }
}