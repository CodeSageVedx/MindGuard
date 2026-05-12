import mongoose, { Schema, Document } from "mongoose";

export interface Session extends Document {
    userId : mongoose.Types.ObjectId;
    channel : "web" | "whatsapp" | "videoCall";
    status : "active" | "completed";
    riskLevel ?: "low" | "medium" | "high";
    createdAt : Date;
    endedAt : Date;
}

const sessionSchema: Schema<Session> = new Schema({
    userId :{
        type : Schema.Types.ObjectId,
        ref : "User",
        required : true
    },
    channel : {
        type : String,
        enum : ["web", "whatsapp", "videoCall"],
        required : true
    },
    status : {
        type : String,
        enum : ["active", "completed"],
        required : true
    }, 
    riskLevel : {
        type : String,
        enum : ["low", "medium", "high"],
    }
},{
    timestamps : {
        createdAt : "createdAt",
        updatedAt : "endedAt"
    }
})


const SessionModel =
  (mongoose.models.Session as mongoose.Model<Session>) ||
  mongoose.model<Session>('Session', sessionSchema);

export default SessionModel;