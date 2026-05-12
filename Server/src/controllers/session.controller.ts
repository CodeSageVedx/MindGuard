import SessionModel from "@server/models/session.model.ts";
import { ApiError } from "@server/utils/apiError.ts";
import { ApiResponse } from "@server/utils/apiResponse.ts";
import { asyncHandler } from "@server/utils/asyncHandler.ts";
import { Request, Response } from "express";


export const startSession = asyncHandler(async (req : Request, res : Response) => {
    try {
        const {channel} = req.body;
    
        const userId = req.user?._id;
        if (!userId) {
            throw new ApiError(401, "Unauthorized request");
        }
        
        const newSession = await SessionModel.create({
            userId,
            channel,
            status : "active"
        })
    
        const createdSession = await SessionModel.findById(newSession._id);
        if (!createdSession) {
            throw new ApiError(500, "Failed to create session");
        }
        //TODO : Connect with AI service  or LiveKit service
        //FIXME : Risk level should be added after the completion of the session
        res.status(201).json(
            new ApiResponse(201, createdSession, "Session started successfully")
        )
    } catch (error : any) {
        throw new ApiError(error.statusCode || 500, error.message || "Internal Server Error");
    }
})

export const endSession = asyncHandler(async (req : Request, res : Response) => {
    const {sessionId} = req.body; // TODO : sessionID will come from agent microservice
    try {
        const session = await SessionModel.findById(sessionId);
        if (!session) {
            throw new ApiError(404, "Session not found");
        }
        session.status = "completed";
        await session.save();
        //TODO : Call report generation pipline
        res.status(200).json(
            new ApiResponse(200, session, "Session ended successfully")
        )
    } catch (error : any) {
        throw new ApiError(error.statusCode || 500, error.message || "Internal Server Error");
    }
})