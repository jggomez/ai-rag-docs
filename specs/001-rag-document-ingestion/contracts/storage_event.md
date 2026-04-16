# Contract: GCS Storage Notification Event

**Type**: Eventarc / Cloud Storage Event
**Format**: JSON

```json
{
  "kind": "storage#object",
  "id": "bucket/folder/subfolder/file.pdf/123",
  "name": "Communications/[CONTRACT_ID]/[FILE_NAME].pdf",
  "bucket": "communications-bucket",
  "metageneration": "1",
  "contentType": "application/pdf",
  "timeCreated": "2026-04-15T22:00:00Z",
  "updated": "2026-04-15T22:00:00Z",
  "size": "1048576"
}
```

## Payload Validation Rules
1. `name` MUST match regex: `^Communications/([^/]+)/(.+)$`
2. `contentType` MUST be one of: `application/pdf`, `text/plain`, `text/markdown`.
3. `size` MUST be less than 50MB (52428800 bytes).
