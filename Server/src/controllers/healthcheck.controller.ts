import { ApiResponse } from "@server/utils/apiResponse.ts";
import { asyncHandler } from "@server/utils/asyncHandler.ts";

const healthCheck = asyncHandler(async (req, res) => {
    res.status(200).json(
        new ApiResponse(200, {
            isServerRunning: true
        }, "Server is running successfully")
    )
});

export { healthCheck };