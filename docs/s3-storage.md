# S3-Compatible Storage

NyayaVault uses the async S3 API through `aioboto3`. MinIO is the local development backend; private cloud S3 is selected with `STORAGE_PROVIDER=s3`.

## Local MinIO

Run the MinIO services from the repository root:

```powershell
docker compose up -d minio minio-init
```

The bootstrap creates both buckets:

- `nyayavault-documents`: live document and certificate objects
- `nyayavault-canonical`: canonical evidence copies used for restoration

Use these backend settings for local development:

```env
STORAGE_PROVIDER=minio
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_PUBLIC_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
STORAGE_BUCKET=nyayavault-documents
STORAGE_BACKUP_BUCKET=nyayavault-canonical
STORAGE_REGION=us-east-1
STORAGE_SECURE=false
STORAGE_ADDRESSING_STYLE=path
STORAGE_CREATE_BUCKET=false
```

When the backend runs inside Compose, use `http://minio:9000` as the endpoint.

## Cloud S3

Provision the buckets outside FastAPI startup. Keep both buckets private and enable:

- Block Public Access
- versioning on both buckets
- SSE-S3 or SSE-KMS encryption
- retention/Object Lock on the canonical bucket when required by legal policy
- lifecycle rules only after retention requirements are approved

Use an IAM role or workload identity in deployed environments. Static access keys should be limited to local development or a secrets manager.

```env
STORAGE_PROVIDER=s3
STORAGE_ENDPOINT=
STORAGE_ACCESS_KEY=<iam-access-key>
STORAGE_SECRET_KEY=<iam-secret-key>
STORAGE_BUCKET=<live-bucket-name>
STORAGE_BACKUP_BUCKET=<canonical-bucket-name>
STORAGE_REGION=<aws-region>
STORAGE_SECURE=true
STORAGE_ADDRESSING_STYLE=virtual
STORAGE_CREATE_BUCKET=false
STORAGE_PRESIGNED_URL_TTL=300
STORAGE_SSE=aws:kms
STORAGE_KMS_KEY_ID=<kms-key-arn-or-id>
```

The application does not create cloud buckets. The IAM identity needs only the required object permissions for the configured bucket prefixes, including live object reads/writes and controlled canonical writes/reads for restoration.

## Download flow

The backend authorizes the user before issuing a short-lived presigned GET URL. The URL does not make either bucket public. Existing proxy download endpoints remain available for compatibility.

## Integrity behavior

Live objects and canonical objects are stored separately. Tamper simulation modifies only the live object. Restoration reads from the canonical bucket and verifies the SHA-256 hash before reporting success. Missing storage objects are treated as failures; the application does not generate replacement evidence bytes.
