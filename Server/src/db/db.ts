import mongoose from "mongoose";

const connectDB = async () => {
    try {
        const Instance  = await mongoose.connect(process.env.MONGO_URI || "");
        console.log(`MongoDB connected DB Host: ${Instance.connection.host}`);
    } catch (error) {
        console.error("MongoDB Connection Error:", error);
        process.exit(1);
    }
};

export default connectDB;