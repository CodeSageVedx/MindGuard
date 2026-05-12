import { healthCheck } from "@server/controllers/healthcheck.controller.ts";
import { Router } from "express";

const healthCheckRouter = Router();

healthCheckRouter.route('/').get(healthCheck);

export default healthCheckRouter;