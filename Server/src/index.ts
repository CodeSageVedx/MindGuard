import app from "./app.ts";
import dotenv from "dotenv";
import connectDB from "./db/db.ts";

dotenv.config({ path: "./.env" });

app.get("/", (req, res) => {
  res.send("Welcome to MindGuardAI API");
});

connectDB()
  .then(() => {
    app.listen(process.env.PORT, () => {
      console.log(`Server is listening at : http://localhost:${process.env.PORT}`);
    });
  })
  .catch((error) => {
    console.log("Database connection error : ", error);
  });