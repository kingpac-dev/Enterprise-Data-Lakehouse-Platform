const databaseName = process.env.MONGO_INITDB_DATABASE || "source_uat";
const appUser = process.env.MONGO_APP_USER || "source_app";
const appPassword = process.env.MONGO_APP_PASSWORD;

if (!appPassword) {
  throw new Error("MONGO_APP_PASSWORD is required");
}

const applicationDatabase = db.getSiblingDB(databaseName);
if (!applicationDatabase.getUser(appUser)) {
  applicationDatabase.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [{ role: "readWrite", db: databaseName }],
  });
}
