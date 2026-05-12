import mongoose, { Schema, Document } from "mongoose";
import jwt, { Secret, SignOptions } from "jsonwebtoken";

export interface User extends Document {
  phoneNumber: string;
  whatsappId?: string;
  emergencyContact?: string;
  otp?: string;
  otpExpiry?: Date;
  createdAt: Date;
  updatedAt: Date;
  refreshToken: string;

  generateAccessToken() : string;
  generateRefreshToken() : string;
}

const userSchema: Schema<User> = new Schema(
  {
    phoneNumber: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    whatsappId: {
      type: String,
      unique: true, // TODO: Subject to check
      trim: true,
    },
    emergencyContact: {
      type: String,
      required: false,
      trim: true,
    },
    otp: {
      type: String,
      trim: true,
    },
    otpExpiry: {
      type: Date,
    },
    refreshToken: {
      type: String,
    },
  },
  { timestamps: true },
);

userSchema.methods.generateAccessToken = function () {
  const secret = process.env.ACCESS_TOKEN_SECRET;
  const expiresInEnv = process.env.ACCESS_TOKEN_EXPIRES_IN;

  if (!secret) {
    throw new Error("ACCESS_TOKEN_SECRET is not set");
  }
  if (!expiresInEnv) {
    throw new Error("ACCESS_TOKEN_EXPIRES_IN is not set");
  }

  const options: SignOptions = {
    // jsonwebtoken’s types use a template‑literal `StringValue`,
    // so we cast the env string into that shape explicitly.
    expiresIn: expiresInEnv as unknown as SignOptions["expiresIn"],
  };

  return jwt.sign(
    {
      _id: this._id,
      phoneNumber: this.phoneNumber,
    },
    secret as Secret,
    options,
  );
};

userSchema.methods.generateRefreshToken = function () {
  const secret = process.env.REFRESH_TOKEN_SECRET;
  const expiresInEnv = process.env.REFRESH_TOKEN_EXPIRES_IN;

  if (!secret) {
    throw new Error("REFRESH_TOKEN_SECRET is not set");
  }
  if (!expiresInEnv) {
    throw new Error("REFRESH_TOKEN_EXPIRES_IN is not set");
  }

  const options: SignOptions = {
    // jsonwebtoken’s types use a template‑literal `StringValue`,
    // so we cast the env string into that shape explicitly.
    expiresIn: expiresInEnv as unknown as SignOptions["expiresIn"],
  };

  return jwt.sign(
    {
      _id : this._id,
      phoneNumber : this.phoneNumber
    },
    secret as Secret,
    options
  )
}

export const UserModel = (mongoose.models.User as mongoose.Model<User>) || mongoose.model<User>("User", userSchema);

// export default UserModel;