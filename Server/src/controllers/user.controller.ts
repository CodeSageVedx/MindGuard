import {UserModel} from "@server/models/user.model.ts";
import { loginSchema, type LoginInput } from "@server/schema/login.schema.ts";
import { emergencyContactSchema, type EmergencyContactInput } from "@server/schema/emergencyContact.schema.ts";
import { verifyOtpSchema, type VerifyOtpInput } from "@server/schema/verifyOtp.schema.ts";
import { ApiError } from "@server/utils/apiError.ts";
import { ApiResponse } from "@server/utils/apiResponse.ts";
import { asyncHandler } from "@server/utils/asyncHandler.ts";
import { randomInt } from "crypto";
import { Request, Response } from "express";
import { Types } from "mongoose";

type LoginRequest = Request<{}, any, LoginInput>;
type EmergencyContactRequest = Request<{}, any, EmergencyContactInput>;

const generateOtp = (): string => {
  const num = randomInt(100000, 1000000); // 100000–999999
  return String(num);
};

const getAccessRefreshToken = async (userId : Types.ObjectId) => {
    const user = await UserModel.findById(userId);
    const accessToken = user.generateAccessToken();
    const refreshToken = user.generateRefreshToken();

    user.refreshToken = refreshToken;
    await user.save({validateBeforeSave : false})
    return {accessToken, refreshToken};
}

// Login route
export const loginUser = asyncHandler(async (req: LoginRequest, res: Response) => {
    try {
        const parsed = loginSchema.safeParse(req.body);
        if (!parsed.success) {
            throw new ApiError(400, "Invalid phone number");
        }

        const { phoneNumber } = parsed.data;

        let user = await UserModel.findOne({ phoneNumber });

        const otp = generateOtp();
        const otpExpiry = new Date(Date.now() + 5 * 60 * 1000); // 5 minutes from now
        // TODO : SEND OTP TO USER using whatsapp

        if (!user) {
            user = await UserModel.create({
                phoneNumber,
                otp,
                otpExpiry,
            });

            return res.status(200).json(
                new ApiResponse(
                    200,
                    {
                        phoneNumber,
                        requiresEmergencyContact : true,
                    },
                    "First time login, OTP sent. Emergency contact required"
                )
            )
        }

        user.otp = otp;
        user.otpExpiry = otpExpiry;
        await user.save();

        const requiresEmergencyContact = !user.emergencyContact || user.emergencyContact.trim().length === 0;

        return res.status(200).json(
            new ApiResponse(
                200,
                {
                    phoneNumber,
                    requiresEmergencyContact,
                },
                "OTP sent successfully",
            ),
            );

    } catch (error: any) {
        throw new ApiError(error.statusCode || 500, error.message || "Internal Server Error");
    }
});



export const submitEmergencyContact = asyncHandler(
  async (req: EmergencyContactRequest, res: Response) => {
    try {
      const parsed = emergencyContactSchema.safeParse(req.body);
      if (!parsed.success) {
        throw new ApiError(400, "Invalid input data");
      }

      const { emergencyContact } = parsed.data;

      const authUser = req.user;
      if (!authUser) {
        throw new ApiError(401, "Unauthorized request");
      }

      const user = await UserModel.findById(authUser._id);
      if (!user) {
        throw new ApiError(404, "User not found");
      }

      user.emergencyContact = emergencyContact;
      await user.save();

      return res
        .status(200)
        .json(
          new ApiResponse(
            200,
            { user },
            "Emergency contact updated successfully",
          ),
        );
    } catch (error: any) {
      throw new ApiError(
        error.statusCode || 500,
        error.message || "Internal Server Error",
      );
    }
  },
);

// Verify OTP -----------------------
type VerifyOtpRequest = Request<{}, any, VerifyOtpInput>;

export const verifyOtp = asyncHandler(async (req: VerifyOtpRequest, res: Response) => {
  try {
    const parsed = verifyOtpSchema.safeParse(req.body);
    if (!parsed.success) {
      throw new ApiError(400, "Invalid input data");
    }

    const { phoneNumber, otp } = parsed.data;

    const user = await UserModel.findOne({ phoneNumber });
    if (!user) {
      throw new ApiError(404, "User not found for this phone number");
    }

    if (!user.otp || !user.otpExpiry) {
      throw new ApiError(400, "OTP not requested or already verified");
    }

    if (user.otpExpiry.getTime() < Date.now()) {
      // clear expired OTP
      user.otp = undefined;
      user.otpExpiry = undefined;
      await user.save();
      throw new ApiError(400, "OTP has expired, please request a new one");
    }

    if (user.otp !== otp) {
      throw new ApiError(400, "Invalid OTP");
    }

    // OTP is valid – clear it
    user.otp = undefined;
    user.otpExpiry = undefined;
    await user.save();

    const requiresEmergencyContact = !user.emergencyContact || user.emergencyContact.trim().length === 0;

    const {refreshToken, accessToken} = await getAccessRefreshToken(user._id);

    const loggedInUser = await UserModel.findById(user._id).select("-refreshToken");

    const options = {
        httpOnly : true,
        secure : true
    }

    const accessTokenMaxAge = 24 * 60 * 60 * 1000; // 1 day in ms
    const refreshTokenMaxAge = 10 * 24 * 60 * 60 * 1000; // 10 days in ms

    return res.status(200)
      .cookie("refreshToken", refreshToken, {
        ...options,
        maxAge: refreshTokenMaxAge,
      })
      .cookie("accessToken", accessToken, {
        ...options,
        maxAge: accessTokenMaxAge,
      })
      .json(
      new ApiResponse(
        200,
        {
          loggedInUser,
          requiresEmergencyContact,
        },
        "OTP verified successfully",
      ),
    );
  } catch (error: any) {
    throw new ApiError(error.statusCode || 500, error.message || "Internal Server Error");
  }
});


export const logoutUser = asyncHandler(async (req: Request, res: Response) => {
  try {
    const user = req.user;
    if (!user) {
      throw new ApiError(401, "Unauthorized request");
    }

    await UserModel.findByIdAndUpdate(
      user._id,
      { $unset: { refreshToken: 1 } },
      { new: true },
    );

    const cookieOptions = {
      httpOnly: true,
      secure: true,
      // sameSite: "strict" as const,
    };

    return res
      .status(200)
      .clearCookie("accessToken", cookieOptions)
      .clearCookie("refreshToken", cookieOptions)
      .json(new ApiResponse(200, {}, "Logged out successfully"));
  } catch (error: any) {
    throw new ApiError(error.statusCode || 500, error.message || "Internal Server Error");
  }
});