import express, { urlencoded } from 'express';
import cookieParser from "cookie-parser";
import cors from "cors";

const app = express();

app.use(cors({
    origin : process.env.CORS_ORIGIN,
    credentials : true
}))
app.use(express.json({
    limit : "20kb"
}))
app.use(urlencoded({
    extended: true,
    limit : "20kb"
}))
app.use(express.static("public"))
app.use(cookieParser())



import healthCheckRouter from './routes/healthcheck.route.ts';
import userRouter from './routes/user.route.ts';
import sessionRouter from './routes/session.route.ts';

app.use('/api/v1/healthcheck', healthCheckRouter);
app.use('/api/v1/auth', userRouter);
app.use('/api/v1/session', sessionRouter);

export default app;