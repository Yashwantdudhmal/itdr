# AzureHound manual ingestion

This guide describes how to collect Entra ID (Azure AD) data with AzureHound and load it into the BloodHound CE instance that is already running in this workspace. All steps are operator-driven; no credentials are stored in the repo.

## Prerequisites
- Azure tenant access with the ability to consent to the required Microsoft Graph permissions.
- A service principal or user with one of:
  - `Directory.Read.All`, `AuditLog.Read.All`, `Policy.Read.All`, `RoleManagement.Read.All`
  - Or a Global Reader account that can grant those permissions at runtime.
- Docker available on the operator machine (used to run AzureHound without installing .NET).
- The BloodHound UI reachable at `http://localhost:8080/` with an admin account.

## Collect with AzureHound (docker-based)
1. Create an output folder on your host, e.g. `C:\temp\azurehound-output`.
2. Run AzureHound in a container (replace the placeholders in ALL_CAPS):

   ```powershell
   $AzureHoundImage = "ghcr.io/specterops/azurehound:2.2.0"
   $Output = "C:\temp\azurehound-output"
   $Tenant = "<tenant-id-or-domain>"

   docker pull $AzureHoundImage
   docker run --rm -it ^
     -v "$Output:/data" ^
     $AzureHoundImage ^
     collect ^
       --tenant $Tenant ^
       --auth-type devicecode ^
       --output /data
   ```

   - If you prefer an app registration, add: `--client-id <appId> --client-secret <secret>` and ensure the app has the Graph permissions listed above.
   - The command writes BloodHound JSON files into the mapped `C:\temp\azurehound-output` folder.

## Import into BloodHound UI
1. Open `http://localhost:8080/` and sign in as an administrator.
2. Navigate to **Data Import** → **Upload**.
3. Drag-and-drop the AzureHound JSON files (or zip them first and upload the zip). Wait for the UI to show the ingestion completed message.

## Verify data is present
After import, confirm the graph is populated:
- Search for a known user or service principal via the top search bar.
- Open **Analysis** → **Paths** and compute a path from a user to a sensitive asset (e.g., Global Administrator role). If a path renders, the data is connected.
- Check **Administration** → **Data Quality** to ensure collectors show recent timestamps.

## Operational notes
- Keep collector outputs under source control **out of this repo**; treat them as sensitive.
- Rerun AzureHound when permissions or memberships change materially; re-import the new JSON set.
- If ingestion fails, review the BloodHound UI notifications and the `bloodhound-app` container logs for details.
