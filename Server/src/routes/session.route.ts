import { endSession, startSession } from "@server/controllers/session.controller.ts";
import { verifyJWT, verifyUserOrAgent } from "@server/middleware/auth.middleware.ts";
import { Router } from "express";


const sessionRouter = Router();

sessionRouter.route('/start').post(verifyJWT, startSession);
sessionRouter.route('/end').post(verifyUserOrAgent, endSession); 

export default sessionRouter;