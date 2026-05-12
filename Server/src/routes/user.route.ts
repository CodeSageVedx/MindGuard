import { loginUser, logoutUser, submitEmergencyContact, verifyOtp } from "@server/controllers/user.controller.ts";
import { verifyJWT } from "@server/middleware/auth.middleware.ts";
import { Router } from "express";

const userRouter = Router();

userRouter.route('/generateotp').post(loginUser);
userRouter.route('/verifyotp').post(verifyOtp);
userRouter.route('/submitEmergencyContact').post(verifyJWT,submitEmergencyContact);
userRouter.route("/logout").post( verifyJWT,logoutUser);

export default userRouter;