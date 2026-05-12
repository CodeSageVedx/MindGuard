import mongoose, { Schema, Document } from "mongoose";

export interface ChatLog extends Document {
    sessionId : mongoose.Types.ObjectId;
    sender : "user" | "AI";
    content : string;
    createdAt : Date;
    updatedAt : Date;
}


const chatLogSchema: Schema<ChatLog> = new Schema({
    sessionId : {
        type : Schema.Types.ObjectId,
        ref : "Session",
        required : true
    }, 
    sender : {
        type : String,
        enum : ["user", "AI"],
        required : true
    }, 
    content : {
        type : String,
        required : true
    }
}, {timestamps : true})

const ChatLogModel =
    (mongoose.models.ChatLog as mongoose.Model<ChatLog>) ||
    mongoose.model<ChatLog>('ChatLog', chatLogSchema);

export default ChatLogModel;