import ChatLogModel from "@server/models/chatLog.model.ts";
import SessionModel from "@server/models/session.model.ts";
import { ApiError } from "@server/utils/apiError.ts";
import { ApiResponse } from "@server/utils/apiResponse.ts";
import { asyncHandler } from "@server/utils/asyncHandler.ts";
import { Request, Response } from "express";

export const chatMessage = asyncHandler(async (req: Request, res: Response) => {
    const { sessionId, content } = req.body;
    const userId = req.user?._id;

    if (!sessionId || !content) {
        throw new ApiError(400, "Session ID and content are required");
    }

    try {
        // Verify session exists and is active
        const session = await SessionModel.findById(sessionId);
        if (!session) {
            throw new ApiError(404, "Session not found");
        }
        if (session.status !== "active") {
            throw new ApiError(400, "Session is not active");
        }
        if (session.userId.toString() !== userId?.toString()) {
            throw new ApiError(403, "Unauthorized to access this session");
        }

        // 1. Save user message to DB
        const userMessage = await ChatLogModel.create({
            sessionId,
            sender: "user",
            content
        });

        // 2. Forward message to AI microservice
        // TODO: Import and use AI service
        // const aiResponse = await aiService.sendMessage(sessionId, content);
        const aiResponse = { content: "AI response placeholder" }; // Placeholder

        // 3. Save AI response to DB
        const aiMessage = await ChatLogModel.create({
            sessionId,
            sender: "ai",
            content: aiResponse.content
        });

        // 4. Return both messages to user for real-time chat experience
        res.status(200).json(
            new ApiResponse(200, {
                userMessage,
                aiMessage
            }, "Message sent successfully")
        );

    } catch (error: any) {
        throw new ApiError(
            error.statusCode || 500,
            error.message || "Failed to process message"
        );
    }
});

// Get chat history for a session
export const getChatHistory = asyncHandler(async (req: Request, res: Response) => {
    const { sessionId } = req.params;
    const userId = req.user?._id;

    try {
        // Verify session ownership
        const session = await SessionModel.findById(sessionId);
        if (!session) {
            throw new ApiError(404, "Session not found");
        }
        if (session.userId.toString() !== userId?.toString()) {
            throw new ApiError(403, "Unauthorized to access this session");
        }

        // Fetch chat history
        const chatHistory = await ChatLogModel.find({ sessionId })
            .sort({ createdAt: 1 }); // Oldest first for chronological order

        res.status(200).json(
            new ApiResponse(200, chatHistory, "Chat history retrieved successfully")
        );

    } catch (error: any) {
        throw new ApiError(
            error.statusCode || 500,
            error.message || "Failed to retrieve chat history"
        );
    }
});