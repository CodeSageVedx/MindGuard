import mongoose, { Schema, Document } from "mongoose";

export interface Report extends Document {
    sessionId : mongoose.Types.ObjectId;
    riskScore : number;
    symptoms : any;
    summary ?: string;
    nextSteps ?: any;
    createdAt : Date;
    updatedAt : Date;
}

const reportSchema: Schema<Report> = new Schema({
    sessionId : {
        type : Schema.Types.ObjectId,
        ref : "Session",
        required : true
    }, 
    riskScore : {
        type : Number,
        min : 0,
        max : 5,
        default : 0,
        required : true
    },
    symptoms : {
        type: Schema.Types.Mixed, 
        default: {}
    },
    summary : {
        type : String,
    },
    nextSteps : {
        type : Schema.Types.Mixed,
        default : {}
    }
},
{timestamps : true}
)

const ReportModel =
    (mongoose.models.Report as mongoose.Model<Report>) ||
    mongoose.model<Report>('Report', reportSchema);

export default ReportModel;