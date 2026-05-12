import { UserModel } from "@server/models/user.model.ts";
import { ApiError } from "@server/utils/apiError.ts";
import { asyncHandler } from "@server/utils/asyncHandler.ts";
import { NextFunction, Request, Response } from "express";
import jwt, { JwtPayload, Secret } from "jsonwebtoken";

export const verifyJWT = asyncHandler(
  async (req: Request, _res: Response, next: NextFunction) => {
    try {
      const token =
        req.cookies?.accessToken ||
        req.header("Authorization")?.replace("Bearer ", "");

      if (!token) {
        throw new ApiError(401, "Unauthorized request");
      }

      const secret = process.env.ACCESS_TOKEN_SECRET;
      if (!secret) {
        throw new ApiError(500, "ACCESS_TOKEN_SECRET is not set");
      }

      const decoded = jwt.verify(token, secret as Secret) as JwtPayload & {
        _id: string;
      };

      const user = await UserModel.findById(decoded._id).select("-refreshToken");
      if (!user) {
        throw new ApiError(401, "Invalid access token");
      }

      req.user = user;
      next();
    } catch (error: any) {
      throw new ApiError(
        error.statusCode || 500,
        error?.message || "Invalid access token",
      );
    }
  },
);


export const verifyUserOrAgent = asyncHandler(
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Check for agent service token first
      const agentToken = req.header("X-Agent-Token");
      if (agentToken) {
        const agentSecret = process.env.AGENT_SERVICE_SECRET;
        if (!agentSecret) {
          throw new ApiError(500, "AGENT_SERVICE_SECRET is not set");
        }
        if (agentToken === agentSecret) {
          // Agent authenticated - skip user verification
          return next();
        }
        throw new ApiError(401, "Invalid agent token");
      }

      // Fall back to user JWT verification
      return verifyJWT(req, res, next);
    } catch (error: any) {
      throw new ApiError(
        error.statusCode || 500,
        error?.message || "Authentication failed",
      );
    }
  },
);