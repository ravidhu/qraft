---
description: CRM contacts loaded from source
tags: [bronze, crm]
---
SELECT
    id           AS contact_id,
    account_id,
    name         AS contact_name,
    email,
    role
FROM source('crm', 'contacts')
